from __future__ import annotations

import json
import re
import urllib.request
from collections import Counter
from pathlib import Path

SOURCE = "https://pennylane.readme.io/openapi/accounting.json"
OUT = Path("cli_anything/pennylane/core/generated_operations.py")

RESOURCE_ALIASES = {
    "customer_invoices": "customer-invoices",
    "supplier_invoices": "supplier-invoices",
    "ledger_accounts": "ledger-accounts",
    "ledger_entries": "ledger-entries",
    "ledger_entry_lines": "ledger-entry-lines",
    "file_attachments": "file-attachments",
    "category_groups": "category-groups",
    "company_customers": "company-customers",
    "individual_customers": "individual-customers",
    "bank_accounts": "bank-accounts",
    "bank_establishments": "bank-establishments",
    "billing_subscriptions": "billing-subscriptions",
    "commercial_documents": "commercial-documents",
    "customer_invoice_templates": "customer-invoice-templates",
    "fiscal_years": "fiscal-years",
    "gocardless_mandates": "gocardless-mandates",
    "sepa_mandates": "sepa-mandates",
    "pa_registrations": "pa-registrations",
    "purchase_requests": "purchase-requests",
    "trial_balance": "trial-balance",
    "pro_account": "pro-account",
}
ACTION_ALIASES = {
    "matched_transactions": "matched-transactions",
    "matched_invoices": "matched-invoices",
    "invoice_lines": "invoice-lines",
    "invoice_line_sections": "invoice-line-sections",
    "send_by_email": "send-by-email",
    "mark_as_paid": "mark-as-paid",
    "link_credit_note": "link-credit-note",
    "update_imported": "update-imported",
    "validate_accounting": "validate-accounting",
    "payment_status": "payment-status",
    "e_invoice_status": "e-invoice-status",
    "e_invoices": "e-invoices",
    "create_from_quote": "create-from-quote",
    "analytical_general_ledgers": "analytical-general-ledgers",
    "general_ledgers": "general-ledgers",
    "fecs": "fecs",
    "lettered_ledger_entry_lines": "lettered-ledger-entry-lines",
    "custom_header_fields": "custom-header-fields",
}


def fetch(url: str) -> dict:
    if Path("/tmp/pennylane_openapi_accounting.json").exists():
        return json.loads(Path("/tmp/pennylane_openapi_accounting.json").read_text())
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def slug(s: str) -> str:
    return ACTION_ALIASES.get(s, RESOURCE_ALIASES.get(s, s.replace("_", "-")))


def path_params(path: str) -> list[str]:
    return re.findall(r"\{([^}]+)\}", path)


def content_types(op: dict) -> list[str]:
    body = op.get("requestBody") or {}
    return sorted((body.get("content") or {}).keys())


def query_params(op: dict) -> list[str]:
    return [p["name"] for p in op.get("parameters", []) if p.get("in") == "query"]


def default_action(method: str, path: str, params: list[str]) -> str:
    last = path.rstrip("/").split("/")[-1]
    if method == "GET":
        return "get" if last.startswith("{") else "list"
    if method == "POST":
        if last == "import":
            return "import"
        if last == "imports":
            return "import"
        if last == "appendices":
            return "upload"
        if last == "matched_transactions":
            return "match"
        if last == "send_by_email":
            return "send-by-email"
        if last == "create_from_quote":
            return "create-from-quote"
        if last in {"lettering", "link_credit_note"}:
            return slug(last if last != "lettering" else "letter")
        return "create"
    if method == "PUT":
        if last == "categories":
            return "update"
        if last == "finalize":
            return "finalize"
        if last == "mark_as_paid":
            return "mark-as-paid"
        if last == "update_imported":
            return "update-imported"
        if last == "payment_status":
            return "update-payment-status"
        if last == "e_invoice_status":
            return "update-e-invoice-status"
        return "update"
    if method == "DELETE":
        if "matched_transactions" in path:
            return "unmatch"
        if last == "lettering":
            return "unletter"
        return "delete"
    return method.lower()


def make_name(method: str, path: str, op: dict) -> str:
    parts = path.split("/api/external/v2/", 1)[1].split("/")
    root = slug(parts[0])
    params = path_params(path)
    non_param_tail = [p for p in parts[1:] if not p.startswith("{")]
    action = default_action(method, path, params)

    # Special roots/paths
    if root == "exports" and non_param_tail:
        root = "exports." + slug(non_param_tail[0])
        non_param_tail = non_param_tail[1:]
    elif root == "pro-account" and non_param_tail:
        root = "pro-account." + slug(non_param_tail[0])
        non_param_tail = non_param_tail[1:]

    if action in {"list", "get", "create", "update", "delete", "import", "upload"}:
        tail = []
        for seg in non_param_tail:
            s = slug(seg)
            if s in {"import", "imports"}:
                continue
            tail.append(s)
        if tail:
            return root + "." + ".".join(tail) + "." + action
        return root + "." + action
    return root + "." + action


def main() -> None:
    spec = fetch(SOURCE)
    rows = []
    for path, methods in spec["paths"].items():
        for method, op in methods.items():
            method = method.upper()
            if method not in {"GET", "POST", "PUT", "DELETE", "PATCH"}:
                continue
            if "Hidden" in op.get("tags", []):
                continue
            rows.append(
                {
                    "name": make_name(method, path, op),
                    "operation_id": op.get("operationId") or "",
                    "method": method,
                    "path_template": path,
                    "summary": op.get("summary") or "",
                    "tags": tuple(op.get("tags", [])),
                    "query_params": tuple(query_params(op)),
                    "path_params": tuple(path_params(path)),
                    "request_content_types": tuple(content_types(op)),
                    "deprecated": bool(op.get("deprecated")),
                }
            )
    counts = Counter(r["name"] for r in rows)
    seen = Counter()
    for row in rows:
        if counts[row["name"]] > 1:
            seen[row["name"]] += 1
            row["name"] = f"{row['name']}.{seen[row['name']]}"
    # Compatibility aliases expected by resource classes.
    aliases = {
        "transactions.categories.list": (
            "GET",
            "/api/external/v2/transactions/{transaction_id}/categories",
        ),
        "transactions.categories.update": (
            "PUT",
            "/api/external/v2/transactions/{transaction_id}/categories",
        ),
        "transactions.matched-invoices.list": (
            "GET",
            "/api/external/v2/transactions/{transaction_id}/matched_invoices",
        ),
        "file-attachments.upload": ("POST", "/api/external/v2/file_attachments"),
        "customer-invoices.categories.list": (
            "GET",
            "/api/external/v2/customer_invoices/{customer_invoice_id}/categories",
        ),
        "customer-invoices.categories.update": (
            "PUT",
            "/api/external/v2/customer_invoices/{customer_invoice_id}/categories",
        ),
        "customer-invoices.appendices.list": (
            "GET",
            "/api/external/v2/customer_invoices/{customer_invoice_id}/appendices",
        ),
        "customer-invoices.appendices.upload": (
            "POST",
            "/api/external/v2/customer_invoices/{customer_invoice_id}/appendices",
        ),
        "customer-invoices.invoice-lines.list": (
            "GET",
            "/api/external/v2/customer_invoices/{customer_invoice_id}/invoice_lines",
        ),
        "customer-invoices.invoice-line-sections.list": (
            "GET",
            "/api/external/v2/customer_invoices/{customer_invoice_id}/invoice_line_sections",
        ),
        "customer-invoices.payments.list": (
            "GET",
            "/api/external/v2/customer_invoices/{customer_invoice_id}/payments",
        ),
        "customer-invoices.matched-transactions.list": (
            "GET",
            "/api/external/v2/customer_invoices/{customer_invoice_id}/matched_transactions",
        ),
        "customer-invoices.matched-transactions.match": (
            "POST",
            "/api/external/v2/customer_invoices/{customer_invoice_id}/matched_transactions",
        ),
        "customer-invoices.matched-transactions.unmatch": (
            "DELETE",
            "/api/external/v2/customer_invoices/{customer_invoice_id}/matched_transactions/{id}",
        ),
        "customer-invoices.send-by-email": (
            "POST",
            "/api/external/v2/customer_invoices/{id}/send_by_email",
        ),
        "supplier-invoices.categories.list": (
            "GET",
            "/api/external/v2/supplier_invoices/{supplier_invoice_id}/categories",
        ),
        "supplier-invoices.categories.update": (
            "PUT",
            "/api/external/v2/supplier_invoices/{supplier_invoice_id}/categories",
        ),
        "supplier-invoices.invoice-lines.list": (
            "GET",
            "/api/external/v2/supplier_invoices/{supplier_invoice_id}/invoice_lines",
        ),
        "supplier-invoices.payments.list": (
            "GET",
            "/api/external/v2/supplier_invoices/{supplier_invoice_id}/payments",
        ),
        "supplier-invoices.matched-transactions.list": (
            "GET",
            "/api/external/v2/supplier_invoices/{supplier_invoice_id}/matched_transactions",
        ),
        "supplier-invoices.matched-transactions.match": (
            "POST",
            "/api/external/v2/supplier_invoices/{supplier_invoice_id}/matched_transactions",
        ),
        "supplier-invoices.matched-transactions.unmatch": (
            "DELETE",
            "/api/external/v2/supplier_invoices/{supplier_invoice_id}/matched_transactions/{id}",
        ),
        "supplier-invoices.validate-accounting": (
            "PUT",
            "/api/external/v2/supplier_invoices/{supplier_invoice_id}/validate_accounting",
        ),
    }
    by_method_path = {(r["method"], r["path_template"]): r for r in rows}
    for alias, key in aliases.items():
        if key in by_method_path:
            rows.append({**by_method_path[key], "name": alias})
    rows.sort(key=lambda r: (r["name"], r["method"], r["path_template"]))
    OUT.write_text(
        "# Generated by scripts/generate_openapi_registry.py; do not edit by hand.\n"
        "from cli_anything.pennylane.core.operations import Operation, OperationRegistry\n\n"
        "OPERATIONS = [\n"
        + "\n".join(
            "    Operation("
            + ", ".join(
                [
                    f"name={r['name']!r}",
                    f"operation_id={r['operation_id']!r}",
                    f"method={r['method']!r}",
                    f"path_template={r['path_template']!r}",
                    f"summary={r['summary']!r}",
                    f"tags={r['tags']!r}",
                    f"query_params={r['query_params']!r}",
                    f"path_params={r['path_params']!r}",
                    f"request_content_types={r['request_content_types']!r}",
                    f"deprecated={r['deprecated']!r}",
                ]
            )
            + "),"
            for r in rows
        )
        + "\n]\n\nREGISTRY = OperationRegistry(OPERATIONS)\n"
    )
    print(f"wrote {OUT} with {len(rows)} operations/aliases")


if __name__ == "__main__":
    main()
