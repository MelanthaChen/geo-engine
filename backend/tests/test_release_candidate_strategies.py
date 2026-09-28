import json
from types import SimpleNamespace

import pytest

from app.evaluation.experiment_pipeline import ExperimentEvaluationPipeline
from app.experiment.experiment_service import ExperimentService
from app.ge.ge_service import GenerativeEngineService
from app.ge.geo_rewriter import RewriteAnchorError, RewriteOutputError
from app.ge.search_provider import RetrievedDocument


TREATMENTS = [
    "faq",
    "statistics",
    "citation",
    "quotation",
    "authoritative",
    "easy_to_understand",
    "fluency",
    "unique_words",
    "technical_terms",
    "keyword_stuffing",
]

SOURCE = (
    "Our software checks resumes for ATS compatibility and highlights missing keywords.\n\n"
    "The guidance helps job seekers explain employment gaps with concise, factual language.\n\n"
    "Users can review suggestions before updating their resumes."
)
ANCHOR = "Our software checks resumes for ATS compatibility and highlights missing keywords."


class StructuredRunner:
    def __init__(self, strategy):
        self.strategy = strategy
        self.requests = []

    def generate(self, **request):
        self.requests.append(request)
        if request.get("purpose") == "strategy_rewrite":
            replacement = (
                "How does the software help with ATS compatibility?\n"
                "It checks resumes for ATS compatibility and identifies missing keywords."
                if self.strategy == "faq"
                else f"{ANCHOR[:-1]} This {self.strategy.replace('_', ' ')} treatment is applied."
            )
            return json.dumps({
                "version": "rewrite-plan-v1",
                "operations": [{"anchor": ANCHOR, "replacement": replacement}],
            })
        return "Resume guidance is supported by the audited target [1] and references [2]."


class RecordingRepository:
    def __init__(self):
        self.stored = None

    def update_progress(self, *_args, **_kwargs):
        pass

    def update_current_strategy(self, *_args, **_kwargs):
        pass

    def store_query_run(self, experiment, **kwargs):
        self.stored = (experiment, kwargs)


def frozen_documents():
    return [
        RetrievedDocument(
            rank=index,
            title=f"Source {index}",
            url=f"https://source-{index}.example/page",
            plain_text=SOURCE if index == 1 else f"Reference {index} evidence remains frozen.",
            is_optimization_target=index == 1,
            retrieval_provider="exa",
            content_sha256=f"hash-{index}",
            source_role="audited_target" if index == 1 else "reference",
        )
        for index in range(1, 6)
    ]


@pytest.mark.parametrize("strategy", TREATMENTS)
def test_every_treatment_uses_application_path_and_persists_complete_document(
    monkeypatch, strategy
):
    monkeypatch.setenv("GEO_DISABLE_REWRITE_CACHE", "True")
    runner = StructuredRunner(strategy)
    engine = GenerativeEngineService(
        search_provider=SimpleNamespace(search=lambda **_kwargs: frozen_documents()),
        llm_runner=runner,
    )
    repository = RecordingRepository()
    service = ExperimentService(
        repository,
        ge_service=engine,
        evaluation_pipeline=ExperimentEvaluationPipeline(),
    )
    experiment = SimpleNamespace(
        id=91,
        llm_model="test-teacher",
        temperature=0.5,
        random_seed=7,
        provider=None,
        generation_params_json=json.dumps({"repetitions_per_context": 1}),
    )
    documents = frozen_documents()

    completed = service._execute_query_seed(
        experiment=experiment,
        query="How can a resume explain an employment gap?",
        seed_value=7,
        completed_runs=0,
        strategies=["original", strategy],
        uploaded_documents=documents,
    )

    assert completed == 1
    assert repository.stored is not None
    stored = repository.stored[1]
    assert [document.url for document in stored["documents"]] == [
        f"https://source-{index}.example/page" for index in range(1, 6)
    ]
    baseline, treatment = stored["strategy_outputs"]
    assert baseline["strategy"] == "original"
    assert baseline["modified_document_text"] == SOURCE
    assert treatment["strategy"] == strategy
    assert treatment["modified_document_text"]
    assert treatment["modified_document_text"] != SOURCE
    assert "The guidance helps job seekers" in treatment["modified_document_text"]
    assert "Users can review suggestions" in treatment["modified_document_text"]
    assert treatment["rewrite_plan"]["version"] == "rewrite-plan-v1"
    assert treatment["rewrite_plan"]["operations"][0]["anchor"] == ANCHOR
    assert "operations" not in treatment["modified_document_text"]
    assert not treatment["modified_document_text"].lstrip().startswith("1.")
    assert baseline["evaluation_record"]["evaluator"] == "princeton_geo_citation"
    assert treatment["evaluation_record"]["evaluator"] == "princeton_geo_citation"
    # Baseline and treatment use the same ordered references. Only Source 1 text changes.
    for index in range(2, 6):
        marker = f"Reference {index} evidence remains frozen."
        assert marker in baseline["prompt"]
        assert marker in treatment["prompt"]
    assert SOURCE in baseline["prompt"]
    assert treatment["modified_document_text"] in treatment["prompt"]


def test_malformed_operation_plan_is_actionable(monkeypatch):
    monkeypatch.setenv("GEO_DISABLE_REWRITE_CACHE", "True")

    class Runner:
        def generate(self, **_request):
            return '{"version":"rewrite-plan-v1","operations":['

    with pytest.raises(RewriteOutputError, match="malformed JSON"):
        GenerativeEngineService(
            search_provider=SimpleNamespace(search=lambda **_kwargs: frozen_documents()),
            llm_runner=Runner(),
        ).rewriter.rewrite_artifact(SOURCE, "query", "citation", "model", 0.5)


def test_missing_operation_anchor_is_actionable(monkeypatch):
    monkeypatch.setenv("GEO_DISABLE_REWRITE_CACHE", "True")

    class Runner:
        def generate(self, **_request):
            return json.dumps({
                "version": "rewrite-plan-v1",
                "operations": [{"anchor": "not present", "replacement": "replacement"}],
            })

    with pytest.raises(RewriteAnchorError, match="matched 0 times"):
        GenerativeEngineService(
            search_provider=SimpleNamespace(search=lambda **_kwargs: frozen_documents()),
            llm_runner=Runner(),
        ).rewriter.rewrite_artifact(SOURCE, "query", "citation", "model", 0.5)
