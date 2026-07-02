import re

from bs4 import BeautifulSoup


class DocumentCleaner:
    def clean_html(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")

        for element in soup(
            [
                "script",
                "style",
                "noscript",
                "svg",
                "header",
                "footer",
                "nav",
                "form",
            ]
        ):
            element.decompose()

        text = soup.get_text(separator=" ")
        return self.clean_text(text)

    def clean_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()
