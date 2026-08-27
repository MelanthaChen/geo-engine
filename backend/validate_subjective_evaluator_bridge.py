#!/usr/bin/env python3
"""Run a standalone, resumable subjective-evaluator bridge validation."""

from __future__ import annotations

import argparse
import os
import random
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env.local", override=True)
load_dotenv(BACKEND_DIR / ".env", override=False)

from openai import OpenAI  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.models.experiment import (  # noqa: E402
    ExperimentQuery,
    ExperimentRun,
    ExperimentStrategyResult,
)
from app.evaluation.subjective_bridge_validation import (  # noqa: E402
    AnswerSample,
    BridgeModelEvaluator,
    CANDIDATE_MODEL,
    DIMENSIONS,
    LEGACY_MODEL,
    evaluate_with_retries,
    generate_outputs,
    load_checkpoint,
    save_checkpoint,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare Princeton's legacy subjective judge with GPT-4o mini."
    )
    parser.add_argument("--execute", action="store_true", help="Authorize paid API calls.")
    parser.add_argument("--sample-size", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20260820)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=BACKEND_DIR.parent / "verification_artifacts/subjective_evaluator_bridge",
    )
    parser.add_argument("--restart", action="store_true", help="Ignore an existing checkpoint.")
    return parser.parse_args()


def sample_completed_answers(sample_size: int, seed: int) -> list[AnswerSample]:
    with SessionLocal() as db:
        rows = (
            db.query(ExperimentStrategyResult, ExperimentQuery)
            .join(ExperimentRun, ExperimentStrategyResult.run_id == ExperimentRun.id)
            .join(ExperimentQuery, ExperimentStrategyResult.experiment_query_id == ExperimentQuery.id)
            .filter(
                ExperimentRun.status == "completed",
                ExperimentStrategyResult.answer.isnot(None),
                ExperimentStrategyResult.answer != "",
                ExperimentQuery.selected_document_rank.isnot(None),
            )
            .order_by(ExperimentStrategyResult.id)
            .all()
        )
    if len(rows) < sample_size:
        raise RuntimeError(
            f"Need {sample_size} completed answers with selected ranks; found {len(rows)}."
        )
    selected = random.Random(seed).sample(rows, sample_size)
    return [
        AnswerSample(
            result_id=result.id,
            run_id=result.run_id,
            query=query.query,
            answer=result.answer,
            selected_rank=query.selected_document_rank,
            strategy=result.strategy,
            sample_index=result.sample_index,
            pawc=float(result.pawc or 0.0),
        )
        for result, query in selected
    ]


def main() -> int:
    args = parse_args()
    if args.sample_size <= 1:
        raise SystemExit("--sample-size must be at least 2")
    output_dir = args.output_dir.resolve()
    checkpoint = output_dir / "checkpoint.json"
    if checkpoint.exists() and not args.restart:
        samples, observations = load_checkpoint(checkpoint)
        if len(samples) != args.sample_size:
            raise SystemExit(
                "Checkpoint sample size differs; use --restart or the original --sample-size."
            )
    else:
        samples = sample_completed_answers(args.sample_size, args.seed)
        observations = []

    expected_calls = args.sample_size * len(DIMENSIONS) * 2
    completed = {(row.result_id, row.model, row.dimension) for row in observations}
    print(f"Bridge sample: {len(samples)} completed answers")
    print(f"Provider calls: {expected_calls} total, {expected_calls - len(completed)} remaining")
    print(f"Output: {output_dir}")
    if not args.execute:
        print("Plan only. Re-run with --execute to authorize paid API calls.")
        return 0
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not configured")

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    evaluators = {
        LEGACY_MODEL: BridgeModelEvaluator(client, LEGACY_MODEL),
        CANDIDATE_MODEL: BridgeModelEvaluator(client, CANDIDATE_MODEL),
    }
    order_rng = random.Random(args.seed)
    work = [
        (sample, model, dimension)
        for sample in samples
        for dimension in DIMENSIONS
        for model in (LEGACY_MODEL, CANDIDATE_MODEL)
        if (sample.result_id, model, dimension) not in completed
    ]
    order_rng.shuffle(work)
    for index, (sample, model, dimension) in enumerate(work, start=1):
        print(f"[{index}/{len(work)}] result={sample.result_id} model={model} dimension={dimension}")
        observation = evaluate_with_retries(
            lambda s=sample, m=model, d=dimension: evaluators[m].evaluate_dimension(s, d)
        )
        observations.append(observation)
        save_checkpoint(checkpoint, samples, observations)

    summary = generate_outputs(output_dir, samples, observations)
    print(f"Decision: {summary['decision']}")
    print(f"Report: {output_dir / 'BridgeValidationReport.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
