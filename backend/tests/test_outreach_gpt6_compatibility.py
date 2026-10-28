from types import SimpleNamespace
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
            choices=[SimpleNamespace(index=0, message=SimpleNamespace(content="answer"))],
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
    )

    assert result == "answer"
    assert fake.options == {"max_retries": 0}
    assert fake.request["reasoning_effort"] == "none"
    assert fake.request["temperature"] == 0.2
    assert fake.request["top_p"] == 1
    assert fake.request["max_completion_tokens"] == 640
    assert "max_tokens" not in fake.request
    assert captured[0]["actual_model"] == "gpt-6-luna"


def test_outreach_rewrite_has_one_transport_attempt_and_640_token_cap():
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
    assert runner.calls[0]["max_tokens"] == 640
