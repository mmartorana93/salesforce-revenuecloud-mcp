"""Runtime configuration: toolset filtering and org allowlist."""

import argparse
import os


CORE_TOOLS = frozenset(
    {
        "server_info",
        "list_revenue_cloud_actions",
        "describe_revenue_cloud_action",
    }
)

DATA_TOOLS = frozenset({"soql_query", "salesforce_rest_request"})

DIAGNOSTICS_TOOLS = frozenset(
    {
        "validate_revenue_cloud_actions",
        "list_available_standard_actions",
        "revenue_cloud_org_readiness",
    }
)

GENERIC_ACTION_TOOLS = frozenset({"invoke_revenue_cloud_action"})

CONTEXT_TOOLS = frozenset(
    {
        "hydrate_pricing_context",
        "place_sales_transaction",
        "assign_revenue_cloud_usage",
    }
)

CPQ_HEADLESS_TOOLS = frozenset(
    {
        "cpq_configure",
        "cpq_load_instance",
        "cpq_save_instance",
        "cpq_set_product_quantity",
        "cpq_add_nodes",
        "cpq_update_nodes",
        "cpq_delete_nodes",
    }
)

# Tool names that belong to a domain-specific toolset are derived from the
# action registry by domain (see domain_toolset_filter).
DOMAIN_TOOLSETS = {
    "billing": {"Billing", "Payments"},
    "orders": {"Orders", "Transaction Management"},
    "approvals": {"Approvals"},
    "assets": {"Transaction Management"},
    "catalog": {"Product Catalog Management"},
    "pricing": {"Salesforce Pricing", "Product Configurator"},
    "usage": {"Usage Management", "Rate Management"},
}

KNOWN_TOOLSETS = (
    "core",
    "actions",
    "diagnostics",
    "data",
    "context",
    "cpq_headless",
    "billing",
    "orders",
    "approvals",
    "assets",
    "catalog",
    "pricing",
    "usage",
    "all",
)

ALLOW_ALL_ORGS = "ALLOW_ALL_ORGS"
DEFAULT_TARGET_ORG_TOKEN = "DEFAULT_TARGET_ORG"

_RUNTIME_CONFIG = None


def _split_csv(value):
    if not value:
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog="revenuecloud-mcp", add_help=False)
    parser.add_argument("--toolsets", default=None)
    parser.add_argument("--tools", default=None)
    parser.add_argument("--orgs", default=None)
    args, _ = parser.parse_known_args(argv)
    return args


def load_config(argv=None, env=None):
    env = env if env is not None else os.environ
    args = parse_args(argv)
    return {
        "toolsets": _split_csv(args.toolsets) or _split_csv(env.get("REVENUECLOUD_TOOLSETS")),
        "tools": _split_csv(args.tools) or _split_csv(env.get("REVENUECLOUD_TOOLS")),
        "orgs": _split_csv(args.orgs) or _split_csv(env.get("REVENUECLOUD_ORGS")),
    }


def set_runtime_config(config):
    global _RUNTIME_CONFIG
    _RUNTIME_CONFIG = config


def get_runtime_config():
    return _RUNTIME_CONFIG or {}


def resolve_enabled_tools(config, all_tool_names, action_tool_names, action_domains=None):
    """Return the set of tool names enabled given the active filter.

    action_domains: optional dict mapping action tool name -> domain string. Used to
    resolve domain-aware toolsets (billing, orders, approvals, ...).
    """
    toolsets = [t.lower() for t in (config.get("toolsets") or [])]
    explicit = list(config.get("tools") or [])
    action_domains = action_domains or {}

    if not toolsets and not explicit:
        return set(all_tool_names)

    if "all" in toolsets:
        return set(all_tool_names)

    enabled = set(CORE_TOOLS)
    for ts in toolsets:
        if ts == "core":
            continue
        if ts == "actions":
            enabled.update(GENERIC_ACTION_TOOLS)
            enabled.update(action_tool_names)
        elif ts == "diagnostics":
            enabled.update(DIAGNOSTICS_TOOLS)
        elif ts == "data":
            enabled.update(DATA_TOOLS)
        elif ts == "context":
            enabled.update(CONTEXT_TOOLS)
        elif ts == "cpq_headless":
            enabled.update(CPQ_HEADLESS_TOOLS)
            enabled.update(GENERIC_ACTION_TOOLS)
            for tool_name, domain in action_domains.items():
                if domain in {"Salesforce Pricing", "Product Configurator"}:
                    enabled.add(tool_name)
        elif ts in DOMAIN_TOOLSETS:
            wanted = DOMAIN_TOOLSETS[ts]
            enabled.update(GENERIC_ACTION_TOOLS)
            for tool_name, domain in action_domains.items():
                if domain in wanted:
                    enabled.add(tool_name)
    enabled.update(explicit)
    return enabled & set(all_tool_names)


def org_allowlist(config=None):
    config = config if config is not None else get_runtime_config()
    return list(config.get("orgs") or [])


def is_org_allowed(target, allowlist, is_default=False):
    if not allowlist:
        return True
    if ALLOW_ALL_ORGS in allowlist:
        return True
    if is_default and DEFAULT_TARGET_ORG_TOKEN in allowlist:
        return True
    return target in allowlist
