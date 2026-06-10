from sqlalchemy.orm import Session

from app.models.campaign import Campaign

from app.services.content_service import (
    generate_content
)

from app.services.publishing_service import (
    publish_content
)

from app.services.citation_test_service import (
    run_citation_test
)


def run_campaign(
    campaign_id: int,
    db: Session,
):

    campaign = (
        db.query(Campaign)
        .filter(Campaign.id == campaign_id)
        .first()
    )

    if not campaign:

        return {
            "error": "Campaign not found"
        }

    query_list = [
        query.strip()
        for query in (
            campaign.target_queries or ""
        ).split(",")
        if query.strip()
    ]

    generated_contents = []
    publishable_contents = []

    for query in query_list:

        content = generate_content(
            db=db,
            query=query,
            persona="student",
            content_type="research_summary",
            target_url=None,
            mode="ai",
        )

        generated_contents.append(content)

        reddit_content = generate_content(
            db=db,
            query=query,
            persona="student",
            content_type="reddit_discussion",
            target_url=None,
            mode="reddit",
        )

        publishable_contents.append(reddit_content)

    published_results = []

    for content in publishable_contents:

        publish_result = publish_content(
            content_id=content.id,
            db=db,
        )

        published_results.append(publish_result)

    citation_results = []

    for content in generated_contents:

        citation_result = run_citation_test(
            content_id=content.id,
            platform="openai",
            db=db,
        )

        citation_results.append(citation_result)

    return {
        "campaign_id": campaign.id,
        "campaign_name": campaign.name,
        "queries_processed": len(query_list),
        "contents_generated": len(generated_contents),
        "published_count": len(published_results),
        "citation_tests": citation_results,
    }
