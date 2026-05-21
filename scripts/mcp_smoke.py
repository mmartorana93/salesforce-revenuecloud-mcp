#!/usr/bin/env python3
"""Local smoke tests for the Revenue Cloud MCP server."""

import json
import subprocess
import sys


def rpc(proc, req):
    proc.stdin.write(json.dumps(req) + "\n")
    proc.stdin.flush()
    line = proc.stdout.readline()
    if not line:
        raise AssertionError("server closed stdout")
    msg = json.loads(line)
    if "error" in msg:
        raise AssertionError(msg["error"])
    return msg["result"]


def framed_rpc(proc, req):
    payload = json.dumps(req).encode("utf-8")
    proc.stdin.write(b"Content-Length: %d\r\n\r\n" % len(payload))
    proc.stdin.write(payload)
    proc.stdin.flush()
    header = b""
    while b"\r\n\r\n" not in header:
        b = proc.stdout.read(1)
        if not b:
            raise AssertionError("server closed stdout")
        header += b
    length = None
    for line in header.decode("ascii", "replace").split("\r\n"):
        if line.lower().startswith("content-length:"):
            length = int(line.split(":", 1)[1].strip())
            break
    if length is None:
        raise AssertionError("missing Content-Length")
    msg = json.loads(proc.stdout.read(length).decode("utf-8"))
    if "error" in msg:
        raise AssertionError(msg["error"])
    return msg["result"]


def start_server(extra_args=None):
    cmd = [sys.executable, "-m", "revenuecloud_mcp.server"]
    if extra_args:
        cmd.extend(extra_args)
    return subprocess.Popen(
        cmd,
        text=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def main():
    proc = start_server()
    try:
        init = rpc(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        assert init["serverInfo"]["name"] == "revenuecloud-mcp"
        tools = rpc(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["tools"]
        names = {t["name"] for t in tools}
        required = {
            "createContract",
            "createOrderFromQuote",
            "createOrUpdateAssetFromOrder",
            "initiateAmendment",
            "initiateCancellation",
            "initiateRenewal",
            "initiateTransfer",
            "initiateRollBackLastAction",
            "createServiceDocument",
            "getMultipleProductDetails",
            "executeQualificationProcedure",
            "runConfigRules",
            "runSalesforcePricing",
            "rateUsageRecords",
            "processConsumptionOverages",
            "salesforce_rest_request",
            "soql_query",
        }
        missing = sorted(required - names)
        assert not missing, missing
        info = rpc(proc, {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "server_info", "arguments": {}}})
        assert info["content"][0]["type"] == "text"
        listed = rpc(
            proc,
            {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "list_revenue_cloud_actions", "arguments": {}}},
        )
        assert "createContract" in listed["content"][0]["text"]
    finally:
        proc.kill()
        proc.wait()

    proc = subprocess.Popen(
        [sys.executable, "-m", "revenuecloud_mcp.server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        init = framed_rpc(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        assert init["serverInfo"]["name"] == "revenuecloud-mcp"
        framed_tools = framed_rpc(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["tools"]
        assert len(framed_tools) == len(tools)
    finally:
        proc.kill()
        proc.wait()

    proc = start_server(["--toolsets", "data", "--tools", "createContract"])
    try:
        rpc(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        filtered = rpc(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["tools"]
        filtered_names = {t["name"] for t in filtered}
        assert "soql_query" in filtered_names
        assert "salesforce_rest_request" in filtered_names
        assert "createContract" in filtered_names
        assert "initiateRenewal" not in filtered_names
        assert len(filtered_names) < len(tools)
    finally:
        proc.kill()
        proc.wait()

    proc = start_server(["--orgs", "sandbox-only"])
    try:
        rpc(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        proc.stdin.write(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "soql_query",
                        "arguments": {"target_org": "blocked-org", "query": "SELECT Id FROM User LIMIT 1"},
                    },
                }
            )
            + "\n"
        )
        proc.stdin.flush()
        line = proc.stdout.readline()
        msg = json.loads(line)
        assert "error" in msg, "allowlist should reject blocked-org"
        assert "allowlist" in msg["error"]["message"], msg["error"]["message"]
    finally:
        proc.kill()
        proc.wait()

    print("smoke ok: %d tools, line+framed transports, filter+allowlist" % len(tools))


if __name__ == "__main__":
    main()
