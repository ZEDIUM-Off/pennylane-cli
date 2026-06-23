"""HTTP backend for the real Pennylane Company API v2."""

from __future__ import annotations

import json
import mimetypes
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error, parse, request

DEFAULT_BASE_URL = "https://app.pennylane.com"
INSTALL_HELP = "Create a Pennylane Company API token in Settings > Connectivity > Developers, then set PENNYLANE_API_TOKEN or run `cli-anything-pennylane auth login`."


class PennylaneAPIError(RuntimeError):
    def __init__(
        self,
        status: int,
        message: str,
        body: Any | None = None,
        headers: dict[str, str] | None = None,
    ):
        super().__init__(message)
        self.status = status
        self.body = body
        self.headers = headers or {}


@dataclass
class APIResponse:
    status: int
    headers: dict[str, str]
    data: Any
    raw: bytes


def require_token(token: str | None = None) -> str:
    value = token or os.environ.get("PENNYLANE_API_TOKEN")
    if not value:
        raise RuntimeError(f"Pennylane API token is required. {INSTALL_HELP}")
    return value


def _build_url(path: str, base_url: str | None, query: dict[str, Any] | None) -> str:
    base = (
        base_url or os.environ.get("PENNYLANE_BASE_URL") or DEFAULT_BASE_URL
    ).rstrip("/")
    qs = ""
    if query:
        clean = {k: v for k, v in query.items() if v is not None and v != ""}
        qs = "?" + parse.urlencode(clean, doseq=True) if clean else ""
    return f"{base}{path}{qs}"


def _send_request(
    method: str,
    url: str,
    *,
    payload: bytes | None,
    headers: dict[str, str],
    timeout: int,
    retry_429: bool,
) -> APIResponse:
    def once() -> APIResponse:
        req = request.Request(url, data=payload, headers=headers, method=method.upper())
        try:
            with request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                parsed = _parse_body(raw, resp.headers.get("content-type", ""))
                return APIResponse(resp.status, dict(resp.headers.items()), parsed, raw)
        except error.HTTPError as exc:
            raw = exc.read()
            parsed = _parse_body(raw, exc.headers.get("content-type", ""))
            msg = _error_message(exc.code, parsed, raw)
            raise PennylaneAPIError(
                exc.code, msg, parsed, dict(exc.headers.items())
            ) from exc
        except error.URLError as exc:
            raise RuntimeError(
                f"Cannot reach Pennylane API at {url}: {exc.reason}"
            ) from exc

    try:
        return once()
    except PennylaneAPIError as exc:
        if retry_429 and exc.status == 429:
            wait = int(exc.headers.get("retry-after", "1") or "1")
            time.sleep(max(0, min(wait, 10)))
            return once()
        raise


def request_json(
    method: str,
    path: str,
    *,
    token: str | None = None,
    base_url: str | None = None,
    query: dict[str, Any] | None = None,
    body: Any | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
    retry_429: bool = True,
) -> APIResponse:
    """Call Pennylane API and parse JSON responses."""
    bearer = require_token(token)
    url = _build_url(path, base_url, query)
    payload = None
    req_headers = {
        "Authorization": f"Bearer {bearer}",
        "Accept": "application/json",
        "User-Agent": "cli-anything-pennylane/1.0.0",
    }
    if body is not None:
        payload = json.dumps(body).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    if headers:
        req_headers.update(headers)
    return _send_request(
        method,
        url,
        payload=payload,
        headers=req_headers,
        timeout=timeout,
        retry_429=retry_429,
    )


def request_multipart(
    method: str,
    path: str,
    *,
    token: str | None = None,
    base_url: str | None = None,
    query: dict[str, Any] | None = None,
    files: dict[str, str] | None = None,
    fields: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
    retry_429: bool = True,
) -> APIResponse:
    """Call Pennylane API using multipart/form-data."""
    bearer = require_token(token)
    url = _build_url(path, base_url, query)
    boundary = "----cli-anything-pennylane-" + uuid.uuid4().hex
    payload = _encode_multipart(boundary, files=files or {}, fields=fields or {})
    req_headers = {
        "Authorization": f"Bearer {bearer}",
        "Accept": "application/json",
        "User-Agent": "cli-anything-pennylane/1.0.0",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }
    if headers:
        req_headers.update(headers)
    return _send_request(
        method,
        url,
        payload=payload,
        headers=req_headers,
        timeout=timeout,
        retry_429=retry_429,
    )


def _encode_multipart(
    boundary: str, *, files: dict[str, str], fields: dict[str, Any]
) -> bytes:
    chunks: list[bytes] = []
    for name, value in fields.items():
        if value is None:
            continue
        chunks.append(f"--{boundary}\r\n".encode())
        chunks.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        chunks.append(str(value).encode())
        chunks.append(b"\r\n")
    for name, file_path in files.items():
        path = Path(file_path)
        filename = path.name
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        chunks.append(f"--{boundary}\r\n".encode())
        chunks.append(
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode()
        )
        chunks.append(f"Content-Type: {content_type}\r\n\r\n".encode())
        chunks.append(path.read_bytes())
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks)


class PennylaneClient:
    """Small object-oriented API client used by resource classes and CLI commands."""

    def __init__(self, *, token: str | None = None, base_url: str | None = None):
        self.token = token
        self.base_url = base_url

    def request_json(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        body: Any | None = None,
    ) -> APIResponse:
        return request_json(
            method,
            path,
            token=self.token,
            base_url=self.base_url,
            query=query,
            body=body,
        )

    def request_multipart(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        files: dict[str, str] | None = None,
        fields: dict[str, Any] | None = None,
    ) -> APIResponse:
        return request_multipart(
            method,
            path,
            token=self.token,
            base_url=self.base_url,
            query=query,
            files=files,
            fields=fields,
        )


def _parse_body(raw: bytes, content_type: str) -> Any:
    if not raw:
        return None
    text = raw.decode("utf-8", errors="replace")
    if "json" in content_type or text[:1] in "[{":
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
    return text


def _error_message(status: int, parsed: Any, raw: bytes) -> str:
    if isinstance(parsed, dict):
        detail = parsed.get("message") or parsed.get("error") or parsed
    else:
        detail = parsed or raw.decode("utf-8", errors="replace")
    if status == 401:
        return f"401 Unauthorized: invalid/missing Pennylane token. {INSTALL_HELP}"
    if status == 403:
        return f"403 Forbidden: token lacks the required Pennylane scope. Details: {detail}"
    if status == 429:
        return f"429 Rate limited by Pennylane. Details: {detail}"
    return f"Pennylane API error {status}: {detail}"
