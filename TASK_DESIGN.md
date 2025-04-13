# News Summarizer Task Design Document

This document outlines the architecture, AI task logic, API interactions, and technical implementation details of the News Summarizer application.

## System Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────────┐
│  RSS Feeds  │───>│  Scheduler  │───>│ Database Storage│
└─────────────┘    └─────────────┘    └─────────────────┘
                                                │
                                                ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────────┐
│  Frontend   │◄───┤  Backend    │◄───┤ Google Gemini AI│
│  (Vue.js)   │    │  (Flask)    │    │     API         │
└─────────────┘    └─────────────┘    └─────────────────┘
```

## News Collection Flow

1. **RSS Feed Processing**
   - The scheduler runs at regular intervals (hourly)
   - Fetches articles from configured RSS feeds (BBC News)
   - Parses feed content and extracts article metadata
   - Determines article topics using keyword analysis
   - Extracts full article content using web scraping

2. **Storage Flow**
   - Checks for duplicate articles by URL and title
   - Stores new articles in SQLite database
   - Maintains article metadata (title, URL, summary, content, topic, timestamps)

## AI Chat Flow

1. **User Query Processing**
   - User submits a query through the chat interface
   - Backend receives the query via API endpoint
   - Chat history is maintained for context

2. **Article Search**
   - System searches for relevant articles using:
     - Topic-based search (matches article topics)
     - Keyword-based search (matches title, summary, content)
     - Recency-based search (filters by date)

3. **AI Response Generation**
   - Google Gemini API receives query and chat history
   - System instructions guide AI to prioritize news context
   - Function calling enables API to run database searches
   - AI receives article data and formulates a response
   - Response is streamed back to frontend

## API Interactions

### Frontend ↔ Backend

| Endpoint | Method | Purpose | Parameters | Response |
|----------|--------|---------|------------|----------|
| `/api/chat` | POST | Generate AI chat response | `message`, `history` (optional) | Streamed AI response |
| `/api/chat/title` | POST | Generate title for chat | `query` | Generated title |
| `/api/feeds/fetch` | POST | Manual feed fetch trigger | None | Task ID |
| `/api/feeds/tasks/<task_id>` | GET | Check feed task status | Task ID | Task status |
| `/api/feeds/status` | GET | Get scheduler status | None | Scheduler info |

### Backend ↔ Gemini API

- **Authentication**: Uses API key stored in `.env`
- **Function Calling**: Enables Gemini to access:
  - `search_news_by_topic()`
  - `search_news_by_query()`
  - `search_news_by_date()`
- **System Instructions**: Direct Gemini to behave as a news assistant
- **Streaming**: Supports chunked response streaming

## Database Schema

```
┌───────────────────────────┐
│ Article                   │
├───────────────────────────┤
│ id: Integer (PK)          │
│ title: String             │
│ url: String               │
│ summary: Text (nullable)  │
│ content: Text (nullable)  │
│ topic: String (nullable)  │
│ published_at: DateTime    │
│ created_at: DateTime      │
└───────────────────────────┘
```

## Task Scheduling

- **Technologies**: APScheduler with BackgroundScheduler
- **Scheduled Tasks**:
  - RSS feed fetching (hourly)
  - Old task cleanup (every 10 minutes)
- **Manual Tasks**:
  - On-demand feed fetching via admin panel
  - Progress tracking for background tasks

## Frontend Implementation

- **Technologies**: Vue 3, Vite, TailwindCSS
- **State Management**: Pinia store for chat state
- **Key Components**:
  - Chat interface with message history
  - Markdown renderer for AI responses
  - Admin dashboard for feed management

## Backend Implementation

- **Technologies**: Flask, SQLAlchemy, Google Generative AI
- **Key Modules**:
  - RSS Parser for feed processing
  - Scheduler for background tasks
  - Gemini API integration
  - Database models and queries

## Security Considerations

- HTML sanitization for user-generated content
- API key storage in environment variables
- Input validation and error handling
- CORS configuration for API access

## Future Enhancements

- Authentication for admin features
- Additional news sources
- Enhanced topic classification using ML
- Content summarization via AI
- Sentiment analysis of news articles
- User preferences and personalization