import json
from pathlib import Path
from urllib.request import urlopen


GEO_BENCH_TEST_URL = (
    "https://huggingface.co/datasets/GEO-Optim/geo-bench/resolve/main/test.jsonl"
)
DEFAULT_CACHE_PATH = (
    Path(__file__).resolve().parents[2]
    / "experiment_dataset"
    / "geo_bench"
    / "test.jsonl"
)


class GeoBenchLoader:
    def __init__(self, cache_path: Path | None = None):
        self.cache_path = cache_path or DEFAULT_CACHE_PATH

    def load_test_entries(self, limit: int) -> list[dict]:
        self._ensure_cached()
        entries = []

        with self.cache_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if len(entries) >= limit:
                    break

                row = json.loads(line)
                entry = self._to_benchmark_entry(row)

                if entry:
                    entries.append(entry)

        if not entries:
            raise RuntimeError("Official GEO-bench test split did not yield any rows.")

        return entries

    def _ensure_cached(self):
        if self.cache_path.exists() and self.cache_path.stat().st_size > 0:
            return

        self.cache_path.parent.mkdir(parents=True, exist_ok=True)

        with urlopen(GEO_BENCH_TEST_URL, timeout=120) as response:
            self.cache_path.write_bytes(response.read())

    def _to_benchmark_entry(self, row: dict) -> dict | None:
        query = str(row.get("query") or "").strip()
        sources = row.get("sources") or []

        if not query or len(sources) < 5:
            return None

        documents = []

        for rank, source in enumerate(sources[:5], start=1):
            url = str(source.get("url") or "").strip()
            content = str(
                source.get("cleaned_text") or source.get("raw_text") or ""
            ).strip()

            if not content:
                return None

            documents.append(
                {
                    "rank": rank,
                    "title": self._title_from_url(url, rank),
                    "url": url,
                    "content": content,
                    "raw_text": source.get("raw_text"),
                }
            )

        return {
            "query": query,
            "documents": documents,
            "metadata": {
                "benchmark": "GEO-bench",
                "split": "test",
                "tags": row.get("tags") or [],
                "sugg_idx": row.get("sugg_idx"),
            },
        }

    def _title_from_url(self, url: str, rank: int) -> str:
        if not url:
            return f"GEO-bench Source {rank}"

        return url.replace("https://", "").replace("http://", "").rstrip("/") or (
            f"GEO-bench Source {rank}"
        )
