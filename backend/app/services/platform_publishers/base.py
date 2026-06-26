from dataclasses import dataclass
from typing import Protocol


@dataclass
class PublishRequest:
    title: str
    body: str
    target: str


class Publisher(Protocol):
    platform: str

    def publish(self, request: PublishRequest) -> dict:
        ...
