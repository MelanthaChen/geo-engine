"""Embedding provider boundary for the future GEO Predictor."""

from typing import Protocol


class EmbeddingService(Protocol):
    """Contract implemented by future local or hosted embedding adapters.

    This module is the foundation for a future GEO prediction system.
    """

    @property
    def model_name(self) -> str:
        """Return the stable identifier for the configured embedding model."""
        ...

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts while preserving input order.

        TODO: Add a concrete, versioned provider implementation.
        """
        ...
