"""Audited, offline metric correction from persisted completed responses only."""
import argparse
import hashlib
import json
from dataclasses import asdict

from app.core.database import SessionLocal
from app.evaluation.evaluator import Evaluator
from app.models.experiment import (Experiment, ExperimentDocument, ExperimentEvent,
    ExperimentEvaluation, ExperimentMetric, ExperimentQuery, ExperimentRun, ExperimentStrategyResult)


def reconcile(experiment_id: int, run_ids: list[int]) -> list[dict]:
    outcomes=[]
    with SessionLocal() as db:
        experiment=db.query(Experiment).filter(Experiment.id==experiment_id).with_for_update().one()
        runs=db.query(ExperimentRun).filter(ExperimentRun.experiment_id==experiment_id,
            ExperimentRun.id.in_(run_ids)).order_by(ExperimentRun.id).with_for_update().all()
        if [run.id for run in runs] != sorted(run_ids):
            raise ValueError("Requested run IDs do not exactly belong to the experiment")
        for run in runs:
            if run.status!="completed" or not run.raw_response or run.strategy_result is None:
                raise ValueError(f"Run {run.id} lacks a completed archived response and strategy result")
            if run.raw_response != run.strategy_result.answer:
                raise ValueError(f"Run {run.id} archive and strategy result disagree")
            query=db.query(ExperimentQuery).filter(ExperimentQuery.id==run.experiment_query_id,
                ExperimentQuery.experiment_id==experiment_id).one()
            if query.selected_document_rank is None:
                raise ValueError(f"Run {run.id} has no selected-document identity")
            document=db.query(ExperimentDocument).filter(ExperimentDocument.experiment_query_id==query.id,
                ExperimentDocument.rank==query.selected_document_rank).one()
            evaluation=Evaluator().evaluate(run.raw_response,document.plain_text,document.title or "",
                document.url,query.selected_document_rank)
            after=asdict(evaluation)
            record={"run_id":run.id,"strategy":run.strategy,"response_sha256":hashlib.sha256(run.raw_response.encode()).hexdigest(),
                "before":{"word_count":run.strategy_result.word_count,"citation_count":run.strategy_result.citation_count},
                "after":{"word_count":evaluation.word_count,"citation_count":evaluation.citation_count}}
            existing=db.query(ExperimentEvent).filter(ExperimentEvent.experiment_id==experiment_id,
                ExperimentEvent.event_type=="evaluator_metrics_reconciled_from_archived_response").all()
            prior=next((event for event in existing if json.loads(event.metadata_json or "{}").get("run_id")==run.id),None)
            if prior:
                outcomes.append(record|{"status":"already_reconciled"});continue
            if record["before"]==record["after"]:
                outcomes.append(record|{"status":"already_consistent"});continue
            evaluations=db.query(ExperimentEvaluation).filter(ExperimentEvaluation.run_id==run.id,
                ExperimentEvaluation.status=="completed").order_by(ExperimentEvaluation.id.desc()).all()
            if not evaluations:
                raise ValueError(f"Run {run.id} has no completed evaluation row")
            latest=evaluations[0]
            detail=json.loads(latest.details_json or "{}")
            old_detail={key:detail.get(key) for key in after}
            detail.update(after);latest.details_json=json.dumps(detail,separators=(",",":"))
            metric_rows=db.query(ExperimentMetric).filter(ExperimentMetric.evaluation_id==latest.id).all()
            by_name={item.name:item for item in metric_rows}
            for name,value in after.items():
                if name in by_name:by_name[name].value=float(value) if value is not None else None
            run.strategy_result.word_count=evaluation.word_count
            run.strategy_result.position=evaluation.position
            run.strategy_result.pawc=evaluation.pawc
            run.strategy_result.citation_count=evaluation.citation_count
            run.strategy_result.visibility_score=evaluation.visibility_score
            db.add(ExperimentEvent(experiment_id=experiment_id,event_type="evaluator_metrics_reconciled_from_archived_response",
                status="completed",message=f"Recomputed run {run.id} from its exact archived response without provider calls",
                metadata_json=json.dumps(record|{"old_evaluation_details":old_detail,"new_evaluation_details":after},separators=(",",":"))))
            db.commit()
            outcomes.append(record|{"status":"corrected"})
    return outcomes


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--experiment-id",type=int,required=True)
    parser.add_argument("--run-ids",required=True,help="Comma-separated exact run IDs")
    args=parser.parse_args()
    selected=[int(value) for value in args.run_ids.split(",") if value.strip()]
    if not selected or len(set(selected))!=len(selected): raise SystemExit("Run IDs must be distinct and nonempty")
    print(json.dumps(reconcile(args.experiment_id,selected),indent=2))
