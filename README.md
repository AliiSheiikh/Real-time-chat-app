# Real-Time Chat App

A real-time chat application built with FastAPI and WebSockets, with persistent message history and support for horizontal scaling across multiple server instances via Redis pub/sub.

## Features

- Real-time messaging over WebSockets (no polling)
- Usernames per connection
- Join/leave announcements
- Persistent message history (Postgres) — new clients see recent history on connect
- Horizontally scalable — multiple server instances stay in sync via Redis pub/sub

## Tech stack

- **FastAPI** — web framework and WebSocket handling
- **PostgreSQL** + **SQLAlchemy** (async) — message persistence
- **Redis** — pub/sub message bus for broadcasting across server instances
- **Vanilla HTML/CSS/JS** — chat client, no frontend framework

## Architecture

Each connected client holds a WebSocket connection to one server process. When a client sends a message:

1. The message is saved to Postgres.
2. It's published to a Redis channel.
3. Every server process (each one subscribed to that channel) receives it and forwards it to whichever clients are connected locally to it.

This means clients can be spread across multiple server processes/instances and still all see each other's messages — no single process needs to know about every connection in the system.

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL running locally
- Docker (for Redis)

### 1. Clone and install dependencies

```bash
python -m venv venv
venv\Scripts\pip install -r requirements.txt
```

### 2. Set up the database

Create a Postgres database for the app (adjust user/password as needed):

```sql
CREATE DATABASE chatapp;
```

### 3. Configure environment variables

Copy `.env.example` to `.env` and fill in your actual database credentials:

```bash
cp .env.example .env
```

### 4. Start Redis

```bash
docker compose up -d
```

### 5. Run the server

```bash
venv\Scripts\uvicorn main:app --reload
```

Visit `http://localhost:8000/chat` in your browser.

## Running multiple instances (to see horizontal scaling in action)

```bash
venv\Scripts\uvicorn main:app --port 8000
venv\Scripts\uvicorn main:app --port 8001
```

Open the chat page against each port in separate browser tabs — messages sent from one instance are broadcast to clients connected to the other, via Redis.
