from typing import Protocol


class Provider(Protocol):
    name: str

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
        ...

    def generate_messages(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        top_p: float = 1,
        max_tokens: int | None = None,
    ) -> str:
        ...

    def run_query(self, **kwargs):
        raise NotImplementedError

    def generate_content(self, **kwargs):
        raise NotImplementedError

    def run_citation_test(self, **kwargs):
        raise NotImplementedError

    def run_experiment(self, **kwargs):
        raise NotImplementedError


class UnimplementedProvider:
    name = "unimplemented"

    def generate_text(self, **kwargs) -> str:
        raise NotImplementedError(
            f"{self.name} provider is not implemented yet."
        )

    def generate_messages(self, **kwargs) -> str:
        raise NotImplementedError(
            f"{self.name} provider is not implemented yet."
        )

    def run_query(self, **kwargs):
        raise NotImplementedError(
            f"{self.name} provider is not implemented yet."
        )

    def generate_content(self, **kwargs):
        raise NotImplementedError(
            f"{self.name} provider is not implemented yet."
        )

    def run_citation_test(self, **kwargs):
        raise NotImplementedError(
            f"{self.name} provider is not implemented yet."
        )

    def run_experiment(self, **kwargs):
        raise NotImplementedError(
            f"{self.name} provider is not implemented yet."
        )
