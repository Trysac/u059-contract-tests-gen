# Project record

## Objective

Contract drift between an API and its OpenAPI document is discovered by clients in production. Generate readable pytest contract tests from an OpenAPI 3.x document, so a committed, reviewable suite can be regenerated and diffed in CI.

## Scope

- In scope: loading OpenAPI 3.0.x and 3.1.x documents (JSON or YAML) with local `$ref` resolution; extracting one case per operation and documented 2xx response; rendering a deterministic, injection-safe pytest module; a schema validator for a JSON Schema subset; an injectable HTTP transport that never follows redirects; a CLI with a `--check` drift mode.
- Out of scope: fuzzing, stateful or authentication flows, response header assertions, full JSON Schema support. Property-based tools such as schemathesis were not chosen because they are runtime-heavy and leave no reviewable artifact.

## Timeline

| Date | Event |
|---|---|
| 2026 | Repository created from the factory utility template. |

## Effort metrics

Measured values only; a value that has not been measured stays "pending measurement".

| Metric | Value |
|---|---|
| Tokens (input / output) | 146742 / 305148 |
| Hours (human) | pending measurement |
| Cost (USD) | 1.5857 |

## Factory run u059 (measured from API usage)

| Phase | Model | Batch | Input | Output | Cache write | Cache read | Cost (USD) |
|---|---|---|---|---|---|---|---|
| generation | claude-sonnet-5-5 | yes | 2316 | 128000 | 0 | 4246 | 0.6427 |
| generation | claude-sonnet-5-5 | yes | 2316 | 128000 | 0 | 4246 | 0.6427 |
| generation | claude-sonnet-5-5 | yes | 2316 | 44443 | 0 | 4246 | 0.2250 |
| audit | claude-sonnet-5-5 | no | 0 | 0 | 0 | 0 | 0.0000 |
| docs | claude-haiku-5-5 | no | 127056 | 4705 | 0 | 0 | 0.0753 |

Total: $1.5857. Prices: Anthropic list prices.
