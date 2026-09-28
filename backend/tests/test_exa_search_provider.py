import pytest
import requests

from app.ge.brave_search_provider import BraveSearchProvider
from app.ge.exa_search_provider import ExaRetrievalError, ExaSearchProvider
from app.ge.ge_service import GenerativeEngineService
from app.ge.search_provider import RetrievedDocument
from app.ge.search_provider_factory import build_search_provider
from app.services.website_audit.crawler import CrawlResponse


class Response:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


def exa_payload(count=3):
    return {
        "requestId": "request-123",
        "results": [
            {
                "id": f"exa-result-{index}",
                "title": f"Result {index}",
                "url": f"https://reference-{index}.example/page",
                "publishedDate": f"2026-09-{index:02d}T00:00:00.000Z",
                "author": f"Author {index}",
                "highlights": [f"Preview {index}"],
            }
            for index in range(1, count + 1)
        ],
    }


def test_exa_preserves_order_and_uses_official_request_contract(monkeypatch):
    captured = {}

    def request(url, **kwargs):
        captured.update({"url": url, **kwargs})
        return Response(payload=exa_payload())

    monkeypatch.setattr("app.ge.exa_search_provider.requests.post", request)
    monkeypatch.setattr(
        "app.ge.exa_search_provider.fetch_page",
        lambda url, timeout_seconds: CrawlResponse(
            url=url,
            status_code=200,
            html=f"<html><body><h1>{url}</h1><p>Fetched body</p></body></html>",
            content_type="text/html",
            html_accepted=True,
        ),
    )

    documents = ExaSearchProvider(api_key="test-key", result_count=10).search(
        "controlled query", top_k=3
    )

    assert captured["url"] == "https://api.exa.ai/search"
    assert captured["headers"]["x-api-key"] == "test-key"
    assert captured["json"] == {
        "query": "controlled query",
        "numResults": 10,
        "type": "auto",
    }
    assert [item.rank for item in documents] == [1, 2, 3]
    assert [item.url for item in documents] == [
        "https://reference-1.example/page",
        "https://reference-2.example/page",
        "https://reference-3.example/page",
    ]
    assert [item.snippet for item in documents] == [
        "Preview 1", "Preview 2", "Preview 3"
    ]
    assert documents[0].provider_metadata == {
        "request_id": "request-123",
        "id": "exa-result-1",
        "published_date": "2026-09-01T00:00:00.000Z",
        "author": "Author 1",
    }
    assert all(item.retrieval_provider == "exa" for item in documents)


def test_factory_selects_exa_by_default_without_other_credentials(monkeypatch):
    monkeypatch.setattr("app.ge.search_provider_factory.settings.SEARCH_PROVIDER", "exa")
    monkeypatch.setattr("app.ge.search_provider_factory.settings.EXA_API_KEY", None)
    monkeypatch.setattr("app.ge.search_provider_factory.settings.BRAVE_SEARCH_API_KEY", None)
    monkeypatch.setattr("app.ge.search_provider_factory.settings.GOOGLE_SEARCH_API_KEY", None)
    monkeypatch.setattr("app.ge.search_provider_factory.settings.GOOGLE_SEARCH_ENGINE_ID", None)

    assert isinstance(build_search_provider(), ExaSearchProvider)


def test_factory_keeps_brave_compatibility(monkeypatch):
    monkeypatch.setattr("app.ge.search_provider_factory.settings.SEARCH_PROVIDER", "brave")
    assert isinstance(build_search_provider(), BraveSearchProvider)


def test_missing_exa_key_disables_only_exa_live_retrieval():
    with pytest.raises(ExaRetrievalError, match="^Exa Search API is not configured\\.$"):
        ExaSearchProvider(api_key="").search("query")


@pytest.mark.parametrize(
    ("status", "message"),
    [
        (401, "authentication failed"),
        (403, "authentication failed"),
        (429, "rate limit"),
        (500, "temporarily unavailable"),
        (503, "temporarily unavailable"),
    ],
)
def test_exa_provider_errors_are_clean(monkeypatch, status, message):
    monkeypatch.setattr(
        "app.ge.exa_search_provider.requests.post",
        lambda *_args, **_kwargs: Response(status_code=status),
    )
    with pytest.raises(ExaRetrievalError, match=message):
        ExaSearchProvider(api_key="test-key").search("query")


def test_exa_timeout_is_clean(monkeypatch):
    def timeout(*_args, **_kwargs):
        raise requests.Timeout("provider timeout")

    monkeypatch.setattr("app.ge.exa_search_provider.requests.post", timeout)
    with pytest.raises(ExaRetrievalError, match="timed out"):
        ExaSearchProvider(api_key="test-key").search("query")


def test_empty_exa_results_are_reported(monkeypatch):
    monkeypatch.setattr(
        "app.ge.exa_search_provider.requests.post",
        lambda *_args, **_kwargs: Response(payload={"results": []}),
    )
    with pytest.raises(ExaRetrievalError, match="no web results"):
        ExaSearchProvider(api_key="test-key").search("query")


def test_baseline_and_treatment_reuse_one_exa_source_set():
    class Provider:
        provider_id = "exa"

        def __init__(self):
            self.calls = 0

        def search(self, query, top_k=5):
            self.calls += 1
            return [
                RetrievedDocument(
                    rank=index,
                    title=f"Source {index}",
                    url=f"https://source-{index}.example",
                    plain_text=f"frozen source {index}",
                    is_optimization_target=index == 1,
                    retrieval_provider="exa",
                )
                for index in range(1, 6)
            ]

    class Runner:
        def __init__(self):
            self.prompts = []

        def generate(self, **request):
            self.prompts.append(request["user_prompt"])
            return "Teacher answer"

    provider = Provider()
    runner = Runner()
    service = GenerativeEngineService(search_provider=provider, llm_runner=runner)
    from app.ge.geo_rewriter import RewriteArtifact

    service.rewriter.rewrite_artifact = lambda document_text, strategy, **_kwargs: RewriteArtifact(
        document_text if strategy == "original" else "optimized target",
        {"version": "rewrite-plan-v1", "operations": []},
    )

    result = service.run_query(
        query="Controlled question",
        strategies=["original", "authoritative"],
        model="test-model",
        temperature=0,
        random_seed=1,
        response_samples=1,
    )

    assert provider.calls == 1
    assert len(result["documents"]) == 5
    assert all("frozen source 2" in prompt for prompt in runner.prompts)
    assert "optimized target" not in runner.prompts[0]
    assert "optimized target" in runner.prompts[1]
