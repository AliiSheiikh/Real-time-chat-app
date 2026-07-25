# Real-Time Chat App

A real-time chat application built with FastAPI and WebSockets, with persistent message history and support for horizontal scaling across multiple server instances via Redis pub/sub.

## Features

- Real-time messaging over WebSockets (no polling)
- Usernames per connection
- Join/leave announcements
- Persistent message history (Postgres) — new clients see recent history on connect
- Horizontally scalable — multiple server instances stay in sync via Redis pub/sub
- Per-connection rate limiting — caps abusive clients without affecting others

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

## Load testing

`load_test.py` spins up many concurrent WebSocket clients (via `asyncio.gather`), has each one connect, send a message, and wait for it to be broadcast back, then reports connection throughput and round-trip latency:

```bash
venv\Scripts\python load_test.py 100
```

Results on a single local instance (Postgres, Redis, and the app all running on the same machine):

| Concurrent clients | Wall time | Median latency | p95 latency |
|---|---|---|---|
| 100 | ~1.8s | ~300-500ms | ~1.3s |

**A finding worth noting:** the initial instinct when tuning for load is "increase the database connection pool size." We tried it (5 base connections → 20, with overflow 10 → 30) expecting an improvement, and instead measured a *regression* — total time for 100 clients went from ~1.8s to 12-15s. The smaller pool was actually acting as a natural throttle, feeding Postgres a controlled trickle of work; removing that limit let 100 requests hit the database and event loop truly simultaneously, and something else (contention on this single dev machine running the load generator, app, Postgres, and Redis all at once) became the new bottleneck instead. The pool size was reverted back to SQLAlchemy's default after confirming this with repeated runs. Lesson: measure before tuning — the obvious fix isn't always the correct one.
