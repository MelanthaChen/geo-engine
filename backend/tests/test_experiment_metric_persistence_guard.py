import json
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.database import Base
from app.evaluation.experiment_pipeline import ExperimentEvaluationPipeline
from app.experiment.experiment_service import ExperimentService
from app.ge.search_provider import RetrievedDocument
from app.models.experiment import ExperimentMetric, ExperimentStrategyResult
from app.storage.experiment_repository import ExperimentRepository


def test_store_query_run_recomputes_nonempty_cited_answers_and_preserves_empty_zero():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    repo = ExperimentRepository(db)
    experiment = repo.create_run(property_id=None, name="persist metric guard", description=None,
        llm_model="offline", provider=None, dataset_name="outreach_owner_website_research",
        benchmark_queries=[{"query":"Q"}], strategies=["original", "faq"], metrics=["word_count"],
        number_of_queries=1, random_seed=1, temperature=0, repetitions_per_context=1)
    docs = [RetrievedDocument(rank=i, title=f"Doc {i}", url=f"https://d{i}.example",
        plain_text="source text", is_optimization_target=i == 1,
        source_role="audited_target" if i == 1 else "reference") for i in range(1, 6)]
    outputs = [
        {"strategy":"original", "sample_index":0, "answer":"GeoAIResume’s ‘Build Better Resumes Faster’ examines how AI systems discover, cite, summarize, and recommend resume-related material—not a writing service or hiring promise. [1] Its guidance covers readable formatting, honest keyword use, role scope, tools, and results. [1]",
         "prompt":"p", "modified_document_text":"source", "query":"Q", "latency_ms":1},
        {"strategy":"faq", "sample_index":0, "answer":"GeoAIResume’s research studies how AI systems discover and recommend resume content. [1] Its resources cover examples, ATS guidance, review frameworks, and career readiness. [1]",
         "prompt":"p", "modified_document_text":"source", "query":"Q", "latency_ms":1},
        {"strategy":"empty", "sample_index":0, "answer":"", "prompt":"p", "modified_document_text":"source", "query":"Q", "latency_ms":1},
    ]
    ExperimentEvaluationPipeline().evaluate_outputs(outputs, selected_document=docs[0])
    outputs[0]["evaluation"].word_count = 0
    outputs[0]["evaluation_record"]["details"]["word_count"] = 0
    outputs[0]["evaluation_record"]["metrics"]["word_count"] = 0
    outputs[1]["evaluation"].word_count = 0
    outputs[1]["evaluation_record"]["details"]["word_count"] = 0
    outputs[1]["evaluation_record"]["metrics"]["word_count"] = 0
    repo.store_query_run(experiment, query="Q", seed_value=1, documents=docs,
        selected_document_rank=1, strategy_outputs=outputs)
    rows = {row.strategy:row for row in db.execute(select(ExperimentStrategyResult)).scalars().all()}
    assert rows["empty"].word_count == 0
    assert rows["faq"].word_count > 0 and rows["original"].word_count > 0
    metrics = {m.run_id: m.value for m in db.execute(select(ExperimentMetric)).scalars().all() if m.name == "word_count"}
    assert metrics[rows["original"].run_id] > 0 and metrics[rows["faq"].run_id] > 0
    assert metrics[rows["empty"].run_id] == 0
    db.close(); engine.dispose()
