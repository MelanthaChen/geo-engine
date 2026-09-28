from types import SimpleNamespace
import json

from app.experiment.experiment_service import ExperimentService
from app.ge.prompt_builder import PromptBuilder
from app.ge.search_provider import RetrievedDocument
from app.services.website_audit.crawler import CrawlResponse
from app.teacher_pipeline.dataset_writer import DatasetWriter
from app.teacher_pipeline.provenance import context_fingerprint
from app.teacher_pipeline.query_contexts import AuditQueryContextGenerator
from app.teacher_pipeline.router import DatasetGenerationRequest
from app.teacher_pipeline.teacher_pipeline import TeacherPipeline
from app.teacher_pipeline.training_context_builder import TrainingContextBuilder


def audit_with_pages(count=40):
    pages = [
        SimpleNamespace(
            id=index + 1,
            url=f"https://example.com/family-{index % 8}/topic-{index}",
            page_title=f"Topic {index} Research Overview",
            h1=f"Understanding Topic {index}",
            meta_description=f"Facts and guidance for distinct subject {index}",
            status_code=200,
            word_count=300,
            content_sha256=f"{index:064x}",
            is_duplicate=False,
        )
        for index in range(count)
    ]
    return SimpleNamespace(
        id=7,
        pages=pages,
        property=SimpleNamespace(name="Example", brand_name="Example"),
    )


def test_one_hundred_samples_means_one_hundred_unique_queries_and_contexts():
    contexts = AuditQueryContextGenerator().generate(audit_with_pages(), count=100)

    assert len(contexts) == 100
    assert len({context.query.lower() for context in contexts}) == 100
    assert len({context.target_url for context in contexts}) > 20
    assert all(context.query_source == "generated" for context in contexts)


def test_duplicate_queries_are_deduplicated_deterministically():
    audit = audit_with_pages(2)
    audit.pages[1].page_title = audit.pages[0].page_title
    audit.pages[1].h1 = audit.pages[0].h1
    audit.pages[1].meta_description = audit.pages[0].meta_description

    contexts = AuditQueryContextGenerator().generate(audit, count=3)

    assert len({context.query.lower() for context in contexts}) == 3


def fake_query(text="What is Topic?", reference_hash="ref-a"):
    documents = [
        SimpleNamespace(
            rank=1,
            url="https://target.example/page",
            content_sha256="target-hash",
            plain_text="Target",
            is_selected=True,
        ),
        SimpleNamespace(
            rank=2,
            url="https://reference.example/page",
            content_sha256=reference_hash,
            plain_text="Reference",
            is_selected=False,
        ),
    ]
    return SimpleNamespace(query=text, documents=documents)


def test_stochastic_repetition_does_not_change_context_fingerprint():
    query = fake_query()

    first = context_fingerprint(query=query, strategy="authoritative")
    second = context_fingerprint(query=query, strategy="authoritative")

    assert first == second


def test_different_queries_and_source_sets_create_different_contexts():
    original = context_fingerprint(query=fake_query(), strategy="authoritative")
    changed_query = context_fingerprint(
        query=fake_query(text="How does Topic work?"),
        strategy="authoritative",
    )
    changed_sources = context_fingerprint(
        query=fake_query(reference_hash="ref-b"),
        strategy="authoritative",
    )

    assert len({original, changed_query, changed_sources}) == 3


def test_frozen_context_preserves_one_ordered_source_set(monkeypatch):
    context = AuditQueryContextGenerator().generate(audit_with_pages(1), count=1)[0]
    monkeypatch.setattr(
        "app.teacher_pipeline.training_context_builder.fetch_page",
        lambda *_args, **_kwargs: CrawlResponse(
            url=context.target_url,
            status_code=200,
            html="<html><title>Target</title><body><h1>Target</h1>Real content</body></html>",
            content_type="text/html",
            html_accepted=True,
        ),
    )

    class Provider:
        provider_id = "brave"

        def search(self, query, top_k=10):
            return [
                RetrievedDocument(
                    rank=index,
                    title=f"Reference {index}",
                    url=f"https://reference-{index}.example/page",
                    plain_text=f"Reference content {index}",
                )
                for index in range(1, 6)
            ]

    entry = TrainingContextBuilder(search_provider=Provider()).freeze([context])[0]

    assert len(entry["documents"]) == 5
    assert [document["rank"] for document in entry["documents"]] == [1, 2, 3, 4, 5]
    assert entry["documents"][0]["is_optimization_target"] is True
    assert all(
        document["supporting_evidence"]["training_eligible"] is True
        for document in entry["documents"]
    )
    assert all(document["supporting_evidence"]["page_id"] == context.target_page_id for document in entry["documents"])
    assert all(document["retrieval_provider"] == "brave" for document in entry["documents"])


def test_baseline_and_treatment_change_only_the_frozen_target():
    documents = [
        RetrievedDocument(
            rank=index,
            title=f"Source {index}",
            url=f"https://source-{index}.example",
            plain_text=f"original source {index}",
            is_optimization_target=index == 1,
        )
        for index in range(1, 6)
    ]
    builder = PromptBuilder()
    baseline = builder.build(
        query="What is the topic?",
        documents=documents,
        selected_rank=1,
        modified_document_text="original source 1",
    )
    treatment = builder.build(
        query="What is the topic?",
        documents=documents,
        selected_rank=1,
        modified_document_text="optimized source 1",
    )

    assert "original source 1" in baseline
    assert "optimized source 1" in treatment
    assert "optimized source 1" not in baseline
    for index in range(2, 6):
        assert f"original source {index}" in baseline
        assert f"original source {index}" in treatment


def test_training_sample_count_and_repetitions_are_separate():
    request = DatasetGenerationRequest(property_id=1, audit_id=2, strategy="citation")

    assert request.training_sample_count == 100
    assert request.repetitions_per_context == 1


def test_historical_five_sample_configuration_remains_readable():
    historical = SimpleNamespace(
        generation_params_json=json.dumps({"samples_per_strategy": 5}),
    )
    current = SimpleNamespace(
        generation_params_json=json.dumps({
            "repetitions_per_context": 1,
            "samples_per_strategy": 1,
        }),
    )

    assert ExperimentService._repetitions_per_context(historical) == 5
    assert ExperimentService._repetitions_per_context(current) == 1


def test_historical_sample_without_new_provenance_fields_remains_readable():
    sample = SimpleNamespace(
        sample_id="historical",
        website_id=1,
        experiment_id=2,
        experiment_run_id=3,
        audit_id=4,
        audit_version="v1",
        feature_vector_json="{}",
        strategy="citation",
        teacher_provider="chatgpt",
        teacher_model="gpt-3.5-turbo",
        teacher_model_version="gpt-3.5-turbo",
        prompt_version="v1",
        evaluation_version="v1",
        original_metrics_json="{}",
        optimized_metrics_json="{}",
        delta_metrics_json="{}",
        provenance_json=json.dumps({
            "query": {"text": "Historical query"},
            "selected_document": {"url": "https://example.com"},
            "source_set": [],
        }),
        dataset_version="teacher-dataset-v000001",
        provenance_hash="abc",
        created_at="2026-09-27T00:00:00Z",
    )

    serialized = TeacherPipeline.serialize_sample(sample)

    assert serialized["query"] == "Historical query"
    assert serialized["context_fingerprint"] is None
    assert serialized["baseline_answer"] is None
    assert serialized["source_mode"] == "live_retrieval"


def test_demo_only_provenance_can_be_excluded_from_training_export():
    assert DatasetWriter._training_eligible({
        "source_set": [{"retrieval_provider": "frozen-geo-bench-cache"}],
    }) is False
    assert DatasetWriter._training_eligible({
        "source_mode": "generated_query",
        "training_eligible": True,
    }) is True
