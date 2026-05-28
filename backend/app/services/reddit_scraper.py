import requests
from bs4 import BeautifulSoup


def scrape_reddit_questions(
    keyword: str
):

    url = (
        f"https://old.reddit.com/search/?q={keyword}"
    )

    headers = {
        "User-Agent":
        (
            "Mozilla/5.0 "
            "(Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/136.0.0.0 Safari/537.36"
        )
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=20
    )

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    results = []

    posts = soup.select(
        "a.search-title"
    )

    for post in posts[:15]:

        title = post.get_text(
            strip=True
        )

        if title:
            results.append(title)

    return results