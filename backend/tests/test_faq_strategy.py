import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.experiment.experiment_service import ExperimentService
from app.ge.geo_rewriter import (
    FAQGroundingError,
    GeoRewriter,
    OFFICIAL_GEO_STRATEGIES,
    STRATEGY_LABELS,
    faq_optimization,
    validate_faq_rewrite,
)
from app.ge.prompt_builder import PromptBuilder
from app.ge.search_provider import RetrievedDocument
from app.services.website_audit.crawler import CrawlResponse
from app.services.website_audit.extractor import extract_page
from app.teacher_pipeline.router import _validate_treatment_strategy
from app.teacher_pipeline.query_contexts import AuditQueryContextGenerator
from app.teacher_pipeline.sample_builder import TrainingSampleBuilder


def test_faq_is_a_supported_controlled_treatment():
    assert STRATEGY_LABELS["faq"] == "FAQ / Q&A Structure"
    assert "faq" not in OFFICIAL_GEO_STRATEGIES
    _validate_treatment_strategy("faq")
    assert ExperimentService._paper_mode_strategies(
        ExperimentService.__new__(ExperimentService),
        "teacher_training_contexts",
        ["faq"],
    ) == ["original", "faq"]


def test_one_hundred_context_teacher_workflow_accepts_faq():
    pages = [
        SimpleNamespace(
            id=index,
            url=f"https://example.com/topic-{index}",
            page_title=f"Topic {index} research guide",
            h1=f"Understanding topic {index}",
            meta_description=f"Facts and guidance for subject {index}",
            status_code=200,
            word_count=300,
            content_sha256=f"{index:064x}",
            is_duplicate=False,
        )
        for index in range(1, 41)
    ]
    audit = SimpleNamespace(
        id=7,
        pages=pages,
        property=SimpleNamespace(name="Example", brand_name="Example"),
    )

    contexts = AuditQueryContextGenerator().generate(audit, count=100)
    _validate_treatment_strategy("faq")

    assert len(contexts) == 100
    assert len({context.query.lower() for context in contexts}) == 100


def test_faq_prompt_requires_grounded_answers_and_preserved_facts():
    source = "Our software checks resumes for ATS compatibility and highlights missing keywords."
    prompt = faq_optimization(source)
    treatment = (
        "How does the software help with ATS compatibility?\n\n"
        "Our software checks resumes for ATS compatibility and highlights missing keywords."
    )

    validate_faq_rewrite(source, treatment)
    assert source in prompt
    assert "using only information stated in the source" in prompt
    assert "Do not invent" in prompt


def test_faq_grounding_guard_rejects_unsupported_facts_and_claims():
    source = "Our software checks resumes for ATS compatibility and highlights missing keywords."
    fabricated = (
        "How successful is the software?\n\n"
        "Our software checks resumes for ATS compatibility and highlights missing keywords. "
        "It guarantees 95% success."
    )

    with pytest.raises(FAQGroundingError):
        validate_faq_rewrite(source, fabricated)


def test_faq_grounding_accepts_supported_paraphrase():
    source = "Our software checks resumes for ATS compatibility and highlights missing keywords."
    paraphrase = (
        "How does the software help with ATS compatibility?\n\n"
        "It checks resumes for ATS compatibility and identifies missing keywords."
    )

    validate_faq_rewrite(source, paraphrase)


@pytest.mark.parametrize(
    "unsupported",
    [
        "It checks resumes for ATS compatibility with 95% accuracy and highlights missing keywords.",
        "It checks resumes for ATS compatibility for $19 and highlights missing keywords.",
        "It checks resumes for ATS compatibility for free and highlights missing keywords.",
        "It checks resumes for ATS compatibility and guarantees customer success while highlighting missing keywords.",
        "According to Harvard Research [1], it checks resumes for ATS compatibility and highlights missing keywords.",
        "It checks resumes, highlights missing keywords, and exports polished PDF cover letters.",
    ],
    ids=["accuracy", "numeric-price", "free-price", "guarantee", "citation", "capability"],
)
def test_faq_grounding_rejects_specific_unsupported_claim_types(unsupported):
    source = "Our software checks resumes for ATS compatibility and highlights missing keywords."
    treatment = f"How does the software help?\n\n{unsupported}"

    with pytest.raises(FAQGroundingError):
        validate_faq_rewrite(source, treatment)


def test_faq_runs_through_the_existing_rewriter_pipeline_without_paid_calls(monkeypatch):
    source = "Our software checks resumes for ATS compatibility and highlights missing keywords."
    treatment = (
        "How does the software help with ATS compatibility?\n\n"
        "Our software checks resumes for ATS compatibility and highlights missing keywords."
    )

    class FakeRunner:
        def generate(self, **_kwargs):
            return treatment

    monkeypatch.setenv("GEO_DISABLE_REWRITE_CACHE", "True")
    rewritten = GeoRewriter(FakeRunner()).rewrite(
        document_text=source,
        query="How does resume checking work?",
        strategy="faq",
        model="unused-in-faq-rewrite-test",
        temperature=0,
    )

    assert rewritten == treatment


def test_extractor_reports_factual_faq_structure_without_an_llm():
    html = """
    <html><head>
      <title>Support</title>
      <script type="application/ld+json">{"@type":"FAQPage"}</script>
    </head><body>
      <h1>Frequently Asked Questions</h1>
      <h2>How does the service work?</h2><p>It checks the submitted document.</p>
      <h2>What does it report?</h2><p>It reports missing terms.</p>
    </body></html>
    """
    page = extract_page(CrawlResponse(
        url="https://example.com/support",
        status_code=200,
        html=html,
        content_type="text/html",
        html_accepted=True,
    ))

    assert page.faq_page_schema_detected is True
    assert page.faq_like_heading_count == 1
    assert page.question_heading_count == 2
    assert page.detected_qa_pair_count == 2


def test_faq_treatment_keeps_the_same_frozen_reference_set():
    documents = [
        RetrievedDocument(
            rank=index,
            title=f"Source {index}",
            url=f"https://source-{index}.example",
            plain_text=f"source content {index}",
            is_optimization_target=index == 1,
        )
        for index in range(1, 6)
    ]
    baseline = PromptBuilder().build(
        "How does it work?", documents, 1, "source content 1",
    )
    treatment = PromptBuilder().build(
        "How does it work?", documents, 1,
        "How does it work?\n\nsource content 1",
    )

    for index in range(2, 6):
        assert f"### Source {index}:\nsource content {index}" in baseline
        assert f"### Source {index}:\nsource content {index}" in treatment
    assert "How does it work?\n\nsource content 1" not in baseline
    assert "How does it work?\n\nsource content 1" in treatment


def test_teacher_sample_persists_faq_strategy(monkeypatch):
    now = datetime.now(timezone.utc)
    documents = [
        SimpleNamespace(
            rank=index,
            url=f"https://source-{index}.example",
            title=f"Source {index}",
            plain_text=f"source content {index}",
            is_selected=index == 1,
            source_role="audited_target" if index == 1 else "reference",
            retrieval_provider="google-custom-search-api",
            retrieval_timestamp=now,
            content_sha256=f"{index:064x}",
        )
        for index in range(1, 6)
    ]

    def run(run_id, strategy, value, answer):
        return SimpleNamespace(
            id=run_id,
            experiment_query_id=20,
            strategy=strategy,
            sample_index=0,
            seed_value=42,
            provider="chatgpt",
            model="gpt-3.5-turbo",
            status="completed",
            raw_prompt="prompt",
            raw_response=answer,
            generation_params_json='{"repetitions_per_context":1}',
            prompt_version_id=5,
            prompt_version=SimpleNamespace(version="prompt-v1"),
            evaluations=[SimpleNamespace(evaluator="test", evaluator_version="1")],
            metrics=[SimpleNamespace(name="visibility_score", value=value)],
            started_at=now,
            finished_at=now,
            strategy_result=SimpleNamespace(
                modified_document_text=(
                    "source content 1" if strategy == "original"
                    else "What is source 1?\n\nsource content 1"
                ),
            ),
        )

    baseline = run(10, "original", 0.1, "baseline")
    treatment = run(11, "faq", 0.4, "treatment")
    query = SimpleNamespace(
        id=20,
        query="What is source 1?",
        seed_value=42,
        selected_document_rank=1,
        query_policy_version="audit-evidence-contexts-v1",
        source_audit_id=30,
        supporting_evidence_json=json.dumps({
            "query_source": "generated",
            "query_intent": "informational",
            "page_id": 40,
            "page_url": documents[0].url,
            "source_mode": "generated_query",
            "training_eligible": True,
        }),
        retrieval_provider="google-custom-search-api",
        retrieval_timestamp=now,
        documents=documents,
        strategy_results=[
            SimpleNamespace(strategy="original", word_count=1, position=1, pawc=0.1, citation_count=1, visibility_score=0.1),
            SimpleNamespace(strategy="faq", word_count=2, position=1, pawc=0.4, citation_count=2, visibility_score=0.4),
        ],
    )
    experiment = SimpleNamespace(
        id=50,
        property_id=60,
        status="completed",
        completed_at=now,
        dataset_name="teacher_training_contexts",
        dataset_version="1",
        random_seed=42,
        temperature=0.7,
    )
    audit = SimpleNamespace(id=30, completed_at=now, base_url="https://source-1.example")
    monkeypatch.setattr("app.teacher_pipeline.sample_builder.build_website_profile", lambda _audit: {})
    monkeypatch.setattr("app.teacher_pipeline.sample_builder.build_website_features", lambda _audit: {})

    sample = TrainingSampleBuilder().build(
        experiment=experiment,
        query=query,
        baseline_run=baseline,
        optimized_run=treatment,
        audit=audit,
        dataset_version="teacher-dataset-v000001",
    )

    assert sample.strategy == "faq"
    assert json.loads(sample.provenance_json)["optimized_run"]["strategy"] == "faq"
