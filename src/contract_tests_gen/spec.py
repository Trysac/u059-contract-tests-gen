"""Load OpenAPI documents and extract contract cases."""

from __future__ import annotations

import datetime
import json
import logging
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import yaml  # type: ignore[import-untyped]  # PyYAML ships no type stubs

from .errors import ContractGenError

logger = logging.getLogger(__name__)

MAX_DEPTH = 64
MAX_CASES = 5000
METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")
_PLACEHOLDER = re.compile(r"\{([^{}]+)\}")
_MISSING: Any = object()


@dataclass(frozen=True)
class ContractCase:
    """One generated contract test: an operation and one documented 2xx response."""

    case_id: str
    method: str
    path_template: str
    path_params: dict[str, Any]
    query: dict[str, Any]
    body: Any
    expected_status: int
    response_schema: dict[str, Any] | None
    skip_reason: str | None


def sanitize_id(raw: str) -> str:
    """Turn arbitrary text into a lowercase identifier made of [a-z0-9_]."""
    cleaned = re.sub(r"[^a-z0-9_]+", "_", raw.lower())
    if cleaned[:1].isdigit():
        cleaned = "op_" + cleaned
    return cleaned


def read_spec_bytes(path: Path, *, max_bytes: int = 10_485_760) -> bytes:
    """Read at most ``max_bytes`` bytes of ``path``; larger files raise ``too_large``."""
    try:
        with path.open("rb") as handle:
            data = handle.read(max_bytes + 1)
    except OSError as exc:
        raise ContractGenError("invalid_spec", "cannot read spec file") from exc
    if len(data) > max_bytes:
        raise ContractGenError("too_large", f"spec exceeds {max_bytes} bytes")
    return data


def parse_spec(data: bytes) -> dict[str, Any]:
    """Parse JSON or YAML bytes and check the OpenAPI version."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ContractGenError("invalid_spec", "spec is not valid UTF-8") from exc
    try:
        try:
            doc = json.loads(text)
        except ValueError:
            doc = yaml.safe_load(text)
    except RecursionError as exc:
        raise ContractGenError("too_deep", "document nesting too deep") from exc
    except yaml.YAMLError as exc:
        raise ContractGenError("invalid_spec", "spec is neither JSON nor YAML") from exc
    if not isinstance(doc, dict):
        raise ContractGenError("invalid_spec", "document must be a mapping")
    version = doc.get("openapi")
    if version is None:
        if "swagger" in doc:
            raise ContractGenError(
                "unsupported_version", "only OpenAPI 3.0.x and 3.1.x are supported"
            )
        raise ContractGenError("invalid_spec", "missing openapi field")
    if not isinstance(version, str):
        raise ContractGenError("invalid_spec", "openapi field must be a string")
    if not version.startswith(("3.0.", "3.1.")):
        raise ContractGenError("unsupported_version", "only OpenAPI 3.0.x and 3.1.x are supported")
    return doc


def load_spec(path: Path, *, max_bytes: int = 10_485_760) -> dict[str, Any]:
    """Load an OpenAPI 3.0.x/3.1.x document (JSON or YAML) from ``path``."""
    return parse_spec(read_spec_bytes(path, max_bytes=max_bytes))


def _lookup(spec: dict[str, Any], ref: str) -> Any:
    if not ref.startswith("#"):
        raise ContractGenError("unresolved_ref", "only local references are supported")
    pointer = ref[1:]
    node: Any = spec
    if pointer == "":
        return node
    if not pointer.startswith("/"):
        raise ContractGenError("unresolved_ref", f"bad reference {ref[:100]}")
    for raw in pointer[1:].split("/"):
        key = unquote(raw).replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict) and key in node:
            node = node[key]
        elif isinstance(node, list) and key.isdigit() and int(key) < len(node):
            node = node[int(key)]
        else:
            raise ContractGenError("unresolved_ref", f"cannot resolve {ref[:100]}")
    return node


def _inline(spec: dict[str, Any], node: Any, depth: int, stack: frozenset[str]) -> Any:
    """Resolve local $ref recursively; cyclic references become an empty schema."""
    if depth > MAX_DEPTH:
        raise ContractGenError("too_deep", "nesting or $ref chain too deep")
    if isinstance(node, dict):
        if "$ref" in node:
            ref = node["$ref"]
            if not isinstance(ref, str):
                raise ContractGenError("unresolved_ref", "$ref must be a string")
            if ref in stack:
                return {}
            return _inline(spec, _lookup(spec, ref), depth + 1, stack | {ref})
        return {k: _inline(spec, v, depth + 1, stack) for k, v in node.items()}
    if isinstance(node, list):
        return [_inline(spec, v, depth + 1, stack) for v in node]
    return node


def _plain(value: Any, depth: int = 0) -> Any:
    if depth > MAX_DEPTH:
        raise ContractGenError("too_deep", "example nesting too deep")
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, list):
        return [_plain(v, depth + 1) for v in value]
    if isinstance(value, dict):
        return {k: _plain(v, depth + 1) for k, v in value.items()}
    return value


def _schema_value(schema: Any) -> Any:
    if not isinstance(schema, dict):
        return _MISSING
    if "example" in schema:
        return schema["example"]
    examples = schema.get("examples")
    if isinstance(examples, list) and examples:
        return examples[0]
    if "default" in schema:
        return schema["default"]
    enum = schema.get("enum")
    if isinstance(enum, list) and enum:
        return enum[0]
    return _MISSING


def _param_value(param: dict[str, Any]) -> Any:
    if "example" in param:
        return param["example"]
    return _schema_value(param.get("schema"))


def _merge_params(*lists: Any) -> dict[tuple[str, str], dict[str, Any]]:
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for items in lists:
        if not isinstance(items, list):
            continue
        for param in items:
            if (
                isinstance(param, dict)
                and isinstance(param.get("name"), str)
                and isinstance(param.get("in"), str)
            ):
                merged[(param["in"], param["name"])] = param
    return merged


def _request_body(op: dict[str, Any]) -> Any:
    body = op.get("requestBody")
    if not isinstance(body, dict):
        return None
    content = body.get("content")
    media = content.get("application/json") if isinstance(content, dict) else None
    if not isinstance(media, dict):
        return None
    value = media["example"] if "example" in media else _schema_value(media.get("schema"))
    return None if value is _MISSING else _plain(value)


def _op_cases(
    path: str,
    method: str,
    op: dict[str, Any],
    params: dict[tuple[str, str], dict[str, Any]],
) -> list[ContractCase]:
    path_params: dict[str, Any] = {}
    skip: str | None = None
    for name in _PLACEHOLDER.findall(path):
        param = params.get(("path", name))
        value = _param_value(param) if param is not None else _MISSING
        if value is _MISSING:
            skip = skip or f"no example for path parameter {name}"
        else:
            path_params[name] = _plain(value)
    query: dict[str, Any] = {}
    for (location, name), param in sorted(params.items(), key=lambda kv: kv[0]):
        if location == "query":
            value = _param_value(param)
            if value is not _MISSING:
                query[name] = _plain(value)
    body = _request_body(op)
    raw_id = op.get("operationId")
    base = raw_id if isinstance(raw_id, str) and raw_id else f"{method}_{path}"
    responses = op.get("responses")
    if not isinstance(responses, dict):
        return []
    cases: list[ContractCase] = []
    for code in sorted(responses, key=str):
        status = str(code)
        if len(status) != 3 or not status.isdigit() or status[0] != "2":
            continue
        response = responses[code]
        schema: dict[str, Any] | None = None
        content = response.get("content") if isinstance(response, dict) else None
        media = content.get("application/json") if isinstance(content, dict) else None
        candidate = media.get("schema") if isinstance(media, dict) else None
        if isinstance(candidate, dict):
            schema = candidate
        cases.append(
            ContractCase(
                case_id=sanitize_id(base),
                method=method,
                path_template=path,
                path_params=dict(path_params),
                query=dict(query),
                body=body,
                expected_status=int(status),
                response_schema=schema,
                skip_reason=skip,
            )
        )
    return cases


def extract_cases(
    spec: dict[str, Any], *, include_tags: set[str] | None = None
) -> list[ContractCase]:
    """Return one case per operation and documented 2xx response, in stable order."""
    paths = spec.get("paths", {})
    if not isinstance(paths, dict):
        raise ContractGenError("invalid_spec", "paths must be a mapping")
    cases: list[ContractCase] = []
    used: set[str] = set()
    for path in sorted(paths, key=str):
        if not isinstance(path, str):
            raise ContractGenError("invalid_spec", "path keys must be strings")
        item = _inline(spec, paths[path], 0, frozenset())
        if not isinstance(item, dict):
            raise ContractGenError("invalid_spec", "path item must be a mapping")
        for method in METHODS:
            op = item.get(method)
            if op is None:
                continue
            if not isinstance(op, dict):
                raise ContractGenError("invalid_spec", "operation must be a mapping")
            if include_tags is not None:
                tags = op.get("tags")
                names = {t for t in tags if isinstance(t, str)} if isinstance(tags, list) else set()
                if not include_tags & names:
                    continue
            params = _merge_params(item.get("parameters"), op.get("parameters"))
            for case in _op_cases(path, method, op, params):
                unique = case.case_id
                n = 2
                while unique in used:
                    unique = f"{case.case_id}_{n}"
                    n += 1
                used.add(unique)
                cases.append(replace(case, case_id=unique))
                if len(cases) > MAX_CASES:
                    raise ContractGenError("too_large", f"more than {MAX_CASES} cases")
    logger.debug("extracted %d cases", len(cases))
    return cases
