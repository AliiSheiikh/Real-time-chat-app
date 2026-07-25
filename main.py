from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from database import Base, engine, async_session
from models import Message


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


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

    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        self.active_connections[websocket] = username

    def disconnect(self, websocket: WebSocket):
        del self.active_connections[websocket]

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    username = websocket.query_params.get("username", "Anonymous")
    await manager.connect(websocket, username)

    async with async_session() as session:
        result = await session.execute(
            select(Message).order_by(Message.created_at.desc()).limit(20)
        )
        history = reversed(result.scalars().all())
        for message in history:
            await websocket.send_text(f"{message.username}: {message.content}")

    await manager.broadcast(f"{username} joined the chat")
    try:
        while True:
            data = await websocket.receive_text()

            async with async_session() as session:
                session.add(Message(username=username, content=data))
                await session.commit()

            await manager.broadcast(f"{username}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"{username} left the chat")
