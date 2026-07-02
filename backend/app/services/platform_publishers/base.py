from dataclasses import dataclass
from typing import Protocol


@dataclass
class PublishRequest:
    title: str
    body: str
    target: str
    account_id: int | None = None
    account_handle: str | None = None
    browser_profile_name: str | None = None
    session_path: str | None = None


class Publisher(Protocol):
    platform: str

    def publish(self, request: PublishRequest) -> dict:
        ...
