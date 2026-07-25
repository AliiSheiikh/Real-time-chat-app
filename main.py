import asyncio
import os
from contextlib import asynccontextmanager

import redis.asyncio as redis
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from database import Base, engine, async_session
from models import Message

load_dotenv()

CHANNEL = "chat"
redis_client = redis.from_url(os.environ["REDIS_URL"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    listener_task = asyncio.create_task(redis_listener())
    yield
    listener_task.cancel()


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def read_root():
    return {"message": "Chat server is alive"}


@app.get("/chat")
def get_chat_page():
    return FileResponse("static/index.html")


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[WebSocket, str] = {}

    async def accept(self, websocket: WebSocket):
        await websocket.accept()

    def register(self, websocket: WebSocket, username: str):
        self.active_connections[websocket] = username

    def disconnect(self, websocket: WebSocket):
        del self.active_connections[websocket]

    async def broadcast_locally(self, message: str):
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                dead_connections.append(connection)
        for connection in dead_connections:
            self.disconnect(connection)


manager = ConnectionManager()


async def publish(message: str):
    await redis_client.publish(CHANNEL, message)


async def redis_listener():
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(CHANNEL)
    async for message in pubsub.listen():
        if message["type"] == "message":
            await manager.broadcast_locally(message["data"].decode())


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    username = websocket.query_params.get("username", "Anonymous")
    await manager.accept(websocket)

    async with async_session() as session:
        result = await session.execute(
            select(Message).order_by(Message.created_at.desc()).limit(20)
        )
        history = reversed(result.scalars().all())
        for message in history:
            await websocket.send_text(f"{message.username}: {message.content}")

    manager.register(websocket, username)
    await publish(f"{username} joined the chat")
    try:
        while True:
            data = await websocket.receive_text()

            async with async_session() as session:
                session.add(Message(username=username, content=data))
                await session.commit()

            await publish(f"{username}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await publish(f"{username} left the chat")
