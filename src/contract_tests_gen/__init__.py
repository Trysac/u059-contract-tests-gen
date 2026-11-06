"""Generate readable pytest contract tests from an OpenAPI 3.x document."""

from __future__ import annotations

import logging

from .errors import ContractGenError
from .render import render_module
from .runtime import Response, Transport, UrllibTransport, validate_instance
from .spec import ContractCase, extract_cases, load_spec

__all__ = [
    "ContractCase",
    "ContractGenError",
    "Response",
    "Transport",
    "UrllibTransport",
    "__version__",
    "extract_cases",
    "load_spec",
    "render_module",
    "validate_instance",
]

__version__ = "0.1.0"

logging.getLogger(__name__).addHandler(logging.NullHandler())
