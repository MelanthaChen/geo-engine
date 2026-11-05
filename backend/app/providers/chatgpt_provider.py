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
        response_format: dict | None = None,
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
            response_format=response_format,
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
        response_format: dict | None = None,
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
            response_format=response_format,
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
        response_format: dict | None = None,
    ) -> str:
        return self.generate_messages_many(
            messages=messages,
            model=model,
            temperature=temperature,
            count=1,
            top_p=top_p,
            max_tokens=max_tokens,
            purpose=purpose,
            response_format=response_format,
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
        response_format: dict | None = None,
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
        if response_format is not None:
            request["response_format"] = response_format

        started = time.perf_counter()
        client = self.client
        budget = None
        reservation = None
        if model == "gpt-6-luna":
            # GPT-6 Luna supports Chat Completions.  Pin reasoning off so the
            # documented sampling controls are supported, use the current
            # completion-token parameter, and disable SDK retries so an
            # outreach attempt cannot silently multiply billable calls.
            request["reasoning_effort"] = "none"
            if max_tokens is not None:
                request.pop("max_tokens", None)
                request["max_completion_tokens"] = max_tokens
            client = self.client.with_options(max_retries=0)
            from app.experiment.token_usage_profiler import active_outreach_budget
            budget = active_outreach_budget()
            if budget is not None:
                replay = budget.replay_model_response(
                    model, messages, purpose, count=count,
                    parameters={"temperature": temperature, "top_p": top_p,
                                "max_output_tokens": int(max_tokens or 0),
                                "response_format": response_format},
                )
                if replay is not None:
                    return [output + "\n" for output in replay]
                reservation = budget.reserve_model(model, messages, int(max_tokens or 0))

        response = client.chat.completions.create(**request)
        if budget is not None:
            # Archive the provider's raw output before settling or returning it
            # to the GEO rewriter. A parser failure must not destroy paid work.
            budget.persist_model_response(
                reservation, response, response.model, messages, purpose,
                parameters={"temperature": temperature, "top_p": top_p,
                            "max_output_tokens": int(max_tokens or 0),
                            "response_format": response_format},
            )
            budget.settle_model(reservation, response.model, response.usage)
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
