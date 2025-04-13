import json
import os
import traceback
from datetime import datetime

import requests
from flask import (
    Blueprint,
    Response,
    current_app,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    stream_with_context,
    url_for,
)

from ..extensions import db
from ..models.article import Article
from ..utils.gemini import (
    generate_chat_title,
    generate_response,
)
from ..utils.scheduler import (
    fetch_and_save_articles,
    get_task_status,
    scheduler,
    start_manual_feed_fetch,
)

api = Blueprint("api", __name__)


@api.route("/api")
def index():
    """
    Index route for the API.
    """
    return jsonify({"message": "Welcome to the News Parser API!"})


@api.route("/api/health")
def health():
    """
    Health check route for the API.
    """
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})


@api.route("/api/chat", methods=["POST"])
def chat():
    """
    Chat endpoint for generating AI responses.
    Accepts a JSON payload with a message and conversation history.
    Returns a stream of AI-generated responses.
    """
    try:
        data = request.get_json()

        if not data or "message" not in data:
            return jsonify({"error": "No message provided"}), 400

        user_message = data["message"]
        conversation_history = data.get("history", [])

        ai_response_stream = generate_response(user_message, conversation_history)

        def generate():
            try:
                for chunk in ai_response_stream:
                    if hasattr(chunk, "text") and chunk.text:
                        yield f"data: {json.dumps({'chunk': chunk.text})}\n\n"

                # Signal end of stream with a special message
                yield f"data: {json.dumps({'done': True})}\n\n"
            except Exception as e:
                current_app.logger.error(f"Error in stream generation: {str(e)}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return Response(
            stream_with_context(generate()), content_type="text/event-stream"
        )

    except Exception as e:
        current_app.logger.error(f"Error in chat endpoint: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify(
            {"error": "An error occurred processing your request", "details": str(e)}
        ), 500


@api.route("/api/chat/title", methods=["POST"])
def create_chat_title():
    """
    Endpoint to generate a chat title based on the provided query.
    Accepts a JSON payload with a query string.
    Returns a JSON response with the generated title.
    """
    try:
        data = request.get_json()
        if not data or "query" not in data:
            return jsonify({"error": "No query provided"}), 400

        query = data["query"]
        title = generate_chat_title(query)

        return jsonify({"title": title, "timestamp": datetime.now().isoformat()})
    except Exception as e:
        current_app.logger.error(f"Error generating chat title: {str(e)}")
        return jsonify({"error": str(e)}), 500


@api.route("/api/feeds/fetch", methods=["POST"])
def manual_fetch_feeds():
    """
    Start a manual RSS feed fetch in the background.
    Returns a task ID that can be used to check task status.
    """
    try:
        # In a production app, you should add authentication here
        task_id = start_manual_feed_fetch()

        return jsonify(
            {
                "status": "started",
                "task_id": task_id,
                "message": "Feed fetch started in the background",
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        current_app.logger.error(f"Error starting manual feed fetch: {str(e)}")
        return jsonify({"error": str(e)}), 500


@api.route("/api/feeds/tasks/<task_id>", methods=["GET"])
def check_task_status(task_id):
    """
    Check the status of a feed fetch task by ID.
    """
    try:
        # In a production app, you should add authentication here
        task_status = get_task_status(task_id)

        if task_status["status"] == "not_found":
            return jsonify(
                {
                    "error": "Task not found",
                    "task_id": task_id,
                }
            ), 404

        # Format timestamp for better readability
        if "started_at" in task_status:
            task_status["started_at_formatted"] = datetime.fromtimestamp(
                task_status["started_at"]
            ).isoformat()

        if task_status.get("completed_at"):
            task_status["completed_at_formatted"] = datetime.fromtimestamp(
                task_status["completed_at"]
            ).isoformat()
            # Calculate duration
            duration = task_status["completed_at"] - task_status["started_at"]
            task_status["duration_seconds"] = round(duration, 1)

        return jsonify(
            {
                "task": task_status,
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        current_app.logger.error(f"Error checking task status: {str(e)}")
        return jsonify({"error": str(e)}), 500


@api.route("/api/feeds/status", methods=["GET"])
def feed_status():
    """
    Get the status of the RSS feed scheduler.
    Requires admin authentication in production.
    """
    try:
        # In a production app, you should add authentication here

        jobs = []
        for job in scheduler.get_jobs():
            jobs.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat()
                    if job.next_run_time
                    else None,
                    "trigger": str(job.trigger),
                }
            )

        return jsonify(
            {
                "status": "running" if scheduler.running else "stopped",
                "jobs": jobs,
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        current_app.logger.error(f"Error fetching scheduler status: {str(e)}")
        return jsonify({"error": str(e)}), 500
