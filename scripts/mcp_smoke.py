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
            # New tools
            "hydrate_pricing_context",
            "place_sales_transaction",
            "assign_revenue_cloud_usage",
            "cpq_configure",
            "cpq_load_instance",
            "cpq_save_instance",
            "cpq_set_product_quantity",
            "cpq_add_nodes",
            "cpq_update_nodes",
            "cpq_delete_nodes",
            "decomposeSalesTransaction",
            "orchestrateSalesTransaction",
            "orchestrateTransaction",
            "submitSalesTransaction",
            "freezeSalesTransaction",
            "unfreezeSalesTransaction",
            "runSalesforceHeadlessPricing",
            "invokeSummaryCreationService",
            "refreshUsageEntitlementBucket",
            "retriggerEntlCreaProc",
            "cancelApprovalSubmission",
            "recallApprovalSubmission",
            "reviewApprovalWorkItem",
            "overrideApprovalWorkItem",
            "reassignApprovalWorkItem",
            "applyPaymentsAndCreditsByRules",
            "blngSvcSuspendBilling",
            "blngSvcExtendInvoiceDueDate",
            "createInvoiceFromFulfillmentOrder",
            "postDraftInvoice",
            "applyPayment",
            "writeOffInvoices",
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

    # Test domain-aware toolsets: billing should expose Billing+Payments actions only
    proc = start_server(["--toolsets", "billing"])
    try:
        rpc(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        billing = {t["name"] for t in rpc(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["tools"]}
        assert "postDraftInvoice" in billing
        assert "applyPayment" in billing
        assert "blngSvcSuspendBilling" in billing
        assert "createOrderFromQuote" not in billing
        assert "soql_query" not in billing
    finally:
        proc.kill()
        proc.wait()

    # Test toolset 'context' exposes the new Connect tools
    proc = start_server(["--toolsets", "context"])
    try:
        rpc(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        ctx_tools = {t["name"] for t in rpc(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["tools"]}
        assert "hydrate_pricing_context" in ctx_tools
        assert "place_sales_transaction" in ctx_tools
        assert "assign_revenue_cloud_usage" in ctx_tools
        assert "postDraftInvoice" not in ctx_tools
    finally:
        proc.kill()
        proc.wait()

    # Test productDataInputs alias normalization in invoke_revenue_cloud_action
    # We don't actually contact Salesforce, just verify the alias path doesn't crash on shape.
    proc = start_server()
    try:
        rpc(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        # Just verify the tool exposes 'productData' in its schema
        tools_resp = rpc(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["tools"]
        gmpd = next(t for t in tools_resp if t["name"] == "getMultipleProductDetails")
        props = gmpd["inputSchema"]["properties"]
        assert "productData" in props, "schema should expose productData"
        assert "productDataInputs" in props, "schema should expose productDataInputs alias"
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
