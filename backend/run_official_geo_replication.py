import argparse
import json
from pathlib import Path

from app.core.database import SessionLocal
from app.experiment.official_replication_runner import OfficialReplicationRunner
from app.storage.experiment_repository import ExperimentRepository
from app.experiment.trend_validation import STAGES, estimate_stage


def main():
    parser = argparse.ArgumentParser(description="Run or resume official Princeton GEO replication")
    parser.add_argument("--experiment-id", type=int)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--stage", choices=STAGES)
    parser.add_argument("--confirm-stage", help="Required confirmation token, e.g. stage1")
    parser.add_argument("--prior-report", type=Path, help="Previous stage paper_conclusion_verification.json")
    parser.add_argument("--subjective", action="store_true")
    parser.add_argument("--output-dir", default="replication_artifacts")
    parser.add_argument("--plan", action="store_true")
    args = parser.parse_args()
    if args.plan:
        stages = [args.stage] if args.stage else list(STAGES)
        for stage in stages:
            # Planning always represents the complete replication methodology,
            # including the measured seven-dimensional subjective evaluation.
            print(estimate_stage(stage, subjective=True))
        return
    if not args.experiment_id and not args.stage:
        parser.error("New executions require --stage. Use --plan first.")
    required_confirmation = args.stage or "resume"
    if args.confirm_stage != required_confirmation:
        parser.error(f"Execution requires --confirm-stage {required_confirmation}")
    if args.stage and args.stage != "stage1":
        previous = {"stage2": "stage1", "stage3": "stage2", "full": "stage3"}[args.stage]
        if not args.prior_report or not args.prior_report.is_file():
            parser.error(f"{args.stage} requires --prior-report from {previous}")
        prior = json.loads(args.prior_report.read_text(encoding="utf-8"))
        if prior.get("stage") != previous or prior.get("stage_decision", {}).get("decision") != "PROCEED":
            parser.error(f"Prior report must be a passing {previous} report")
    with SessionLocal() as db:
        runner = OfficialReplicationRunner(ExperimentRepository(db), subjective=args.subjective)
        experiment = runner.repository.get_run(args.experiment_id) if args.experiment_id else runner.create(stage=args.stage)
        runner.execute(experiment.id)
        report = runner.export(experiment.id, Path(args.output_dir) / str(experiment.id))
        print(f"Experiment {experiment.id} completed. Report: {report}")


if __name__ == "__main__":
    main()
