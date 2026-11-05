import json
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.database import Base
from app.evaluation.experiment_pipeline import ExperimentEvaluationPipeline
from app.experiment.experiment_service import ExperimentService
from app.ge.ge_service import GenerativeEngineService
from app.ge.search_provider import RetrievedDocument
from app.storage.experiment_repository import ExperimentRepository


DOCS = [RetrievedDocument(
    rank=i, title=f"Doc {i}", url=f"https://source{i}.example/",
    plain_text=("The audited source explains resume readability, ATS clarity, and honest use of experience. "
                "It offers educational guidance, not a resume-writing service or hiring promise." if i == 1 else f"Reference {i} verifies resume guidance."),
    is_optimization_target=i == 1, source_role="audited_target" if i == 1 else "reference",
    retrieval_provider="exa", content_sha256=f"hash-{i}") for i in range(1, 6)]


class Runner:
    def __init__(self, fail_rewrite=False):
        self.fail_rewrite = fail_rewrite
        self.calls = []

    def generate(self, **request):
        self.calls.append(request["purpose"])
        if request["purpose"] == "strategy_rewrite":
            if self.fail_rewrite:
                raise RuntimeError("controlled interruption after baseline checkpoint")
            anchor = DOCS[0].plain_text
            return json.dumps({"version": "rewrite-plan-v1", "operations": [{
                "anchor": anchor,
                "replacement": "What resume guidance is available?\n" + anchor,
            }]})
        return "Resume readability and honest experience descriptions are discussed in [1]."


def test_completed_strategy_checkpoint_survives_failure_and_resume(monkeypatch):
    monkeypatch.setenv("GEO_DISABLE_REWRITE_CACHE", "True")
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    repo = ExperimentRepository(db)
    exp = repo.create_run(property_id=None, name="checkpoint test", description=None,
        llm_model="gpt-6-luna", provider=None, dataset_name="outreach_owner_website_research",
        benchmark_queries=[{"query": "What resume guidance is available?", "documents": []}],
        strategies=["original", "faq"], metrics=["citation_count"], number_of_queries=1,
        random_seed=42, temperature=0.2, repetitions_per_context=1)
    query = "What resume guidance is available?"
    first_runner = Runner(fail_rewrite=True)
    first_engine = GenerativeEngineService(
        search_provider=SimpleNamespace(search=lambda **_: DOCS), llm_runner=first_runner)
    first_run = first_engine.run_query
    first_engine.run_query = lambda **kw: first_run(**(kw | {"provider": None}))
    first = ExperimentService(repo, first_engine, evaluation_pipeline=ExperimentEvaluationPipeline())
    with pytest.raises(RuntimeError, match="controlled interruption"):
        first._execute_query_seed(experiment=exp, query=query, seed_value=42,
            completed_runs=0, strategies=["original", "faq"], uploaded_documents=DOCS)
    assert [run.strategy for run in exp.runs] == ["original"]
    assert exp.runs[0].raw_response.startswith("Resume readability")

    second_runner = Runner()
    second_engine = GenerativeEngineService(
        search_provider=SimpleNamespace(search=lambda **_: DOCS), llm_runner=second_runner)
    second_run = second_engine.run_query
    second_engine.run_query = lambda **kw: second_run(**(kw | {"provider": None}))
    second = ExperimentService(repo, second_engine, evaluation_pipeline=ExperimentEvaluationPipeline())
    second._execute_query_seed(experiment=exp, query=query, seed_value=42,
        completed_runs=0, strategies=["original", "faq"], uploaded_documents=DOCS)
    assert second_runner.calls == ["strategy_rewrite", "answer_generation"]
    assert sorted(run.strategy for run in exp.runs) == ["faq", "original"]
    assert len(exp.queries) == 1
    assert len(exp.queries[0].documents) == 5
    db.close(); engine.dispose()
