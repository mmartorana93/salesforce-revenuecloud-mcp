#!/usr/bin/env python3
"""Deterministic tests for every Revenue Cloud MCP tool without Salesforce side effects."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import revenuecloud_mcp.server as server
from revenuecloud_mcp.actions import action_metadata, action_names


SAMPLES = {
    "createContract": {"sourceId": "0Q0xx0000000001", "contractPriceOption": "NET_UNIT_PRICE_ONLY"},
    "createOrderFromQuote": {"quoteRecordId": "0Q0xx0000000001"},
    "createOrdersFromQuote": {"quoteRecordId": "0Q0xx0000000001"},
    "createOrUpdateAssetFromOrder": {"orderId": "801xx0000000001"},
    "createOrUpdateAssetFromOrderItem": {"orderItemIds": ["802xx0000000001"]},
    "getRenewableAssetsSummary": {"orderId": "801xx0000000001"},
    "initiateAmendment": {
        "amendAssetIds": ["02ixx0000000001"],
        "amendStartDate": "2026-01-01T00:00:00.000Z",
        "amendOutputType": "Quote",
        "quantityChange": 1,
    },
    "initiateCancellation": {
        "cancelAssetIds": ["02ixx0000000001"],
        "cancelStartDate": "2026-01-01T00:00:00.000Z",
        "cancelOutputType": "Quote",
    },
    "initiateRenewal": {"renewAssetIds": ["02ixx0000000001"], "renewOutputType": "Quote"},
    "initiateRollBackLastAction": {"assetIds": ["02ixx0000000001"], "outputType": "Quote"},
    "initiateTransfer": {
        "transferRecords": [{"assetId": "02ixx0000000001", "transferQuantity": 1}],
        "transferDate": "2026-01-01T00:00:00.000Z",
        "targetAccountId": "001xx0000000001",
        "outputRecordType": "Quote",
    },
    "executeQualificationProcedure": {"productIds": ["01txx0000000001"]},
    "getMultipleProductDetails": {"productDataInputs": {"productData": [{"productId": "01txx0000000001"}]}},
    "runSalesforcePricing": {"contextInstanceId": "ctx-1", "pricingProcedureName": "PricingProcedure"},
    "runConfigRules": {"transactionId": "0Q0xx0000000001"},
    "invokeRatingService": {"recordID": "56jxx0000000001", "contextDefinitionId": "11Oxx0000000001"},
    "rateUsageRecords": {"recordID": "56jxx0000000001", "contextDefinitionId": "11Oxx0000000001"},
    "processConsumptionOverages": {"usageRatableSummaryId": "3ttxx0000000001"},
    "createServiceDocument": {"recordId": "0WOxx0000000001", "templateId": "0M0xx0000000001"},
}


def main():
    calls = []

    def fake_describe(action_name, target_org=None, api_version=None):
        calls.append(("describe", action_name, target_org, api_version))
        return {"ok": True, "status": 200, "body": {"name": action_name}}

    def fake_invoke(action_name, inputs, target_org=None, api_version=None):
        calls.append(("invoke", action_name, inputs, target_org, api_version))
        return {"ok": True, "status": 200, "body": {"actionName": action_name, "inputs": inputs}}

    def fake_rest(method, path, body=None, query=None, target_org=None, api_version=None):
        calls.append(("rest", method, path, body, query, target_org, api_version))
        if path == "actions/standard":
            return {
                "ok": True,
                "status": 200,
                "targetOrg": target_org,
                "username": "mock@example.com",
                "body": {
                    "actions": [
                        {"name": action_metadata(name)["api_name"], "label": name, "type": name.upper()}
                        for name in action_names()
                    ]
                },
            }
        return {"ok": True, "status": 200, "targetOrg": target_org, "username": "mock@example.com", "body": {"path": path}}

    def fake_query(query, target_org=None, api_version=None, tooling=False):
        calls.append(("query", query, target_org, api_version, tooling))
        return {"ok": True, "status": 200, "body": {"records": []}}

    server.describe_action = fake_describe
    server.invoke_action = fake_invoke
    server.rest_request = fake_rest
    server.query_soql = fake_query

    listed = {tool["name"] for tool in server.tools_list()}
    for name in action_names():
        assert name in listed, "%s not exposed in tools/list" % name
        meta = action_metadata(name)
        assert "api_name" in meta and meta["api_name"], "%s missing api_name" % name
        assert name in SAMPLES, "%s missing test sample" % name

        result = server.call_tool(name, dict(SAMPLES[name]))
        assert result["ok"] is True, result
        kind, api_name, inputs = calls[-1][0], calls[-1][1], calls[-1][2]
        assert kind == "invoke", calls[-1]
        assert api_name == meta["api_name"], calls[-1]
        assert isinstance(inputs, list) and isinstance(inputs[0], dict), calls[-1]

        result = server.call_tool(name, {"validate_only": True})
        assert result["ok"] is True, result
        assert calls[-1][0] == "describe", calls[-1]

    generic = server.call_tool(
        "invoke_revenue_cloud_action",
        {"action_name": "createContract", "inputs": [{"sourceId": "0Q0xx0000000001"}]},
    )
    assert generic["ok"] is True
    assert calls[-1][0] == "invoke" and calls[-1][1] == "createContract"

    described = server.call_tool("describe_revenue_cloud_action", {"action_name": "createContract", "live": True})
    assert described["salesforce"]["ok"] is True

    validated = server.call_tool("validate_revenue_cloud_actions", {})
    assert len(validated) == len(action_names())
    assert all(item["ok"] for item in validated)

    available = server.call_tool("list_available_standard_actions", {"filter": "contract"})
    assert available["ok"] is True and available["count"] >= 1

    readiness = server.call_tool("revenue_cloud_org_readiness", {})
    assert readiness["ok"] is True
    assert readiness["summary"]["available_action_tools"] == len(action_names())

    rest = server.call_tool("salesforce_rest_request", {"method": "GET", "path": "query", "query": {"q": "SELECT Id FROM Account"}})
    assert rest["ok"] is True

    soql = server.call_tool("soql_query", {"query": "SELECT Id FROM Account LIMIT 1"})
    assert soql["ok"] is True

    print("mock ok: %d action tools plus generic REST/SOQL tools" % len(action_names()))


if __name__ == "__main__":
    main()
