"""Core API operations exposed by the CLI."""

from __future__ import annotations

from typing import Any

from cli_anything.pennylane.core.endpoints import BASE_PATH, ENDPOINTS, endpoint_path
from cli_anything.pennylane.utils.pennylane_backend import APIResponse, request_json


def list_endpoints() -> list[dict[str, Any]]:
    return [{"name": name, **meta} for name, meta in sorted(ENDPOINTS.items())]


def call_endpoint(
    endpoint: str,
    method: str = "GET",
    *,
    resource_id: str | int | None = None,
    subpath: str | None = None,
    token: str | None = None,
    base_url: str | None = None,
    query: dict[str, Any] | None = None,
    body: Any | None = None,
) -> APIResponse:
    path = BASE_PATH + endpoint_path(endpoint, resource_id, subpath)
    return request_json(
        method, path, token=token, base_url=base_url, query=query, body=body
    )


def raw_call(
    path: str,
    method: str = "GET",
    *,
    token: str | None = None,
    base_url: str | None = None,
    query: dict[str, Any] | None = None,
    body: Any | None = None,
) -> APIResponse:
    if not path.startswith("/"):
        path = "/" + path
    return request_json(
        method, path, token=token, base_url=base_url, query=query, body=body
    )
