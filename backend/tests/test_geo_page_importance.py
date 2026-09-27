import inspect

from app.services.website_audit import importance
from app.services.website_audit.crawler import select_candidate_urls
from app.services.website_audit.extractor import PageExtract
from app.services.website_audit.importance import rank_page, select_geo_important_pages


def page(
    url: str,
    *,
    words: int = 300,
    body: str = "explanatory content " * 150,
    links: list[str] | None = None,
    references: int = 0,
    numeric: int = 0,
    methodology: int = 0,
    duplicate: bool = False,
) -> PageExtract:
    evidence = {
        "identity": {"requested_url": url},
        "content": {"paragraph_count": 8, "list_count": 1},
        "links": {"internal_urls": links or []},
        "structured_data": {"schema_types": []},
        "authorship": {"author_name": None, "published_date": None, "modified_date": None},
        "strategies": {
            "faq": {"detected_qa_pair_count": 0, "explanatory_text_present": True},
            "statistics": {"numeric_claim_count": numeric},
            "citation": {"reference_like_link_count": references},
            "authoritative": {"methodology_language_count": methodology},
            "technical_terms": {"glossary_definition_count": 0},
        },
    }
    return PageExtract(
        url=url,
        page_title="Page",
        meta_description="Description",
        h1="Heading",
        status_code=200,
        word_count=words,
        internal_link_count=len(links or []),
        external_link_count=references,
        body_text=body,
        content_sha256=url.encode().hex()[:64].ljust(64, "0"),
        is_duplicate=duplicate,
        h2_count=3,
        h3_count=2,
        canonical_url=url,
        evidence=evidence,
    )


def select(pages, *, audited="https://example.com/", homepage_links=None, limit=3):
    return select_geo_important_pages(
        pages,
        audited_url=audited,
        homepage_url="https://example.com/",
        homepage_links=set(homepage_links or []),
        sitemap_urls={item.url for item in pages},
        limit=limit,
    )


def test_audited_url_is_always_included_when_analyzable():
    audited = page("https://example.com/deep/audited", words=45)
    rich = page("https://example.com/knowledge/rich", words=1500)
    assert audited in select([audited, rich], audited=audited.url, limit=1)
    assert "Explicitly audited URL" in audited.selection_reasons


def test_homepage_and_navigation_prominence_raise_importance():
    home = page("https://example.com/")
    navigation = page("https://example.com/primary")
    ordinary = page("https://example.com/other")
    nav_rank = rank_page(navigation, audited_url=ordinary.url, homepage_url=home.url, homepage_links={navigation.url}, sitemap_urls={navigation.url}, inbound_count=0)
    ordinary_rank = rank_page(ordinary, audited_url="https://example.com/audited", homepage_url=home.url, homepage_links=set(), sitemap_urls={ordinary.url}, inbound_count=0)
    assert nav_rank.score > ordinary_rank.score
    assert "Linked directly from the homepage" in nav_rank.reasons


def test_high_internal_inbound_link_page_is_prioritized():
    target = page("https://example.com/core")
    sources = [page(f"https://example.com/family/source-{index}", links=[target.url]) for index in range(4)]
    selected = select([page("https://example.com/"), target, *sources], limit=2)
    assert target in selected
    assert any("internal-link prominence" in reason for reason in target.selection_reasons)


def test_rich_content_is_preferred_over_thin_utility_page():
    rich = page("https://example.com/knowledge", words=1200, numeric=5, methodology=4)
    utility = page("https://example.com/login", words=20, body="sign in")
    rich_rank = rank_page(rich, audited_url="https://example.com/else", homepage_url="https://example.com/", homepage_links=set(), sitemap_urls={rich.url}, inbound_count=0)
    utility_rank = rank_page(utility, audited_url="https://example.com/else", homepage_url="https://example.com/", homepage_links=set(), sitemap_urls={utility.url}, inbound_count=0)
    assert rich_rank.score > utility_rank.score
    assert utility_rank.signals["score_components"]["utility_page_penalty"] < 0


def test_duplicate_page_is_excluded_and_filter_path_is_deprioritized():
    duplicate = page("https://example.com/copy", duplicate=True)
    normal = page("https://example.com/content")
    filtered = page("https://example.com/filter/results")
    selected = select([page("https://example.com/"), duplicate, normal, filtered], limit=4)
    assert duplicate not in selected
    normal_rank = rank_page(normal, audited_url="https://example.com/else", homepage_url="https://example.com/", homepage_links=set(), sitemap_urls={normal.url}, inbound_count=0)
    filter_rank = rank_page(filtered, audited_url="https://example.com/else", homepage_url="https://example.com/", homepage_links=set(), sitemap_urls={filtered.url}, inbound_count=0)
    assert normal_rank.score > filter_rank.score


def test_citation_and_research_evidence_raise_importance():
    cited = page("https://example.com/evidence", references=3, methodology=4)
    plain = page("https://example.com/plain")
    cited_rank = rank_page(cited, audited_url="https://example.com/else", homepage_url="https://example.com/", homepage_links=set(), sitemap_urls={cited.url}, inbound_count=0)
    plain_rank = rank_page(plain, audited_url="https://example.com/else", homepage_url="https://example.com/", homepage_links=set(), sitemap_urls={plain.url}, inbound_count=0)
    assert cited_rank.score > plain_rank.score
    assert any("Reference-like citations" in reason for reason in cited_rank.reasons)


def test_route_family_round_robin_prevents_one_family_dominating():
    pages = [page("https://example.com/")]
    pages.extend(page(f"https://example.com/news/item-{index}", words=900) for index in range(12))
    pages.extend([
        page("https://example.com/company/overview", words=500),
        page("https://example.com/evidence/study", words=500),
        page("https://example.com/tools/reference", words=500),
    ])
    selected = select(pages, limit=4)
    assert len({item.content_family for item in selected}) == 4
    assert sum(item.content_family == "/news" for item in selected) == 1


def test_selection_is_deterministic_for_the_same_inventory():
    urls = ["https://example.com/", *[f"https://example.com/family-{index}/page" for index in range(8)]]
    first = [item.url for item in select([page(url) for url in urls], limit=5)]
    second = [item.url for item in select([page(url) for url in reversed(urls)], limit=5)]
    assert first == second


def test_large_inventory_is_reduced_before_page_extraction():
    inventory = {"https://example.com/", *{f"https://example.com/family-{index % 40}/page-{index}" for index in range(15_000)}}
    candidates = select_candidate_urls(
        urls=inventory,
        audited_url="https://example.com/",
        homepage_url="https://example.com/",
        homepage_links=set(),
        limit=150,
    )
    assert len(candidates) == 150
    assert len(candidates) < len(inventory)


def test_importance_ranking_has_no_llm_dependency_or_call():
    source = inspect.getsource(importance).lower()
    assert "openai" not in source
    assert "llm" not in source
