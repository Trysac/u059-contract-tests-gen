# contract-tests-gen

[![PyPI version](https://img.shields.io/pypi/v/trysac-contract-tests-gen)](https://pypi.org/project/trysac-contract-tests-gen/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-contract-tests-gen)](LICENSE)
[![CI](https://github.com/Trysac/u059-contract-tests-gen/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u059-contract-tests-gen/actions/workflows/ci.yml)

Generate readable pytest contract tests from an OpenAPI 3.x document, injection-safe, with a small schema validator, injectable transport and drift check.

## Problem

Contract drift between an API and its OpenAPI document is usually discovered by clients in production. Property-based tools can find it but are heavy and leave no reviewable artifact. contract-tests-gen generates plain pytest files from the spec, giving a committed, readable suite that CI can regenerate and diff.

## Install

```sh
pip install trysac-contract-tests-gen
# or
uv add trysac-contract-tests-gen
```

Requires Python 3.10 or newer. Runtime dependency: PyYAML >= 6.0, < 7.

## Usage

```python
from pathlib import Path
from contract_tests_gen import extract_cases, load_spec, render_module

spec = load_spec(Path("openapi.yaml"))
cases = extract_cases(spec)
source = render_module(cases, spec_sha256="0" * 64)
Path("test_contract.py").write_text(source, encoding="utf-8")
print(len(cases), "contract tests generated")
```

## Public API

- `load_spec(path, *, max_bytes=10_485_760) -> dict`: reads at most `max_bytes + 1` bytes; accepts JSON or YAML with OpenAPI 3.0.x or 3.1.x; resolves local `$ref` only.
- `extract_cases(spec, *, include_tags=None) -> list[ContractCase]`: one case per operation and documented 2xx response; at most 5000 cases.
- `render_module(cases, *, spec_sha256, base_url_env='CONTRACT_BASE_URL', auth_env='CONTRACT_AUTH_HEADER') -> str`: renders pytest source with a do-not-edit header.
- `validate_instance(instance, schema) -> list[str]`: validates against a JSON Schema subset (type, required, properties, additionalProperties false, items, enum, nullable, minimum, maximum, minLength, maxLength, oneOf, anyOf). `format` is ignored.
- `Transport` (Protocol) and `UrllibTransport(timeout=10.0, max_body_bytes=10_485_760)`: http and https only; never follows redirects; reads at most `max_body_bytes + 1`.
- `ContractGenError`: carries `code` in `invalid_spec`, `unsupported_version`, `too_large`, `too_deep`, `unresolved_ref`, `unsupported_scheme`.
- CLI: `contract-tests-gen <spec> -o <file> [--tag TAG ...] [--check]`; exit 0 written or up to date, 1 drift, 2 errors.

Limits: no fuzzing, no stateful or authentication flows, no response header checks, no full JSON Schema support. Generated tests read the base URL from `CONTRACT_BASE_URL` and skip when it is unset; the transport can be overridden with a `contract_transport` fixture.

See [docs/SECURITY.md](docs/SECURITY.md) for the threat model.

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
