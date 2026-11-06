# Architecture

## Purpose

`trysac-contract-tests-gen` is a small Python library (import name `contract_tests_gen`) that generates readable pytest contract tests from an OpenAPI 3.0/3.1 document, with a small schema validator, an injectable transport and a drift check. Its only runtime dependency is PyYAML.

## Shape

```text
caller code --> contract_tests_gen (public API in __init__.py)
                    |
                    +-- spec.py     load and parse spec, extract cases
                    +-- render.py   emit pytest source (repr-only literals)
                    +-- runtime.py validator, transport, request helpers used by generated tests
                    +-- __main__.py CLI with --check drift mode
```

- **Public API**: the names listed in `__all__` of `src/contract_tests_gen/__init__.py`.
- **Errors**: `ContractGenError` with a stable `code` attribute. The library does not print or exit; only the CLI writes to stderr.
- **Logging**: a module logger with a NullHandler; the library never configures logging.
- **Side effects**: reading the spec file in `load_spec`, and the transport performing HTTP requests when generated tests run. The CLI writes the output file.

## Quality contract

The quality gates are described in [TESTING.md](TESTING.md). Project configuration is in `pyproject.toml` and `fabrica.json`.

## Decisions

Architecture decisions are recorded in [decisions/](decisions/) as numbered ADRs.
