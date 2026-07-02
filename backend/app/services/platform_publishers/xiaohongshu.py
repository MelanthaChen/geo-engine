from app.services.platform_publishers.base import PublishRequest
from app.services.xiaohongshu_publisher import publish_to_xiaohongshu


class XiaohongshuPublisher:
    platform = "xiaohongshu"

    def publish(self, request: PublishRequest) -> dict:
        return publish_to_xiaohongshu(
            target=request.target,
            title=request.title,
            body=request.body,
            session_path=request.session_path,
        )
