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
        property=SimpleNamespace(name="Example", brand_name="Example", domain="example.com"),
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


def test_natural_target_not_in_audit_inventory_is_fetched_and_kept(monkeypatch):
    pages = [page(8, "https://example.com/home", "Homepage")]
    audit_row, recommendation = audit(pages)
    candidates = [
        candidate(1, "https://example.com/revuelto-sv", "Revuelto SV"),
        candidate(2, "https://other.example/reference"),
    ]
    snapshots = {
        "https://example.com/revuelto-sv": SimpleNamespace(
            status_code=200, body_text="Revuelto SV details", page_title="Revuelto SV", h1="Revuelto SV", url="https://example.com/revuelto-sv"
        )
    }
    monkeypatch.setattr("app.experiment.new_website_validation.fetch_page", lambda url, **_kwargs: url)
    monkeypatch.setattr("app.experiment.new_website_validation.extract_page", lambda response: snapshots[response])
    result = NewWebsiteValidationBuilder(DB(audit_row), Provider(candidates + [candidate(3, "https://ref-three.example/source"), candidate(4, "https://ref-four.example/source"), candidate(5, "https://ref-five.example/source")] )).build(property_id=7, audit_id=4, opportunity_id=9)
    assert result["metadata"]["target_url"] == "https://example.com/revuelto-sv"
    assert result["metadata"]["target_retrieval_status"] == "retrieved_by_provider"
    assert result["metadata"]["target_retrieval_rank"] == 1
    assert result["metadata"]["target_page_id"] is None


def test_failed_rank_one_target_uses_next_valid_same_domain_result(monkeypatch):
    audit_row, _ = audit([page(8, "https://example.com/home", "Homepage")])
    candidates = [candidate(1, "https://example.com/broken"), candidate(2, "https://example.com/revuelto-sv")]
    valid = SimpleNamespace(status_code=200, body_text="Revuelto SV details", page_title="Revuelto SV", h1="Revuelto SV", url="https://example.com/revuelto-sv")
    def fetch(url, **_kwargs):
        return url
    def extract(url):
        return valid if url.endswith("revuelto-sv") else SimpleNamespace(status_code=404, body_text="", page_title=None, h1=None, url=url)
    monkeypatch.setattr("app.experiment.new_website_validation.fetch_page", fetch)
    monkeypatch.setattr("app.experiment.new_website_validation.extract_page", extract)
    provider = Provider(candidates + [candidate(3, "https://one.example/source"), candidate(4, "https://two.example/source"), candidate(5, "https://three.example/source"), candidate(6, "https://four.example/source")])
    result = NewWebsiteValidationBuilder(DB(audit_row), provider).build(property_id=7, audit_id=4, opportunity_id=9)
    assert result["metadata"]["target_url"] == "https://example.com/revuelto-sv"
    assert result["metadata"]["target_retrieval_rank"] == 2


def test_build_returns_content_gap_without_a_real_target(monkeypatch):
    pages = [page(8, "https://example.com/careers", "Careers and hiring")]
    audit_row, recommendation = audit(pages)
    provider = Provider([candidate(index, f"https://other{index}.example/source") for index in range(1, 11)])

    result = NewWebsiteValidationBuilder(DB(audit_row), provider).build(
        property_id=7, audit_id=4, opportunity_id=9
    )
    assert result["metadata"]["status"] == "content_gap"
    assert result["documents"] == []


def _retrieval_fixture(unavailable_external=1):
    from hashlib import sha256
    site='https://example.com/revuelto'
    docs=[candidate(1,site,'Audited target')]
    for rank in range(2,6):
        text='' if rank >= 6-unavailable_external else f'Public source text {rank}'
        doc=RetrievedDocument(rank=rank,title=f'Source {rank}',url=f'https://source{rank}.example/page',
            plain_text=text,snippet=f'Provider snippet {rank}',retrieval_provider='exa',
            retrieved_at=datetime(2026,11,5,tzinfo=timezone.utc),
            provider_metadata={'request_id':'exa-request-retrieval-test'})
        doc.content_sha256=sha256(text.encode()).hexdigest()
        docs.append(doc)
    docs[0].provider_metadata={'request_id':'exa-request-retrieval-test'}
    return docs


def _target_snapshot(url):
    return SimpleNamespace(status_code=200,body_text='Audited company content',page_title='Revuelto SV',h1='Revuelto SV',url=url)


def test_raw_retrieval_is_checkpointed_before_evidence_validation_failure(monkeypatch):
    audit_row,_=audit([page(8,'https://example.com/revuelto','Revuelto')])
    docs=_retrieval_fixture(unavailable_external=2)  # only two external pages contain content
    target=_target_snapshot('https://example.com/revuelto')
    monkeypatch.setattr('app.experiment.new_website_validation.fetch_page',lambda url,**_kwargs:url)
    monkeypatch.setattr('app.experiment.new_website_validation.extract_page',lambda response:target)
    captured=[]
    with pytest.raises(NewWebsiteValidationError,match='at least 3 required') as failure:
        NewWebsiteValidationBuilder(DB(audit_row),Provider(docs)).build(
            property_id=7,audit_id=4,opportunity_id=9,
            checkpoint_callback=lambda **checkpoint:captured.append(checkpoint))
    assert failure.value.code == 'insufficient_external_sources'
    assert len(captured)==1
    assert len(captured[0]['documents'])==5
    assert sum(not item.plain_text for item in captured[0]['documents'])==2
    assert captured[0]['documents'][0].provider_metadata['request_id']=='exa-request-retrieval-test'


def test_recovered_exa_documents_skip_search_and_mark_unavailable_sources(monkeypatch):
    audit_row,_=audit([page(8,'https://example.com/revuelto','Revuelto')])
    docs=_retrieval_fixture(unavailable_external=1)
    target=_target_snapshot('https://example.com/revuelto')
    monkeypatch.setattr('app.experiment.new_website_validation.fetch_page',lambda url,**_kwargs:url)
    monkeypatch.setattr('app.experiment.new_website_validation.extract_page',lambda response:target)
    class SearchMustNotRun:
        provider_id='exa'
        def search(self,**_kwargs):pytest.fail('recovery must not repeat Exa')
    result=NewWebsiteValidationBuilder(DB(audit_row),SearchMustNotRun()).build(
        property_id=7,audit_id=4,opportunity_id=9,retrieved_documents=docs)
    assert len(result['documents'])==4  # audited target plus three usable external references
    quality=result['metadata']['evidence_quality']
    assert quality=={'minimum_external_sources':3,'usable_external_sources':3,
        'unavailable_retrieval_results':1,'status':'ACCEPTED'}
    unavailable=next(item for item in result['metadata']['retrieval_results'] if not item['content_available'])
    assert unavailable['content_length']==0
    assert unavailable['provider_metadata']['request_id']=='exa-request-retrieval-test'
