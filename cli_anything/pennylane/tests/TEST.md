# Pennylane CLI Test Plan

## Test Inventory Plan

- `test_core.py`: 8 unit tests planned.
- `test_full_e2e.py`: 6 E2E/subprocess tests planned.

## Unit Test Plan

### `core/endpoints.py`
- Verify registered endpoint metadata includes high-value resources.
- Verify endpoint path construction with IDs and nested subpaths.
- Verify unknown endpoint errors are explicit.
- Expected: 3 tests.

### `core/session.py`
- Verify default session values.
- Verify locked JSON save/load round-trip.
- Verify history auto-save and dry-run suppression.
- Expected: 3 tests.

### `utils/pennylane_backend.py`
- Verify missing token fails loudly with setup guidance.
- Verify query/body handling against an API-compatible test server.
- Expected: 2 tests.

## E2E Test Plan

The E2E suite runs against a real local HTTP backend implementing Pennylane-compatible response shapes. It verifies that the CLI sends actual HTTP requests, uses Bearer authentication, parses JSON, preserves rate-limit headers, handles errors, and works as an installed subprocess command.

- `auth whoami` calls `/api/external/v2/me` and verifies user/company data.
- `resource get customers` calls `/api/external/v2/customers` with cursor-style list data.
- `resource post products` sends a JSON body and receives a created product.
- `request GET /api/external/v2/me` exercises the raw path escape hatch.
- Subprocess tests invoke `cli-anything-pennylane` through `_resolve_cli()`.

## Realistic Workflow Scenarios

### Customer data inspection
- Simulates: an agent retrieving customers before creating invoices.
- Operations chained: `status` → `auth whoami` → `resource get customers --param limit=20`.
- Verified: token presence, auth header, list response structure, rate-limit metadata.

### Product creation dry run and POST
- Simulates: an agent preparing a catalog item for invoicing.
- Operations chained: parse JSON payload → POST to `products` → inspect created resource.
- Verified: request body, response ID/name, status code, subprocess behavior.

### Raw API escape hatch
- Simulates: using newly released Pennylane endpoints before the registry is updated.
- Operations chained: `request GET <path>`.
- Verified: arbitrary paths are accepted and parsed.

---

# Test Results

Command run:

```bash
cd /home/zedium/pennylane-cli/agent-harness
CLI_ANYTHING_FORCE_INSTALLED=1 python -m pytest cli_anything/pennylane/tests -v -s --tb=no
```

Output:

```text
============================= test session starts ==============================
platform linux -- Python 3.10.4, pytest-9.0.3, pluggy-1.6.0
rootdir: /home/zedium/pennylane-cli/agent-harness
[_resolve_cli] Using installed command: /home/zedium/.pyenv/shims/cli-anything-pennylane
collected 14 items

cli_anything/pennylane/tests/test_core.py::test_endpoint_registry_contains_common_resources PASSED
cli_anything/pennylane/tests/test_core.py::test_endpoint_path_with_id_and_subpath PASSED
cli_anything/pennylane/tests/test_core.py::test_endpoint_path_unknown_is_explicit PASSED
cli_anything/pennylane/tests/test_core.py::test_session_defaults PASSED
cli_anything/pennylane/tests/test_core.py::test_session_save_load_roundtrip PASSED
cli_anything/pennylane/tests/test_core.py::test_session_record_dry_run_does_not_create_file PASSED
cli_anything/pennylane/tests/test_core.py::test_require_token_missing PASSED
cli_anything/pennylane/tests/test_core.py::test_request_json_sends_bearer_and_body PASSED
cli_anything/pennylane/tests/test_full_e2e.py::TestCLISubprocess::test_help PASSED
cli_anything/pennylane/tests/test_full_e2e.py::TestCLISubprocess::test_status_json PASSED
cli_anything/pennylane/tests/test_full_e2e.py::TestCLISubprocess::test_auth_whoami_real_http PASSED
  API: http://127.0.0.1:<port>/api/external/v2/me (status 200)
cli_anything/pennylane/tests/test_full_e2e.py::TestCLISubprocess::test_resource_get_customers_real_http PASSED
  API: http://127.0.0.1:<port>/api/external/v2/customers?limit=20 (customers 1)
cli_anything/pennylane/tests/test_full_e2e.py::TestCLISubprocess::test_resource_post_products_real_http PASSED
  API: http://127.0.0.1:<port>/api/external/v2/products (created 99)
cli_anything/pennylane/tests/test_full_e2e.py::TestCLISubprocess::test_request_raw_path_real_http PASSED

============================== 14 passed in 4.20s ==============================
```

## Summary Statistics

- Total tests: 14
- Passed: 14
- Failed: 0
- Pass rate: 100%
- Installed-command mode: verified with `CLI_ANYTHING_FORCE_INSTALLED=1`

## Coverage Notes

- Tests verify real HTTP transport against a Pennylane-compatible backend, including auth headers, JSON bodies, rate-limit headers, and subprocess invocation.
- Production Pennylane API calls require a private token and are documented but not executed in CI to avoid mutating real accounting data.
