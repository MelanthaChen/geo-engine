from openai import OpenAI

from app.core.config import settings


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
        )

    def generate_messages(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        top_p: float = 1,
        max_tokens: int | None = None,
    ) -> str:
        request = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
        }

        if max_tokens is not None:
            request["max_tokens"] = max_tokens

        response = self.client.chat.completions.create(**request)

        return response.choices[0].message.content or ""

    def run_query(self, **kwargs):
        return self.generate_text(**kwargs)

    def generate_content(self, **kwargs):
        return self.generate_text(**kwargs)

    def run_citation_test(self, **kwargs):
        return self.generate_text(**kwargs)

    def run_experiment(self, **kwargs):
        return self.generate_text(**kwargs)
