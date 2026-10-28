
import feedparser
import json
import hashlib
import os
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit

FEEDS = {
    "AI & Innovation": (
        "https://news.google.com/rss/search?"
        "q=artificial+intelligence+OR+generative+AI"
        "&hl=en-US&gl=US&ceid=US:en"
    ),
    "Tech News": (
        "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY"
        "?hl=en-US&gl=US&ceid=US:en"
    ),
    "Cybersecurity": (
        "https://news.google.com/rss/search?"
        "q=cybersecurity+OR+data+breach"
        "&hl=en-US&gl=US&ceid=US:en"
    ),
    "Fact Check": (
        "https://news.google.com/rss/search?"
        "q=fact+check+OR+misinformation"
        "&hl=en-US&gl=US&ceid=US:en"
    ),
    "Nepal News": (
        "https://news.google.com/rss/search?"
        "q=news+Nepal&hl=en&gl=NP&ceid=NP:en"
    ),
    "Nepal Technology": (
        "https://news.google.com/rss/search?"
        "q=technology+Nepal&hl=en&gl=NP&ceid=NP:en"
    ),
    "नेपाली समाचार": (
        "https://news.google.com/rss/search?"
        "q=नेपाल+समाचार&hl=ne&gl=NP&ceid=NP:ne"
    ),
    "नेपाली प्रविधि": (
        "https://news.google.com/rss/search?"
        "q=प्रविधि+OR+कृत्रिम+बुद्धिमत्ता"
        "&hl=ne&gl=NP&ceid=NP:ne"
    ),
}

OUTPUT_FILE = "news.json"


def clean_text(text):
    import re
    return re.sub(r"\s+", " ", text or "").strip()


def normalize_url(url):
    parts = urlsplit(url)
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, "", "")
    )


def make_id(title, url):
    value = normalize_url(url) or clean_text(title).lower()
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]


def load_existing_news():
    if not os.path.exists(OUTPUT_FILE):
        return []

    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        print("WARNING: Could not read existing news.json")
        return []


def get_published_date(entry):
    published = entry.get("published_parsed")

    if published:
        from calendar import timegm
        return datetime.fromtimestamp(
            timegm(published), timezone.utc
        ).isoformat()

    return None


def main():
    # Keep every article already saved in JSON
    existing = load_existing_news()

    # Index existing news so new runs do not create duplicates
    news_by_id = {
        item.get("id") or make_id(
            item.get("title", ""), item.get("url", "")
        ): item
        for item in existing
    }

    fetched_count = 0

    for category, feed_url in FEEDS.items():
        print(f"Fetching: {category}")

        try:
            feed = feedparser.parse(feed_url)

            if feed.bozo and not feed.entries:
                print(f"Feed failed: {category}")
                continue

            for entry in feed.entries:
                title = clean_text(entry.get("title", ""))
                url = entry.get("link", "")

                if not title or not url:
                    continue

                article_id = make_id(title, url)

                # Keep existing record; add only genuinely new articles
                if article_id in news_by_id:
                    continue

                source_info = entry.get("source", {})
                source = (
                    source_info.get("title", "")
                    if hasattr(source_info, "get") else ""
                )

                if not source:
                    source = urlsplit(url).netloc

                news_by_id[article_id] = {
                    "id": article_id,
                    "title": title,
                    "url": url,
                    "source": clean_text(source),
                    "category": category,
                    "published_at": get_published_date(entry),
                    "summary": clean_text(entry.get("summary", "")),
                    "status": "pending_review"
                }

                fetched_count += 1

        except Exception as error:
            print(f"Error in {category}: {error}")

    # Save all previous articles plus newly discovered articles
    all_news = list(news_by_id.values())

    # Newest articles first; records without dates go last
    all_news.sort(
        key=lambda item: item.get("published_at") or "",
        reverse=True
    )

    temp_file = OUTPUT_FILE + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(all_news, file, ensure_ascii=False, indent=2)

    os.replace(temp_file, OUTPUT_FILE)

    print(f"New articles added: {fetched_count}")
    print(f"Total saved articles: {len(all_news)}")


if __name__ == "__main__":
    main()
