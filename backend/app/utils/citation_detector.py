def detect_citation(
    ai_response: str,
    generated_content: str,
):

    ai_text = ai_response.lower()

    content_text = generated_content.lower()

    matched_keywords = []

    keywords = content_text.split()

    unique_keywords = set(keywords)

    for keyword in unique_keywords:

        if len(keyword) < 6:
            continue

        if keyword in ai_text:

            matched_keywords.append(keyword)

    score = len(matched_keywords)

    citation_found = score >= 10

    return {
        "citation_found": citation_found,
        "matched_keywords": matched_keywords[:25],
        "similarity_score": score
    }