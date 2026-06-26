from app.services.platform_publishers.base import PublishRequest


class UnsupportedPublisher:
    platform = "unsupported"

    def __init__(self, platform: str):
        self.platform = platform

    def publish(self, request: PublishRequest) -> dict:
        raise NotImplementedError(
            f"No publisher is configured for platform: {self.platform}"
        )
