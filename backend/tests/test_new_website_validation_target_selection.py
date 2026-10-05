from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.experiment.new_website_validation import (
    NewWebsiteValidationBuilder,
    NewWebsiteValidationError,
)
from app.ge.search_provider import RetrievedDocument


class Query:
    def __init__(self, audit):
        self.audit = audit

    def options(self, *_args):
        return self

    def filter(self, *_args):
        return self

    def first(self):
        return self.audit


class DB:
    def __init__(self, audit):
        self.audit = audit

    def query(self, *_args):
        return Query(self.audit)


class Provider:
    provider_id = "exa"

    def __init__(self, candidates):
        self.candidates = candidates

    def search(self, *, query, top_k):
        assert query
        assert top_k == 10
        return self.candidates


def page(page_id, url, title):
    return SimpleNamespace(
        id=page_id,
        url=url,
        page_title=title,
        h1=title,
        status_code=200,
        word_count=100,
        is_duplicate=False,
    )


def candidate(rank, url, title="Result"):
    return RetrievedDocument(
        rank=rank,
        title=title,
        url=url,
        plain_text=f"{title} content",
        retrieved_at=datetime.now(timezone.utc),
        retrieval_provider="exa",
    )


def audit(pages, evidence_url=None):
    recommendation = SimpleNamespace(
        id=9,
        evidence_url=evidence_url,
        category="topic",
        title="Revuelto SV",
        description="Observed topic evidence",
    )
    return SimpleNamespace(
        id=4,
        property_id=7,
        status="completed",
        base_url="https://example.com/",
        brand_summary="Example",
        product_summary="Revuelto SV",
        property=SimpleNamespace(name="Example", brand_name="Example"),
        pages=pages,
        recommendations=[recommendation],
    ), recommendation


def test_highest_ranked_audited_page_is_selected_and_identity_preserved():
    pages = [page(1, "https://example.com/one", "One"), page(2, "https://example.com/two", "Two")]
    audit_row, recommendation = audit(pages)
    builder = NewWebsiteValidationBuilder(DB(audit_row))

    selected, rank, status = builder._select_target_page(
        audit_row,
        recommendation,
        [candidate(4, "https://example.com/two"), candidate(2, "https://example.com/one")],
    )

    assert selected.id == 1
    assert rank == 2
    assert status == "retrieved_by_provider"


def test_multiple_same_site_matches_choose_highest_exa_rank():
    pages = [page(1, "https://example.com/one", "One"), page(2, "https://example.com/two", "Two")]
    audit_row, recommendation = audit(pages)
    builder = NewWebsiteValidationBuilder(DB(audit_row))

    selected, rank, _ = builder._select_target_page(
        audit_row,
        recommendation,
        [candidate(5, "https://example.com/two"), candidate(3, "https://example.com/one")],
    )

    assert selected.id == 1
    assert rank == 3


def test_valid_recommendation_evidence_page_is_injected_when_not_retrieved():
    pages = [page(8, "https://example.com/revuelto", "Revuelto")]
    audit_row, recommendation = audit(pages, evidence_url="https://example.com/revuelto/")
    builder = NewWebsiteValidationBuilder(DB(audit_row))

    selected, rank, status = builder._select_target_page(
        audit_row, recommendation, [candidate(1, "https://other.example/source")]
    )

    assert selected.id == 8
    assert rank is None
    assert status == "injected_for_controlled_experiment"


def test_no_retrieved_or_relevant_asset_has_no_target():
    pages = [page(8, "https://example.com/careers", "Careers and hiring")]
    audit_row, recommendation = audit(pages, evidence_url=None)
    builder = NewWebsiteValidationBuilder(DB(audit_row))

    selected, rank, status = builder._select_target_page(
        audit_row, recommendation, [candidate(1, "https://other.example/source")]
    )

    assert selected is None
    assert rank is None
    assert status == "content_gap"
    assert audit_row.base_url != "https://example.com/revuelto"


def test_build_preserves_raw_retrieval_before_same_domain_reference_filter(monkeypatch):
    pages = [page(8, "https://example.com/revuelto", "Revuelto")]
    audit_row, recommendation = audit(pages)
    candidates = [
        candidate(1, "https://example.com/revuelto"),
        candidate(2, "https://example.com/news"),
        candidate(3, "https://reference-one.example/source"),
        candidate(4, "https://reference-two.example/source"),
        candidate(5, "https://reference-three.example/source"),
        candidate(6, "https://reference-four.example/source"),
    ]
    target = SimpleNamespace(
        status_code=200,
        body_text="Audited Revuelto content",
        page_title="Revuelto",
        h1="Revuelto",
        url="https://example.com/revuelto",
    )
    monkeypatch.setattr("app.experiment.new_website_validation.fetch_page", lambda *_args, **_kwargs: object())
    monkeypatch.setattr("app.experiment.new_website_validation.extract_page", lambda _response: target)

    result = NewWebsiteValidationBuilder(DB(audit_row), Provider(candidates)).build(
        property_id=7, audit_id=4, opportunity_id=9
    )

    assert [row["url"] for row in result["metadata"]["retrieval_results"]] == [item.url for item in candidates]
    assert result["metadata"]["target_page_id"] == 8
    assert result["metadata"]["target_retrieval_rank"] == 1
    assert [document["url"] for document in result["documents"]] == [
        "https://example.com/revuelto",
        "https://reference-one.example/source",
        "https://reference-two.example/source",
        "https://reference-three.example/source",
        "https://reference-four.example/source",
    ]


def test_build_returns_content_gap_without_a_real_target(monkeypatch):
    pages = [page(8, "https://example.com/careers", "Careers and hiring")]
    audit_row, recommendation = audit(pages)
    provider = Provider([candidate(index, f"https://other{index}.example/source") for index in range(1, 11)])

    result = NewWebsiteValidationBuilder(DB(audit_row), provider).build(
        property_id=7, audit_id=4, opportunity_id=9
    )
    assert result["metadata"]["status"] == "content_gap"
    assert result["documents"] == []
