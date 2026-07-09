"""
WebSocket endpoint for real-time graph updates.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import JWTError, jwt

from api.config import get_api_settings
from api.engine.websocket import manager
from api.services.session_service import websocket_has_session_access

router = APIRouter()
_settings = get_api_settings()


@router.websocket("/{session_id}/stream")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = Query(default=None),
):
    """Real-time graph updates. Requires ?token=<jwt> for auth."""
    if not token:
        await websocket.close(code=4001, reason="Missing authentication token")
        return

    try:
        payload = jwt.decode(
            token, _settings.secret_key, algorithms=[_settings.jwt_algorithm]
        )
        email: str = payload.get("sub")
        if email is None:
            await websocket.close(code=4001, reason="Invalid token")
            return
    except JWTError:
        await websocket.close(code=4001, reason="Invalid token")
        return

    if not await websocket_has_session_access(session_id, email):
        await websocket.close(code=4003, reason="Session access denied")
        return

    await manager.connect(websocket, session_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket, session_id)
