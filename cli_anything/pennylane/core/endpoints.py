"""Endpoint registry for high-value Pennylane API v2 resources."""

from __future__ import annotations

BASE_PATH = "/api/external/v2"

ENDPOINTS = {
    "me": {"path": "/me", "methods": ["GET"], "scope": "token identity"},
    "customers": {
        "path": "/customers",
        "methods": ["GET"],
        "scope": "customers:readonly/customers:all",
    },
    "company-customers": {
        "path": "/company_customers",
        "methods": ["POST"],
        "scope": "customers:all",
    },
    "individual-customers": {
        "path": "/individual_customers",
        "methods": ["POST"],
        "scope": "customers:all",
    },
    "products": {
        "path": "/products",
        "methods": ["GET", "POST", "PUT"],
        "scope": "products:readonly/products:all",
    },
    "customer-invoices": {
        "path": "/customer_invoices",
        "methods": ["GET", "POST"],
        "scope": "customer_invoices:readonly/customer_invoices:all",
    },
    "quotes": {
        "path": "/quotes",
        "methods": ["GET", "POST"],
        "scope": "quotes:readonly/quotes:all",
    },
    "supplier-invoices": {
        "path": "/supplier_invoices",
        "methods": ["GET", "PUT"],
        "scope": "supplier_invoices:readonly/supplier_invoices:all",
    },
    "ledger-accounts": {
        "path": "/ledger_accounts",
        "methods": ["GET", "POST"],
        "scope": "ledger_accounts:readonly/ledger_accounts:all",
    },
    "ledger-entries": {
        "path": "/ledger_entries",
        "methods": ["GET", "POST"],
        "scope": "ledger_entries:readonly/ledger_entries:all",
    },
    "ledger-entry-lines": {
        "path": "/ledger_entry_lines",
        "methods": ["GET"],
        "scope": "ledger_entries:readonly/ledger_entries:all",
    },
    "journals": {
        "path": "/journals",
        "methods": ["GET", "POST"],
        "scope": "journals:readonly/journals:all",
    },
    "categories": {
        "path": "/categories",
        "methods": ["GET", "POST"],
        "scope": "categories:readonly/categories:all",
    },
    "category-groups": {
        "path": "/category_groups",
        "methods": ["GET"],
        "scope": "categories:readonly/categories:all",
    },
    "transactions": {
        "path": "/transactions",
        "methods": ["GET", "POST", "PUT"],
        "scope": "transactions:readonly/transactions:all",
    },
    "trial-balance": {
        "path": "/trial_balance",
        "methods": ["GET"],
        "scope": "trial_balance:readonly",
    },
    "fiscal-years": {
        "path": "/fiscal_years",
        "methods": ["GET"],
        "scope": "fiscal_years:readonly",
    },
    "file-attachments": {
        "path": "/file_attachments",
        "methods": ["POST"],
        "scope": "file_attachments:all",
    },
    "fec-exports": {
        "path": "/exports/fecs",
        "methods": ["GET", "POST"],
        "scope": "exports:fec",
    },
    "general-ledger-exports": {
        "path": "/exports/general_ledgers",
        "methods": ["GET", "POST"],
        "scope": "exports:gl",
    },
    "analytical-general-ledger-exports": {
        "path": "/exports/analytical_general_ledgers",
        "methods": ["GET", "POST"],
        "scope": "exports:agl",
    },
}


def endpoint_path(
    name: str, resource_id: str | int | None = None, subpath: str | None = None
) -> str:
    if name not in ENDPOINTS:
        raise KeyError(f"Unknown endpoint '{name}'. Run `resource list`.")
    path = ENDPOINTS[name]["path"]
    if resource_id is not None:
        path += f"/{resource_id}"
    if subpath:
        path += "/" + subpath.strip("/")
    return path
