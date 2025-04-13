import os
from datetime import datetime, timedelta
from logging import config
from typing import Any, Dict, List, Optional

from flask import current_app
from google import genai
from google.genai import types

from ..models.article import Article


def search_news_by_topic(topic: str) -> Dict[str, Any]:  # type: ignore
    """
    Search for news articles based on topic.

    Args:
        topic: The news topic (e.g., "politics", "technology", "sports", "world", "uk", "science", "health".)

    Returns:
        News articles related to the topic
    """
    try:
        print(f"Searching for news articles on topic: {topic}")
        # First check if we have articles with this topic in our database
        db_articles = Article.get_by_topic(topic, limit=5)

        if db_articles and len(db_articles) > 0:
            # We have articles from our database
            articles = []
            for article in db_articles:
                articles.append(
                    {
                        "title": article.title,
                        "published_at": article.published_at,
                        "summary": article.summary,
                        "url": article.url,
                    }
                )
            return {"articles": articles, "found": len(articles), "source": "database"}

    except Exception as e:
        current_app.logger.error(f"Topic-based news search error: {str(e)}")
        return {"articles": []}


def search_news_by_query(query: str) -> Dict[str, Any]:  # type: ignore
    """
    Search for news articles based on the query string.

    Args:
        query: Free-text search query

    Returns:
        News articles matching the query
    """
    try:
        print(f"Searching for news articles with query: {query}")
        # First check if we have articles matching this query in our database
        db_articles = Article.search_by_keywords(query, limit=5)

        if db_articles and len(db_articles) > 0:
            # We have articles from our database
            articles = []
            for article in db_articles:
                articles.append(
                    {
                        "title": article.title,
                        "published_at": article.published_at,
                        "summary": article.summary,
                        "url": article.url,
                        "topic": article.topic,
                    }
                )
            return {"articles": articles, "found": len(articles), "source": "database"}
    except Exception as e:
        current_app.logger.error(f"Query-based news search error: {str(e)}")
        return {"articles": []}


def search_news_by_date(days: int) -> dict[str, Any]:  # type: ignore
    """
    Search for recent news articles within the specified number of days.

    Args:
        days: Number of days to look back

    Returns:
        Recent news articles
    """
    if not days:
        days = 1

    try:
        print(f"Searching for recent news articles within the last {days} days")
        # Get recent articles from database
        cutoff_date = datetime.now() - timedelta(days=days)

        # Use SQLAlchemy query to get articles after the cutoff date
        db_articles = Article.get_recent_articles(limit=10)

        # Filter articles to only include those after cutoff date
        recent_db_articles = [
            article
            for article in db_articles  # type: ignore
            if article.published_at >= cutoff_date
        ]

        if recent_db_articles and len(recent_db_articles) > 0:
            # We have recent articles from our database
            articles = []
            for article in recent_db_articles:
                articles.append(
                    {
                        "title": article.title,
                        "published_at": article.published_at,
                        "summary": article.summary,
                        "url": article.url,
                        "topic": article.topic,
                    }
                )
            return {"articles": articles, "found": len(articles), "source": "database"}
    except Exception as e:
        current_app.logger.error(f"Date-based news search error: {str(e)}")
        return {"articles": []}


def generate_response(query: str, old_messages: List[Dict[str, Any]]):
    # Make sure AI knows that it being provided with chat history
    formatted_messages = []
    if old_messages:
        for msg in old_messages:
            formatted_messages.append(
                {
                    "role": msg.get("role", "user"),
                    "parts": [{"text": msg.get("content", "")}],
                }
            )
    formatted_messages.append({"role": "user", "parts": [{"text": query}]})

    try:
        api_key = os.environ.get("_GEMINI_API_KEY")

        client = genai.Client(api_key=api_key)
        config = types.GenerateContentConfig(
            tools=[search_news_by_topic, search_news_by_query, search_news_by_date],
            system_instruction=(
                "You are a helpful AI news assistant that specializes in summarizing and analyzing news articles. "
                "ALWAYS include a url link to the article"
                "When users ask about news, search for relevant articles and summarize the key information. "
                "For specific topics like politics, technology, health, business, sports, or science, provide focused news summaries on those topics. "
                "If asked for the latest news, provide recent headlines across various categories. "
                "Always mention the topic of the article when referencing it"
                "You have access to tools that can search for news articles by topic, query, and date. You are only allowed to get articles from those tools and you can not rely on your own knowledge or any other resources. "
                "Try to always retrieve some information by using tools, even if the user is not being very clear. Also assume that the user is trying to search by a topic first, and then by a query. "
            ),
        )

        response = client.models.generate_content_stream(
            model="gemini-2.0-flash",
            contents=formatted_messages,
            config=config,
        )

        return response
    except Exception as e:
        current_app.logger.error(f"Gemini API error: {str(e)}")
        raise


def extract_news_context(news_results: dict[str, Any]) -> str:
    """
    Extract context from news search results.

    Args:
        news_results: Results from the news search

    Returns:
        Extracted context as a string
    """
    if not news_results or "articles" not in news_results or not news_results["articles"]:
        return ""

    context = ""
    for article in news_results["articles"]:
        # Add title and source
        if "title" in article:
            context += f"Headline: {article['title']}\n"
        if "source" in article:
            context += f"Source: {article['source']}\n"
        if "topic" in article:
            context += f"Topic: {article['topic']}\n"

        # Add publication date
        if "published_at" in article:
            # Format datetime for readability
            pub_time = article["published_at"]
            if isinstance(pub_time, datetime):
                formatted_time = pub_time.strftime("%Y-%m-%d %H:%M")
                context += f"Published: {formatted_time}\n"

        # Add summary and URL
        if "summary" in article:
            context += f"Summary: {article['summary']}\n"
        if "url" in article:
            context += f"URL: {article['url']}\n"

        context += "\n----\n"

    return context.strip()


def generate_chat_title(query: str) -> str:
    """
    Generate a title for a news chat based on the user's query.

    Args:
        query: The user's query

    Returns:
        A title for the chat
    """
    try:
        # Get API key from environment or settings
        api_key = os.environ.get("_GEMINI_API_KEY") or current_app.config.get("_GEMINI_API_KEY")
        client = genai.Client(api_key=api_key)

        # Search for news related to the query
        news_results = search_news_by_query(query)
        context = extract_news_context(news_results)

        title_prompt = f"Generate a short, descriptive title (3-5 words) for a chat about the following news query: {query}\n\nDon't include anything but the name as a clear string without any quotes or other characters."
        if context:
            title_prompt = f"Based on these news articles:\n\n{context}\n\nGenerate a short, descriptive title (3-5 words) for a chat about: {query}\n\nDon't include anything but the name as a clear string without any quotes or other characters."

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[{"role": "user", "parts": [{"text": title_prompt}]}],
            config={"temperature": 0.2, "max_output_tokens": 10},
        )

        return response.text.strip("\"'")  # type: ignore
    except Exception as e:
        current_app.logger.error(f"Error generating chat title: {str(e)}")
        # Return a simple fallback title
        return "News Discussion"
