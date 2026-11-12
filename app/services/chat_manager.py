from collections import defaultdict
from fastapi import WebSocket
import asyncio


class ChatConnectionManager:

    def __init__(self):

        # conversation_id -> user_id -> WebSocket connections
        self.active_connections = defaultdict(
            lambda: defaultdict(set)
        )

        # All connections of a user, across conversations
        self.user_connections = defaultdict(set)

        self.lock = asyncio.Lock()

    async def connect(
        self,
        user_id: int,
        conversation_id: int,
        websocket: WebSocket
    ):

        async with self.lock:

            self.active_connections[conversation_id][user_id].add(
                websocket
            )

            self.user_connections[user_id].add(websocket)

    async def disconnect(
        self,
        user_id: int,
        conversation_id: int,
        websocket: WebSocket
    ):

        async with self.lock:

            conversation_connections = (
                self.active_connections.get(conversation_id, {})
            )

            user_connections = conversation_connections.get(
                user_id,
                set()
            )

            user_connections.discard(websocket)

            if not user_connections:
                conversation_connections.pop(user_id, None)

            if not conversation_connections:
                self.active_connections.pop(conversation_id, None)

            all_connections = self.user_connections.get(
                user_id,
                set()
            )

            all_connections.discard(websocket)

            if not all_connections:
                self.user_connections.pop(user_id, None)

    async def send_to_user(
        self,
        user_id: int,
        conversation_id: int,
        message: dict
    ) -> bool:

        connections = list(
            self.active_connections
            .get(conversation_id, {})
            .get(user_id, set())
        )

        delivered = False

        for connection in connections:

            try:

                await connection.send_json(message)
                delivered = True

            except Exception:

                await self.disconnect(
                    user_id,
                    conversation_id,
                    connection
                )

        return delivered

    async def broadcast(
        self,
        conversation_id: int,
        user_ids: list,
        message: dict
    ) -> list:

        delivered_users = []

        for user_id in set(user_ids):

            delivered = await self.send_to_user(
                user_id,
                conversation_id,
                message
            )

            if delivered:
                delivered_users.append(user_id)

        return delivered_users

    def is_online(self, user_id: int) -> bool:

        return bool(
            self.user_connections.get(user_id)
        )


chat_manager = ChatConnectionManager()