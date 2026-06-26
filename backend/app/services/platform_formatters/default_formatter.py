from app.models.content import Content
from app.services.platform_formatters.base import PlatformPost
from app.utils.title_extractor import extract_article_title


class DefaultFormatter:
    platform = "default"

    def prepare(self, content: Content) -> PlatformPost:
        title = extract_article_title(
            generated_content=content.body,
            fallback=content.title,
        )

        return PlatformPost(
            title=title,
            body=content.body or "",
            platform=self.platform,
        )
