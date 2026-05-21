"""Revenue Cloud action registry derived from the local guide and source image."""

DEFAULT_API_VERSION = "65.0"
DEFAULT_TARGET_ORG = None

TARGET_ORG_DESCRIPTION = (
    "Salesforce org alias or username. Defaults to SALESFORCE_TARGET_ORG or SF_TARGET_ORG."
)

CONTROL_FIELDS = {
    "input",
    "inputs",
    "target_org",
    "api_version",
    "validate_only",
}


ACTION_REGISTRY = {
    "createContract": {
        "domain": "Transaction Management",
        "api_name": "createContract",
        "since": "60.0",
        "description": "Create a contract from a quote or order.",
        "required": ["sourceId"],
        "optional": ["contractPriceOption"],
        "properties": {
            "sourceId": {"type": "string", "description": "ID of the quote or order."},
            "contractPriceOption": {
                "type": "string",
                "description": "CONTRACT_HEADER_ONLY, NET_UNIT_PRICE_ONLY, or DISCOUNT_ONLY.",
            },
        },
    },
    "createOrderFromQuote": {
        "domain": "Transaction Management",
        "api_name": "createOrderFromQuote",
        "since": "60.0",
        "description": "Create an order from a quote record.",
        "required": ["quoteRecordId"],
        "optional": [],
        "properties": {
            "quoteRecordId": {"type": "string", "description": "ID of the quote record."},
        },
    },
    "createOrdersFromQuote": {
        "domain": "Transaction Management",
        "api_name": "createOrdersFromQuote",
        "since": "65.0",
        "description": "Create multiple orders from a single quote.",
        "required": [],
        "optional": [],
        "properties": {},
    },
    "createOrUpdateAssetFromOrder": {
        "domain": "Transaction Management",
        "api_name": "createOrUpdateAssetFromOrder",
        "since": "60.0",
        "description": "Create or update assets for all order items in an order.",
        "required": ["orderId"],
        "optional": [],
        "properties": {
            "orderId": {"type": "string", "description": "ID of the order."},
        },
    },
    "createOrUpdateAssetFromOrderItem": {
        "domain": "Transaction Management",
        "api_name": "createOrUpdateAssetFromOrderItem",
        "since": "60.0",
        "description": "Create or update assets from individual order items.",
        "required": ["orderItemIds"],
        "optional": [],
        "properties": {
            "orderItemIds": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Order item IDs to assetize.",
            },
        },
    },
    "getRenewableAssetsSummary": {
        "domain": "Transaction Management",
        "api_name": "getRenewableAssetsSummary",
        "since": "64.0",
        "description": "Retrieve renewable asset details for an order.",
        "required": [],
        "optional": [],
        "properties": {},
    },
    "initiateAmendment": {
        "domain": "Transaction Management",
        "api_name": "initiateAmendment",
        "since": "60.0",
        "description": "Initiate and execute an asset amendment.",
        "required": ["amendAssetIds", "amendStartDate", "amendOutputType", "quantityChange"],
        "optional": ["amendContractId", "amendOpportunityId", "skipPricing"],
        "properties": {
            "amendAssetIds": {"type": "array", "items": {"type": "string"}},
            "amendStartDate": {"type": "string", "description": "ISO datetime."},
            "amendOutputType": {"type": "string", "description": "Quote or Order."},
            "quantityChange": {"type": "number"},
            "amendContractId": {"type": "string"},
            "amendOpportunityId": {"type": "string"},
            "skipPricing": {"type": "boolean"},
        },
    },
    "initiateCancellation": {
        "domain": "Transaction Management",
        "api_name": "initiateCancellation",
        "since": "60.0",
        "description": "Initiate and execute an asset cancellation.",
        "required": ["cancelAssetIds", "cancelStartDate", "cancelOutputType"],
        "optional": ["cancelContractId", "cancelOpportunityId", "skipPricing"],
        "properties": {
            "cancelAssetIds": {"type": "array", "items": {"type": "string"}},
            "cancelStartDate": {"type": "string", "description": "ISO datetime."},
            "cancelOutputType": {"type": "string", "description": "Quote or Order."},
            "cancelContractId": {"type": "string"},
            "cancelOpportunityId": {"type": "string"},
            "skipPricing": {"type": "boolean"},
        },
    },
    "initiateRenewal": {
        "domain": "Transaction Management",
        "api_name": "initiateRenewal",
        "since": "60.0",
        "description": "Initiate and execute an asset renewal.",
        "required": ["renewAssetIds", "renewOutputType"],
        "optional": ["renewContractId", "renewOpportunityId", "renewStartDate", "renewEndDate", "skipPricing"],
        "properties": {
            "renewAssetIds": {"type": "array", "items": {"type": "string"}},
            "renewOutputType": {"type": "string", "description": "Quote or Order."},
            "renewContractId": {"type": "string"},
            "renewOpportunityId": {"type": "string"},
            "renewStartDate": {"type": "string", "description": "ISO datetime."},
            "renewEndDate": {"type": "string", "description": "ISO datetime."},
            "skipPricing": {"type": "boolean"},
        },
    },
    "initiateRollBackLastAction": {
        "domain": "Transaction Management",
        "api_name": "initiateRollBackLastAction",
        "since": "65.0",
        "description": "Reverse the last future-dated amendment or renewal on assets.",
        "required": ["assetIds", "outputType"],
        "optional": [],
        "properties": {
            "assetIds": {"type": "array", "items": {"type": "string"}},
            "outputType": {"type": "string", "description": "Quote or Order."},
        },
    },
    "initiateTransfer": {
        "domain": "Transaction Management",
        "api_name": "initiateTransfer",
        "since": "65.0",
        "description": "Transfer assets from one account to another.",
        "required": ["transferRecords", "transferDate", "targetAccountId", "outputRecordType"],
        "optional": ["targetContractId", "shouldSkipPricing"],
        "properties": {
            "transferRecords": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Records with assetId and transferQuantity.",
            },
            "transferDate": {"type": "string", "description": "ISO datetime."},
            "targetAccountId": {"type": "string"},
            "targetContractId": {"type": "string"},
            "outputRecordType": {"type": "string", "description": "Quote or Order."},
            "shouldSkipPricing": {"type": "boolean"},
        },
    },
    "executeQualificationProcedure": {
        "domain": "Product Catalog Management",
        "api_name": "executeQualificationProcedure",
        "since": "64.0",
        "description": "Execute qualification for specified products.",
        "required": ["productIds"],
        "optional": [
            "additionalContextData",
            "contextDefinitionName",
            "contextMappingName",
            "correlationId",
            "qualificationProcedureName",
            "userContextInputRepresentation",
        ],
        "properties": {
            "productIds": {"type": "array", "items": {"type": "string"}},
            "additionalContextData": {"type": "object"},
            "contextDefinitionName": {"type": "string"},
            "contextMappingName": {"type": "string"},
            "correlationId": {"type": "string"},
            "qualificationProcedureName": {"type": "string"},
            "userContextInputRepresentation": {"type": "object"},
        },
    },
    "getMultipleProductDetails": {
        "domain": "Product Catalog Management",
        "api_name": "getMultipleProductDetails",
        "since": "64.0",
        "description": "Get details for a list of products.",
        "required": ["productDataInputs"],
        "optional": [
            "additionalContextData",
            "additionalFields",
            "catalogId",
            "contextDefinitionName",
            "contextMappingName",
            "correlationId",
            "currencyCode",
            "enablePricing",
            "enableQualificationProcedure",
            "priceBookId",
            "pricingProcedureName",
            "qualificationProcedureName",
            "userContextInputRepresentation",
        ],
        "properties": {
            "productDataInputs": {"type": "object", "description": "BulkProductDetailsInputBodyList."},
            "additionalContextData": {"type": "object"},
            "additionalFields": {"type": "object"},
            "catalogId": {"type": "string"},
            "contextDefinitionName": {"type": "string"},
            "contextMappingName": {"type": "string"},
            "correlationId": {"type": "string"},
            "currencyCode": {"type": "string"},
            "enablePricing": {"type": "boolean"},
            "enableQualificationProcedure": {"type": "boolean"},
            "priceBookId": {"type": "string"},
            "pricingProcedureName": {"type": "string"},
            "qualificationProcedureName": {"type": "string"},
            "userContextInputRepresentation": {"type": "object"},
        },
    },
    "runSalesforcePricing": {
        "domain": "Salesforce Pricing",
        "api_name": "runSalesforcePricing",
        "since": "60.0",
        "description": "Invoke Salesforce Pricing by context and pricing procedure.",
        "required": ["contextInstanceId", "pricingProcedureName"],
        "optional": ["discoveryProcedure", "effectiveDate", "isDeveloperName", "isSkipWaterfall", "skipDiscovery"],
        "properties": {
            "contextInstanceId": {"type": "string"},
            "pricingProcedureName": {"type": "string"},
            "discoveryProcedure": {"type": "string"},
            "effectiveDate": {"type": "string", "description": "ISO datetime."},
            "isDeveloperName": {"type": "boolean"},
            "isSkipWaterfall": {"type": "boolean"},
            "skipDiscovery": {"type": "boolean"},
        },
    },
    "runConfigRules": {
        "domain": "Product Configurator",
        "api_name": "runConfigRules",
        "since": "65.0",
        "description": "Run product configuration rules for a transaction.",
        "required": ["transactionId"],
        "optional": ["transactionContextId"],
        "properties": {
            "transactionId": {"type": "string"},
            "transactionContextId": {"type": "string"},
        },
    },
    "invokeRatingService": {
        "domain": "Rate Management",
        "api_name": "invokeRatingService",
        "since": "62.0",
        "description": "Rate usage records through the rating service.",
        "required": ["recordID", "contextDefinitionId"],
        "optional": [
            "attributeRateCardID",
            "baseRateCardID",
            "contextMappingID",
            "isSkipWaterfall",
            "procedureName",
            "tierRateCardID",
        ],
        "properties": {
            "recordID": {"type": "string", "description": "Usage ratable summary record ID."},
            "recordIDs": {"type": "string", "description": "Alias used by examples in the guide."},
            "contextDefinitionId": {"type": "string"},
            "contextMappingID": {"type": "string"},
            "contextMappingId": {"type": "string"},
            "procedureName": {"type": "string"},
            "isSkipWaterfall": {"type": "boolean"},
            "baseRateCardID": {"type": "string"},
            "tierRateCardID": {"type": "string"},
            "attributeRateCardID": {"type": "string"},
        },
    },
    "rateUsageRecords": {
        "domain": "Rate Management",
        "api_name": "invokeRatingService",
        "since": "62.0",
        "description": "Image command alias for invokeRatingService.",
        "required": ["recordID", "contextDefinitionId"],
        "optional": [
            "attributeRateCardID",
            "baseRateCardID",
            "contextMappingID",
            "isSkipWaterfall",
            "procedureName",
            "tierRateCardID",
        ],
        "properties": {},
    },
    "processConsumptionOverages": {
        "domain": "Usage Management",
        "api_name": "processConsumptionOverages",
        "since": "63.0",
        "description": "Process overages for a usage ratable summary record.",
        "required": ["usageRatableSummaryId"],
        "optional": [],
        "properties": {
            "usageRatableSummaryId": {"type": "string"},
        },
    },
    "createServiceDocument": {
        "domain": "Transaction Management",
        "api_name": "createServiceDocument",
        "since": None,
        "description": "Create service documents from a record and service document template.",
        "required": ["recordId", "templateId"],
        "optional": ["title", "locale", "documentType", "pdfReportId"],
        "properties": {
            "recordId": {"type": "string", "description": "ID of the record to print."},
            "templateId": {"type": "string", "description": "ID of the flexipage service document template."},
            "title": {"type": "string", "description": "Document title."},
            "locale": {"type": "string", "description": "Locale used to create the document."},
            "documentType": {"type": "string", "description": "Feature document type."},
            "pdfReportId": {"type": "string", "description": "Existing PDF report ID, when applicable."},
        },
    },
}


def action_names():
    return sorted(ACTION_REGISTRY.keys())


def action_metadata(name):
    meta = ACTION_REGISTRY.get(name)
    if not meta:
        raise KeyError("Unknown Revenue Cloud action: %s" % name)
    merged = dict(meta)
    if not merged.get("properties") and merged["api_name"] in ACTION_REGISTRY:
        merged["properties"] = ACTION_REGISTRY[merged["api_name"]].get("properties", {})
    return merged


def action_input_schema(name):
    meta = action_metadata(name)
    properties = {
        "target_org": {
            "type": "string",
            "description": TARGET_ORG_DESCRIPTION,
        },
        "api_version": {
            "type": "string",
            "description": "Salesforce API version without leading v. Defaults to the target org API version reported by Salesforce CLI.",
        },
        "validate_only": {
            "type": "boolean",
            "description": "If true, describe the action endpoint instead of executing POST.",
        },
        "input": {
            "type": "object",
            "description": "Single invocable action input object. If omitted, direct fields are collected into one input.",
        },
        "inputs": {
            "type": "array",
            "items": {"type": "object"},
            "description": "Raw Salesforce invocable action inputs array.",
        },
    }
    properties.update(meta.get("properties", {}))
    return {
        "type": "object",
        "properties": properties,
        "additionalProperties": True,
    }
