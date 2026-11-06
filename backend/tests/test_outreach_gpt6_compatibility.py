from types import SimpleNamespace
import json
import pytest

from app.providers.chatgpt_provider import ChatGPTProvider
from app.ge.geo_rewriter import GeoRewriter


class FakeClient:
    def __init__(self):
        self.options = None
        self.request = None
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def with_options(self, **kwargs):
        self.options = kwargs
        return self

    def create(self, **kwargs):
        self.request = kwargs
        return SimpleNamespace(
            model="gpt-6-luna",
            usage=SimpleNamespace(prompt_tokens=12, completion_tokens=4),
            choices=[SimpleNamespace(index=0, finish_reason="stop", message=SimpleNamespace(content="answer"))],
        )


def test_gpt6_luna_chat_completion_uses_supported_bounded_parameters(monkeypatch):
    captured = []
    monkeypatch.setattr("app.providers.chatgpt_provider.record_provider_usage", lambda **kwargs: captured.append(kwargs))
    provider = object.__new__(ChatGPTProvider)
    fake = FakeClient()
    provider.client = fake

    result = provider.generate_messages(
        messages=[{"role": "user", "content": "question"}],
        model="gpt-6-luna", temperature=0.2, top_p=1,
        max_tokens=640, purpose="strategy_rewrite",
        response_format={"type": "json_object"},
    )

    assert result == "answer"
    assert fake.options == {"max_retries": 0}
    assert fake.request["reasoning_effort"] == "none"
    assert fake.request["temperature"] == 0.2
    assert fake.request["top_p"] == 1
    assert fake.request["max_completion_tokens"] == 640
    assert fake.request["response_format"] == {"type": "json_object"}
    assert "max_tokens" not in fake.request
    assert captured[0]["actual_model"] == "gpt-6-luna"


def test_raw_response_is_archived_before_budget_settlement(monkeypatch):
    events = []
    class Budget:
        def replay_model_response(self, *_args, **_kwargs):
            return None
        def reserve_model(self, *_args, **_kwargs):
            events.append("reserve")
            return 1
        def persist_model_response(self, *_args, **_kwargs):
            events.append("persist")
        def settle_model(self, *_args, **_kwargs):
            events.append("settle")

    monkeypatch.setattr("app.experiment.token_usage_profiler.active_outreach_budget", lambda: Budget())
    monkeypatch.setattr("app.providers.chatgpt_provider.record_provider_usage", lambda **_kwargs: None)
    provider = object.__new__(ChatGPTProvider)
    provider.client = FakeClient()
    provider.generate_messages(
        messages=[{"role": "user", "content": "question"}],
        model="gpt-6-luna", temperature=0, max_tokens=32,
        purpose="strategy_rewrite", response_format={"type": "json_object"},
    )
    assert events == ["reserve", "persist", "settle"]


def test_outreach_rewrite_has_one_transport_attempt_and_budget_maximum_token_cap():
    class FailingRunner:
        def __init__(self):
            self.calls = []

        def generate(self, **kwargs):
            self.calls.append(kwargs)
            raise RuntimeError("provider unavailable")

    runner = FailingRunner()
    with pytest.raises(RuntimeError, match="provider unavailable"):
        GeoRewriter(runner)._generate_with_official_retry("prompt", model="gpt-6-luna")
    assert len(runner.calls) == 1
    assert runner.calls[0]["model"] == "gpt-6-luna"
    assert runner.calls[0]["max_tokens"] == 1024


def test_luna_rewrite_plan_completes_with_the_budget_maximum_output_cap(monkeypatch):
    monkeypatch.setenv("GEO_DISABLE_REWRITE_CACHE", "True")
    source = "Our software checks resumes for ATS compatibility and highlights missing keywords."
    treatment = (
        "How does the software help with ATS compatibility?\n\n"
        "It checks resumes for ATS compatibility and highlights missing keywords."
    )

    class Runner:
        def __init__(self):
            self.calls = []

        def generate(self, **request):
            self.calls.append(request)
            assert request["max_tokens"] == 1024
            assert request["response_format"] == {"type": "json_object"}
            return json.dumps({
                "version": "rewrite-plan-v1",
                "operations": [{"anchor": source, "replacement": treatment}],
            })

    runner = Runner()
    artifact = GeoRewriter(runner).rewrite_artifact(
        source, "How does the software help?", "faq", "gpt-6-luna", 0.2,
    )
    assert len(runner.calls) == 1
    assert artifact.document == treatment
    assert artifact.plan["version"] == "rewrite-plan-v1"
    assert artifact.plan["operations"][0]["anchor"] == source
