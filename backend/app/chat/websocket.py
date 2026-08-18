"""
WebSocket Infrastructure and Connection Manager for Real-Time Chat.
"""

import json
import logging
from typing import Dict, List, Set, Optional

from fastapi import WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.auth.jwt import decode_token
from app.users.models import User

logger = logging.getLogger("ventureai.chat_ws")


class ConnectionManager:
    """
    Manages active WebSocket connections per user ID.
    Supports personal delivery, presence tracking, and conversation broadcasting.
    """

    def __init__(self):
        # Maps user_id -> Set[WebSocket]
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        """Accept connection and register user WebSocket."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info(f"WebSocket connected for User {user_id}. Active sockets: {len(self.active_connections[user_id])}")

    def disconnect(self, websocket: WebSocket, user_id: int):
        """Unregister user WebSocket upon disconnect."""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"WebSocket disconnected for User {user_id}")

    def is_user_online(self, user_id: int) -> bool:
        """Check if user has an active WebSocket connection."""
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0

    async def send_personal_message(self, data: dict, user_id: int) -> int:
        """
        Send a JSON payload to all active WebSockets of a specific user.
        Returns the count of successfully notified sockets.
        """
        if user_id not in self.active_connections:
            return 0

        delivered_count = 0
        dead_sockets = set()

        for ws in list(self.active_connections[user_id]):
            try:
                await ws.send_text(json.dumps(data, default=str))
                delivered_count += 1
            except Exception as e:
                logger.warning(f"Failed sending WS to User {user_id}: {e}")
                dead_sockets.add(ws)

        for dead_ws in dead_sockets:
            self.disconnect(dead_ws, user_id)

        return delivered_count

    async def broadcast_to_users(self, data: dict, user_ids: List[int]):
        """Send JSON payload to multiple users."""
        for uid in user_ids:
            await self.send_personal_message(data, uid)


# Global singleton instance
ws_manager = ConnectionManager()


async def get_ws_authenticated_user(websocket: WebSocket, db: Session) -> Optional[User]:
    """
    Authenticate WebSocket connection from HttpOnly cookie or query param token.
    """
    token = websocket.cookies.get("access_token")
    if not token:
        token = websocket.query_params.get("token")

    if not token:
        return None

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    user = db.query(User).filter(User.id == int(user_id)).first()
    return user
