#!/usr/bin/env python3
"""Validate every exposed action tool through MCP without executing mutations."""

import json
import os
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from revenuecloud_mcp.actions import action_names


def rpc(proc, req):
    proc.stdin.write(json.dumps(req) + "\n")
    proc.stdin.flush()
    line = proc.stdout.readline()
    if not line:
        err = proc.stderr.read()
        raise AssertionError("server closed stdout: %s" % err)
    msg = json.loads(line)
    if "error" in msg:
        raise AssertionError(msg["error"])
    return msg["result"]


def main():
    target_org = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SALESFORCE_TARGET_ORG") or os.environ.get("SF_TARGET_ORG")
    api_version = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("SALESFORCE_API_VERSION")
    if not target_org:
        raise SystemExit("Usage: live_tool_validate.py <target-org> [api-version] or set SALESFORCE_TARGET_ORG.")
    proc = subprocess.Popen(
        [sys.executable, "-m", "revenuecloud_mcp.server"],
        text=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        rpc(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        results = []
        next_id = 2
        for name in action_names():
            res = rpc(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": next_id,
                    "method": "tools/call",
                    "params": {
                        "name": name,
                        "arguments": {
                            key: value
                            for key, value in {
                                "target_org": target_org,
                                "api_version": api_version,
                                "validate_only": True,
                            }.items()
                            if value is not None
                        },
                    },
                },
            )
            next_id += 1
            body = json.loads(res["content"][0]["text"])
            results.append(
                {
                    "tool": name,
                    "ok": body.get("ok"),
                    "status": body.get("status"),
                    "unsupported_by_org": body.get("status") == 400
                    and "Unsupported action type" in json.dumps(body.get("body")),
                }
            )

        soql = rpc(
            proc,
            {
                "jsonrpc": "2.0",
                "id": next_id,
                "method": "tools/call",
                "params": {
                    "name": "soql_query",
                    "arguments": {
                        "target_org": target_org,
                        "query": "SELECT Id, Name FROM Organization LIMIT 1",
                        **({"api_version": api_version} if api_version else {}),
                    },
                },
            },
        )
        next_id += 1
        rest = rpc(
            proc,
            {
                "jsonrpc": "2.0",
                "id": next_id,
                "method": "tools/call",
                "params": {
                    "name": "salesforce_rest_request",
                    "arguments": {
                        "target_org": target_org,
                        "method": "GET",
                        "path": "/services/data/v%s/" % api_version if api_version else "",
                        **({"api_version": api_version} if api_version else {}),
                    },
                },
            },
        )
        next_id += 1
        available = rpc(
            proc,
            {
                "jsonrpc": "2.0",
                "id": next_id,
                "method": "tools/call",
                "params": {
                    "name": "list_available_standard_actions",
                    "arguments": {
                        "target_org": target_org,
                        "filter": "product",
                        **({"api_version": api_version} if api_version else {}),
                    },
                },
            },
        )
        next_id += 1
        readiness = rpc(
            proc,
            {
                "jsonrpc": "2.0",
                "id": next_id,
                "method": "tools/call",
                "params": {
                    "name": "revenue_cloud_org_readiness",
                    "arguments": {
                        "target_org": target_org,
                        **({"api_version": api_version} if api_version else {}),
                    },
                },
            },
        )

        failed = [r for r in results if not r["ok"] and not r["unsupported_by_org"]]
        available_body = json.loads(available["content"][0]["text"])
        readiness_body = json.loads(readiness["content"][0]["text"])
        report = {
            "target_org": target_org,
            "api_version": api_version or "target org default",
            "tool_count": len(results),
            "described": len([r for r in results if r["ok"]]),
            "unsupported_by_org": len([r for r in results if r["unsupported_by_org"]]),
            "failed": len(failed),
            "action_tools": results,
            "soql_ok": json.loads(soql["content"][0]["text"]).get("ok"),
            "rest_ok": json.loads(rest["content"][0]["text"]).get("ok"),
            "available_standard_actions_ok": available_body.get("ok"),
            "revenue_cloud_org_readiness_ok": readiness_body.get("ok"),
            "revenue_cloud_org_readiness_summary": readiness_body.get("summary"),
        }
        print(json.dumps(report, indent=2))
        if (
            failed
            or not report["soql_ok"]
            or not report["rest_ok"]
            or not report["available_standard_actions_ok"]
            or not report["revenue_cloud_org_readiness_ok"]
        ):
            sys.exit(2)
    finally:
        proc.kill()
        proc.wait()


if __name__ == "__main__":
    main()
