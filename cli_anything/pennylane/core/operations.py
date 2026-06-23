"""OpenAPI-derived operation registry for Pennylane API v2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Operation:
    name: str
    operation_id: str
    method: str
    path_template: str
    summary: str
    tags: tuple[str, ...] = ()
    query_params: tuple[str, ...] = ()
    path_params: tuple[str, ...] = ()
    request_content_types: tuple[str, ...] = ()
    deprecated: bool = False

    def render_path(
        self, *, path_params: dict[str, str] | None = None, id: str | int | None = None
    ) -> str:
        values = dict(path_params or {})
        if id is not None and "id" in self.path_params and "id" not in values:
            values["id"] = str(id)
        path = self.path_template
        missing: list[str] = []
        for key in self.path_params:
            token = "{" + key + "}"
            if key not in values:
                missing.append(key)
            else:
                path = path.replace(token, str(values[key]))
        if missing:
            raise ValueError(
                f"Missing path parameter(s) for {self.name}: {', '.join(missing)}. "
                "Use --id or --path-param key=value."
            )
        return path

    @property
    def supports_multipart(self) -> bool:
        return any("multipart/form-data" in ct for ct in self.request_content_types)


class OperationRegistry:
    def __init__(self, operations: Iterable[Operation]):
        self._operations = list(operations)
        self._by_name: dict[str, Operation] = {}
        self._by_id: dict[str, Operation] = {}
        for operation in self._operations:
            self._by_name[operation.name] = operation
            self._by_id[operation.operation_id] = operation

    def list(self, tag: str | None = None) -> list[Operation]:
        if tag is None:
            return list(self._operations)
        needle = tag.lower()
        return [
            op for op in self._operations if any(t.lower() == needle for t in op.tags)
        ]

    def get(self, name_or_operation_id: str) -> Operation:
        if name_or_operation_id in self._by_name:
            return self._by_name[name_or_operation_id]
        if name_or_operation_id in self._by_id:
            return self._by_id[name_or_operation_id]
        # tolerate legacy hyphen/underscore variants
        alt = name_or_operation_id.replace("_", "-")
        if alt in self._by_name:
            return self._by_name[alt]
        raise KeyError(
            f"Unknown operation '{name_or_operation_id}'. Run `operations list`."
        )

    def by_tag(self, tag: str) -> list[Operation]:
        return self.list(tag=tag)


def operation_to_dict(operation: Operation) -> dict[str, object]:
    return {
        "name": operation.name,
        "operation_id": operation.operation_id,
        "method": operation.method,
        "path": operation.path_template,
        "summary": operation.summary,
        "tags": list(operation.tags),
        "query_params": list(operation.query_params),
        "path_params": list(operation.path_params),
        "request_content_types": list(operation.request_content_types),
        "deprecated": operation.deprecated,
    }
