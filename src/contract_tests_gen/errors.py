"""Typed errors for contract-tests-gen."""

from __future__ import annotations

from typing import Literal

ErrorCode = Literal[
    "invalid_spec",
    "unsupported_version",
    "too_large",
    "too_deep",
    "unresolved_ref",
    "unsupported_scheme",
]


class ContractGenError(Exception):
    """Base error of the library; ``code`` is a stable machine-readable identifier."""

    def __init__(self, code: ErrorCode, message: str) -> None:
        self.code: ErrorCode = code
        self.message = message[:200]
        super().__init__(f"{code}: {self.message}")
