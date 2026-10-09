"""Command Line Interface for Recon — The Integration Readiness Engine."""

import argparse
import sys
from pathlib import Path

import recon
from recon.adapters.generator import generate_adapter
from recon.contracts.loader import load_target_contract
from recon.exceptions import ReconError
from recon.ingestion.loader import load_dataset
from recon.mapping.approval import approve_mapping_plan
from recon.mapping.proposer import propose_mappings
from recon.profiling.profiler import profile_dataset
from recon.reporting.generator import build_readiness_report, export_reports, render_markdown_report
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
        contract = load_target_contract(args.contract)
        profile = profile_dataset(dataset)
        plan = propose_mappings(profile, contract)
        risks = evaluate_risks(profile, contract, plan)

        print("\n" + "=" * 70)
        print(f"RECON RISK ASSESSMENT: {dataset.file_name} -> {contract.contract_name}")
        print("=" * 70)
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
        contract = load_target_contract(args.contract)
        profile = profile_dataset(dataset)
        plan = propose_mappings(profile, contract)
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


def main() -> None:
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        prog="recon",
        description="Recon — The Integration Readiness Engine: Know what will break before you build the integration.",
    )
    parser.add_argument("--version", action="version", version=f"recon {recon.__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # profile
    p_prof = subparsers.add_parser("profile", help="Run deterministic profiling on a CSV dataset")
    p_prof.add_argument("source", help="Path to source CSV file")
    p_prof.set_defaults(func=cmd_profile)

    # assess
    p_assess = subparsers.add_parser("assess", help="Assess mappings and integration risks against a target contract")
    p_assess.add_argument("source", help="Path to source CSV file")
    p_assess.add_argument("contract", help="Path to target contract JSON file")
    p_assess.set_defaults(func=cmd_assess)

    # run
    p_run = subparsers.add_parser("run", help="Execute complete workflow: profile, map, risks, adapter, validation, and reports")
    p_run.add_argument("source", help="Path to source CSV file")
    p_run.add_argument("contract", help="Path to target contract JSON file")
    p_run.add_argument("--output-dir", default="recon_output", help="Directory to save generated reports and adapters")
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
