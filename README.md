# News Summarizer

A modern news aggregation and summarization application that fetches news articles from various sources, stores them in a database, and provides an AI-powered interface for users to query and interact with news content.

## Features

-   Automatic news fetching from RSS feeds
-   Article storage and search functionality
-   AI-powered news summarization with Google's Gemini API
-   Interactive chat interface for news queries
-   Admin dashboard for feed management

## Prerequisites

-   Python 3.13+ for the backend
-   Node.js and npm for the frontend
-   Google Gemini API key ([Get your API key here](https://makersuite.google.com/app/apikey))

## Installation

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd news-summarizer
```

### 2. Configure Environment Variables

Edit `.env` and replace `your_gemini_api_key` with your actual Gemini API key.

### 3. Setting Up Backend

#### Automatic Setup (using script)

```bash
source backend.sh
```

#### Manual Setup

```bash
# Install uv package manager
pip install uv

# Navigate to backend folder
cd backend

# Create and activate virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv sync

# Start Flask server
flask run
```

### 4. Setting Up Frontend

#### Automatic Setup (using script)

```bash
source frontend.sh
```

#### Manual Setup

```bash
# Navigate to frontend folder
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## Usage

Once both servers are running:

1. Access the frontend at: `http://localhost:5173/`
2. The backend API will be available at: `http://localhost:5000/api/`
3. Visit the admin dashboard at: `http://localhost:5173/admin` to manage news feeds

## Development

### Project Structure

-   `frontend/` - Vue.js frontend application
-   `backend/` - Flask API and news processing logic
-   `.venv/` - Python virtual environment (created during setup)

---
