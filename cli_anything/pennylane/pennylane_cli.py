"""Click entry point for cli-anything-pennylane."""

from __future__ import annotations

import json
import os
import shlex
import sys
from typing import Any

import click

from cli_anything.pennylane import __version__
from cli_anything.pennylane.core.api import call_endpoint, list_endpoints, raw_call
from .core.generated_operations import REGISTRY
from .core.operations import operation_to_dict
from cli_anything.pennylane.core.session import Session
from cli_anything.pennylane.utils.pennylane_backend import (
    PennylaneAPIError,
    PennylaneClient,
)
from cli_anything.pennylane.utils.repl_skin import ReplSkin


def _emit(data: Any, as_json: bool) -> None:
    if as_json:
        click.echo(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True))
    elif isinstance(data, list):
        for item in data:
            click.echo(
                item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)
            )
    elif isinstance(data, dict):
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
    elif data is not None:
        click.echo(str(data))


def _parse_kv(values: tuple[str, ...]) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise click.BadParameter(f"Expected key=value, got {value!r}")
        key, val = value.split("=", 1)
        result[key] = val
    return result


def _load_body(data: str | None, data_file: str | None) -> Any | None:
    if data and data_file:
        raise click.ClickException("Use either --data or --data-file, not both.")
    if data_file:
        with open(data_file, encoding="utf-8") as f:
            return json.load(f)
    if data:
        return json.loads(data)
    return None


def _parse_files(values: tuple[str, ...]) -> dict[str, str]:
    return _parse_kv(values)


def _client(ctx: click.Context) -> PennylaneClient:
    session: Session = ctx.obj["session"]
    token = ctx.obj["token"] or os.environ.get(session.token_env)
    return PennylaneClient(token=token, base_url=session.base_url)


def _response_payload(resp: Any) -> dict[str, Any]:
    return {
        "ok": True,
        "status": resp.status,
        "data": resp.data,
        "rate_limit": _rate(resp.headers),
    }


def _execute_operation(
    ctx: click.Context,
    operation_name: str,
    *,
    resource_id: str | None = None,
    path_param: tuple[str, ...] = (),
    param: tuple[str, ...] = (),
    data: str | None = None,
    data_file: str | None = None,
    file: tuple[str, ...] = (),
    field: tuple[str, ...] = (),
    dry_run: bool = False,
) -> None:
    operation = REGISTRY.get(operation_name)
    path_params = _parse_kv(path_param)
    query = _parse_kv(param)
    body = _load_body(data, data_file)
    files = _parse_files(file)
    fields = _parse_kv(field)
    path = operation.render_path(path_params=path_params, id=resource_id)
    if dry_run:
        _emit(
            {
                "ok": True,
                "dry_run": True,
                "operation": operation_to_dict(operation),
                "path": path,
                "query": query,
                "body": body,
                "files": files,
                "fields": fields,
            },
            ctx.obj["json"],
        )
        return
    client = _client(ctx)
    if files:
        resp = client.request_multipart(
            operation.method, path, query=query, files=files, fields=fields
        )
    else:
        resp = client.request_json(operation.method, path, query=query, body=body)
    _emit(_response_payload(resp), ctx.obj["json"])


def _handle_error(exc: Exception, as_json: bool) -> None:
    if isinstance(exc, PennylaneAPIError):
        payload = {
            "ok": False,
            "status": exc.status,
            "error": str(exc),
            "body": exc.body,
            "headers": exc.headers,
        }
        _emit(payload, as_json)
        raise click.exceptions.Exit(1)
    payload = {"ok": False, "error": str(exc)}
    _emit(payload, as_json)
    raise click.exceptions.Exit(1)


@click.group(invoke_without_command=True)
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.option("--session", "session_path", type=click.Path(), help="Session JSON path.")
@click.option(
    "--base-url",
    default=None,
    help="Override API base URL (defaults to session/env/production).",
)
@click.option(
    "--token", default=None, help="API token. Prefer PENNYLANE_API_TOKEN or auth login."
)
@click.pass_context
def cli(
    ctx: click.Context,
    as_json: bool,
    session_path: str | None,
    base_url: str | None,
    token: str | None,
) -> None:
    """Agent-friendly CLI for the Pennylane Company API v2."""
    session = Session.load(session_path)
    if base_url:
        session.base_url = base_url
    ctx.obj = {"json": as_json, "session": session, "token": token}
    if ctx.invoked_subcommand is None:
        ctx.invoke(repl)


@cli.group()
def auth() -> None:
    """Configure local authentication metadata."""


@auth.command("login")
@click.option(
    "--token",
    prompt=True,
    hide_input=True,
    help="Pennylane Company API token to store in session metadata only if --persist-token-env is used.",
)
@click.option(
    "--token-env",
    default="PENNYLANE_API_TOKEN",
    show_default=True,
    help="Environment variable used for the token.",
)
@click.option("--base-url", default="https://app.pennylane.com", show_default=True)
@click.option(
    "--persist-token-env",
    is_flag=True,
    help="Write token into the current process environment for immediate REPL use; session stores only env var name.",
)
@click.option("--dry-run", is_flag=True, help="Validate but do not save session.")
@click.pass_context
def auth_login(
    ctx: click.Context,
    token: str,
    token_env: str,
    base_url: str,
    persist_token_env: bool,
    dry_run: bool,
) -> None:
    """Save base URL and token environment-variable preference."""
    session: Session = ctx.obj["session"]
    session.base_url = base_url
    session.token_env = token_env
    if persist_token_env:
        os.environ[token_env] = token
    session.record(
        "auth login", {"base_url": base_url, "token_env": token_env}, dry_run=dry_run
    )
    _emit(
        {
            "ok": True,
            "base_url": base_url,
            "token_env": token_env,
            "saved": not dry_run,
            "token_stored": False,
        },
        ctx.obj["json"],
    )


@auth.command("whoami")
@click.pass_context
def whoami(ctx: click.Context) -> None:
    """Call /me to verify the current token."""
    try:
        session: Session = ctx.obj["session"]
        token = ctx.obj["token"] or os.environ.get(session.token_env)
        resp = raw_call("/api/external/v2/me", token=token, base_url=session.base_url)
        _emit(
            {
                "ok": True,
                "status": resp.status,
                "data": resp.data,
                "rate_limit": _rate(resp.headers),
            },
            ctx.obj["json"],
        )
    except Exception as exc:  # noqa: BLE001 - convert to CLI error
        _handle_error(exc, ctx.obj["json"])


@cli.group("resource")
def resource() -> None:
    """Discover and call registered Pennylane resources."""


@resource.command("list")
@click.pass_context
def resource_list(ctx: click.Context) -> None:
    _emit(list_endpoints(), ctx.obj["json"])


@resource.command("get")
@click.argument("endpoint")
@click.option(
    "--id",
    "resource_id",
    default=None,
    help="Optional resource ID appended to the endpoint path.",
)
@click.option(
    "--subpath", default=None, help="Optional nested path appended after --id."
)
@click.option(
    "--param", multiple=True, help="Query parameter as key=value. Repeatable."
)
@click.pass_context
def resource_get(
    ctx: click.Context,
    endpoint: str,
    resource_id: str | None,
    subpath: str | None,
    param: tuple[str, ...],
) -> None:
    try:
        session: Session = ctx.obj["session"]
        token = ctx.obj["token"] or os.environ.get(session.token_env)
        resp = call_endpoint(
            endpoint,
            "GET",
            resource_id=resource_id,
            subpath=subpath,
            token=token,
            base_url=session.base_url,
            query=_parse_kv(param),
        )
        _emit(
            {
                "ok": True,
                "status": resp.status,
                "data": resp.data,
                "rate_limit": _rate(resp.headers),
            },
            ctx.obj["json"],
        )
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc, ctx.obj["json"])


@resource.command("post")
@click.argument("endpoint")
@click.option("--id", "resource_id", default=None)
@click.option("--subpath", default=None)
@click.option(
    "--param", multiple=True, help="Query parameter as key=value. Repeatable."
)
@click.option("--data", default=None, help="JSON request body string.")
@click.option(
    "--data-file",
    type=click.Path(exists=True),
    default=None,
    help="JSON request body file.",
)
@click.option(
    "--dry-run", is_flag=True, help="Parse and display request without sending it."
)
@click.pass_context
def resource_post(
    ctx: click.Context,
    endpoint: str,
    resource_id: str | None,
    subpath: str | None,
    param: tuple[str, ...],
    data: str | None,
    data_file: str | None,
    dry_run: bool,
) -> None:
    try:
        body = _load_body(data, data_file)
        session: Session = ctx.obj["session"]
        if dry_run:
            _emit(
                {"ok": True, "dry_run": True, "endpoint": endpoint, "body": body},
                ctx.obj["json"],
            )
            return
        token = ctx.obj["token"] or os.environ.get(session.token_env)
        resp = call_endpoint(
            endpoint,
            "POST",
            resource_id=resource_id,
            subpath=subpath,
            token=token,
            base_url=session.base_url,
            query=_parse_kv(param),
            body=body,
        )
        session.record(
            "resource post",
            {"endpoint": endpoint, "id": resource_id, "subpath": subpath},
            dry_run=False,
        )
        _emit(
            {
                "ok": True,
                "status": resp.status,
                "data": resp.data,
                "rate_limit": _rate(resp.headers),
            },
            ctx.obj["json"],
        )
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc, ctx.obj["json"])


@resource.command("put")
@click.argument("endpoint")
@click.option("--id", "resource_id", required=True)
@click.option("--subpath", default=None)
@click.option(
    "--param", multiple=True, help="Query parameter as key=value. Repeatable."
)
@click.option("--data", default=None, help="JSON request body string.")
@click.option("--data-file", type=click.Path(exists=True), default=None)
@click.pass_context
def resource_put(
    ctx: click.Context,
    endpoint: str,
    resource_id: str,
    subpath: str | None,
    param: tuple[str, ...],
    data: str | None,
    data_file: str | None,
) -> None:
    """PUT a registered legacy resource."""
    try:
        session: Session = ctx.obj["session"]
        token = ctx.obj["token"] or os.environ.get(session.token_env)
        resp = call_endpoint(
            endpoint,
            "PUT",
            resource_id=resource_id,
            subpath=subpath,
            token=token,
            base_url=session.base_url,
            query=_parse_kv(param),
            body=_load_body(data, data_file),
        )
        _emit(_response_payload(resp), ctx.obj["json"])
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc, ctx.obj["json"])


@resource.command("delete")
@click.argument("endpoint")
@click.option("--id", "resource_id", required=True)
@click.option("--subpath", default=None)
@click.option(
    "--param", multiple=True, help="Query parameter as key=value. Repeatable."
)
@click.pass_context
def resource_delete(
    ctx: click.Context,
    endpoint: str,
    resource_id: str,
    subpath: str | None,
    param: tuple[str, ...],
) -> None:
    """DELETE a registered legacy resource."""
    try:
        session: Session = ctx.obj["session"]
        token = ctx.obj["token"] or os.environ.get(session.token_env)
        resp = call_endpoint(
            endpoint,
            "DELETE",
            resource_id=resource_id,
            subpath=subpath,
            token=token,
            base_url=session.base_url,
            query=_parse_kv(param),
        )
        _emit(_response_payload(resp), ctx.obj["json"])
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc, ctx.obj["json"])


@cli.group("operations")
def operations() -> None:
    """List OpenAPI-derived operations covered by the CLI."""


@operations.command("list")
@click.option("--tag", default=None, help="Filter by OpenAPI tag.")
@click.pass_context
def operations_list(ctx: click.Context, tag: str | None) -> None:
    _emit([operation_to_dict(op) for op in REGISTRY.list(tag=tag)], ctx.obj["json"])


@cli.command("call")
@click.argument("operation")
@click.option(
    "--id",
    "resource_id",
    default=None,
    help="Shortcut for a path parameter named {id}.",
)
@click.option(
    "--path-param", multiple=True, help="Path parameter as key=value. Repeatable."
)
@click.option(
    "--param", multiple=True, help="Query parameter as key=value. Repeatable."
)
@click.option("--data", default=None, help="JSON request body string.")
@click.option(
    "--data-file",
    type=click.Path(exists=True),
    default=None,
    help="JSON request body file.",
)
@click.option("--file", multiple=True, help="Multipart file as field=path. Repeatable.")
@click.option(
    "--field", multiple=True, help="Multipart field as key=value. Repeatable."
)
@click.option("--dry-run", is_flag=True, help="Render the request without sending it.")
@click.pass_context
def call_cmd(
    ctx: click.Context,
    operation: str,
    resource_id: str | None,
    path_param: tuple[str, ...],
    param: tuple[str, ...],
    data: str | None,
    data_file: str | None,
    file: tuple[str, ...],
    field: tuple[str, ...],
    dry_run: bool,
) -> None:
    """Call any OpenAPI-covered operation by short name or operationId."""
    try:
        _execute_operation(
            ctx,
            operation,
            resource_id=resource_id,
            path_param=path_param,
            param=param,
            data=data,
            data_file=data_file,
            file=file,
            field=field,
            dry_run=dry_run,
        )
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc, ctx.obj["json"])


@cli.group("files")
def files() -> None:
    """Upload file attachments."""


@files.command("upload")
@click.argument("file_path", type=click.Path(exists=True))
@click.option(
    "--filename", default=None, help="Optional filename override sent to Pennylane."
)
@click.pass_context
def files_upload(ctx: click.Context, file_path: str, filename: str | None) -> None:
    try:
        from .resources import FileAttachmentsResource

        resp = FileAttachmentsResource(_client(ctx), REGISTRY).upload(
            file_path, filename
        )
        _emit(_response_payload(resp), ctx.obj["json"])
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc, ctx.obj["json"])


@cli.group("transactions")
def transactions() -> None:
    """Convenience commands for bank transactions."""


@transactions.command("list")
@click.option("--limit", default=None, type=int)
@click.option("--cursor", default=None)
@click.option("--filter", "filter_", default=None)
@click.option("--sort", default=None)
@click.pass_context
def transactions_list(
    ctx: click.Context,
    limit: int | None,
    cursor: str | None,
    filter_: str | None,
    sort: str | None,
) -> None:
    try:
        from .resources import TransactionsResource

        query = {"limit": limit, "cursor": cursor, "filter": filter_, "sort": sort}
        resp = TransactionsResource(_client(ctx), REGISTRY).list(**query)
        _emit(_response_payload(resp), ctx.obj["json"])
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc, ctx.obj["json"])


@transactions.command("get")
@click.argument("transaction_id")
@click.pass_context
def transactions_get(ctx: click.Context, transaction_id: str) -> None:
    try:
        from .resources import TransactionsResource

        resp = TransactionsResource(_client(ctx), REGISTRY).get(transaction_id)
        _emit(_response_payload(resp), ctx.obj["json"])
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc, ctx.obj["json"])


@cli.command("request")
@click.argument("method")
@click.argument("path")
@click.option(
    "--param", multiple=True, help="Query parameter as key=value. Repeatable."
)
@click.option("--data", default=None, help="JSON request body string.")
@click.option(
    "--data-file",
    type=click.Path(exists=True),
    default=None,
    help="JSON request body file.",
)
@click.pass_context
def request_cmd(
    ctx: click.Context,
    method: str,
    path: str,
    param: tuple[str, ...],
    data: str | None,
    data_file: str | None,
) -> None:
    """Call an arbitrary Pennylane API path."""
    try:
        session: Session = ctx.obj["session"]
        token = ctx.obj["token"] or os.environ.get(session.token_env)
        resp = raw_call(
            path,
            method,
            token=token,
            base_url=session.base_url,
            query=_parse_kv(param),
            body=_load_body(data, data_file),
        )
        _emit(
            {
                "ok": True,
                "status": resp.status,
                "data": resp.data,
                "rate_limit": _rate(resp.headers),
            },
            ctx.obj["json"],
        )
    except Exception as exc:  # noqa: BLE001
        _handle_error(exc, ctx.obj["json"])


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show local session status without making an API request."""
    session: Session = ctx.obj["session"]
    token_present = bool(ctx.obj["token"] or os.environ.get(session.token_env))
    _emit(
        {
            "base_url": session.base_url,
            "session": str(session.path),
            "token_env": session.token_env,
            "token_present": token_present,
            "history_count": len(session.history),
        },
        ctx.obj["json"],
    )


@cli.command()
@click.pass_context
def repl(ctx: click.Context) -> None:
    """Start an interactive Pennylane CLI REPL."""
    skin = ReplSkin("pennylane", version=__version__)
    skin.print_banner()
    pt_session = skin.create_prompt_session()
    skin.info(
        "Type commands like: status, resource list, auth whoami, request GET /api/external/v2/me. Type exit to quit."
    )
    while True:
        try:
            line = skin.get_input(pt_session, project_name="pennylane", modified=False)
        except (EOFError, KeyboardInterrupt):
            click.echo()
            break
        if not line.strip():
            continue
        if line.strip() in {"exit", "quit"}:
            break
        try:
            args = shlex.split(line)
            cli.main(
                args=args,
                prog_name="cli-anything-pennylane",
                obj=ctx.obj,
                standalone_mode=False,
            )
        except SystemExit:
            pass
        except Exception as exc:  # noqa: BLE001
            skin.error(str(exc))
    skin.print_goodbye()


def _rate(headers: dict[str, str]) -> dict[str, str | None]:
    lower = {k.lower(): v for k, v in headers.items()}
    return {
        "limit": lower.get("ratelimit-limit"),
        "remaining": lower.get("ratelimit-remaining"),
        "reset": lower.get("ratelimit-reset"),
    }


def main() -> None:
    cli(prog_name="cli-anything-pennylane")


if __name__ == "__main__":
    sys.exit(main())
