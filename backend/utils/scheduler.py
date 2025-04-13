import logging
import threading
import time
from typing import Dict, List

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from flask import Flask, current_app

from ..extensions import db
from ..models.article import Article
from ..utils.rss_parser import (
    extract_article_content,
    fetch_and_process_feeds,
    parse_bbc_feed,
)

logger = logging.getLogger(__name__)

# Create a global scheduler instance
scheduler = BackgroundScheduler()

# Store task status information
fetch_tasks = {}
# Store a reference to the Flask app for use in background threads
_app = None


def fetch_and_save_articles() -> Dict:
    """
    Fetch articles from RSS feeds and save them to the database.
    Returns summary of the operation.
    """
    result = {"new": 0, "duplicates": 0, "errors": 0}
    try:
        # Fetch articles from feeds
        articles = fetch_and_process_feeds()

        for article in articles:
            print(f"Processing article: {article.title}")
            try:
                # Check if article already exists by URL
                existing = Article.get_by_url(article.url)
                if existing:
                    result["duplicates"] += 1
                    continue

                # Check if article exists by title
                existing_by_title = Article.get_by_title(article.title)
                if existing_by_title:
                    result["duplicates"] += 1
                    continue

                # Save new article to database
                db.session.add(article)
                db.session.commit()
                result["new"] += 1

            except Exception as e:
                db.session.rollback()
                logger.error(f"Error saving article {article.title}: {str(e)}")
                result["errors"] += 1

        logger.info(
            f"RSS feed processing completed. New: {result['new']}, "
            f"Duplicates: {result['duplicates']}, Errors: {result['errors']}"
        )
        print(result)
        return result

    except Exception as e:
        logger.error(f"Error in RSS feed fetching task: {str(e)}")
        result["errors"] += 1
        print(result)
        return result


def fetch_and_save_articles_async(task_id: str):
    """
    Asynchronously fetch and save articles with status tracking.

    Args:
        task_id: Unique identifier for this task
    """
    try:
        # Update task status to running
        fetch_tasks[task_id]["status"] = "running"
        fetch_tasks[task_id]["progress"] = 0
        fetch_tasks[task_id]["result"] = {"new": 0, "duplicates": 0, "errors": 0}

        # Get the Flask app instance
        app = _app
        if not app:
            logger.error("No Flask app available in background thread")
            fetch_tasks[task_id]["status"] = "failed"
            fetch_tasks[task_id]["error"] = "No Flask application context available"
            fetch_tasks[task_id]["completed_at"] = time.time()
            return

        # Execute the feed process within the app context
        with app.app_context():
            # Get the feed URLs
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

            # Calculate progress step per feed - allocate 10% of progress bar for feed fetching
            total_feeds = len(feed_urls)
            feed_step = 10 / total_feeds  # Use 10% of progress bar for feed fetching
            article_count = 0
            total_articles = 0

            # Process each feed
            all_articles = []
            for i, feed_url in enumerate(feed_urls):
                try:
                    # Update progress - fetching feeds phase
                    current_progress = int(i * feed_step)
                    fetch_tasks[task_id]["progress"] = current_progress
                    fetch_tasks[task_id]["status_message"] = (
                        f"Fetching feed {i + 1}/{total_feeds}"
                    )

                    # Parse the feed
                    print(f"Fetching feed: {feed_url}")
                    articles = parse_bbc_feed(feed_url)
                    logger.info(f"Parsed {len(articles)} articles from {feed_url}")

                    total_articles += len(articles)
                    for article_data in articles:
                        # Create placeholder Article objects
                        article = Article(
                            title=article_data["title"],
                            url=article_data["link"],
                            summary=article_data.get("description"),  # type: ignore
                            content=None,
                            topic=article_data.get("topic"),
                            published_at=article_data["published_at"],
                        )
                        all_articles.append((article, article_data))

                except Exception as e:
                    logger.error(f"Error processing feed {feed_url}: {str(e)}")
                    fetch_tasks[task_id]["result"]["errors"] += 1

            # Calculate progress step per article for the remaining 90%
            article_step = 90 / max(1, total_articles)

            # Process each article
            for idx, (article, article_data) in enumerate(all_articles):
                try:
                    # Update progress - processing articles phase
                    current_progress = int(10 + (idx * article_step))
                    fetch_tasks[task_id]["progress"] = min(
                        99, current_progress
                    )  # Cap at 99% until completely done
                    fetch_tasks[task_id]["status_message"] = (
                        f"Processing article {idx + 1}/{total_articles}"
                    )

                    # Check if article already exists by URL
                    existing = Article.get_by_url(article.url)
                    if existing:
                        fetch_tasks[task_id]["result"]["duplicates"] += 1
                        continue

                    # Check if article exists by title
                    existing_by_title = Article.get_by_title(article.title)
                    if existing_by_title:
                        fetch_tasks[task_id]["result"]["duplicates"] += 1
                        continue

                    # Fetch full content for new articles
                    content = extract_article_content(article_data["link"])
                    if content:
                        article.content = content

                    # Save to database
                    db.session.add(article)
                    db.session.commit()
                    fetch_tasks[task_id]["result"]["new"] += 1
                    article_count += 1

                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Error saving article {article.title}: {str(e)}")
                    fetch_tasks[task_id]["result"]["errors"] += 1

            # Update task status to completed with results
            fetch_tasks[task_id]["status"] = "completed"
            fetch_tasks[task_id]["progress"] = 100
            fetch_tasks[task_id]["status_message"] = "Feed fetch completed"
            fetch_tasks[task_id]["completed_at"] = time.time()
            fetch_tasks[task_id]["stats"] = {
                "processed_feeds": total_feeds,
                "processed_articles": article_count,
                "total_found": total_articles,
            }

            logger.info(
                f"Feed fetch task {task_id} completed. New: {fetch_tasks[task_id]['result']['new']}, "
                f"Duplicates: {fetch_tasks[task_id]['result']['duplicates']}, "
                f"Errors: {fetch_tasks[task_id]['result']['errors']}"
            )

    except Exception as e:
        logger.error(f"Error in async feed fetch task {task_id}: {str(e)}")
        # Update task status to failed
        fetch_tasks[task_id]["status"] = "failed"
        fetch_tasks[task_id]["error"] = str(e)
        fetch_tasks[task_id]["completed_at"] = time.time()


def start_manual_feed_fetch() -> str:
    """
    Start a manual feed fetch in a background thread and return the task ID.

    Returns:
        Task ID that can be used to check status
    """
    task_id = f"feed_fetch_{int(time.time())}"

    # Create task entry
    fetch_tasks[task_id] = {
        "id": task_id,
        "status": "starting",
        "status_message": "Starting feed fetch",
        "progress": 0,
        "started_at": time.time(),
        "completed_at": None,
        "result": {},
        "error": None,
    }

    # Start background thread
    thread = threading.Thread(target=fetch_and_save_articles_async, args=(task_id,))
    thread.daemon = True
    thread.start()

    return task_id


def get_task_status(task_id: str) -> Dict:
    """
    Get the status of a specific task.

    Args:
        task_id: ID of the task to check

    Returns:
        Task status information
    """
    if task_id in fetch_tasks:
        return fetch_tasks[task_id]
    return {"id": task_id, "status": "not_found"}


def cleanup_old_tasks():
    """
    Remove completed tasks that are older than one hour to prevent memory leaks.
    """
    current_time = time.time()
    to_remove = []

    for task_id, task_info in fetch_tasks.items():
        # If the task is completed or failed and is older than one hour
        if (
            task_info.get("completed_at")
            and current_time - task_info["completed_at"] > 3600
        ):
            to_remove.append(task_id)

    # Remove old tasks
    for task_id in to_remove:
        del fetch_tasks[task_id]


def setup_scheduler(app: Flask):
    """
    Initialize and start the scheduler with the Flask application context.

    Args:
        app: The Flask application
    """
    global _app
    # Store the Flask app for use in background threads
    _app = app

    if not scheduler.running:
        # Add hourly job to fetch and process RSS feeds
        scheduler.add_job(
            lambda: app.app_context().__enter__() and fetch_and_save_articles(),
            trigger=IntervalTrigger(hours=1),
            id="fetch_rss_feeds",
            name="Fetch RSS feeds hourly",
            replace_existing=True,
        )

        # Add job to clean up old tasks
        scheduler.add_job(
            cleanup_old_tasks,
            trigger=IntervalTrigger(minutes=10),
            id="cleanup_old_tasks",
            name="Clean up old tasks every 10 minutes",
            replace_existing=True,
        )

        # Start the scheduler
        scheduler.start()
        logger.info("Scheduler started with hourly RSS feed job")
