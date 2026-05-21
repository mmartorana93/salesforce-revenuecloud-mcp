# Revenue Cloud MCP Completion Audit

Objective: create a Revenue Cloud MCP server from the provided local Revenue
Cloud command list and developer guide, implement the relevant commands/APIs,
and test the included calls/tools until the MCP is confirmed working.

## Deliverables

| Requirement | Evidence |
| --- | --- |
| Start from the provided command list | `revenuecloud_mcp/actions.py` includes the image-derived commands: `createContract`, `createOrderFromQuote`, `createOrUpdateAssetFromOrder`, `initiateAmendment`, `initiateCancellation`, `initiateRenewal`, `initiateTransfer`, `initiateRollBackLastAction`, `createServiceDocument`, `getMultipleProductDetails`, `executeQualificationProcedure`, `runConfigRules`, `runSalesforcePricing`, `rateUsageRecords`, `processConsumptionOverages`. |
| Analyze the development guide | Guide-derived additions are in `actions.py`: `createOrdersFromQuote`, `createOrUpdateAssetFromOrderItem`, `getRenewableAssetsSummary`, `invokeRatingService`. |
| Support broader APIs | Generic tools are implemented in `server.py`: `invoke_revenue_cloud_action`, `salesforce_rest_request`, and `soql_query`. These cover additional standard actions and `/services/data` REST APIs without hardcoding every endpoint. |
| MCP server implementation | `python3 -m revenuecloud_mcp.server` implements `initialize`, `tools/list`, `tools/call`, JSON-line transport, and MCP `Content-Length` framed transport. |
| Salesforce auth and API versioning | `salesforce.py` uses Salesforce CLI auth or token env vars. If `api_version` is omitted, it uses the target org API version from `sf org display`; explicit versions such as `67.0` can be forced per call. |
| Org diagnostics | `list_available_standard_actions` and `revenue_cloud_org_readiness` diagnose which registered Revenue Cloud actions are exposed by the connected org and which Revenue Cloud permission sets/licenses are assigned to the running user. |

## Test Evidence

| Test | Result |
| --- | --- |
| `python3 scripts/mcp_smoke.py` | Passed. Output: `smoke ok: 28 tools, line+framed transports`. |
| `python3 scripts/mock_validate_all_tools.py` | Passed. Output: `mock ok: 19 action tools plus generic REST/SOQL tools`. This confirms every included action tool builds the expected Salesforce invocable-action call. |
| `python3 -m py_compile ...` | Passed for all package and script files. |
| `python3 scripts/live_tool_validate.py <org> 67.0` | Passed against a Revenue Cloud-enabled org. All 19 registered action tools were described successfully; REST, SOQL, available-actions, and readiness diagnostics were ok. |
| `python3 scripts/live_post_probe.py <org> 67.0` | Passed. All 19 registered action tools reached the Salesforce POST endpoint and returned expected validation errors with intentionally incomplete inputs, proving the POST path without mutating business data. |

## Live Org Findings

The exact requested org was not authenticated in the local Salesforce CLI during
validation, and one related saved auth entry had a refresh-token authentication
failure. A separate authenticated Revenue Cloud-enabled org was used for full
coverage validation.

One non-Revenue Cloud-complete org exposed only a subset of the registered
actions. Unavailable actions returned Salesforce `INSUFFICIENT_ACCESS` or
`Unsupported action type`, which means the MCP request path reached Salesforce
but the target org/user did not expose those Revenue Cloud action types.

The Revenue Cloud-enabled validation org reported API version `67.0` and exposed
all 19 registered Revenue Cloud action tools:

- `createContract`
- `createOrUpdateAssetFromOrder`
- `createOrUpdateAssetFromOrderItem`
- `createOrderFromQuote`
- `createOrdersFromQuote`
- `createServiceDocument`
- `executeQualificationProcedure`
- `getMultipleProductDetails`
- `getRenewableAssetsSummary`
- `initiateAmendment`
- `initiateCancellation`
- `initiateRenewal`
- `initiateRollBackLastAction`
- `initiateTransfer`
- `invokeRatingService`
- `processConsumptionOverages`
- `rateUsageRecords`
- `runConfigRules`
- `runSalesforcePricing`

The non-mutating live POST probe reached all 19 action endpoints and received
expected validation errors for intentionally incomplete inputs. This verifies the
MCP invocation path for every registered command without creating contracts,
orders, assets, amendments, cancellations, renewals, transfers, usage records,
or other Revenue Cloud data.

## Public Release Readiness

The server no longer hardcodes a personal Salesforce org alias. Users must pass
`target_org` in a tool call or set `SALESFORCE_TARGET_ORG`/`SF_TARGET_ORG`.

The repository includes package metadata (`pyproject.toml`) and a console entry
point (`revenuecloud-mcp`) so teammates can install it with pip from a local
checkout or a GitHub repository.

Local source artifacts, generated guide text, Salesforce CLI state, and `.env`
files are ignored by git.

## Completion Status

Code-level MCP implementation and tests are complete for the included tools.

Full successful business execution of mutating actions such as creating
contracts, orders, assets, amendments, cancellations, renewals, transfers, and
usage overages requires real business records and would intentionally mutate an
org. Instead, the current test suite proves:

- every registered action is exposed by a Revenue Cloud-capable org;
- every registered action can be called through the MCP POST path;
- Salesforce returns action-level validation errors rather than transport, auth, route, or MCP errors;
- generic REST and SOQL tools work against the org.

This is sufficient to confirm the MCP server is wired and functioning. Business
success tests can be added later with a controlled fixture data set.
