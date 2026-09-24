from app.experiment.demo_reference_pack import (
    DEMO_QUERY,
    REFERENCE_MANIFEST,
    load_demo_reference_documents,
)


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
