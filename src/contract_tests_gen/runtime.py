"""Runtime support for generated tests: validator, transport and request helpers."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol, TypeGuard, cast
from urllib.parse import quote, urlencode, urlsplit

from .errors import ContractGenError

MAX_DEPTH = 64
MAX_ERRORS = 100
_PLACEHOLDER = re.compile(r"\{([^{}]+)\}")
_HEADER_NAME = re.compile(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+")


def _type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _is_num(value: Any) -> TypeGuard[int | float]:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _matches(value: Any, kind: str) -> bool:
    if kind == "integer":
        if isinstance(value, bool):
            return False
        return isinstance(value, int) or (isinstance(value, float) and value.is_integer())
    if kind == "number":
        return _is_num(value)
    if kind == "boolean":
        return isinstance(value, bool)
    if kind == "string":
        return isinstance(value, str)
    if kind == "null":
        return value is None
    if kind == "array":
        return isinstance(value, list)
    if kind == "object":
        return isinstance(value, dict)
    return False


def _same(a: Any, b: Any) -> bool:
    return isinstance(a, bool) == isinstance(b, bool) and bool(a == b)


def _add(errors: list[str], path: str, message: str) -> None:
    if len(errors) < MAX_ERRORS:
        errors.append(f"{path}: {message}"[:200])


def _validate(instance: Any, schema: Any, path: str, depth: int, errors: list[str]) -> None:
    if len(errors) >= MAX_ERRORS or not isinstance(schema, dict):
        return
    if depth > MAX_DEPTH:
        _add(errors, path, "schema nesting too deep")
        return
    if instance is None and schema.get("nullable") is True:
        return
    declared = schema.get("type")
    types: list[str] = []
    if isinstance(declared, str):
        types = [declared]
    elif isinstance(declared, list):
        types = [t for t in declared if isinstance(t, str)]
    if types and not any(_matches(instance, t) for t in types):
        _add(errors, path, f"expected type {'|'.join(types)}, got {_type_name(instance)}")
        return
    enum = schema.get("enum")
    if isinstance(enum, list) and not any(_same(instance, e) for e in enum):
        _add(errors, path, "value not in enum")
    for key in ("oneOf", "anyOf"):
        branches = schema.get(key)
        if isinstance(branches, list) and branches:
            ok = False
            for branch in branches:
                sub: list[str] = []
                _validate(instance, branch, path, depth + 1, sub)
                if not sub:
                    ok = True
                    break
            if not ok:
                _add(errors, path, f"does not match any schema of {key}")
    if _is_num(instance):
        minimum, maximum = schema.get("minimum"), schema.get("maximum")
        if _is_num(minimum) and instance < minimum:
            _add(errors, path, "value below minimum")
        if _is_num(maximum) and instance > maximum:
            _add(errors, path, "value above maximum")
    if isinstance(instance, str):
        min_len, max_len = schema.get("minLength"), schema.get("maxLength")
        if _is_num(min_len) and len(instance) < min_len:
            _add(errors, path, "string shorter than minLength")
        if _is_num(max_len) and len(instance) > max_len:
            _add(errors, path, "string longer than maxLength")
    if isinstance(instance, dict):
        required = schema.get("required")
        if isinstance(required, list):
            for name in required:
                if isinstance(name, str) and name not in instance:
                    _add(errors, path, f"missing required property {name}")
        properties = schema.get("properties")
        if isinstance(properties, dict):
            for key, sub_schema in properties.items():
                if key in instance:
                    _validate(instance[key], sub_schema, f"{path}.{key}", depth + 1, errors)
        if schema.get("additionalProperties") is False:
            known = properties if isinstance(properties, dict) else {}
            for key in instance:
                if key not in known:
                    _add(errors, path, f"unexpected property {key}")
    if isinstance(instance, list):
        items = schema.get("items")
        if isinstance(items, dict):
            for index, element in enumerate(instance):
                _validate(element, items, f"{path}[{index}]", depth + 1, errors)


def validate_instance(instance: Any, schema: Any) -> list[str]:
    """Validate ``instance`` against a small JSON Schema subset; return error strings."""
    errors: list[str] = []
    _validate(instance, schema, "$", 0, errors)
    return errors


@dataclass(frozen=True)
class Response:
    """A minimal HTTP response."""

    status: int
    headers: dict[str, str]
    body: bytes


class Transport(Protocol):
    """Anything that can perform an HTTP request."""

    def send(self, method: str, url: str, headers: dict[str, str], body: bytes | None) -> Response:
        """Send a request and return the response without following redirects."""
        ...


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


class UrllibTransport:
    """http/https transport that never follows redirects and caps the body size."""

    def __init__(self, timeout: float = 10.0, max_body_bytes: int = 10_485_760) -> None:
        self.timeout = timeout
        self.max_body_bytes = max_body_bytes

    def send(self, method: str, url: str, headers: dict[str, str], body: bytes | None) -> Response:
        """Send a request; only http and https URLs are allowed."""
        if urlsplit(url).scheme.lower() not in ("http", "https"):
            raise ContractGenError("unsupported_scheme", "only http and https are allowed")
        request = urllib.request.Request(  # noqa: S310
            url, data=body, headers=headers, method=method
        )
        opener = urllib.request.build_opener(_NoRedirect)
        try:
            reply = opener.open(request, timeout=self.timeout)
        except urllib.error.HTTPError as err:
            reply = err
        with reply:
            data = reply.read(self.max_body_bytes + 1)
            status = int(reply.status if hasattr(reply, "status") else reply.code)
            reply_headers = {k: v for k, v in reply.headers.items()}
        if len(data) > self.max_body_bytes:
            raise ContractGenError("too_large", "response body too large")
        return Response(status, reply_headers, data)


def _scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return str(value)


def send_case(
    transport: Transport,
    base_url: str,
    auth_header: str | None,
    method: str,
    path_template: str,
    path_params: dict[str, Any],
    query: dict[str, Any],
    body: bytes | None,
) -> Response:
    """Build the request for a generated test and send it."""

    def fill(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in path_params:
            raise ContractGenError("invalid_spec", f"missing path parameter {name[:50]}")
        return quote(_scalar(path_params[name]), safe="")

    path = _PLACEHOLDER.sub(fill, path_template)
    pairs = [
        (key, _scalar(item))
        for key, value in query.items()
        for item in (value if isinstance(value, list) else [value])
    ]
    url = base_url.rstrip("/") + path + ("?" + urlencode(pairs) if pairs else "")
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if auth_header:
        name, sep, value = auth_header.partition(":")
        name, value = name.strip(), value.strip()
        if not sep or _HEADER_NAME.fullmatch(name) is None or "\r" in value or "\n" in value:
            raise ContractGenError("invalid_spec", "auth header must have the form Name: value")
        headers[name] = value
    return transport.send(method, url, headers, body)


def check_response(response: Response, expected_status: int, schema: Any) -> list[str]:
    """Return problems found in ``response`` (status first, then body schema)."""
    if response.status != expected_status:
        return [f"expected status {expected_status}, got {response.status}"]
    if schema is None:
        return []
    try:
        document = json.loads(response.body.decode("utf-8"))
    except ValueError:
        return ["$: response body is not valid JSON"]
    return validate_instance(document, schema)


def get_transport(request: Any) -> Transport:
    """Return the ``contract_transport`` fixture if defined, else a UrllibTransport."""
    try:
        transport = request.getfixturevalue("contract_transport")
    except Exception as exc:
        if type(exc).__name__ != "FixtureLookupError":
            raise
        return UrllibTransport()
    return cast(Transport, transport)
