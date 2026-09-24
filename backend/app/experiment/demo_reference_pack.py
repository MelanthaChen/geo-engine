"""Immutable reference pack for the isolated GeoAIResume professor demo."""

from datetime import datetime
import hashlib
import json
from pathlib import Path


DEMO_PROPERTY_DOMAIN = "http://127.0.0.1:8000"
DEMO_WORKFLOW = "princeton-style-frozen-new-website-demo-validation-v1"
DEMO_QUERY_POLICY_VERSION = "geoairesume-resume-gap-query-v1"
DEMO_QUERY = "how to explain gaps in employment on your resume"
DEMO_AUDIT_EVIDENCE = {
    "source_repository": "https://github.com/MelanthaChen/geoairesume-web",
    "source_file": "src/data/expandedArticles.ts",
    "source_slug": "resume-gap-explanation-guide",
    "primary_intent": "Explain resume gaps clearly and return attention to current readiness.",
}
DEMO_FROZEN_AT = datetime.fromisoformat("2026-09-23T19:45:00+00:00")
DEMO_TARGET_SHA256 = "83d7f3a6571ff7e8d4bd42e72460a8a687f9acadfd6ffa97ed023d61fb6cffb2"
GEO_BENCH_ROW_INDEX = 547
REFERENCE_MANIFEST = (
    ("https://hbr.org/2023/06/how-to-explain-a-gap-in-your-resume", "035cb9219440cec20bdd2a29565f0ff77bf5d15c16b9dd5cad80a24e224ba8d8"),
    ("https://novoresume.com/career-blog/employment-gap-in-resume", "f9168fe05894b3b1a3fc7fa9f357514ab3eecb011f33455300f92e1df2006276"),
    ("https://www.grammarly.com/blog/resume-gap/", "21c39c1c1fb346bc38b55442517c14e35165a8f7d0ff584b37ce41b98ffd098d"),
    ("https://www.umassglobal.edu/news-and-events/blog/how-to-explain-gaps-in-employment", "db2c47e440d73e01f969c616922c07c145a62bd936e55c3d367c1bd889c89b8e"),
)


class DemoReferencePackError(RuntimeError):
    pass


def is_demo_property(property_record) -> bool:
    return (
        property_record.name == "GeoAIResume"
        and property_record.domain.rstrip("/") == DEMO_PROPERTY_DOMAIN
    )


def load_demo_reference_documents() -> list[dict]:
    dataset_path = (
        Path(__file__).resolve().parents[2]
        / "experiment_dataset" / "geo_bench" / "test.jsonl"
    )
    with dataset_path.open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            if index == GEO_BENCH_ROW_INDEX:
                row = json.loads(line)
                break
        else:
            raise DemoReferencePackError("Frozen GEO-Bench reference row is missing")

    if row.get("query") != DEMO_QUERY:
        raise DemoReferencePackError("Frozen demo query no longer matches its source row")
    documents = []
    for rank, ((expected_url, expected_hash), source) in enumerate(
        zip(REFERENCE_MANIFEST, row.get("sources", [])[:4]), start=2
    ):
        content = str(source.get("cleaned_text") or source.get("raw_text") or "").strip()
        actual_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if source.get("url") != expected_url or actual_hash != expected_hash:
            raise DemoReferencePackError(
                f"Frozen demo reference integrity check failed at source rank {rank}"
            )
        documents.append({
            "rank": rank,
            "title": expected_url.split("/")[2],
            "url": expected_url,
            "content": content,
            "content_sha256": actual_hash,
        })
    if len(documents) != 4:
        raise DemoReferencePackError("Frozen demo pack must contain four references")
    return documents
