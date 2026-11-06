# Testing

## Running

```sh
uv run pytest --cov=contract_tests_gen   # tests with coverage report
uv run python scripts/check.py      # every gate, as CI and the factory run it
```

## Policy

- Branch coverage of `src/contract_tests_gen` must stay at or above 80 %; the gate fails below it.
- Tests exercise the public API (`import contract_tests_gen`) and assert observable effects: return values, raised exceptions and their codes or messages.
- Each bug fix starts with a failing test that reproduces it.
- Tests are deterministic: no network, no wall clock, no dependence on test order.

## Layout

`tests/test_<module>.py` mirrors each public module. Shared fixtures go in `tests/conftest.py`. The test files that exist are checked by `scripts/check.py`; the acceptance criteria covered are: case ordering and identifier deduplication, byte-identical rendering with the do-not-edit header, injection-safe output, validator behaviour, the no-redirect transport and scheme rejection, and CLI exit codes including `--check`.
