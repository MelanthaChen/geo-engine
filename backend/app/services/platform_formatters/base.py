from dataclasses import dataclass
from typing import Protocol

from app.models.content import Content


@dataclass
class PlatformPost:
    title: str
    body: str
    platform: str
    formatter_name: str
    formatter_version: str


class PlatformFormatter(Protocol):
    platform: str

    def prepare(self, content: Content) -> PlatformPost:
        ...
