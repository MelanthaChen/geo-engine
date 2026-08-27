from openai import OpenAI
import time

from app.core.config import settings
from app.experiment.token_usage_profiler import record_provider_usage


class ChatGPTProvider:
    name = "chatgpt"

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def generate_text(
        self,
        *,
        system_prompt: str | None,
        user_prompt: str,
        model: str,
        temperature: float,
        top_p: float = 1,
        max_tokens: int | None = None,
        purpose: str = "additional_evaluation",
    ) -> str:
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": user_prompt})

        return self.generate_messages(
            messages=messages,
            model=model,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            purpose=purpose,
        )

    def generate_texts(
        self,
        *,
        system_prompt: str | None,
        user_prompt: str,
        model: str,
        temperature: float,
        count: int,
        top_p: float = 1,
        max_tokens: int | None = None,
        purpose: str = "additional_evaluation",
    ) -> list[str]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})
        return self.generate_messages_many(
            messages=messages,
            model=model,
            temperature=temperature,
            count=count,
            top_p=top_p,
            max_tokens=max_tokens,
            purpose=purpose,
        )

    def generate_messages(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        top_p: float = 1,
        max_tokens: int | None = None,
        purpose: str = "additional_evaluation",
    ) -> str:
        return self.generate_messages_many(
            messages=messages,
            model=model,
            temperature=temperature,
            count=1,
            top_p=top_p,
            max_tokens=max_tokens,
            purpose=purpose,
        )[0].removesuffix("\n")

    def generate_messages_many(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        count: int,
        top_p: float = 1,
        max_tokens: int | None = None,
        purpose: str = "additional_evaluation",
    ) -> list[str]:
        if count < 1:
            raise ValueError("count must be at least one")
        request = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "n": count,
        }

        if max_tokens is not None:
            request["max_tokens"] = max_tokens

        started = time.perf_counter()
        response = self.client.chat.completions.create(**request)
        record_provider_usage(
            purpose=purpose,
            requested_model=model,
            actual_model=response.model,
            usage=response.usage,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )

        choices = sorted(response.choices, key=lambda choice: choice.index)
        if len(choices) != count:
            raise RuntimeError(
                f"OpenAI returned {len(choices)} choices for requested n={count}"
            )
        return [(choice.message.content or "") + "\n" for choice in choices]

    def run_query(self, **kwargs):
        return self.generate_text(**kwargs)

    def generate_content(self, **kwargs):
        return self.generate_text(**kwargs)

    def run_citation_test(self, **kwargs):
        return self.generate_text(**kwargs)

    def run_experiment(self, **kwargs):
        return self.generate_text(**kwargs)
