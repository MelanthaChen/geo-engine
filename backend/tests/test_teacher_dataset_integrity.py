import csv
import io
import json
from types import SimpleNamespace

import pytest

from app.ge.geo_rewriter import GeoRewriter
from app.teacher_pipeline.router import export_latest_dataset
from app.teacher_pipeline.dataset_writer import DatasetWriter
from app.teacher_pipeline.provenance import _target_page_id
from app.teacher_pipeline.sample_builder import TrainingSampleBuilder
from app.teacher_pipeline.teacher_pipeline import TeacherPipeline


def serialized_repetition(index: int) -> dict:
    fingerprint = "a" * 64
    original = {"visibility_score": 0.1 + index / 100}
    optimized = {"visibility_score": 0.4 + index / 100}
    return {
        "sample_id": f"sample-{index}",
        "website_id": 1,
        "experiment_id": 8,
        "experiment_run_id": 200 + index,
        "audit_id": 4,
        "audit_version": "v1",
        "feature_vector": {"schema_version": "website-factual-evidence-vector-v2"},
        "strategy": "keyword_stuffing",
        "teacher_provider": "chatgpt",
        "teacher_model": "gpt-3.5-turbo",
        "teacher_model_version": "gpt-3.5-turbo",
        "prompt_version": "v1",
        "evaluation_version": "v1",
        "original_metrics": original,
        "optimized_metrics": optimized,
        "delta_metrics": {"visibility_score": 0.3},
        "baseline_metrics": original,
        "treatment_metrics": optimized,
        "metric_deltas": {"visibility_score": 0.3},
        "provenance": {
            "context_fingerprint": fingerprint,
            "query": {"text": "Which vehicle design is most recognizable?"},
            "baseline_run": {"id": 100 + index, "sample_index": index},
            "optimized_run": {"id": 200 + index, "sample_index": index},
            "baseline_answer": f"baseline {index}",
            "treatment_answer": f"treatment {index}",
        },
        "context_fingerprint": fingerprint,
        "query": "Which vehicle design is most recognizable?",
        "query_source": "generated",
        "query_intent": "informational",
        "target_url": "https://target.example",
        "target_page_id": 44,
        "originating_page_id": 44,
        "originating_page_url": "https://target.example",
        "target_snapshot_hash": "target-hash",
        "reference_urls": [f"https://reference-{value}.example" for value in range(4)],
        "reference_snapshot_hashes": [f"reference-hash-{value}" for value in range(4)],
        "reference_order": [2, 3, 4, 5],
        "baseline_answer": f"baseline {index}",
        "treatment_answer": f"treatment {index}",
        "repetitions": [],
        "repetition_count": 1,
        "source_mode": "live_retrieval",
        "training_eligible": True,
        "dataset_version": "teacher-dataset-v000003",
        "provenance_hash": f"hash-{index}",
        "created_at": "2026-09-27T00:00:00Z",
    }


def test_five_stochastic_runs_export_as_one_context_with_nested_repetitions(monkeypatch):
    rows = TeacherPipeline.consolidate_samples([
        serialized_repetition(index) for index in range(5)
    ])

    assert len(rows) == 1
    assert rows[0]["repetition_count"] == 5
    assert len(rows[0]["repetitions"]) == 5
    assert len({row["context_fingerprint"] for row in rows}) == 1

    class FakePipeline:
        def __init__(self, _db):
            pass

        def export_latest(self):
            return {"dataset_version": "teacher-dataset-v000003"}, rows

    monkeypatch.setattr("app.teacher_pipeline.router.TeacherPipeline", FakePipeline)
    response = export_latest_dataset(format="csv", db=object())
    exported = list(csv.DictReader(io.StringIO(response.body.decode())))

    assert len(exported) == 1
    assert json.loads(exported[0]["repetitions"]).__len__() == 5


def test_dataset_membership_grouping_is_keyed_by_context_not_sample_id():
    samples = [
        SimpleNamespace(
            sample_id=f"sample-{index}",
            created_at=f"2026-09-27T00:00:0{index}Z",
            provenance_json=json.dumps({"context_fingerprint": "f" * 64}),
        )
        for index in range(5)
    ]

    contexts = DatasetWriter._group_by_context(samples)

    assert len(contexts) == 1
    assert contexts[0][0] == "f" * 64
    assert [sample.sample_id for sample in contexts[0][1]] == [
        f"sample-{index}" for index in range(5)
    ]


def test_target_page_id_resolves_from_the_source_audit_without_fabrication():
    audit = SimpleNamespace(pages=[
        SimpleNamespace(id=44, url="https://Target.Example/page/"),
    ])

    assert _target_page_id(audit, "http://target.example/page", {}) == 44
    assert _target_page_id(audit, "https://unrelated.example", {}) is None


@pytest.mark.parametrize(
    "strategy",
    [
        "statistics", "citation", "quotation", "authoritative",
        "easy_to_understand", "fluency", "unique_words", "technical_terms",
        "keyword_stuffing",
    ],
)
def test_each_standard_strategy_returns_document_content_not_an_edit_plan(monkeypatch, strategy):
    source = "The vehicle combines distinctive design with responsive driving performance for daily journeys."
    anchor = "responsive driving performance"
    rewritten = "The vehicle combines distinctive design with responsive luxury driving performance for daily journeys."

    class Runner:
        def generate(self, **_kwargs):
            return json.dumps({"version": "rewrite-plan-v1", "operations": [{
                "anchor": anchor,
                "replacement": "responsive luxury driving performance",
            }]})

    monkeypatch.setenv("GEO_DISABLE_REWRITE_CACHE", "True")
    output = GeoRewriter(Runner()).rewrite(source, "Which vehicle?", strategy, "unused", 0)

    assert output == rewritten
    assert "In sentence about" not in output


def test_keyword_instruction_plan_is_rejected_and_replaced_by_full_document(monkeypatch):
    source = "The vehicle combines distinctive design with responsive driving performance for daily journeys."
    outputs = iter([
        "1. In sentence about design, add keyword luxury\n"
        "2. In sentence about driving, add keyword precision",
        json.dumps({"version": "rewrite-plan-v1", "operations": [{
            "anchor": "distinctive design with responsive driving performance",
            "replacement": "distinctive luxury design with responsive precision driving performance",
        }]}),
    ])

    class Runner:
        def generate(self, **_kwargs):
            return next(outputs)

    monkeypatch.setenv("GEO_DISABLE_REWRITE_CACHE", "True")
    rewritten = GeoRewriter(Runner()).rewrite(
        source, "Which vehicle?", "keyword_stuffing", "unused", 0
    )

    assert rewritten.startswith("The vehicle combines")
    assert "In sentence about" not in rewritten


def test_faq_strategy_returns_a_grounded_rewritten_document(monkeypatch):
    source = "The service checks resumes for ATS compatibility and highlights missing keywords."
    rewritten = (
        "How does the service help with ATS compatibility?\n\n"
        "The service checks resumes for ATS compatibility and highlights missing keywords."
    )

    class Runner:
        def generate(self, **_kwargs):
            return json.dumps({"version": "rewrite-plan-v1", "operations": [{
                "anchor": source,
                "replacement": rewritten,
            }]})

    monkeypatch.setenv("GEO_DISABLE_REWRITE_CACHE", "True")
    assert GeoRewriter(Runner()).rewrite(source, "How does it work?", "faq", "unused", 0) == rewritten


def test_new_feature_vector_contains_factual_evidence_without_legacy_scores():
    page = SimpleNamespace(
        status_code=200,
        is_duplicate=False,
        word_count=120,
        h1="Evidence",
        meta_description="Observed evidence",
        internal_link_count=4,
        external_link_count=2,
        faq_page_schema_detected=True,
        question_heading_count=3,
        detected_qa_pair_count=2,
        h2_count=4,
        h3_count=1,
        schema_types=["FAQPage", "Organization"],
        evidence_json={
            "authorship": {"author_name": "Researcher", "published_date": "2026-09-27"},
            "content": {"paragraph_count": 8, "list_count": 2},
            "strategies": {
                "citation": {"reference_like_link_count": 2, "attribution_phrase_count": 1},
                "statistics": {"numeric_claim_count": 5},
                "quotation": {"blockquote_count": 1},
                "easy_to_understand": {"long_paragraph_count": 1, "long_sentence_count": 2},
            },
        },
    )

    vector = TrainingSampleBuilder._factual_feature_vector(SimpleNamespace(pages=[page]))
    serialized = json.dumps(vector)

    assert vector["pages_with_authors"] == 1
    assert vector["quantitative_statement_count"] == 5
    for deprecated in ("authority_score", "brand_clarity", "content_coverage", "faq_presence"):
        assert deprecated not in serialized
