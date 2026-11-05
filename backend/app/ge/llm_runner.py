from typing import Protocol

from app.providers import ProviderManager


class LLMRunner(Protocol):
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        top_p: float = 1,
        max_tokens: int | None = None,
        purpose: str = "additional_evaluation",
        response_format: dict | None = None,
    ) -> str:
        ...

    def generate_many(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        count: int,
        top_p: float = 1,
        max_tokens: int | None = None,
        purpose: str = "additional_evaluation",
        response_format: dict | None = None,
    ) -> list[str]:
        ...


class OpenAILLMRunner:
    def __init__(self, provider_name: str | None = "chatgpt"):
        self.provider = ProviderManager.get_provider(provider_name)

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        top_p: float = 1,
        max_tokens: int | None = None,
        purpose: str = "additional_evaluation",
        response_format: dict | None = None,
    ) -> str:
        request = {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "model": model,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
            "purpose": purpose,
        }
        if response_format is not None:
            request["response_format"] = response_format
        return self.provider.run_experiment(**request)

    def generate_many(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        count: int,
        top_p: float = 1,
        max_tokens: int | None = None,
        purpose: str = "additional_evaluation",
        response_format: dict | None = None,
    ) -> list[str]:
        request = dict(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            temperature=temperature,
            count=count,
            top_p=top_p,
            max_tokens=max_tokens,
            purpose=purpose,
        )
        if response_format is not None:
            request["response_format"] = response_format
        return self.provider.generate_texts(**request)
