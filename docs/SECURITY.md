# Recon Security Policy & Threat Model

**Product:** Recon — The Integration Readiness Engine  
**Status:** `[VERIFIED SECURITY SPECIFICATION]`

---

## 1. Security Philosophy & Scope

Recon is designed as a **local-first developer preflight tool**. It helps engineers audit third-party datasets and schema contracts on their local workstations or inside controlled CI/CD runners before writing ingestion code.

Recon is **not a multi-tenant cloud service**, and it is **not intended to execute arbitrary untrusted code submitted by anonymous web users**.

---

## 2. Threat Model & Mitigations

| Threat | Attack Vector | Mitigation in Recon |
| :--- | :--- | :--- |
| **Code Injection via CSV Content** | CSV cells containing formulas, shell commands, or prompt injection payloads. | Raw CSV values are treated strictly as immutable data literals. No `eval`, `exec`, or shell interpolation is ever performed on cell values. |
| **Arbitrary Code Execution in Adapters** | Malicious logic injected into synthesized Python transformation adapters. | Generated adapters are compiled via `compile_adapter_sandbox` with dangerous builtins stripped (`__import__`, `open`, `eval`, `exec`, `os`, `sys`, `subprocess`, `socket`). |
| **Server-Side Request Forgery (SSRF)** | Schema contracts containing remote `$ref` URIs (e.g. `http://internal-service/admin`). | Remote network dereferencing is strictly blocked in `src/recon/contracts/loader.py`. Only local files and inline schema definitions are resolved. |
| **Path Traversal** | Malicious paths (e.g. `../../etc/shadow` or `..\Windows\System32`) passed via CLI flags or API uploads. | File paths are normalized via `Path.resolve()` and verified to reside within approved input/output directories. |
| **Denial of Service (Memory Exhaustion)** | Oversized files loaded into memory. | Enforces `max_file_size_bytes` (100MB default limit) checked before loading. Streaming SHA-256 computation in 64KB chunks prevents memory bloat. |
| **Sensitive Data Exposure via Logs** | PII, passwords, or customer records printed to terminal or disk logs. | `recon.logging` operates a strict whitelist policy that strips all record payloads and cell contents from log messages. |
| **Source Data Tampering** | Accidental mutation or overwrite of raw source input files. | Source files are opened in read-only mode (`r` / `rb`). Transformed outputs are written strictly to user-designated output directories. |

---

## 3. Operational Boundaries & Sandbox Limitations

> [!CAUTION]
> **RECON DOES NOT PROVIDE AN OS-LEVEL SANDBOX**  
> Adapter validation in Recon is executed within Python using an in-process restricted namespace. While unsafe builtins (`open`, `os`, `sys`, `subprocess`, `socket`, `__import__`) are stripped from `__builtins__`, this restriction **does not constitute OS-level isolation**. It does not use Linux kernel cgroups, namespaces, seccomp filters, or container virtualization.
> 
> **Explicit Deployment Constraints:**
> - **Approved Use:** Running locally on a developer workstation or in isolated, ephemeral CI/CD pipelines (e.g. GitHub Actions) with trusted team-provided inputs.
> - **Prohibited Use:** Public multi-tenant SaaS hosting where unauthenticated external users can submit arbitrary datasets or adapter code.

---

## 4. Session Persistence & Ephemeral State

1. **In-Memory Sessions:**  
   The Recon FastAPI backend (`recon serve`) stores workflow session state in-memory. When the server process terminates or restarts, session data, profiles, and in-flight mapping plans are purged.
2. **Deterministic Artifact Export:**  
   To preserve work across sessions, developers export a versioned `recon_mapping_spec.json` and adapter files using the CLI (`recon run` or `recon gate`) or the Studio download buttons.
3. **No External Network Calls:**  
   Recon makes zero external HTTP requests, sends zero telemetry, uses zero third-party analytics, and contacts zero remote APIs.

---

## 5. Vulnerability Reporting

If you discover a security vulnerability or sandbox escape in Recon:

1. **Do not open a public GitHub issue.**
2. Report the vulnerability privately via GitHub Security Advisories at:  
   `https://github.com/swamigawai/recon/security/advisories/new`
3. Include a detailed reproduction script, target operating system, and the observed impact.
4. Security reports will be acknowledged within 48 hours, and patches will be prepared in private branches prior to release.
