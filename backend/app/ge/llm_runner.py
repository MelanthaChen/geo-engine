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
    ) -> str:
        return self.provider.run_experiment(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            purpose=purpose,
        )

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
    ) -> list[str]:
        return self.provider.generate_texts(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            temperature=temperature,
            count=count,
            top_p=top_p,
            max_tokens=max_tokens,
            purpose=purpose,
        )
