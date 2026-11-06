# contract-tests-gen

[![PyPI version](https://img.shields.io/pypi/v/trysac-contract-tests-gen)](https://pypi.org/project/trysac-contract-tests-gen/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-contract-tests-gen)](LICENSE)
[![CI](https://github.com/Trysac/u059-contract-tests-gen/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u059-contract-tests-gen/actions/workflows/ci.yml)

Generate readable pytest contract tests from an OpenAPI 3.x document, injection-safe, with a small schema validator, injectable transport and drift check

## Problem

Describe in two or three sentences the concrete problem this utility solves, who hits it, and what
they do today without it. Replace this paragraph when the first real feature lands.

## Install

```sh
pip install trysac-contract-tests-gen
# or
uv add trysac-contract-tests-gen
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

```python
import contract_tests_gen

# normalize() trims surrounding whitespace and lower-cases the text.
print(contract_tests_gen.normalize("  Hello World "))  # -> "hello world"

# Blank input is rejected explicitly instead of returning an empty string.
try:
    contract_tests_gen.normalize("   ")
except ValueError as exc:
    print(f"rejected: {exc}")
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
