import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer

from click.testing import CliRunner

from cli_anything.pennylane.core.generated_operations import OPERATIONS
from cli_anything.pennylane.pennylane_cli import cli


def test_generated_registry_covers_all_visible_openapi_operations():
    # This is the expected count from https://pennylane.readme.io/openapi/accounting.json
    # at generation time. The generator guarantees unique method/path coverage and may
    # add ergonomic aliases on top of these operations.
    unique_method_paths = {(op.method, op.path_template) for op in OPERATIONS}
    assert len(unique_method_paths) == 160
    assert len(OPERATIONS) >= len(unique_method_paths)


def test_call_dry_run_renders_template_path():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--json",
            "call",
            "transactions.get",
            "--id",
            "123",
            "--param",
            "use_2026_api_changes=true",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["path"] == "/api/external/v2/transactions/123"
    assert data["query"]["use_2026_api_changes"] == "true"


def test_call_put_real_http(monkeypatch):
    with api_server() as (base_url, calls):
        monkeypatch.setenv("PENNYLANE_API_TOKEN", "test-token")
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--json",
                "--base-url",
                base_url,
                "call",
                "transactions.update",
                "--id",
                "42",
                "--data",
                '{"label":"Updated"}',
            ],
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["status"] == 200
        assert calls[-1]["method"] == "PUT"
        assert calls[-1]["path"] == "/api/external/v2/transactions/42"


def test_files_upload_multipart_real_http(monkeypatch, tmp_path):
    file_path = tmp_path / "receipt.pdf"
    file_path.write_bytes(b"%PDF-1.4\n")
    with api_server() as (base_url, calls):
        monkeypatch.setenv("PENNYLANE_API_TOKEN", "test-token")
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--json",
                "--base-url",
                base_url,
                "files",
                "upload",
                str(file_path),
            ],
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["status"] == 201
        assert calls[-1]["method"] == "POST"
        assert calls[-1]["path"] == "/api/external/v2/file_attachments"
        assert "multipart/form-data" in calls[-1]["content_type"]
        assert b"receipt.pdf" in calls[-1]["body"]


@contextmanager
def api_server():
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status, payload):
            self.send_response(status)
            self.send_header("content-type", "application/json")
            self.send_header("ratelimit-limit", "25")
            self.send_header("ratelimit-remaining", "22")
            self.end_headers()
            self.wfile.write(json.dumps(payload).encode())

        def _body(self):
            return self.rfile.read(int(self.headers.get("content-length", "0")))

        def do_PUT(self):
            body = self._body()
            calls.append(
                {
                    "method": self.command,
                    "path": self.path,
                    "authorization": self.headers.get("authorization"),
                    "body": body,
                }
            )
            self._send(200, {"ok": True})

        def do_POST(self):
            body = self._body()
            calls.append(
                {
                    "method": self.command,
                    "path": self.path,
                    "authorization": self.headers.get("authorization"),
                    "content_type": self.headers.get("content-type"),
                    "body": body,
                }
            )
            self._send(201, {"id": 1})

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
