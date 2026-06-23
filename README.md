# cli-anything-pennylane

Agent-friendly CLI for the Pennylane Company API v2.

This project was built with [CLI-Anything](https://github.com/HKUDS/CLI-Anything). It follows the CLI-Anything harness pattern to expose a remote SaaS backend as a predictable command-line interface for humans and coding agents.

## Status

- Pennylane OpenAPI source: <https://pennylane.readme.io/openapi/accounting.json>
- Current registry coverage: **160/160 visible OpenAPI method/path operations**
- Registry entries including ergonomic aliases: **182**
- Raw escape hatch for unsupported or newly added endpoints: `request METHOD PATH`

## Requirements

- Python 3.10+
- A Pennylane Company API v2 token

Create a token in Pennylane from **Settings > Connectivity > Developers**, then export it:

```bash
export PENNYLANE_API_TOKEN='your-token'
```

## Install

```bash
pip install -e .
```

## Quick usage

```bash
cli-anything-pennylane --help
cli-anything-pennylane --json status
cli-anything-pennylane --json auth whoami
cli-anything-pennylane --json operations list
```

Call any OpenAPI-covered operation:

```bash
cli-anything-pennylane --json call transactions.list --param limit=20
cli-anything-pennylane --json call transactions.get --id 123
cli-anything-pennylane --json call transactions.update --id 123 --data '{"label":"Updated"}'
```

Upload a file attachment:

```bash
cli-anything-pennylane --json files upload ./receipt.pdf
```

Use convenience aliases for common resources:

```bash
cli-anything-pennylane --json transactions list --limit 100
cli-anything-pennylane --json transactions get 123
```

Use the raw request escape hatch when needed:

```bash
cli-anything-pennylane --json request GET /api/external/v2/me
```

## Authentication and session

The CLI reads the token from `PENNYLANE_API_TOKEN` by default. You can also store local session metadata:

```bash
cli-anything-pennylane auth login \
  --token-env PENNYLANE_API_TOKEN \
  --base-url https://app.pennylane.com
```

The session stores the environment variable name and base URL, not the token value.

## Operation discovery

List all registered operations:

```bash
cli-anything-pennylane --json operations list
```

Filter by OpenAPI tag:

```bash
cli-anything-pennylane --json operations list --tag "Customer Invoices"
```

The universal `call` command supports:

- `--id` for a path parameter named `{id}`
- `--path-param key=value` for other path parameters
- `--param key=value` for query parameters
- `--data` or `--data-file` for JSON bodies
- `--file field=path` and `--field key=value` for multipart uploads
- `--dry-run` to inspect the request without sending it

## Regenerate the OpenAPI registry

```bash
python scripts/generate_openapi_registry.py
python -m pytest cli_anything/pennylane/tests -q
```

The generator fetches Pennylane's current OpenAPI document and writes:

```text
cli_anything/pennylane/core/generated_operations.py
```

## Tests

```bash
python -m pytest cli_anything/pennylane/tests -q
```

The test suite uses a local Pennylane-compatible HTTP server for integration-style checks, so it does not require a production token.

## Safety notes

- Do not commit API tokens.
- Use `--dry-run` before mutating calls when unsure.
- Accounting, billing, payment, tax, and legal actions should remain human-reviewed.
