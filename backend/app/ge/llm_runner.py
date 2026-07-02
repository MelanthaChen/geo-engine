from typing import Protocol

from openai import OpenAI

from app.core.config import settings


class LLMRunner(Protocol):
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        top_p: float = 1,
    ) -> str:
        ...


class OpenAILLMRunner:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        top_p: float = 1,
    ) -> str:
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": user_prompt})

        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            top_p=top_p,
        )

        return response.choices[0].message.content or ""
