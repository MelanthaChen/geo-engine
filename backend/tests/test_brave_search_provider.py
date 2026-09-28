from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.ge.brave_search_provider import BraveRetrievalError, BraveSearchProvider
from app.ge.search_provider import RetrievedDocument
from app.ge.search_provider_factory import build_search_provider
from app.services.website_audit.crawler import CrawlResponse
from app.teacher_pipeline.query_contexts import AuditQueryContextGenerator
from app.teacher_pipeline.training_context_builder import TrainingContextBuilder


class Response:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


def brave_payload(count=3):
    return {
        "web": {
            "results": [
                {
                    "title": f"Result {index}",
                    "url": f"https://reference-{index}.example/page",
                    "description": f"Snippet {index}",
                }
                for index in range(1, count + 1)
            ]
        }
    }


def test_brave_preserves_result_order_and_request_contract(monkeypatch):
    captured = {}

    def request(url, **kwargs):
        captured.update({"url": url, **kwargs})
        return Response(payload=brave_payload())

    monkeypatch.setattr("app.ge.brave_search_provider.requests.get", request)
    monkeypatch.setattr(
        "app.ge.brave_search_provider.fetch_page",
        lambda url, timeout_seconds: CrawlResponse(
            url=url,
            status_code=200,
            html=f"<html><body><h1>{url}</h1><p>Fetched body</p></body></html>",
            content_type="text/html",
            html_accepted=True,
        ),
    )

    documents = BraveSearchProvider(api_key="test-key", result_count=10).search(
        "controlled query", top_k=3
    )

    assert captured["url"] == BraveSearchProvider.endpoint
    assert captured["headers"]["X-Subscription-Token"] == "test-key"
    assert captured["params"] == {
        "q": "controlled query",
        "count": 10,
        "country": "US",
        "search_lang": "en",
    }
    assert [item.rank for item in documents] == [1, 2, 3]
    assert [item.url for item in documents] == [
        "https://reference-1.example/page",
        "https://reference-2.example/page",
        "https://reference-3.example/page",
    ]
    assert [item.snippet for item in documents] == [
        "Snippet 1", "Snippet 2", "Snippet 3"
    ]
    assert all(item.retrieval_provider == "brave" for item in documents)


def test_missing_brave_key_disables_only_live_retrieval():
    with pytest.raises(BraveRetrievalError, match="^Brave Search API is not configured\\.$"):
        BraveSearchProvider(api_key="").search("query")


def test_brave_remains_selectable_without_google_credentials(monkeypatch):
    monkeypatch.setattr("app.ge.search_provider_factory.settings.SEARCH_PROVIDER", "brave")
    monkeypatch.setattr("app.ge.search_provider_factory.settings.BRAVE_SEARCH_API_KEY", None)
    monkeypatch.setattr("app.ge.search_provider_factory.settings.GOOGLE_SEARCH_API_KEY", None)
    monkeypatch.setattr("app.ge.search_provider_factory.settings.GOOGLE_SEARCH_ENGINE_ID", None)

    provider = build_search_provider()

    assert isinstance(provider, BraveSearchProvider)


@pytest.mark.parametrize(
    ("status", "message"),
    [
        (401, "authentication failed"),
        (403, "authentication failed"),
        (429, "rate limit"),
        (503, "temporarily unavailable"),
    ],
)
def test_brave_provider_errors_are_clean(monkeypatch, status, message):
    monkeypatch.setattr(
        "app.ge.brave_search_provider.requests.get",
        lambda *_args, **_kwargs: Response(status_code=status),
    )
    with pytest.raises(BraveRetrievalError, match=message):
        BraveSearchProvider(api_key="test-key").search("query")


def test_empty_brave_results_are_reported(monkeypatch):
    monkeypatch.setattr(
        "app.ge.brave_search_provider.requests.get",
        lambda *_args, **_kwargs: Response(payload={"web": {"results": []}}),
    )
    with pytest.raises(BraveRetrievalError, match="no web results"):
        BraveSearchProvider(api_key="test-key").search("query")


def test_generic_provider_freezes_once_per_context_and_records_injected_target(monkeypatch):
    audit = SimpleNamespace(
        id=7,
        property=SimpleNamespace(name="Target", brand_name="Target"),
        pages=[SimpleNamespace(
            id=index + 1,
            url=f"https://target.example/topic-{index}",
            page_title=f"Target Topic {index}",
            h1=f"Target Topic {index}",
            meta_description=f"Target evidence {index}",
            status_code=200,
            word_count=100,
            content_sha256=f"{index:064x}",
            is_duplicate=False,
        ) for index in range(40)],
    )
    contexts = AuditQueryContextGenerator().generate(audit, count=100)
    monkeypatch.setattr(
        "app.teacher_pipeline.training_context_builder.fetch_page",
        lambda url, timeout_seconds: CrawlResponse(
            url=url,
            status_code=200,
            html="<html><body><h1>Target</h1><p>Real target text</p></body></html>",
            content_type="text/html",
            html_accepted=True,
        ),
    )

    class Provider:
        provider_id = "exa"
        display_name = "Exa"

        def __init__(self):
            self.calls = []

        def search(self, query, top_k=10):
            self.calls.append(query)
            now = datetime.now(timezone.utc)
            return [
                RetrievedDocument(
                    rank=index,
                    title=f"Reference {index}",
                    url=f"https://reference-{index}.example/{len(self.calls)}",
                    plain_text=f"Reference body {index}",
                    snippet=f"Snippet {index}",
                    retrieval_provider="exa",
                    retrieved_at=now,
                )
                for index in range(1, 6)
            ]

    provider = Provider()
    entries = TrainingContextBuilder(search_provider=provider).freeze(contexts)

    assert len(provider.calls) == len(contexts)
    assert len(entries) == len(contexts)
    for entry in entries:
        evidence = entry["documents"][0]["supporting_evidence"]
        assert evidence["target_retrieval_status"] == "injected_for_controlled_experiment"
        assert evidence["source_order"] == [item["url"] for item in entry["documents"]]
        assert evidence["target_index"] == 0
        assert entry["documents"][0]["retrieval_provider"] == "injected_for_controlled_experiment"
        assert all(item["retrieval_provider"] == "exa" for item in entry["documents"][1:])


def test_target_provenance_records_real_provider_result(monkeypatch):
    context = SimpleNamespace(
        target_url="https://target.example/page",
        query="Target query",
        query_source="generated",
        query_intent="overview",
        originating_evidence={"audit_id": 7, "page_id": 1},
    )
    monkeypatch.setattr(
        "app.teacher_pipeline.training_context_builder.fetch_page",
        lambda url, timeout_seconds: CrawlResponse(
            url=url,
            status_code=200,
            html="<html><body><p>Target text</p></body></html>",
            content_type="text/html",
            html_accepted=True,
        ),
    )

    class Provider:
        provider_id = "exa"

        def search(self, query, top_k=10):
            urls = ["https://target.example/page"] + [
                f"https://reference-{index}.example/page" for index in range(1, 6)
            ]
            return [
                RetrievedDocument(
                    rank=index,
                    title=f"Result {index}",
                    url=url,
                    plain_text=f"Body {index}",
                )
                for index, url in enumerate(urls, start=1)
            ]

    entry = TrainingContextBuilder(search_provider=Provider()).freeze([context])[0]
    evidence = entry["documents"][0]["supporting_evidence"]

    assert evidence["target_retrieval_status"] == "retrieved_by_provider"
    assert evidence["retrieval_results"][0]["url"] == context.target_url
