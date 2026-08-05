
import json
import asyncio
from typing import Dict, List
from fastapi import WebSocket

from api.redis import get_redis


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self._redis = None
        self._pubsub = None
        self.pubsub_task = None

    def _get_redis(self):
        if self._redis is None:
            self._redis = get_redis()
            self._pubsub = self._redis.pubsub()
        return self._redis

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self._get_redis()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
            await self._pubsub.subscribe(f"session:{session_id}")
            if self.pubsub_task is None:
                self.pubsub_task = asyncio.create_task(self._listen_to_redis())
        self.active_connections[session_id].append(websocket)

    async def disconnect(self, websocket: WebSocket, session_id: str):
        if session_id in self.active_connections:
            if websocket in self.active_connections[session_id]:
                self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
                if self._pubsub is not None:
                    await self._pubsub.unsubscribe(f"session:{session_id}")

    async def _listen_to_redis(self):
        async for message in self._pubsub.listen():
            if message["type"] == "message":
                channel = message["channel"].decode()
                data = message["data"].decode()
                session_id = channel.split(":")[1]
                if session_id in self.active_connections:
                    dead_connections: list[WebSocket] = []
                    for connection in list(self.active_connections[session_id]):
                        try:
                            await connection.send_text(data)
                        except Exception:
                            dead_connections.append(connection)
                    for dead in dead_connections:
                        await self.disconnect(dead, session_id)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, session_id: str, message: dict):
        """
        Publish state update to Redis so any node hosting the socket can broadcast it.
        """
        redis = get_redis()
        payload = json.dumps(message)
        await redis.publish(f"session:{session_id}", payload)


manager = ConnectionManager()
