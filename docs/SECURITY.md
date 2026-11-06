# Security notes

## Threat model

`trysac-contract-tests-gen` reads a spec file and, when generated tests run, performs HTTP requests.

Defended:

- **Code injection from the spec**: every value from the spec enters the generated source only through `repr()` of str, int, float, bool, None, list or dict, or as a sanitised identifier. Spec text is never placed in comments or f-strings. The renderer rejects unsupported value types.
- **Redirect leakage of the auth header**: `UrllibTransport` never follows redirects, so `CONTRACT_AUTH_HEADER` is not forwarded to another host.
- **Non-HTTP schemes**: `UrllibTransport` only allows `http` and `https`; other schemes raise `unsupported_scheme`.
- **Oversized input**: `load_spec` reads at most `max_bytes + 1` bytes (default 10 MiB) and raises `too_large`; response bodies are capped by `max_body_bytes`.
- **Deep nesting**: parsing, `$ref` resolution, example extraction and validation are bounded by depth 64; cyclic `$ref` chains become an empty schema. Case extraction stops at 5000 cases.
- **YAML loading**: only `yaml.safe_load` is used.
- **Secrets in output**: the generated file contains no base URL or auth value; assertion messages include status and validation errors, never headers.
- **Path values**: path parameters are encoded with `urllib.parse.quote(safe='')`.

Not defended:

- The library does not authenticate the server or validate TLS policy beyond the standard library defaults.
- Responses are read into memory up to the cap; the timeout is 10 seconds by default and applies per socket operation.
- The schema validator is a subset of JSON Schema; `format` is ignored, so it does not catch format violations.
- Header values from `CONTRACT_AUTH_HEADER` are validated for shape only; their content is trusted.
- Supply chain: PyYAML is the only runtime dependency. Mitigation: Dependabot weekly updates, actions pinned to major versions, minimal workflow permissions, and `gitleaks` in the local gates and CI.

To report a vulnerability, see [SECURITY.md](../SECURITY.md).
