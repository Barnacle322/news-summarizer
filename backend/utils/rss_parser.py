import datetime
import logging
import re
from typing import Dict, List, Optional

import feedparser
import requests
from bs4 import BeautifulSoup

from ..models.article import Article

logger = logging.getLogger(__name__)


def extract_article_content(url: str) -> Optional[str]:
    """
    Extract the full content of an article from its URL using BeautifulSoup.

    Args:
        url: URL of the article

    Returns:
        The article content as plain text, or None if extraction failed
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # BBC specific content extraction
        # Look for article content in different possible BBC article formats
        content_blocks = []

        # Try to find the main content container
        article_body = soup.select_one("article") or soup.select_one("main")

        if article_body:
            # Find paragraphs within the article body
            paragraphs = article_body.select("p")
            for p in paragraphs:
                # Skip paragraphs that are likely to be metadata, captions, or navigation
                if p.parent and p.parent.name in [
                    "figcaption",
                    "footer",
                    "aside",
                    "nav",
                ]:
                    continue

                # Skip paragraphs with classes that suggest they are not main content
                skip_classes = ["media-caption", "footer", "timestamp", "byline"]
                if any(cls in p.get("class", []) for cls in skip_classes):  # type: ignore
                    continue

                text = p.get_text().strip()
                if len(text) > 20:  # Skip very short paragraphs which might be metadata
                    content_blocks.append(text)

        if not content_blocks:
            # If we couldn't find content in the expected structure, try a more generic approach
            content_blocks = [
                p.get_text().strip()
                for p in soup.select("p")
                if len(p.get_text().strip()) > 50
            ]

        # Join paragraphs with newlines
        return "\n\n".join(content_blocks) if content_blocks else None

    except Exception as e:
        logger.error(f"Error extracting content from {url}: {str(e)}")
        return None


def determine_article_topic(title: str, description: str, feed_url: str) -> str:
    """
    Determine the topic of an article based on its title, description, and feed URL.

    Args:
        title: Article title
        description: Article description/summary
        feed_url: URL of the RSS feed

    Returns:
        The determined topic (technology, politics, business, etc.)
    """
    # First check if the topic is in the RSS feed URL
    topic_keywords = {
        "technology": ["tech", "digital", "software", "hardware", "ai", "cyber"],
        "politics": [
            "politics",
            "government",
            "election",
            "parliament",
            "congress",
            "policy",
        ],
        "business": ["business", "economy", "finance", "market", "stock", "trade"],
        "health": ["health", "medical", "medicine", "disease", "covid", "pandemic"],
        "sports": ["sport", "football", "soccer", "basketball", "tennis", "olympic"],
        "science": [
            "science",
            "research",
            "discovery",
            "space",
            "climate",
            "environment",
        ],
        "entertainment": ["entertainment", "movie", "film", "music", "celebrity", "tv"],
        "world": ["world", "global", "international", "foreign"],
        "uk": ["uk", "britain", "london", "scotland", "wales", "england"],
    }

    # Extract topic from feed URL if possible
    for topic, keywords in topic_keywords.items():
        if any(keyword in feed_url.lower() for keyword in keywords):
            return topic

    # If not found in URL, check title and description
    text = (title + " " + description).lower()

    for topic, keywords in topic_keywords.items():
        if any(keyword in text for keyword in keywords):
            return topic

    # Default to "general" if no specific topic is found
    return "general"


def parse_bbc_feed(feed_url: str) -> List[Dict]:
    """
    Parse BBC RSS feed and extract article information.

    Args:
        feed_url: URL of the RSS feed

    Returns:
        List of dictionaries containing article information
    """
    try:
        feed = feedparser.parse(feed_url)
        articles = []

        for entry in feed.entries:
            # Extract publication date
            published = entry.get("published", None)
            if published:
                published_dt = datetime.datetime.strptime(
                    published,  # type: ignore
                    "%a, %d %b %Y %H:%M:%S %Z",
                )
            else:
                published_dt = datetime.datetime.now()

            # Clean title and description
            title = (
                entry.get("title", "")
                .replace("]]>", "")  # type: ignore
                .replace("<![CDATA[", "")
                .strip()
            )
            description = (
                entry.get("description", "")
                .replace("]]>", "")  # type: ignore
                .replace("<![CDATA[", "")
                .strip()
            )

            # Determine article topic
            topic = determine_article_topic(title, description, feed_url)

            # Extract article data
            article_data = {
                "title": title,
                "link": entry.get("link", ""),
                "description": description,
                "published_at": published_dt,
                "topic": topic,
            }

            # Extract image URL if available
            if "media_thumbnail" in entry and entry.media_thumbnail:
                article_data["image_url"] = entry.media_thumbnail[0]["url"]

            articles.append(article_data)

        return articles

    except Exception as e:
        logger.error(f"Error parsing feed {feed_url}: {str(e)}")
        return []


def fetch_and_process_feeds() -> List[Article]:
    """
    Fetch and process all RSS feeds, returning created Article objects.

    Returns:
        List of Article objects created
    """
    feed_urls = [
        "https://feeds.bbci.co.uk/news/politics/rss.xml",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://feeds.bbci.co.uk/news/uk/rss.xml",
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
        "https://feeds.bbci.co.uk/news/health/rss.xml",
        "https://feeds.bbci.co.uk/sport/rss.xml",
    ]

    created_articles = []

    for feed_url in feed_urls:
        print(f"Fetching feed: {feed_url}")
        articles = parse_bbc_feed(feed_url)
        logger.info(f"Parsed {len(articles)} articles from {feed_url}")

        for article_data in articles:
            print(f"Processing article: {article_data['title']}")
            # Fetch full content for the article
            content = extract_article_content(article_data["link"])
            if content:
                article_data["content"] = content

            # Create a summary from description if available
            if article_data.get("description"):
                article_data["summary"] = article_data["description"]

            # Create Article object
            article = Article(
                title=article_data["title"],
                url=article_data["link"],
                summary=article_data.get("summary"),  # type: ignore
                content=article_data.get("content"),
                topic=article_data.get("topic"),
                published_at=article_data["published_at"],
            )

            created_articles.append(article)

    return created_articles
