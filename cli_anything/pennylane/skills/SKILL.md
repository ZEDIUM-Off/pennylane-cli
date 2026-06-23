---
name: "cli-anything-pennylane"
description: "Use Pennylane Company API v2 agentically from a CLI: auth checks, resource listing/get/post, raw requests, JSON output, and REPL."
---

# cli-anything-pennylane

Agent-friendly CLI for Pennylane Company API v2.

## Prerequisites

- A Pennylane Company API token from **Settings > Connectivity > Developers**.
- Token scopes matching the requested resources.
- Export the token before use:

```bash
export PENNYLANE_API_TOKEN='...'
```

Production base URL: `https://app.pennylane.com`.

## Command shape

```bash
cli-anything-pennylane [--json] [--base-url URL] [--token TOKEN] COMMAND ...
```

With no command, the CLI opens a REPL.

## Commands

- `status` — local session status; no API call.
- `auth login` — configure base URL and token environment variable name. Does not store token on disk.
- `auth whoami` — call `/api/external/v2/me` to verify auth and identify user/company.
- `operations list [--tag TAG]` — show OpenAPI-derived operations covered by the CLI.
- `call OPERATION [--id ID] [--path-param k=v] [--param k=v] [--data JSON|--data-file FILE] [--file field=path] [--field k=v] [--dry-run]` — call any OpenAPI-covered operation.
- `files upload FILE [--filename NAME]` — upload a multipart file attachment.
- `transactions list|get` — short aliases for common transaction workflows.
- `resource list` — show the legacy built-in resource registry.
- `resource get ENDPOINT [--id ID] [--subpath PATH] [--param k=v]` — GET a legacy registered resource.
- `resource post|put|delete ENDPOINT ...` — mutate a legacy registered resource.
- `request METHOD PATH [--param k=v] [--data JSON|--data-file FILE]` — raw escape hatch for any Pennylane API path.

## Common examples

```bash
cli-anything-pennylane --json status
cli-anything-pennylane --json auth whoami
cli-anything-pennylane --json operations list
cli-anything-pennylane --json call transactions.list --param limit=20
cli-anything-pennylane --json call transactions.get --id 123
cli-anything-pennylane --json call transactions.update --id 123 --data '{"label":"Updated"}'
cli-anything-pennylane --json files upload ./receipt.pdf
cli-anything-pennylane --json transactions list --limit 100
cli-anything-pennylane --json resource get customers --param limit=20
cli-anything-pennylane --json request GET /api/external/v2/me
```

## Agent guidance

Always use `--json`. Prefer `operations list` + `call` for full OpenAPI coverage; legacy `resource` commands are kept for compatibility. Check `ok`, `status`, and `rate_limit` in responses. For list endpoints, inspect `data.has_more` and `data.next_cursor`. Pass filters as JSON strings via `--param`, e.g. `--param 'filter=[{"field":"name","operator":"start_with","value":"AC"}]'`.

Errors are explicit: `401` means missing/invalid token, `403` means insufficient scope, `429` means rate limit.
