# cli-anything-pennylane

Agent-friendly CLI harness for the Pennylane Company API v2.

## Prerequisites

Pennylane is a SaaS backend, so the hard dependency is a valid Company API token:

1. In Pennylane, go to **Settings > Connectivity > Developers**.
2. Generate an API V2 token with the scopes needed for your workflow.
3. Export it before running commands:

```bash
export PENNYLANE_API_TOKEN='...'
```

The production API base URL is `https://app.pennylane.com`.

## Install

```bash
cd /home/zedium/pennylane-cli/agent-harness
pip install -e .
```

## Usage

```bash
cli-anything-pennylane --help
cli-anything-pennylane --json status
cli-anything-pennylane --json auth whoami
cli-anything-pennylane --json operations list
cli-anything-pennylane --json call transactions.list --param limit=20
cli-anything-pennylane --json call transactions.get --id 123
cli-anything-pennylane --json call transactions.update --id 123 --data '{"label":"Updated"}'
cli-anything-pennylane --json files upload ./receipt.pdf
cli-anything-pennylane --json transactions list --limit 100
cli-anything-pennylane --json request GET /api/external/v2/me
```

Legacy resource commands remain available:

```bash
cli-anything-pennylane --json resource list
cli-anything-pennylane --json resource get customers --param limit=20
cli-anything-pennylane --json resource post products --data '{"name":"Consulting"}'
```

With no arguments, the CLI starts a REPL.

## OpenAPI operation coverage

The CLI ships an OpenAPI-derived operation registry generated from Pennylane's `accounting.json` specification. It covers all visible Company API operations at generation time: 159 unique method/path operations, plus ergonomic aliases.

Use `operations list` to discover names, then `call` to execute any operation. `call` supports:

- `--id` and `--path-param key=value` for path templates
- `--param key=value` for query params
- `--data` / `--data-file` for JSON bodies
- `--file field=path` / `--field key=value` for multipart uploads
- `--dry-run` for request inspection

## JSON output

Use `--json` for all agent workflows. API responses include:

- `ok`
- `status`
- `data`
- `rate_limit.limit`, `rate_limit.remaining`, `rate_limit.reset`

Errors return `ok: false` and a clear error message.

## Session

Local session metadata is stored at `~/.config/cli-anything-pennylane/session.json` by default. Tokens are **not** written to disk; store them in an environment variable.

```bash
cli-anything-pennylane auth login --token-env PENNYLANE_API_TOKEN --base-url https://app.pennylane.com
```

## Tests

```bash
cd /home/zedium/pennylane-cli/agent-harness
python -m pytest cli_anything/pennylane/tests -v -s
CLI_ANYTHING_FORCE_INSTALLED=1 python -m pytest cli_anything/pennylane/tests -v -s
```

The E2E suite uses a local Pennylane-compatible HTTP server so tests can verify real HTTP requests, auth headers, JSON parsing, rate-limit headers, and subprocess behavior without using a private production token.
