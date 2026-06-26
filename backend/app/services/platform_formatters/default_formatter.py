from app.models.content import Content
from app.services.platform_formatters.base import PlatformPost
from app.utils.title_extractor import extract_article_title


class DefaultFormatter:
    platform = "default"
    formatter_name = "DefaultFormatter"
    formatter_version = "1.0.0"

    def prepare(self, content: Content) -> PlatformPost:
        title = extract_article_title(
            generated_content=content.body,
            fallback=content.title,
        )

        return PlatformPost(
            title=title,
            body=content.body or "",
            platform=self.platform,
            formatter_name=self.formatter_name,
            formatter_version=self.formatter_version,
        )
