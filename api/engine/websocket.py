import json
import asyncio
from typing import Dict, List
from fastapi import WebSocket
from redis.asyncio import Redis

from api.config import get_api_settings

_settings = get_api_settings()


class ConnectionManager:
    def __init__(self):
        # Maps session_id to a list of active WebSockets
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.redis = Redis.from_url(_settings.redis_url)
        self.pubsub = self.redis.pubsub()
        self.pubsub_task = None

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
            await self.pubsub.subscribe(f"session:{session_id}")
            if self.pubsub_task is None:
                self.pubsub_task = asyncio.create_task(self._listen_to_redis())
        self.active_connections[session_id].append(websocket)

    def disconnect(self, websocket: WebSocket, session_id: str):
        if session_id in self.active_connections:
            if websocket in self.active_connections[session_id]:
                self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def _listen_to_redis(self):
        async for message in self.pubsub.listen():
            if message["type"] == "message":
                channel = message["channel"].decode()
                data = message["data"].decode()
                session_id = channel.split(":")[1]
                if session_id in self.active_connections:
                    for connection in self.active_connections[session_id]:
                        try:
                            await connection.send_text(data)
                        except Exception:
                            pass

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, session_id: str, message: dict):
        """
        Publish state update to Redis so any node hosting the socket can broadcast it.
        """
        payload = json.dumps(message)
        await self.redis.publish(f"session:{session_id}", payload)


manager = ConnectionManager()
