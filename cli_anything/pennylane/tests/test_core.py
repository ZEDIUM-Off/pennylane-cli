import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer

from cli_anything.pennylane.core.endpoints import ENDPOINTS, endpoint_path
from cli_anything.pennylane.core.session import Session
from cli_anything.pennylane.utils.pennylane_backend import request_json, require_token


def test_endpoint_registry_contains_common_resources():
    assert "customers" in ENDPOINTS
    assert "customer-invoices" in ENDPOINTS
    assert ENDPOINTS["customers"]["path"] == "/customers"


def test_endpoint_path_with_id_and_subpath():
    assert endpoint_path("customers", 42, "contacts") == "/customers/42/contacts"


def test_endpoint_path_unknown_is_explicit():
    try:
        endpoint_path("missing")
    except KeyError as exc:
        assert "Unknown endpoint" in str(exc)
    else:
        raise AssertionError("Expected KeyError")


def test_session_defaults(tmp_path):
    session = Session.load(tmp_path / "missing.json")
    assert session.base_url == "https://app.pennylane.com"
    assert session.default_limit == 20


def test_session_save_load_roundtrip(tmp_path):
    path = tmp_path / "session.json"
    session = Session(path=path, base_url="http://localhost:1", default_limit=10)
    session.save()
    loaded = Session.load(path)
    assert loaded.base_url == "http://localhost:1"
    assert loaded.default_limit == 10


def test_session_record_dry_run_does_not_create_file(tmp_path):
    path = tmp_path / "session.json"
    session = Session(path=path)
    session.record("noop", dry_run=True)
    assert not path.exists()


def test_require_token_missing(monkeypatch):
    monkeypatch.delenv("PENNYLANE_API_TOKEN", raising=False)
    try:
        require_token()
    except RuntimeError as exc:
        assert "Pennylane API token is required" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError")


def test_request_json_sends_bearer_and_body():
    with api_server() as (base_url, seen):
        resp = request_json(
            "POST",
            "/api/external/v2/products",
            token="secret",
            base_url=base_url,
            body={"name": "Service"},
        )
        assert resp.status == 201
        assert resp.data["name"] == "Service"
        assert seen["authorization"] == "Bearer secret"
        assert json.loads(seen["body"])["name"] == "Service"


@contextmanager
def api_server():
    seen = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("content-length", "0"))
            seen["authorization"] = self.headers.get("authorization")
            seen["body"] = self.rfile.read(length).decode()
            self.send_response(201)
            self.send_header("content-type", "application/json")
            self.send_header("ratelimit-limit", "25")
            self.send_header("ratelimit-remaining", "24")
            self.end_headers()
            self.wfile.write(
                json.dumps({"id": 1, "name": json.loads(seen["body"])["name"]}).encode()
            )

        def log_message(self, format, *args):  # noqa: A002
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", seen
    finally:
        server.shutdown()
        thread.join(timeout=2)
