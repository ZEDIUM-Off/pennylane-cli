# Pennylane CLI Harness Analysis

## Source

The user supplied Pennylane's LLM documentation index: `https://pennylane.readme.io/llms.txt`.
Pennylane is not a local GUI application; it is a SaaS accounting platform with a documented Company API v2. This harness therefore maps the cli-anything backend pattern to the real remote backend: HTTPS calls to `https://app.pennylane.com/api/external/v2` authenticated with a required Bearer token.

## Backend Engine

- Real backend: Pennylane Company API v2.
- Base URL: `https://app.pennylane.com`.
- Authentication: `Authorization: Bearer <Company API token>`.
- Hard dependency: a valid Pennylane Company API token with the scopes required by each endpoint.
- Rate limit: 25 requests per 5 seconds per token; 429 responses include `retry-after` and rate-limit headers.

## Data Model

- JSON resources exposed by Pennylane API v2: customers, products, invoices, quotes, ledger accounts, ledger entries, journals, categories, transactions, exports, and file attachments.
- Cursor pagination on list endpoints (`cursor`, `limit`, `has_more`, `next_cursor`).
- Filters are passed as JSON strings in the `filter` query parameter.

## CLI Architecture

- `auth`: stores session metadata and validates token with `/me`.
- `resource`: registry-driven common resources (`list`, `get`, `post`).
- `request`: raw escape hatch for any API path/method.
- `status`: cheap local introspection.
- REPL is the default when no subcommand is provided.

## Safety

- The token is not written to disk by default. The session stores only the token environment variable name.
- Mutating commands support `--dry-run` where practical.
- API errors fail loudly with status, body, and actionable auth/scope guidance.
