# Generate plain pytest files with a tiny runtime validator

Status: accepted (generated, pending human review)

## Context

Contract drift between an API and its OpenAPI document is found late. Property-based tools such as schemathesis are runtime-heavy and leave no reviewable artifact. A committed, deterministic test file can be regenerated and diffed in CI.

## Decision

Render pytest source from OpenAPI 3.x cases. Every spec-derived value enters the source only through repr() of plain types or as a sanitised identifier, never in comments or f-strings, and the module imports only json, os, pytest and contract_tests_gen.runtime. Response checking uses a small in-house JSON Schema subset validator. Transport is injectable via a contract_transport fixture, with a urllib default that allows only http/https and never follows redirects so credentials cannot be forwarded to another host. Specs are parsed with yaml.safe_load only, with size, depth and case-count limits.

## Consequences

Output is reviewable and byte-reproducible, so a --check drift gate works. Injection through spec text is structurally prevented. The validator is intentionally not full JSON Schema (no format, patterns, allOf, fuzzing, stateful or auth flows), and PyYAML becomes the only runtime dependency.
