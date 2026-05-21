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

### Recommended Profiles

> **These profiles are optional context-window optimizations, not capability
> boundaries.** The server can do everything its tools allow regardless of how
> it is started. A profile only changes which schemas are advertised to the
> client at `tools/list` time. The default (no `--toolsets`) is **full
> coverage** — pick a profile only to shrink the LLM context when you know
> the session is scoped to a specific area, and add `--tools <names>` to pull
> in extra tools without changing profile.
>
> Anything not in the active profile is still reachable via two escape hatches
> that we recommend keeping enabled:
> 1. `salesforce_rest_request` (toolset `data`) — call any
>    `/services/data` REST API, including Connect endpoints.
> 2. `invoke_revenue_cloud_action` (toolset `actions`) — invoke any standard
>    action by API name, even one not represented as a typed tool.
>
> If you are not sure whether a profile is hiding something you need, run with
> the default (no `--toolsets`) and the LLM will see the full inventory.

The profiles below are sized so that nothing the server *cannot* fall back to
gets dropped: `data` and `diagnostics` are always recommended.

| Profile name | `--toolsets` | What it is for | What it deliberately drops (still reachable via escape hatches) |
|---|---|---|---|
| Full (default) | *(omit the flag)* | Discovery sessions, exploratory work, agents that switch context. **Recommended when in doubt.** | nothing |
| Telco lifecycle | `assets,orders,context,data,diagnostics` | MH-07 / MH-08 amend / cancel / renew / transfer flows on Asset+Order. | Billing, CPQ headless configurator, Approvals, Catalog inspection. |
| Billing & Payments | `billing,context,data,diagnostics` | Invoicing, payment application, dunning support; v66 actions plus the v67 Billing license set. | Asset lifecycle, Orders orchestration, CPQ, Approvals. |
| Quote-to-Cash | `orders,pricing,context,assets,data,diagnostics` | End-to-end Quote → Order → Asset → renewal. | Billing/Payments, Approvals, Headless Configurator. |
| Catalog & Pricing | `catalog,pricing,data,diagnostics` | Read-mostly: product lookup, qualification, pricing context bootstrap. | Order/Asset mutations, Billing, Approvals. |
| Approvals | `approvals,data,diagnostics` | Cancel / recall / review / override / reassign approval work items. | Everything else. |
| Headless CPQ | `cpq_headless,context,data,diagnostics` | Configurator session over Connect REST + pricing context. | Asset lifecycle, Orders mutations, Billing. |
| Read-only audit | `data,diagnostics` | SOQL/REST exploration + org readiness. No `actions/standard` invocation tools. | All mutation tools. To re-enable a single one without changing profile, add e.g. `--tools invoke_revenue_cloud_action` or `--tools createOrderFromQuote`. |

A few pragmatic notes:

- `core` is always on. `list_revenue_cloud_actions` and
  `describe_revenue_cloud_action` work in every profile, so the LLM can see
  what the **registry** knows about, even if a typed tool is hidden.
- `diagnostics` adds `list_available_standard_actions` and
  `revenue_cloud_org_readiness`, the canonical way to ask Salesforce *itself*
  which actions are exposed in the org. The readiness tool also segregates
  actions that are missing because of the API version / Billing license
  (`missing_v67_or_billing_actions`) from ones that are genuinely missing
  for other reasons. We recommend keeping `diagnostics` on in every profile.
- A profile is additive: missing one tool? `--tools createOrderFromQuote`
  layers it on top of any profile.
- The full registry is documented in the **Tool Coverage** section below; that
  is the source of truth for what this server can do, not a profile.
- Some Billing/Payments and freeze/unfreeze actions are tagged
  `since: 67.0` in the registry: they require both API v67.0 (Summer '26+)
  and a Salesforce Billing license. On older orgs they describe to 404 and
  invoke to `INSUFFICIENT_ACCESS`. Run `revenue_cloud_org_readiness` to see
  the exact set unavailable on the current target org.

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

These wrappers were validated against `/connect/*` endpoints and use the
exact field names the Salesforce server expects. Pass IDs (not names),
otherwise the API returns `JSON_PARSER_ERROR` on unrecognized fields.

- `hydrate_pricing_context` — POST `/connect/core-pricing/pricing`. Required
  inputs: `context_definition_id`, `context_mapping_id`, `pricing_procedure_id`,
  `json_data_string`. The endpoint requires **IDs**: query
  `SELECT Id, DeveloperName FROM ContextDefinition` and the matching
  `ContextMapping` / `PricingProcedure` records first. Use it to obtain a
  hydrated `contextId` to feed downstream tools that fail with
  `NO_CONTEXT_RUNTIME_FOUND` on raw standard records.
- `place_sales_transaction` — POST `/connect/rev/sales-transaction/actions/place`.
  The endpoint accepts only a `contextDetails` object at the top level. The
  wrapper takes `context_id` and builds `{"contextDetails":{"contextId": ...}}`.
  Pass `body` to override entirely (advanced).
- `assign_revenue_cloud_usage` — INSERT `AppUsageAssignment` to mark a record
  as `RevenueLifecycleManagement`. Required to unlock asset lifecycle (amend,
  cancel, transfer) on orders that were created without the RLM flag.

### Headless Configurator (CPQ)

Wrappers over `/connect/cpq/configurator/actions/*`. All accept the same
context fields: `transaction_id`, `transaction_line_id`, `record_id`,
`correlation_id`. Use `body` to override entirely when you need to send
the full payload (e.g. for `cpq_set_product_quantity` you typically pass
`body` with `productId` / `quantity` / attributes).

- `cpq_configure`, `cpq_load_instance`, `cpq_save_instance`,
  `cpq_set_product_quantity`, `cpq_add_nodes`, `cpq_update_nodes`,
  `cpq_delete_nodes`.

### Standard Salesforce Approvals (not Revenue Cloud-native)

The `cancelApprovalSubmission` / `recallApprovalSubmission` /
`reviewApprovalWorkItem` / `overrideApprovalWorkItem` /
`reassignApprovalWorkItem` tools target Revenue Cloud's own
`ApprovalSubmission` (prefix `9j8`) and `ApprovalWorkItem` (`9jR`) records.

For the platform-wide Approval Process (`ProcessInstanceWorkitem` prefix
`04i`) use the REST escape hatch:

```jsonc
salesforce_rest_request({
  "method": "POST",
  "path": "process/approvals",
  "body": {"requests": [{"actionType": "Approve", "contextId": "04i...", "comments": "ok"}]}
})
```

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
