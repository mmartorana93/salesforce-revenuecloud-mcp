# Revenue Cloud MCP

Minimal MCP server for Salesforce Revenue Cloud standard actions and related
Salesforce REST APIs.

The server is intended to run locally on a developer machine and authenticate to
Salesforce through the Salesforce CLI, or through access-token environment
variables supplied by the MCP client.

## Requirements

- Python 3.9+
- Salesforce CLI (`sf`)
- An authenticated Salesforce org with the needed Revenue Cloud features enabled

Authenticate an org before using the server:

```bash
sf org login web --alias my-revenue-cloud-org
```

## Install

From a local checkout:

```bash
python3 -m pip install .
```

From GitHub:

```bash
python3 -m pip install "git+https://github.com/mmartorana93/salesforce-revenuecloud-mcp.git"
```

You can also run directly from the source checkout:

```bash
python3 -m revenuecloud_mcp.server
```

## MCP Configuration

Installed package:

```json
{
  "mcpServers": {
    "revenuecloud": {
      "command": "revenuecloud-mcp",
      "env": {
        "SALESFORCE_TARGET_ORG": "my-revenue-cloud-org"
      }
    }
  }
}
```

Source checkout:

```json
{
  "mcpServers": {
    "revenuecloud": {
      "command": "python3",
      "args": ["-m", "revenuecloud_mcp.server"],
      "cwd": "/path/to/revenuecloud-mcp",
      "env": {
        "SALESFORCE_TARGET_ORG": "my-revenue-cloud-org"
      }
    }
  }
}
```

The server does not hardcode a target org. Pass `target_org` in a tool call, or
set `SALESFORCE_TARGET_ORG` or `SF_TARGET_ORG`.

## Toolset Filtering

By default the server registers all tools. To reduce LLM context, restrict the
tools that are exposed via flags or env vars.

CLI flags (passed in `args`):

- `--toolsets <list>`: comma-separated. `core` is always implicit. Recognized:
  - `actions` — every Revenue Cloud standard action plus `invoke_revenue_cloud_action`.
  - `diagnostics` — `validate_revenue_cloud_actions`, `list_available_standard_actions`, `revenue_cloud_org_readiness`.
  - `data` — `soql_query`, `salesforce_rest_request`.
  - `context` — `hydrate_pricing_context`, `place_sales_transaction`, `assign_revenue_cloud_usage`.
  - `cpq_headless` — Configurator REST tools plus pricing/configurator actions.
  - Domain-aware groups (filter actions by registry `domain`): `billing`, `orders`, `approvals`, `assets`, `catalog`, `pricing`, `usage`.
  - `all` — every tool.
- `--tools <list>`: comma-separated tool names enabled in addition to any toolsets.

Environment variables (used when the matching CLI flag is omitted):

- `REVENUECLOUD_TOOLSETS`
- `REVENUECLOUD_TOOLS`

Example: only billing + diagnostics, plus the bootstrap context helpers:

```json
{
  "mcpServers": {
    "revenuecloud": {
      "command": "revenuecloud-mcp",
      "args": ["--toolsets", "billing,diagnostics,context"]
    }
  }
}
```

If neither flag nor env var is set, all tools are enabled (current default).

## Multi-Org Allowlist

By default the server accepts any `target_org` (resolved per call from
parameter, env var, or Salesforce CLI default). Restrict which orgs can be
targeted by passing an allowlist.

CLI flag:

- `--orgs <list>`: comma-separated aliases/usernames. Two reserved tokens are
  supported: `ALLOW_ALL_ORGS` (no restriction) and `DEFAULT_TARGET_ORG`
  (allows the CLI default org when no explicit `target_org` is given).

Environment variable: `REVENUECLOUD_ORGS`.

Example: lock the server to two known sandboxes plus the CLI default:

```json
{
  "mcpServers": {
    "revenuecloud": {
      "command": "revenuecloud-mcp",
      "args": ["--orgs", "DEFAULT_TARGET_ORG,sandbox-uat,sandbox-dev"]
    }
  }
}
```

Any tool call passing a `target_org` outside the allowlist is rejected before
contacting Salesforce.

If `api_version` is omitted, the server uses the API version reported by
`sf org display` for the target org, then falls back to `65.0`. You can still
force a version per call, for example `"api_version": "67.0"`.

Token-based auth is also supported with `SF_ACCESS_TOKEN` or
`SALESFORCE_ACCESS_TOKEN` plus `SF_INSTANCE_URL` or `SALESFORCE_INSTANCE_URL`.

## Tool Coverage

### Transaction Management & Assets
`createContract`, `createOrderFromQuote`, `createOrdersFromQuote`,
`createOrUpdateAssetFromOrder`, `createOrUpdateAssetFromOrderItem`,
`getRenewableAssetsSummary`, `initiateAmendment`, `initiateCancellation`,
`initiateRenewal`, `initiateRollBackLastAction`, `initiateTransfer`,
`createServiceDocument`.

### Orders / Orchestration (v66+)
`decomposeSalesTransaction`, `orchestrateSalesTransaction`, `orchestrateTransaction`,
`submitSalesTransaction`, `freezeSalesTransaction` (v67), `unfreezeSalesTransaction` (v67).

### Catalog / CPQ / Pricing
`executeQualificationProcedure`, `getMultipleProductDetails`,
`runSalesforcePricing`, `runConfigRules`, `runSalesforceHeadlessPricing`,
`invokeSummaryCreationService`.

### Approvals
`cancelApprovalSubmission`, `recallApprovalSubmission`, `reviewApprovalWorkItem`,
`overrideApprovalWorkItem`, `reassignApprovalWorkItem`, `getPreviousRelaRecDetails`.

### Usage & Rating
`invokeRatingService`, `rateUsageRecords`, `processConsumptionOverages`,
`refreshUsageEntitlementBucket`, `retriggerEntlCreaProc`.

### Billing & Payments
General-availability: `applyPaymentsAndCreditsByRules`,
`blngSvcExtendInvoiceDueDate`, `blngSvcSuspendBilling`, `blngSvcUpdateBillToContact`,
`createInvoiceFromChangeOrders`, `createInvoiceFromFulfillmentOrder`.
Requires Salesforce Billing license + v67.0: `postDraftInvoice`,
`postDraftInvoiceBatchRun`, `postDraftCreditMemo`, `voidPostedCreditMemo`,
`generateInvoiceDocuments`, `applyCredit`, `applyPayment`, `unapplyPayment`,
`unapplyCredit`, `paymentSale`, `writeOffInvoices`, `generateAccountStatement`,
`createBillingSchedulesFromBillingTransaction`, `recoverBillingSchedules`.

### Context bootstrap (Connect REST)
- `hydrate_pricing_context` — POST `/connect/core-pricing/pricing` to attach a
  Revenue Cloud `ContextDefinition` to a Quote/Order and return its
  `contextInstanceId` (use it to feed `runSalesforcePricing` and other tools
  that fail with `NO_CONTEXT_RUNTIME_FOUND` on raw standard records).
- `place_sales_transaction` — POST `/connect/rev/sales-transaction/actions/place`
  to place + price + decompose a sales transaction in one call.
- `assign_revenue_cloud_usage` — INSERT `AppUsageAssignment` to mark a record
  as `RevenueLifecycleManagement`. Required to unlock asset lifecycle (amend,
  cancel, transfer) on orders that were created without the RLM flag.

### Headless Configurator (CPQ)
`cpq_configure`, `cpq_load_instance`, `cpq_save_instance`,
`cpq_set_product_quantity`, `cpq_add_nodes`, `cpq_update_nodes`,
`cpq_delete_nodes` — wrappers over `/connect/cpq/configurator/actions/*`.

### Generic / diagnostics
- `invoke_revenue_cloud_action` — invoke any Salesforce standard action with raw `inputs`.
- `salesforce_rest_request` — call any `/services/data` REST API path.
- `soql_query` — query org data through REST.
- `validate_revenue_cloud_actions` — non-mutating GET validation for every registered action endpoint.
- `list_available_standard_actions` — list action endpoints exposed by the target org.
- `revenue_cloud_org_readiness` — compare registered action coverage with the target org's exposed actions and assigned Revenue Cloud permission sets/licenses.

Specific action tools accept one of these shapes:

```json
{"sourceId": "0Q0...", "contractPriceOption": "NET_UNIT_PRICE_ONLY"}
```

```json
{"input": {"sourceId": "0Q0..."}}
```

```json
{"inputs": [{"sourceId": "0Q0..."}]}
```

Add `"validate_only": true` to describe the Salesforce endpoint instead of
executing the action.

## Tests

Local, non-Salesforce tests:

```bash
python3 scripts/mcp_smoke.py
python3 scripts/mock_validate_all_tools.py
```

Live non-mutating validation against an authenticated org:

```bash
python3 scripts/live_validate.py my-revenue-cloud-org
python3 scripts/live_tool_validate.py my-revenue-cloud-org
```

Optional live POST probe:

```bash
python3 scripts/live_post_probe.py my-revenue-cloud-org
```

`live_post_probe.py` sends intentionally incomplete inputs to each action.
Expected Salesforce validation errors prove the MCP POST path reaches the
actions without providing real business IDs that could create or mutate records.

## Source Notes

The action registry was built from a local Revenue Cloud command list image and
the Salesforce Revenue Cloud Developer Guide. Those source artifacts are not
required at runtime and are intentionally ignored by git.
