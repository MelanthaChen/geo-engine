from app.services.website_audit.crawler import CrawlResponse
from app.services.website_audit.evidence import aggregate_site_evidence
from app.services.website_audit.extractor import extract_page, extract_pages
from app.services.website_audit.recommendations import build_recommendations


def response(url: str, html: str) -> CrawlResponse:
    return CrawlResponse(
        url=url,
        status_code=200,
        html=html,
        content_type="text/html",
        html_accepted=True,
        requested_url=f"{url}?requested=1",
    )


RICH_HTML = """
<html>
  <head>
    <title>Hybrid Powertrain Research</title>
    <meta name="description" content="Measured V12 hybrid powertrain research.">
    <meta name="robots" content="index, follow">
    <meta name="author" content="Dr. Ada Expert">
    <meta property="article:published_time" content="2026-09-01">
    <meta property="article:modified_time" content="2026-09-20">
    <link rel="canonical" href="/research/hybrid">
    <script type="application/ld+json">
      {"@graph": [
        {"@type": "Article", "author": {"@type": "Person", "name": "Dr. Ada Expert"}, "datePublished": "2026-09-01"},
        {"@type": "Organization", "name": "Example Lab"},
        {"@type": "FAQPage"}
      ]}
    </script>
  </head>
  <body>
    <h1>Hybrid Powertrain Evidence</h1>
    <h2>How does the V12 system work?</h2>
    <p>The V12 hybrid powertrain combines two systems and provides measured performance.</p>
    <h3>Research findings</h3>
    <p>According to the 2025 laboratory report, efficiency improved by 18% and testing covered 240 vehicles costing $2 million.</p>
    <blockquote>Measured performance must be independently reproducible.</blockquote>
    <p>Dr. Ada Expert said “The hybrid powertrain evidence is useful for engineering teams.”</p>
    <p><a href="https://social.example/profile">Social profile</a></p>
    <p>Source: <a href="https://journal.example/research/study">laboratory study</a></p>
    <p><a href="/internal">Internal guide</a></p>
    <dl><dt>Regenerative braking</dt><dd>A system that recovers kinetic energy.</dd></dl>
    <ul><li>Hybrid powertrain</li><li>V12 engine</li></ul>
  </body>
</html>
"""


def test_extracts_base_page_evidence_and_strategy_signals():
    page = extract_page(response("https://example.test/final", RICH_HTML))
    evidence = page.evidence

    assert evidence["identity"] == {
        "requested_url": "https://example.test/final?requested=1",
        "final_url": "https://example.test/final",
        "canonical_url": "https://example.test/research/hybrid",
        "path_family": "/final",
        "extraction_method": "http",
        "http_html_accepted": True,
    }
    assert evidence["metadata"]["robots_directives"] == ["index", "follow"]
    assert evidence["headings"]["h1"] == ["Hybrid Powertrain Evidence"]
    assert evidence["headings"]["h2"] == ["How does the V12 system work?"]
    assert evidence["headings"]["h3"] == ["Research findings"]
    assert evidence["content"]["paragraph_count"] == 6
    assert evidence["content"]["list_count"] == 1
    assert evidence["content"]["preview"]

    structured = evidence["structured_data"]
    assert {"Article", "Person", "Organization", "FAQPage"} <= set(structured["schema_types"])
    assert structured["article_present"] is True
    assert structured["organization_present"] is True
    assert structured["person_or_author_present"] is True

    faq = evidence["strategies"]["faq"]
    assert faq["question_heading_count"] == 1
    assert faq["detected_qa_pair_count"] == 1
    assert faq["faq_page_schema_present"] is True

    statistics = evidence["strategies"]["statistics"]
    assert statistics["numeric_claim_count"] >= 4
    assert statistics["percentage_count"] == 1
    assert statistics["currency_value_count"] == 1
    assert statistics["date_or_year_count"] >= 1
    assert any("18%" in snippet for snippet in statistics["quantitative_snippets"])

    links = evidence["links"]
    assert len(links["external_urls"]) == 2
    assert len(links["reference_like_links"]) == 1
    assert links["reference_domains"] == ["journal.example"]
    assert links["reference_like_links"][0]["anchor_text"] == "laboratory study"

    quotation = evidence["strategies"]["quotation"]
    assert quotation["blockquote_count"] == 1
    assert quotation["quoted_passage_count"] >= 1
    assert quotation["attribution_pattern_count"] >= 1
    assert quotation["attributed_quote_count"] >= 1

    assert evidence["authorship"]["author_name"] == "Dr. Ada Expert"
    assert evidence["authorship"]["published_date"] == "2026-09-01"
    assert evidence["authorship"]["modified_date"] == "2026-09-20"


def test_prominent_terms_lexical_diversity_and_repetition_are_factual():
    page = extract_page(response("https://example.test/final", RICH_HTML))
    strategies = page.evidence["strategies"]

    assert "hybrid" in strategies["technical_terms"]["prominent_terms"]
    assert strategies["technical_terms"]["glossary_definition_count"] == 1
    assert strategies["unique_words"]["unique_token_count"] > 0
    assert 0 < strategies["unique_words"]["lexical_diversity_ratio"] <= 1
    assert strategies["keyword_stuffing"]["highest_frequency_terms"]
    assert strategies["keyword_stuffing"]["top_term_concentration"] > 0
    assert strategies["keyword_stuffing"]["note"].startswith("Frequency evidence")


def test_site_aggregation_excludes_duplicate_pages():
    pages = extract_pages([
        response("https://example.test/one", RICH_HTML),
        response("https://example.test/two", RICH_HTML),
    ])

    summary = aggregate_site_evidence(pages)

    assert pages[1].is_duplicate is True
    assert summary["analyzed_pages"] == 1
    assert summary["statistics"]["pages_with_numeric_claims"] == 1
    assert summary["citations"]["pages_with_reference_links"] == 1
    assert summary["authorship"]["pages_with_author"] == 1
    assert summary["structured_data"]["Article"] == 1


def test_strategy_recommendations_reference_factual_affected_pages():
    explanatory = " ".join(
        ["This guide explains how the process works and provides practical help."] * 35
    )
    pages = [
        extract_page(response(
            f"https://example.test/guide-{index}",
            f"<html><head><title>Guide {index}</title></head><body><h1>Guide</h1><p>{explanatory}</p></body></html>",
        ))
        for index in range(3)
    ]

    recommendations = build_recommendations(
        pages,
        requested_urls=3,
        accepted_html_responses=3,
    )
    by_category = {item.category: item for item in recommendations}

    for category in ("faq_opportunities", "statistics", "citation", "authoritative"):
        recommendation = by_category[category]
        assert recommendation.affected_page_count == 3
        assert recommendation.affected_urls == [page.url for page in pages]
        assert "3 of 3 analyzed" in recommendation.observed_evidence
    assert "score" not in by_category["faq_opportunities"].observed_evidence.lower()


def test_evidence_document_contains_no_arbitrary_score_fields():
    evidence = extract_page(response("https://example.test/final", RICH_HTML)).evidence

    def keys(value):
        if isinstance(value, dict):
            for key, child in value.items():
                yield key
                yield from keys(child)
        elif isinstance(value, list):
            for child in value:
                yield from keys(child)

    assert not any("score" in key.lower() for key in keys(evidence))
