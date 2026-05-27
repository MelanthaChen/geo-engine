import requests


def scrape_reddit_questions(
    target: str
):

    url = (
        f"https://www.reddit.com/search.json?q={target}"
    )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 GEOEngine/1.0"
        )
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=30
    )

    data = response.json()

    questions = []

    posts = (
        data
        .get("data", {})
        .get("children", [])
    )

    for post in posts:

        try:

            title = (
                post["data"]["title"]
            )

            if len(title.split()) < 4:
                continue

            questions.append(title)

            if len(questions) >= 15:
                break

        except:

            pass

    return questions