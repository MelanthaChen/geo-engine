from types import SimpleNamespace

import pytest

from app.experiment.demo_reference_pack import (
    DEMO_QUERY,
    REFERENCE_MANIFEST,
    is_demo_property,
    load_demo_reference_documents,
)
from app.experiment import demo_reference_pack


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
