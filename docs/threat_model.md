# Recon Threat Model

## 1. Trust Boundaries & Assumptions

Recon treats all inputs as **untrusted data**, including:
1. Source dataset contents (cell values, line breaks, encoding).
2. Source column headers (naming, length, character sets).
3. Target schema contracts provided by external systems.
4. Generated adapter transformation code.

---

## 2. Threat Analysis & Mitigations

| Threat | Attack Vector | Recon Mitigation |
| :--- | :--- | :--- |
| **Code Injection via CSV Content** | CSV cells containing executable commands or prompt injections. | Raw CSV values are treated strictly as immutable data strings. No eval, exec, or shell interpolation is ever performed on CSV cell values. |
| **Path Traversal** | Malicious paths (e.g. `../../etc/passwd` or `..\Windows\System32`) in source/output flags. | `Path.resolve()` is enforced on all file paths; paths are verified to be regular files and output directories are explicitly isolated. |
| **Sensitive Data Exposure via Logs** | PII, financial details, or secrets printed to logs. | `recon.logging` operates a strict whitelist policy that strips all `raw_*` record parameters and payloads before writing log messages. |
| **Arbitrary Code Execution in Generated Code** | Malicious modifications to generated adapter code. | Generated adapters are compiled in a restricted execution namespace (`compile_adapter_sandbox`) with `eval` and `exec` stripped from builtins. Adapters are never executed silently without explicit user invocation. |
| **Memory Exhaustion (DoS)** | Giant gigabyte-sized CSV files loaded into memory. | Enforces `IngestionConfig.max_file_size_bytes` (100MB ceiling default) and checks file size before opening. Streaming SHA-256 computation in 64KB chunks prevents memory bloat. |
| **Source Data Mutation** | Overwriting original data files during pipeline runs. | Raw input files are strictly read-only. Generated outputs are written exclusively to isolated output directories specified by the user. |
