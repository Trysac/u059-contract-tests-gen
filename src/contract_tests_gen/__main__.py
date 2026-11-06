"""Command line interface."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from .errors import ContractGenError
from .render import render_module
from .spec import extract_cases, parse_spec, read_spec_bytes


def main(argv: list[str] | None = None) -> int:
    """Run the CLI; returns 0 written/up to date, 1 drift, 2 errors."""
    parser = argparse.ArgumentParser(
        prog="contract-tests-gen", description="Generate pytest contract tests from OpenAPI."
    )
    parser.add_argument("spec", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument("--check", action="store_true")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2
    try:
        data = read_spec_bytes(args.spec)
        cases = extract_cases(parse_spec(data), include_tags=set(args.tag) or None)
        text = render_module(cases, spec_sha256=hashlib.sha256(data).hexdigest())
    except ContractGenError as exc:
        print(f"error: {exc.code}: {exc.message}", file=sys.stderr)
        return 2
    new = text.encode("utf-8")
    output: Path = args.output
    try:
        existing = output.read_bytes() if output.exists() else None
        if args.check:
            if existing == new:
                return 0
            print("drift: generated tests differ from the target", file=sys.stderr)
            return 1
        if existing != new:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(new)
    except OSError:
        print("error: cannot access output file", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
