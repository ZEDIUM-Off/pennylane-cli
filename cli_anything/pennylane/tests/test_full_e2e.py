import json
import os
import shutil
import subprocess
import sys
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer


def _resolve_cli(name):
    """Resolve installed CLI command; falls back to python -m for dev.

    Set env CLI_ANYTHING_FORCE_INSTALLED=1 to require the installed command.
    """
    force = os.environ.get("CLI_ANYTHING_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        print(f"[_resolve_cli] Using installed command: {path}")
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    module = (
        name.replace("cli-anything-", "cli_anything.")
        + "."
        + name.split("-")[-1]
        + "_cli"
    )
    print(f"[_resolve_cli] Falling back to: {sys.executable} -m {module}")
    return [sys.executable, "-m", module]


@contextmanager
def api_server():
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status, payload):
            self.send_response(status)
            self.send_header("content-type", "application/json")
            self.send_header("ratelimit-limit", "25")
            self.send_header("ratelimit-remaining", "23")
            self.send_header("ratelimit-reset", "1770379510")
            self.end_headers()
            self.wfile.write(json.dumps(payload).encode())

        def _record(self, body=None):
            calls.append(
                {
                    "method": self.command,
                    "path": self.path,
                    "authorization": self.headers.get("authorization"),
                    "body": body,
                }
            )

        def do_GET(self):
            self._record()
            if self.headers.get("authorization") != "Bearer test-token":
                self._send(401, {"message": "unauthorized"})
                return
            if self.path.startswith("/api/external/v2/me"):
                self._send(
                    200,
                    {
                        "user": {"id": 1, "email": "agent@example.com"},
                        "company": {"id": 2, "name": "Sandbox"},
                    },
                )
                return
            if self.path.startswith("/api/external/v2/customers"):
                self._send(
                    200,
                    {
                        "has_more": False,
                        "next_cursor": None,
                        "items": [
                            {"id": 42, "name": "ACME", "customer_type": "company"}
                        ],
                    },
                )
                return
            self._send(404, {"message": "not found"})

        def do_POST(self):
            body = self.rfile.read(
                int(self.headers.get("content-length", "0"))
            ).decode()
            self._record(body)
            if self.path.startswith("/api/external/v2/products"):
                payload = json.loads(body)
                self._send(201, {"id": 99, "name": payload["name"]})
                return
            self._send(404, {"message": "not found"})

        def log_message(self, format, *args):  # noqa: A002
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", calls
    finally:
        server.shutdown()
        thread.join(timeout=2)


class TestCLISubprocess:
    CLI_BASE = _resolve_cli("cli-anything-pennylane")

    def _run(self, args, env=None, check=True):
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        return subprocess.run(
            self.CLI_BASE + args,
            capture_output=True,
            text=True,
            check=check,
            env=merged_env,
        )

    def test_help(self):
        result = self._run(["--help"])
        assert result.returncode == 0
        assert "Pennylane" in result.stdout

    def test_status_json(self):
        with api_server() as (base_url, _calls):
            result = self._run(
                ["--json", "--base-url", base_url, "status"],
                env={"PENNYLANE_API_TOKEN": "test-token"},
            )
            data = json.loads(result.stdout)
            assert data["token_present"] is True
            assert data["base_url"] == base_url

    def test_auth_whoami_real_http(self):
        with api_server() as (base_url, calls):
            result = self._run(
                ["--json", "--base-url", base_url, "auth", "whoami"],
                env={"PENNYLANE_API_TOKEN": "test-token"},
            )
            data = json.loads(result.stdout)
            assert data["ok"] is True
            assert data["data"]["company"]["name"] == "Sandbox"
            assert calls[-1]["authorization"] == "Bearer test-token"
            print(f"\n  API: {base_url}/api/external/v2/me (status {data['status']})")

    def test_resource_get_customers_real_http(self):
        with api_server() as (base_url, calls):
            result = self._run(
                [
                    "--json",
                    "--base-url",
                    base_url,
                    "resource",
                    "get",
                    "customers",
                    "--param",
                    "limit=20",
                ],
                env={"PENNYLANE_API_TOKEN": "test-token"},
            )
            data = json.loads(result.stdout)
            assert data["data"]["items"][0]["name"] == "ACME"
            assert "limit=20" in calls[-1]["path"]
            assert data["rate_limit"]["limit"] == "25"
            print(
                f"\n  API: {base_url}{calls[-1]['path']} (customers {len(data['data']['items'])})"
            )

    def test_resource_post_products_real_http(self):
        with api_server() as (base_url, calls):
            result = self._run(
                [
                    "--json",
                    "--base-url",
                    base_url,
                    "resource",
                    "post",
                    "products",
                    "--data",
                    '{"name":"Consulting"}',
                ],
                env={"PENNYLANE_API_TOKEN": "test-token"},
            )
            data = json.loads(result.stdout)
            assert data["status"] == 201
            assert data["data"]["name"] == "Consulting"
            assert json.loads(calls[-1]["body"])["name"] == "Consulting"
            print(
                f"\n  API: {base_url}/api/external/v2/products (created {data['data']['id']})"
            )

    def test_request_raw_path_real_http(self):
        with api_server() as (base_url, _calls):
            result = self._run(
                [
                    "--json",
                    "--base-url",
                    base_url,
                    "request",
                    "GET",
                    "/api/external/v2/me",
                ],
                env={"PENNYLANE_API_TOKEN": "test-token"},
            )
            data = json.loads(result.stdout)
            assert data["ok"] is True
            assert data["data"]["user"]["email"] == "agent@example.com"
