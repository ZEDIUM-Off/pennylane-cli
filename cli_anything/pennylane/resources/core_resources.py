"""Concrete resource classes for common Pennylane domains."""

from __future__ import annotations

from .base import (
    AppendicesMixin,
    BaseResource,
    CategorisableMixin,
    InvoiceLinesMixin,
    MatchedTransactionsMixin,
    PaymentsMixin,
    SendByEmailMixin,
)


class TransactionsResource(BaseResource, CategorisableMixin):
    resource_name = "transactions"
    list_operation = "transactions.list"
    get_operation = "transactions.get"
    create_operation = "transactions.create"
    update_operation = "transactions.update"
    categories_list_operation = "transactions.categories.list"
    categories_update_operation = "transactions.categories.update"
    category_path_param = "transaction_id"

    def matched_invoices(self, transaction_id):
        return self.call(
            "transactions.matched-invoices.list",
            path_params={"transaction_id": str(transaction_id)},
        )


class FileAttachmentsResource(BaseResource):
    resource_name = "files"

    def upload(self, file_path: str, filename: str | None = None):
        fields = {"filename": filename} if filename else None
        return self.call(
            "file-attachments.upload", files={"file": file_path}, fields=fields
        )


class SupplierInvoicesResource(
    BaseResource,
    CategorisableMixin,
    InvoiceLinesMixin,
    PaymentsMixin,
    MatchedTransactionsMixin,
):
    resource_name = "supplier-invoices"
    list_operation = "supplier-invoices.list"
    get_operation = "supplier-invoices.get"
    update_operation = "supplier-invoices.update"
    categories_list_operation = "supplier-invoices.categories.list"
    categories_update_operation = "supplier-invoices.categories.update"
    category_path_param = "supplier_invoice_id"
    invoice_lines_operation = "supplier-invoices.invoice-lines.list"
    invoice_path_param = "supplier_invoice_id"
    payments_operation = "supplier-invoices.payments.list"
    payments_path_param = "supplier_invoice_id"
    matched_transactions_list_operation = "supplier-invoices.matched-transactions.list"
    matched_transactions_create_operation = (
        "supplier-invoices.matched-transactions.match"
    )
    matched_transactions_delete_operation = (
        "supplier-invoices.matched-transactions.unmatch"
    )
    matched_transactions_path_param = "supplier_invoice_id"

    def import_with_file(self, data):
        return self.call("supplier-invoices.import", body=data)

    def validate_accounting(self, id):
        return self.call(
            "supplier-invoices.validate-accounting",
            path_params={"supplier_invoice_id": str(id)},
        )


class CustomerInvoicesResource(
    BaseResource,
    CategorisableMixin,
    AppendicesMixin,
    InvoiceLinesMixin,
    PaymentsMixin,
    MatchedTransactionsMixin,
    SendByEmailMixin,
):
    resource_name = "customer-invoices"
    list_operation = "customer-invoices.list"
    get_operation = "customer-invoices.get"
    create_operation = "customer-invoices.create"
    update_operation = "customer-invoices.update"
    delete_operation = "customer-invoices.delete"
    categories_list_operation = "customer-invoices.categories.list"
    categories_update_operation = "customer-invoices.categories.update"
    category_path_param = "customer_invoice_id"
    appendices_list_operation = "customer-invoices.appendices.list"
    appendices_upload_operation = "customer-invoices.appendices.upload"
    appendix_path_param = "customer_invoice_id"
    invoice_lines_operation = "customer-invoices.invoice-lines.list"
    invoice_line_sections_operation = "customer-invoices.invoice-line-sections.list"
    invoice_path_param = "customer_invoice_id"
    payments_operation = "customer-invoices.payments.list"
    payments_path_param = "customer_invoice_id"
    matched_transactions_list_operation = "customer-invoices.matched-transactions.list"
    matched_transactions_create_operation = (
        "customer-invoices.matched-transactions.match"
    )
    matched_transactions_delete_operation = (
        "customer-invoices.matched-transactions.unmatch"
    )
    matched_transactions_path_param = "customer_invoice_id"
    send_by_email_operation = "customer-invoices.send-by-email"
