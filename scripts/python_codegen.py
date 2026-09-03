"""Render typed async Python clients from an OpenAPI document."""

import json
import keyword
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

GENERATED_HEADER = "# Generated from {source}. Do not edit manually.\n"
LINE_LENGTH = 88
REF_PREFIX = "#/components/schemas/"
METHOD_ORDER = ("get", "post", "put", "patch", "delete")
THIRD_PARTY_ROOTS = frozenset({"httpx2", "pydantic"})
FIRST_PARTY_ROOTS = frozenset({"generated"})

PRIMITIVES = {
    "string": "str",
    "integer": "int",
    "number": "float",
    "boolean": "bool",
    "null": "None",
}
FORMATS = {
    "uuid": ("UUID", "uuid"),
    "date-time": ("datetime", "datetime"),
    "date": ("date", "datetime"),
}


class UnsupportedSchemaError(RuntimeError):
    """The document uses an OpenAPI construct the generator does not render."""


@dataclass(frozen=True, slots=True)
class PythonClientOptions:
    client_name: str = "ApiClient"
    source: str = "the OpenAPI document"
    transport_module: str = "generated.transport"


def render_python_client(
    document: dict[str, Any], options: PythonClientOptions
) -> dict[str, str]:
    schemas = document.get("components", {}).get("schemas", {})
    model_names = tuple(_ordered_names(schemas))
    return {
        "models.py": _ModelsRenderer(schemas, options).render(),
        "client.py": _ClientRenderer(document, options).render(),
        "__init__.py": _render_init(model_names, options),
    }


def write_python_client(
    document: dict[str, Any],
    output_dir: Path,
    options: PythonClientOptions,
    *,
    check: bool = False,
) -> tuple[Path, ...]:
    changed: list[Path] = []
    for relative_path, content in render_python_client(document, options).items():
        path = output_dir / relative_path
        if path.exists() and path.read_text(encoding="utf-8") == content:
            continue
        changed.append(path)
        if not check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
    return tuple(changed)


class _Imports:
    """Collects the ``from module import name`` pairs a module needs."""

    def __init__(self) -> None:
        self._pairs: set[tuple[str, str]] = set()

    def add(self, module: str, *names: str) -> None:
        self._pairs.update((module, name) for name in names)

    def render(self) -> str:
        groups: tuple[dict[str, set[str]], ...] = ({}, {}, {}, {})
        for module, name in self._pairs:
            groups[self._group(module)].setdefault(module, set()).add(name)
        blocks = [
            "\n".join(
                _render_import(module, _sorted_names(names))
                for module, names in sorted(group.items(), key=_sort_key)
            )
            for group in groups
            if group
        ]
        return "\n\n".join(blocks)

    def _group(self, module: str) -> int:
        """Place the module in its isort section: stdlib, third party, ours, local."""
        if module.startswith("."):
            return 3
        root = module.split(".")[0]
        if root in FIRST_PARTY_ROOTS:
            return 2
        return 1 if root in THIRD_PARTY_ROOTS else 0


class _TypeResolver:
    """Maps JSON Schema fragments onto Python type expressions."""

    def __init__(self, imports: _Imports) -> None:
        self._imports = imports

    def resolve(self, schema: dict[str, Any] | None) -> str:
        if not schema:
            return self._any()
        if reference := schema.get("$ref"):
            return _ref_name(reference)
        if "const" in schema:
            return self._literal([schema["const"]])
        if "enum" in schema:
            return self._literal(schema["enum"])
        if members := schema.get("anyOf") or schema.get("oneOf"):
            return self._union(self.resolve(member) for member in members)
        return self._by_type(schema)

    def _by_type(self, schema: dict[str, Any]) -> str:
        schema_type = schema.get("type")
        if schema_type is None:
            return self._any()
        if isinstance(schema_type, list):
            return self._union(
                self.resolve({**schema, "type": member}) for member in schema_type
            )
        if schema_type == "array":
            return f"list[{self.resolve(schema.get('items'))}]"
        if schema_type == "object":
            return f"dict[str, {self.resolve(schema.get('additionalProperties'))}]"
        if schema_type == "string" and (name := FORMATS.get(schema.get("format", ""))):
            self._imports.add(name[1], name[0])
            return name[0]
        if primitive := PRIMITIVES.get(schema_type):
            return primitive
        raise UnsupportedSchemaError(f"Unsupported schema type: {schema_type!r}")

    def _any(self) -> str:
        self._imports.add("typing", "Any")
        return "Any"

    def _literal(self, values: Iterable[Any]) -> str:
        self._imports.add("typing", "Literal")
        rendered = ", ".join(_value(value) for value in values)
        return f"Literal[{rendered}]"

    def _union(self, members: Iterable[str]) -> str:
        unique = list(dict.fromkeys(members))
        if "None" in unique:
            unique = [member for member in unique if member != "None"] + ["None"]
        return " | ".join(unique)


class _ModelsRenderer:
    def __init__(
        self, schemas: dict[str, dict[str, Any]], options: PythonClientOptions
    ) -> None:
        self._schemas = schemas
        self._options = options
        self._imports = _Imports()
        self._types = _TypeResolver(self._imports)

    def render(self) -> str:
        blocks = [
            self._declaration(name, self._schemas[name])
            for name in _ordered_names(self._schemas)
        ]
        return _module(self._options.source, self._imports, blocks)

    def _declaration(self, name: str, schema: dict[str, Any]) -> str:
        if "enum" in schema:
            return self._enum(name, schema)
        return self._model(name, schema)

    def _enum(self, name: str, schema: dict[str, Any]) -> str:
        self._imports.add("enum", "StrEnum")
        members = "\n".join(
            f"    {_enum_member(value)} = {_value(value)}" for value in schema["enum"]
        )
        return f"class {name}(StrEnum):\n{members}"

    def _model(self, name: str, schema: dict[str, Any]) -> str:
        self._imports.add("pydantic", "BaseModel")
        properties: dict[str, Any] = schema.get("properties", {})
        if not properties:
            return f"class {name}(BaseModel):\n    pass"
        required = set(schema.get("required", ()))
        fields = "\n".join(
            self._field(field_name, field_schema, field_name in required)
            for field_name, field_schema in properties.items()
        )
        return f"class {name}(BaseModel):\n{fields}"

    def _field(self, name: str, schema: dict[str, Any], required: bool) -> str:
        if not name.isidentifier() or keyword.iskeyword(name):
            raise UnsupportedSchemaError(f"Unsupported property name: {name!r}")
        annotation = self._types.resolve(schema)
        if required:
            return f"    {name}: {annotation}"
        if "default" in schema:
            return f"    {name}: {annotation} = {_value(schema['default'])}"
        if not annotation.endswith("None"):
            annotation = f"{annotation} | None"
        return f"    {name}: {annotation} = None"


@dataclass(frozen=True, slots=True)
class _Parameter:
    name: str
    annotation: str
    required: bool


@dataclass(frozen=True, slots=True)
class _Operation:
    name: str
    method: str
    path: str
    summary: str
    path_params: tuple[_Parameter, ...]
    query_params: tuple[_Parameter, ...]
    body_type: str | None
    body_required: bool
    return_type: str | None


class _ClientRenderer:
    def __init__(self, document: dict[str, Any], options: PythonClientOptions) -> None:
        self._document = document
        self._options = options
        self._imports = _Imports()
        self._types = _TypeResolver(self._imports)

    def render(self) -> str:
        operations = self._operations()
        self._imports.add("httpx2", "AsyncClient")
        self._imports.add(self._options.transport_module, "HttpTransport")
        self._imports.add(".models", *self._model_names(operations))
        return _module(self._options.source, self._imports, [self._class(operations)])

    def _model_names(self, operations: tuple[_Operation, ...]) -> tuple[str, ...]:
        candidates = (
            name
            for operation in operations
            for name in (operation.body_type, operation.return_type)
            if name is not None
        )
        return tuple({name for name in candidates if name.isidentifier()})

    def _class(self, operations: tuple[_Operation, ...]) -> str:
        info = self._document.get("info", {})
        parts = (info.get("title"), info.get("version"))
        title = " ".join(part for part in parts if part)
        name = self._options.client_name
        header = "\n".join(
            (
                f"class {name}:",
                f'    """Typed async client for {title}."""',
                "",
                "    def __init__(",
                "        self,",
                "        base_url: str,",
                "        *,",
                "        client: AsyncClient | None = None,",
                "    ) -> None:",
                "        self._transport = HttpTransport(base_url, client=client)",
                "",
                f"    async def __aenter__(self) -> {name}:",
                "        await self._transport.__aenter__()",
                "        return self",
                "",
                "    async def __aexit__(self, *exc_info: object) -> None:",
                "        await self._transport.__aexit__(*exc_info)",
                "",
                "    async def aclose(self) -> None:",
                "        await self._transport.aclose()",
            )
        )
        methods = "\n\n".join(self._method(operation) for operation in operations)
        return f"{header}\n\n{methods}" if methods else header

    def _method(self, operation: _Operation) -> str:
        lines = [self._signature(operation)]
        if operation.summary:
            lines.append(f'        """{operation.summary}."""')
        lines.extend(self._call(operation))
        return "\n".join(lines)

    def _signature(self, operation: _Operation) -> str:
        arguments = ["self"]
        arguments += [
            f"{parameter.name}: {parameter.annotation}"
            for parameter in operation.path_params
        ]
        if operation.body_type:
            suffix = "" if operation.body_required else " | None = None"
            arguments.append(f"body: {operation.body_type}{suffix}")
        arguments += [
            f"{parameter.name}: {parameter.annotation}"
            for parameter in operation.query_params
            if parameter.required
        ]
        optional = [
            f"{parameter.name}: {parameter.annotation} | None = None"
            for parameter in operation.query_params
            if not parameter.required
        ]
        if optional:
            arguments += ["*", *optional]

        return_type = operation.return_type or "None"
        joined = ", ".join(arguments)
        inline = f"    async def {operation.name}({joined}) -> {return_type}:"
        if len(inline) <= LINE_LENGTH:
            return inline
        wrapped = "\n".join(f"        {argument}," for argument in arguments)
        return f"    async def {operation.name}(\n{wrapped}\n    ) -> {return_type}:"

    def _call(self, operation: _Operation) -> list[str]:
        assignment = "response = " if operation.return_type else ""
        path = f'"{operation.path}"'
        if operation.path_params:
            path = f"f{path}"
        lines = [
            f"        {assignment}await self._transport.request(",
            f'            "{operation.method.upper()}",',
            f"            {path},",
        ]
        if operation.query_params:
            entries = ", ".join(
                f'"{parameter.name}": {parameter.name}'
                for parameter in operation.query_params
            )
            lines.append(f"            params={{{entries}}},")
        if operation.body_type:
            lines.append('            json=body.model_dump(mode="json"),')
        lines.append("        )")
        if operation.return_type:
            lines.append(f"        return {self._validate(operation.return_type)}")
        return lines

    def _validate(self, annotation: str) -> str:
        if annotation.isidentifier():
            return f"{annotation}.model_validate(response.json())"
        self._imports.add("pydantic", "TypeAdapter")
        return f"TypeAdapter({annotation}).validate_python(response.json())"

    def _operations(self) -> tuple[_Operation, ...]:
        return tuple(
            self._operation(path, method, item[method])
            for path, item in self._document.get("paths", {}).items()
            for method in METHOD_ORDER
            if method in item
        )

    def _operation(
        self, path: str, method: str, operation: dict[str, Any]
    ) -> _Operation:
        parameters = operation.get("parameters", ())
        request_body = operation.get("requestBody", {})
        body_schema = request_body.get("content", {}).get("application/json")
        return _Operation(
            name=operation["operationId"],
            method=method,
            path=path,
            summary=operation.get("summary", ""),
            path_params=self._parameters(parameters, "path"),
            query_params=self._parameters(parameters, "query"),
            body_type=self._types.resolve(body_schema["schema"])
            if body_schema
            else None,
            body_required=bool(request_body.get("required", True)),
            return_type=self._return_type(operation),
        )

    def _parameters(
        self, parameters: Iterable[dict[str, Any]], location: str
    ) -> tuple[_Parameter, ...]:
        return tuple(
            _Parameter(
                name=parameter["name"],
                annotation=self._types.resolve(parameter.get("schema")),
                required=bool(parameter.get("required")),
            )
            for parameter in parameters
            if parameter.get("in") == location
        )

    def _return_type(self, operation: dict[str, Any]) -> str | None:
        responses = operation.get("responses", {})
        successes = sorted(
            status
            for status in responses
            if status.isdigit() and 200 <= int(status) < 300
        )
        if not successes:
            return None
        content = responses[successes[0]].get("content", {}).get("application/json")
        return self._types.resolve(content["schema"]) if content else None


def _render_init(model_names: tuple[str, ...], options: PythonClientOptions) -> str:
    imports = [f"from .client import {options.client_name}"]
    if model_names:
        imports.append("from .models import (")
        imports += [f"    {name}," for name in _sorted_names(model_names)]
        imports.append(")")
    exports = "\n".join(
        f'    "{name}",' for name in sorted((options.client_name, *model_names))
    )
    header = GENERATED_HEADER.format(source=options.source)
    body = "\n".join(imports)
    return f"{header}\n{body}\n\n__all__ = [\n{exports}\n]\n"


def _module(source: str, imports: _Imports, blocks: list[str]) -> str:
    header = GENERATED_HEADER.format(source=source)
    rendered = imports.render()
    prefix = f"{header}\n{rendered}\n" if rendered else header
    body = "\n\n\n".join(block for block in blocks if block)
    return f"{prefix}\n\n{body}\n"


def _ordered_names(schemas: dict[str, dict[str, Any]]) -> tuple[str, ...]:
    """Order schema names so every referenced model is declared first."""
    ordered: list[str] = []
    visiting: set[str] = set()

    def visit(name: str) -> None:
        if name in ordered or name in visiting:
            return
        visiting.add(name)
        for dependency in sorted(_references(schemas[name])):
            if dependency in schemas:
                visit(dependency)
        visiting.discard(name)
        ordered.append(name)

    for name in sorted(schemas):
        visit(name)
    return tuple(ordered)


def _references(node: Any) -> set[str]:
    if isinstance(node, dict):
        if reference := node.get("$ref"):
            return {_ref_name(reference)}
        return {name for value in node.values() for name in _references(value)}
    if isinstance(node, list):
        return {name for value in node for name in _references(value)}
    return set()


def _ref_name(reference: str) -> str:
    if not reference.startswith(REF_PREFIX):
        raise UnsupportedSchemaError(f"Unsupported reference: {reference!r}")
    return reference.removeprefix(REF_PREFIX)


def _render_import(module: str, names: list[str]) -> str:
    """Render one import, wrapping it when the inline form is too long."""
    inline = f"from {module} import {', '.join(names)}"
    if len(inline) <= LINE_LENGTH:
        return inline
    wrapped = "\n".join(f"    {name}," for name in names)
    return f"from {module} import (\n{wrapped}\n)"


def _sorted_names(names: Iterable[str]) -> list[str]:
    """Sort imported names the way the project's isort configuration does."""
    return sorted(names, key=str.lower)


def _sort_key(entry: tuple[str, set[str]]) -> str:
    return entry[0].lower()


def _value(value: Any) -> str:
    """Render a schema constant the way the project formats literals."""
    return json.dumps(value) if isinstance(value, str) else repr(value)


def _enum_member(value: object) -> str:
    member = re.sub(r"[^0-9a-zA-Z]+", "_", str(value)).strip("_").upper()
    return f"_{member}" if not member or member[0].isdigit() else member
