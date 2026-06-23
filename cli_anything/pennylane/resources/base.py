"""Reusable object-oriented resource helpers for Pennylane commands."""

from __future__ import annotations

from typing import Any, cast

from ..core.operations import OperationRegistry


class BaseResource:
    """Base wrapper around OperationRegistry names.

    Concrete resources only define operation names; all HTTP details stay in the
    client/operation layer.
    """

    resource_name: str = ""
    list_operation: str | None = None
    get_operation: str | None = None
    create_operation: str | None = None
    update_operation: str | None = None
    delete_operation: str | None = None

    def __init__(self, client: Any, registry: OperationRegistry):
        self.client = client
        self.registry = registry

    def call(
        self,
        operation_name: str,
        *,
        id: str | int | None = None,
        path_params: dict[str, str] | None = None,
        query: dict[str, Any] | None = None,
        body: Any | None = None,
        files: dict[str, str] | None = None,
        fields: dict[str, str] | None = None,
    ):
        operation = self.registry.get(operation_name)
        path = operation.render_path(id=id, path_params=path_params)
        if files:
            return self.client.request_multipart(
                operation.method, path, query=query, files=files, fields=fields
            )
        return self.client.request_json(operation.method, path, query=query, body=body)

    def list(self, **query: Any):
        if not self.list_operation:
            raise NotImplementedError(f"{self.resource_name} has no list operation")
        return cast(Any, self).call(self.list_operation, query=query)

    def get(self, id: str | int, **query: Any):
        if not self.get_operation:
            raise NotImplementedError(f"{self.resource_name} has no get operation")
        return cast(Any, self).call(self.get_operation, id=id, query=query)

    def create(self, data: Any, **query: Any):
        if not self.create_operation:
            raise NotImplementedError(f"{self.resource_name} has no create operation")
        return cast(Any, self).call(self.create_operation, query=query, body=data)

    def update(self, id: str | int, data: Any, **query: Any):
        if not self.update_operation:
            raise NotImplementedError(f"{self.resource_name} has no update operation")
        return cast(Any, self).call(
            self.update_operation, id=id, query=query, body=data
        )

    def delete(self, id: str | int, **query: Any):
        if not self.delete_operation:
            raise NotImplementedError(f"{self.resource_name} has no delete operation")
        return cast(Any, self).call(self.delete_operation, id=id, query=query)


class CategorisableMixin:
    categories_list_operation: str | None = None
    categories_update_operation: str | None = None
    category_path_param: str = "id"

    def list_categories(self, id: str | int):
        if not self.categories_list_operation:
            raise NotImplementedError("No categories list operation")
        return cast(Any, self).call(
            self.categories_list_operation,
            path_params={self.category_path_param: str(id)},
        )

    def update_categories(self, id: str | int, categories: Any):
        if not self.categories_update_operation:
            raise NotImplementedError("No categories update operation")
        return cast(Any, self).call(
            self.categories_update_operation,
            path_params={self.category_path_param: str(id)},
            body=categories,
        )


class AppendicesMixin:
    appendices_list_operation: str | None = None
    appendices_upload_operation: str | None = None
    appendix_path_param: str = "id"

    def list_appendices(self, id: str | int):
        if not self.appendices_list_operation:
            raise NotImplementedError("No appendices list operation")
        return cast(Any, self).call(
            self.appendices_list_operation,
            path_params={self.appendix_path_param: str(id)},
        )

    def upload_appendix(
        self, id: str | int, file_path: str, filename: str | None = None
    ):
        if not self.appendices_upload_operation:
            raise NotImplementedError("No appendices upload operation")
        fields = {"filename": filename} if filename else None
        return cast(Any, self).call(
            self.appendices_upload_operation,
            path_params={self.appendix_path_param: str(id)},
            files={"file": file_path},
            fields=fields,
        )


class InvoiceLinesMixin:
    invoice_lines_operation: str | None = None
    invoice_line_sections_operation: str | None = None
    invoice_path_param: str = "id"

    def list_invoice_lines(self, id: str | int):
        if not self.invoice_lines_operation:
            raise NotImplementedError("No invoice lines operation")
        return cast(Any, self).call(
            self.invoice_lines_operation, path_params={self.invoice_path_param: str(id)}
        )

    def list_invoice_line_sections(self, id: str | int):
        if not self.invoice_line_sections_operation:
            raise NotImplementedError("No invoice line sections operation")
        return cast(Any, self).call(
            self.invoice_line_sections_operation,
            path_params={self.invoice_path_param: str(id)},
        )


class PaymentsMixin:
    payments_operation: str | None = None
    payments_path_param: str = "id"

    def list_payments(self, id: str | int):
        if not self.payments_operation:
            raise NotImplementedError("No payments operation")
        return cast(Any, self).call(
            self.payments_operation, path_params={self.payments_path_param: str(id)}
        )


class MatchedTransactionsMixin:
    matched_transactions_list_operation: str | None = None
    matched_transactions_create_operation: str | None = None
    matched_transactions_delete_operation: str | None = None
    matched_transactions_path_param: str = "id"

    def list_matched_transactions(self, id: str | int):
        if not self.matched_transactions_list_operation:
            raise NotImplementedError("No matched transactions list operation")
        return cast(Any, self).call(
            self.matched_transactions_list_operation,
            path_params={self.matched_transactions_path_param: str(id)},
        )

    def match_transaction(self, id: str | int, data: Any):
        if not self.matched_transactions_create_operation:
            raise NotImplementedError("No matched transactions create operation")
        return cast(Any, self).call(
            self.matched_transactions_create_operation,
            path_params={self.matched_transactions_path_param: str(id)},
            body=data,
        )

    def unmatch_transaction(self, id: str | int, match_id: str | int):
        if not self.matched_transactions_delete_operation:
            raise NotImplementedError("No matched transactions delete operation")
        return cast(Any, self).call(
            self.matched_transactions_delete_operation,
            path_params={
                self.matched_transactions_path_param: str(id),
                "id": str(match_id),
            },
        )


class SendByEmailMixin:
    send_by_email_operation: str | None = None

    def send_by_email(self, id: str | int, data: Any | None = None):
        if not self.send_by_email_operation:
            raise NotImplementedError("No send by email operation")
        return cast(Any, self).call(self.send_by_email_operation, id=id, body=data)
