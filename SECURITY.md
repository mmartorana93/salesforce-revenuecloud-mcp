# Security

This project should not contain Salesforce credentials, access tokens, refresh
tokens, org-specific usernames, or machine-local absolute paths.

Use Salesforce CLI authentication for normal local development:

```bash
sf org login web --alias my-revenue-cloud-org
```

For token-based MCP deployments, provide credentials through environment
variables only:

- `SF_ACCESS_TOKEN` or `SALESFORCE_ACCESS_TOKEN`
- `SF_INSTANCE_URL` or `SALESFORCE_INSTANCE_URL`

Do not commit `.env`, `.sf`, `.sfdx`, logs, or generated local audit files.
