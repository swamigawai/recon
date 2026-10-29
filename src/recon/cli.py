"""Command Line Interface for Recon — The Integration Readiness Engine."""

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import recon
from recon.adapters.generator import generate_adapter
from recon.contracts.loader import load_target_contract
from recon.exceptions import ReconError
from recon.ingestion.loader import load_dataset
from recon.mapping.approval import approve_mapping_plan
from recon.mapping.models import MappingStatus
from recon.mapping.proposer import propose_mappings
from recon.mapping.specification import (
    load_mapping_spec,
    validate_and_apply_mapping_spec,
)
from recon.profiling.profiler import profile_dataset
from recon.reporting.generator import build_readiness_report, export_reports
from recon.risks.evaluator import evaluate_risks
from recon.validation.executor import validate_adapter


def cmd_profile(args: argparse.Namespace) -> int:
    """Runs deterministic profiling on a source dataset."""
    try:
        dataset = load_dataset(args.source)
        profile = profile_dataset(dataset)

        print("\n" + "=" * 60)
        print(f"RECON PROFILING REPORT: {dataset.file_name}")
        print("=" * 60)
        print(f"Total Rows:     {profile.total_rows:,}")
        print(f"Total Columns:  {profile.total_columns}")
        print(f"Duplicate Rows: {profile.duplicate_rows_count}")
        print(f"SHA-256 Digest: {profile.fingerprint[:16]}...")
        print("-" * 60)
        print(f"{'Column Name':<25} {'Inferred Type':<15} {'Nulls':<10} {'Distinct':<10}")
        print("-" * 60)
        for name, col in profile.columns.items():
            null_info = f"{col.null_count} ({col.null_percentage}%)"
            print(f"{name:<25} {col.inferred_type.value:<15} {null_info:<10} {col.distinct_count:<10}")
        print("=" * 60 + "\n")
        return 0
    except ReconError as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        return 1


def cmd_assess(args: argparse.Namespace) -> int:
    """Evaluates mapping proposals and integration risks for a dataset and target contract."""
    try:
        dataset = load_dataset(args.source)
        schema_name = getattr(args, "schema_name", None)
        contract = load_target_contract(args.contract, schema_name=schema_name)
        profile = profile_dataset(dataset)
        plan = propose_mappings(profile, contract)

        reused_info = ""
        if getattr(args, "mapping_spec", None):
            spec = load_mapping_spec(args.mapping_spec)
            plan, spec_val = validate_and_apply_mapping_spec(spec, contract, profile, plan)
            reused_info = f"Spec Mappings Reused: {spec_val.reused_count} (Contract Match: {spec_val.contract_match})\n"

        risks = evaluate_risks(profile, contract, plan)

        print("\n" + "=" * 70)
        print(f"RECON RISK ASSESSMENT: {dataset.file_name} -> {contract.contract_name}")
        print("=" * 70)
        if reused_info:
            print(reused_info.strip())
        print(f"Findings: {len(risks.findings)} (Critical: {len(risks.critical_findings)}, High: {len(risks.high_findings)}, Medium: {len(risks.medium_findings)}, Low: {len(risks.low_findings)})")
        print(f"Status:   {'BLOCKED' if risks.is_blocked else 'PASS / REVIEW NEEDED'}")
        print("-" * 70)
        if risks.findings:
            for f in risks.findings:
                print(f"[{f.severity.upper():<8}] {f.rule_id}: {f.rule_name}")
                print(f"  Fields: {', '.join(f.affected_fields)}")
                print(f"  Evidence: {f.evidence}")
                print(f"  Action:   {f.suggested_action}\n")
        else:
            print("No risk findings detected.\n")
        print("=" * 70 + "\n")
        return 0
    except ReconError as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        return 1


def cmd_run(args: argparse.Namespace) -> int:
    """Executes full end-to-end integration readiness workflow and exports reports."""
    try:
        out_dir = Path(args.output_dir)
        dataset = load_dataset(args.source)
        schema_name = getattr(args, "schema_name", None)
        contract = load_target_contract(args.contract, schema_name=schema_name)
        profile = profile_dataset(dataset)
        plan = propose_mappings(profile, contract)

        if getattr(args, "mapping_spec", None):
            spec = load_mapping_spec(args.mapping_spec)
            plan, spec_val = validate_and_apply_mapping_spec(spec, contract, profile, plan)
            print(f"Reused {spec_val.reused_count} mapping decisions from {args.mapping_spec}")

        risks = evaluate_risks(profile, contract, plan)

        # Approve mappings
        approved_plan = approve_mapping_plan(plan, reviewer="cli_user")

        # Generate adapter & validate
        adapter = generate_adapter(approved_plan, contract)
        validation = validate_adapter(adapter, contract, dataset.rows)

        # Build & export report
        report = build_readiness_report(
            profile=profile,
            contract=contract,
            mapping_plan=plan,
            risk_assessment=risks,
            approved_plan=approved_plan,
            validation_result=validation,
        )

        json_path, md_path = export_reports(report, out_dir)

        # Also write adapter code
        adapter_path = out_dir / f"{adapter.adapter_name}.py"
        with open(adapter_path, "w", encoding="utf-8") as f:
            f.write(adapter.python_code)

        print("\n" + "=" * 70)
        print("RECON INTEGRATION READINESS ENGINE — RUN COMPLETE")
        print("=" * 70)
        print(f"Readiness Status:  {report.readiness_state.value}")
        print(f"Contract:          {contract.contract_name} (v{contract.version})")
        print(f"Source:            {dataset.file_name} ({profile.total_rows} rows)")
        print(f"Contract Pass Rate:{validation.contract_pass_rate}%")
        print(f"Artifacts Created:")
        print(f"  - Markdown Report: {md_path}")
        print(f"  - JSON Report:     {json_path}")
        print(f"  - Adapter Code:    {adapter_path}")
        print("=" * 70 + "\n")
        return 0
    except ReconError as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        return 1


def cmd_gate(args: argparse.Namespace) -> int:
    """Headless CI/CD preflight integration gate.

    Exit codes:
      0: Preflight evaluation succeeded, no blockers remain, quarantine rate within limit.
      1: Unresolved required mappings, critical risks, quarantine limit exceeded, or strict-mode failure.
      2: Invalid input arguments, missing or malformed source/contract/spec, threshold out of range.
      3: Unexpected internal failure.
    """
    is_json = getattr(args, "json_output", False)

    # Validate quarantine threshold range
    max_quarantine_pct = getattr(args, "max_quarantine_pct", 0.0)
    if max_quarantine_pct < 0.0 or max_quarantine_pct > 100.0:
        err = f"Invalid --max-quarantine-pct '{max_quarantine_pct}'. Must be between 0.0 and 100.0."
        if is_json:
            print(json.dumps({"status": "ERROR", "exit_code": 2, "exit_reason": err}))
        else:
            print(f"Error [Exit Code 2]: {err}", file=sys.stderr)
        return 2

    # Step 1-3: Load inputs and profile
    try:
        dataset = load_dataset(args.source)
        schema_name = getattr(args, "schema_name", None)
        contract = load_target_contract(args.contract, schema_name=schema_name)
        profile = profile_dataset(dataset)
        plan = propose_mappings(profile, contract)

        spec_val = None
        reused_count = 0
        if getattr(args, "mapping_spec", None):
            spec = load_mapping_spec(args.mapping_spec)
            plan, spec_val = validate_and_apply_mapping_spec(spec, contract, profile, plan)
            reused_count = spec_val.reused_count

    except (ReconError, FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        if is_json:
            print(json.dumps({"status": "ERROR", "exit_code": 2, "exit_reason": str(exc)}))
        else:
            print(f"Error [Exit Code 2]: Input validation failed: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        if is_json:
            print(json.dumps({"status": "ERROR", "exit_code": 3, "exit_reason": f"Unexpected failure: {exc}"}))
        else:
            print(f"Internal Error [Exit Code 3]: {exc}", file=sys.stderr)
        return 3

    # Step 4-6: Identify blockers, unresolved required fields, and risks
    try:
        unresolved_required = [
            f.name for f in contract.fields.values()
            if f.required and (
                f.name not in plan.proposals
                or plan.proposals[f.name].status == MappingStatus.UNRESOLVED
                or not plan.proposals[f.name].source_field
            )
        ]

        risks = evaluate_risks(profile, contract, plan)

        # Strict mode checks
        strict_failures: list[str] = []
        is_strict = getattr(args, "strict", False)
        if is_strict:
            if not getattr(args, "mapping_spec", None):
                strict_failures.append("Strict mode requires an explicit --mapping-spec file.")
            elif spec_val and not spec_val.contract_match:
                strict_failures.append("Strict mode requires an exact contract fingerprint match in mapping spec.")
            elif spec_val and len(spec_val.mismatches) > 0:
                strict_failures.append(f"Strict mode forbids mapping mismatches: {spec_val.mismatches}")

            unmapped_optional = [
                f.name for f in contract.fields.values()
                if not f.required and (
                    f.name not in plan.proposals or not plan.proposals[f.name].source_field
                )
            ]
            if unmapped_optional:
                strict_failures.append(f"Strict mode requires all fields mapped (unmapped optional: {unmapped_optional}).")

            if len(risks.critical_findings) > 0 or len(risks.high_findings) > 0:
                strict_failures.append(f"Strict mode forbids Critical/High risks ({len(risks.critical_findings)} critical, {len(risks.high_findings)} high).")

        # If required fields are unresolved or critical blockers exist, gate fails (Exit code 1)
        if unresolved_required or risks.is_blocked or strict_failures:
            failure_reasons: list[str] = []
            if unresolved_required:
                failure_reasons.append(f"Unresolved required target fields: {unresolved_required}")
            if risks.is_blocked:
                failure_reasons.append(f"Integration blocked by {len(risks.critical_findings)} critical risk findings.")
            if strict_failures:
                failure_reasons.extend(strict_failures)

            if is_json:
                print(json.dumps({
                    "status": "FAIL",
                    "exit_code": 1,
                    "exit_reason": "; ".join(failure_reasons),
                    "contract": {
                        "name": contract.contract_name,
                        "version": contract.version,
                        "fingerprint": contract.fingerprint,
                    },
                    "source": {
                        "file_name": dataset.file_name,
                        "rows": profile.total_rows,
                        "fingerprint": profile.fingerprint,
                    },
                    "mapping": {
                        "spec_provided": bool(getattr(args, "mapping_spec", None)),
                        "reused_count": reused_count,
                        "unresolved_count": len(plan.unresolved_proposals()),
                        "unresolved_required_fields": unresolved_required,
                    },
                    "risks": {
                        "critical_count": len(risks.critical_findings),
                        "high_count": len(risks.high_findings),
                        "is_blocked": risks.is_blocked,
                    },
                    "strict_mode": is_strict,
                    "failure_reasons": failure_reasons,
                }, indent=2))
            else:
                print("\n" + "=" * 70)
                print("RECON CI/CD PREFLIGHT GATE: BLOCKED")
                print("=" * 70)
                print(f"Status:          FAIL (Exit Code 1)")
                print(f"Contract:        {contract.contract_name} (v{contract.version})")
                print(f"Source Data:     {dataset.file_name} ({profile.total_rows} rows)")
                print(f"Mappings Reused: {reused_count}")
                print(f"Strict Mode:     {'ENABLED' if is_strict else 'DISABLED'}")
                print("-" * 70)
                print("BLOCKING REASONS:")
                for r in failure_reasons:
                    print(f"  - {r}")
                print("=" * 70 + "\n")
            return 1

        # Step 7: Headless approval, adapter generation, and record validation
        approved_plan = approve_mapping_plan(plan, reviewer="ci_gate_preflight")
        adapter = generate_adapter(approved_plan, contract)
        validation = validate_adapter(adapter, contract, dataset.rows)

        # Zero-data-loss accounting check
        total = validation.total_input_records
        valid = validation.valid_records_count
        quarantined = validation.quarantined_records_count
        assert total == valid + quarantined, f"Zero-data-loss accounting invariant violated: {total} != {valid} + {quarantined}"

        quarantine_pct = (quarantined / total * 100.0) if total > 0 else 0.0

        post_val_failures: list[str] = []
        if is_strict and quarantined > 0:
            post_val_failures.append(f"Strict mode requires 0 quarantined records; observed {quarantined}.")

        if quarantine_pct > max_quarantine_pct:
            post_val_failures.append(
                f"Quarantine rate {quarantine_pct:.2f}% exceeds allowed threshold of {max_quarantine_pct:.2f}% ({quarantined}/{total} quarantined)."
            )

        if post_val_failures:
            if is_json:
                print(json.dumps({
                    "status": "FAIL",
                    "exit_code": 1,
                    "exit_reason": "; ".join(post_val_failures),
                    "contract": {
                        "name": contract.contract_name,
                        "version": contract.version,
                        "fingerprint": contract.fingerprint,
                    },
                    "source": {
                        "file_name": dataset.file_name,
                        "rows": profile.total_rows,
                        "fingerprint": profile.fingerprint,
                    },
                    "accounting": {
                        "total_input_records": total,
                        "valid_records_count": valid,
                        "quarantined_records_count": quarantined,
                        "quarantine_pct": round(quarantine_pct, 4),
                        "max_quarantine_pct": max_quarantine_pct,
                    },
                    "strict_mode": is_strict,
                    "failure_reasons": post_val_failures,
                }, indent=2))
            else:
                print("\n" + "=" * 70)
                print("RECON CI/CD PREFLIGHT GATE: FAILED (THRESHOLD EXCEEDED)")
                print("=" * 70)
                print(f"Status:          FAIL (Exit Code 1)")
                print(f"Contract:        {contract.contract_name} (v{contract.version})")
                print(f"Source Data:     {dataset.file_name} ({total} records)")
                print(f"Zero-Data-Loss:  Total={total} = Valid={valid} + Quarantined={quarantined}")
                print(f"Quarantine Rate: {quarantine_pct:.2f}% (Allowed: {max_quarantine_pct:.2f}%)")
                print(f"Strict Mode:     {'ENABLED' if is_strict else 'DISABLED'}")
                print("-" * 70)
                for f in post_val_failures:
                    print(f"  - {f}")
                print("=" * 70 + "\n")
            return 1

        # SUCCESS (Exit code 0)
        if is_json:
            print(json.dumps({
                "status": "PASS",
                "exit_code": 0,
                "exit_reason": "Preflight gate passed successfully.",
                "contract": {
                    "name": contract.contract_name,
                    "version": contract.version,
                    "fingerprint": contract.fingerprint,
                },
                "source": {
                    "file_name": dataset.file_name,
                    "rows": profile.total_rows,
                    "fingerprint": profile.fingerprint,
                },
                "accounting": {
                    "total_input_records": total,
                    "valid_records_count": valid,
                    "quarantined_records_count": quarantined,
                    "quarantine_pct": round(quarantine_pct, 4),
                    "max_quarantine_pct": max_quarantine_pct,
                },
                "mapping": {
                    "spec_provided": bool(getattr(args, "mapping_spec", None)),
                    "reused_count": reused_count,
                    "unresolved_count": len(plan.unresolved_proposals()),
                },
                "strict_mode": is_strict,
            }, indent=2))
        else:
            print("\n" + "=" * 70)
            print("RECON CI/CD PREFLIGHT GATE: PASSED")
            print("=" * 70)
            print(f"Status:          PASS (Exit Code 0)")
            print(f"Contract:        {contract.contract_name} (v{contract.version})")
            print(f"Source Data:     {dataset.file_name} ({total} records)")
            print(f"Zero-Data-Loss:  Total={total} = Valid={valid} + Quarantined={quarantined}")
            print(f"Quarantine Rate: {quarantine_pct:.2f}% (Limit: {max_quarantine_pct:.2f}%)")
            print(f"Mappings Reused: {reused_count}")
            print(f"Strict Mode:     {'ENABLED' if is_strict else 'DISABLED'}")
            print("=" * 70 + "\n")
        return 0

    except Exception as exc:
        if is_json:
            print(json.dumps({"status": "ERROR", "exit_code": 3, "exit_reason": f"Unexpected execution error: {exc}"}))
        else:
            print(f"Internal Error [Exit Code 3]: {exc}", file=sys.stderr)
        return 3


def cmd_web(args: argparse.Namespace) -> int:
    """Launches the Recon developer web interface."""
    import uvicorn
    from recon.server.app import create_app

    app = create_app()
    print(f"\nStarting Recon Web Interface at http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


def main() -> None:
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        prog="recon",
        description="Recon — The Integration Readiness Engine: Know what will break before you build the integration.",
    )
    parser.add_argument("--version", action="version", version=f"recon {recon.__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # profile
    p_prof = subparsers.add_parser("profile", help="Run deterministic profiling on a CSV/JSON dataset")
    p_prof.add_argument("source", help="Path to source CSV/JSON file")
    p_prof.set_defaults(func=cmd_profile)

    # assess
    p_assess = subparsers.add_parser("assess", help="Assess mappings and integration risks against a target contract")
    p_assess.add_argument("source", help="Path to source CSV/JSON file")
    p_assess.add_argument("contract", help="Path to target contract JSON, OpenAPI, or CSV file")
    p_assess.add_argument("--mapping-spec", default=None, help="Path to recon_mapping_spec.json for reusable mapping decisions")
    p_assess.add_argument("--schema-name", default=None, help="Model name when contract is an OpenAPI document with multiple models")
    p_assess.set_defaults(func=cmd_assess)

    # run
    p_run = subparsers.add_parser("run", help="Execute complete workflow: profile, map, risks, adapter, validation, and reports")
    p_run.add_argument("source", help="Path to source CSV/JSON file")
    p_run.add_argument("contract", help="Path to target contract JSON, OpenAPI, or CSV file")
    p_run.add_argument("--mapping-spec", default=None, help="Path to recon_mapping_spec.json for reusable mapping decisions")
    p_run.add_argument("--schema-name", default=None, help="Model name when contract is an OpenAPI document with multiple models")
    p_run.add_argument("--output-dir", default="recon_output", help="Directory to save generated reports and adapters")
    p_run.set_defaults(func=cmd_run)

    # gate (CI/CD Preflight)
    p_gate = subparsers.add_parser("gate", help="Headless CI/CD preflight gate for automated integration testing")
    p_gate.add_argument("--source", required=True, help="Path to incoming source data file (CSV, JSON, JSONL)")
    p_gate.add_argument("--contract", required=True, help="Path to target contract JSON, OpenAPI, or CSV file")
    p_gate.add_argument("--mapping-spec", default=None, help="Path to reusable recon_mapping_spec.json file")
    p_gate.add_argument("--schema-name", default=None, help="Model name within multi-model OpenAPI contracts")
    p_gate.add_argument("--max-quarantine-pct", type=float, default=0.0, help="Maximum allowed percentage of quarantined records (0.0 to 100.0, default: 0.0)")
    p_gate.add_argument("--strict", action="store_true", help="Enable strict preflight enforcement (complete spec, zero warnings, zero quarantine)")
    p_gate.add_argument("--json", dest="json_output", action="store_true", help="Output machine-readable JSON to stdout")
    p_gate.set_defaults(func=cmd_gate)

    # serve / web
    p_web = subparsers.add_parser("serve", aliases=["web"], help="Start the Recon developer web studio")
    p_web.add_argument("--host", default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    p_web.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    p_web.set_defaults(func=cmd_web)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
