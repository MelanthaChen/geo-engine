from types import SimpleNamespace

import pytest

from app.experiment.demo_reference_pack import (
    DEMO_QUERY,
    DEMO_TARGET_SHA256,
    DEMO_TARGET_SNAPSHOT,
    REFERENCE_MANIFEST,
    is_demo_property,
    load_demo_reference_documents,
)
from app.experiment import demo_reference_pack
from app.experiment import new_website_validation
from app.experiment.new_website_validation import NewWebsiteValidationBuilder


def test_tracked_demo_reference_pack_is_complete_and_verified():
    references = load_demo_reference_documents()

    assert DEMO_QUERY == "how to explain gaps in employment on your resume"
    assert len(references) == 4
    assert [reference["rank"] for reference in references] == [2, 3, 4, 5]
    assert [reference["url"] for reference in references] == [
        url for url, _ in REFERENCE_MANIFEST
    ]
    assert [reference["content_sha256"] for reference in references] == [
        digest for _, digest in REFERENCE_MANIFEST
    ]
    assert all(reference["content"] for reference in references)


def test_current_demo_target_snapshot_integrity():
    import hashlib

    content = DEMO_TARGET_SNAPSHOT["content"]
    assert DEMO_TARGET_SNAPSHOT["resolved_url"] == (
        "https://geoairesume-web-six.vercel.app/"
    )
    assert hashlib.sha256(content.encode("utf-8")).hexdigest() == DEMO_TARGET_SHA256


def test_demo_source_order_and_target_index_are_unchanged(monkeypatch):
    target = SimpleNamespace(
        status_code=200,
        body_text=DEMO_TARGET_SNAPSHOT["content"],
        page_title="GeoAIResume | GEO Resume Content Experiment",
        h1=None,
        url=DEMO_TARGET_SNAPSHOT["resolved_url"],
    )
    monkeypatch.setattr(new_website_validation, "fetch_page", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(new_website_validation, "extract_page", lambda _response: target)

    audit = SimpleNamespace(
        id=41,
        base_url=DEMO_TARGET_SNAPSHOT["resolved_url"],
        brand_summary="GeoAIResume",
        product_summary="Resume guidance",
    )
    recommendation = SimpleNamespace(id=73)
    builder = object.__new__(NewWebsiteValidationBuilder)
    frozen = builder._build_demo_pack(audit, recommendation)

    assert frozen["metadata"]["target_index"] == 0
    assert frozen["metadata"]["target_rank"] == 1
    assert frozen["documents"][0]["source_role"] == "audited_target"
    assert frozen["documents"][0]["url"] == DEMO_TARGET_SNAPSHOT["resolved_url"]
    assert [document["url"] for document in frozen["documents"][1:]] == [
        url for url, _ in REFERENCE_MANIFEST
    ]
    assert [document["rank"] for document in frozen["documents"]] == [1, 2, 3, 4, 5]


@pytest.mark.parametrize(
    ("property_domain", "configured_target"),
    [
        ("geoairesume-web-six.vercel.app", "https://geoairesume-web-six.vercel.app/"),
        ("https://example.com", "example.com"),
        ("https://example.com/", "https://example.com"),
        ("HTTPS://EXAMPLE.COM", "https://example.com"),
        ("  https://example.com/  ", " example.com "),
    ],
    ids=["scheme", "scheme-reverse", "trailing-slash", "hostname-case", "whitespace"],
)
def test_demo_property_matches_canonical_equivalent_urls(
    monkeypatch,
    property_domain,
    configured_target,
):
    monkeypatch.setattr(
        demo_reference_pack.settings,
        "DEMO_TARGET_URL",
        configured_target,
    )

    assert is_demo_property(SimpleNamespace(
        name="GeoAIResume",
        domain=property_domain,
    ))


def test_demo_property_rejects_unrelated_domain(monkeypatch):
    monkeypatch.setattr(
        demo_reference_pack.settings,
        "DEMO_TARGET_URL",
        "https://geoairesume-web-six.vercel.app/",
    )

    assert not is_demo_property(SimpleNamespace(
        name="GeoAIResume",
        domain="https://example.com",
    ))


def test_demo_property_still_requires_exact_property_name(monkeypatch):
    monkeypatch.setattr(
        demo_reference_pack.settings,
        "DEMO_TARGET_URL",
        "https://geoairesume-web-six.vercel.app/",
    )

    assert not is_demo_property(SimpleNamespace(
        name="Different Property",
        domain="geoairesume-web-six.vercel.app",
    ))
