import json
import time
import redis.asyncio as redis
from google.adk.sessions import BaseSessionService


class RedisSessionService(BaseSessionService):
    def __init__(self, host, port, password, ttl=3600):
        self.redis = redis.Redis(
            host=host,
            port=port,
            password=password,
            decode_responses=True,
        )
        self.ttl = ttl

    async def get_session(self, session_id: str):
        data = await self.redis.get(f"adk:session:{session_id}")
        return json.loads(data) if data else None

    async def create_session(self, session_id: str):
        session = {
            "id": session_id,
            "state": {},
            "created_at": int(time.time()),
        }

        await self.redis.set(
            f"adk:session:{session_id}",
            json.dumps(session),
            ex=self.ttl,
        )

        return session

    async def update_session(self, session_id: str, session_data: dict):
        await self.redis.set(
            f"adk:session:{session_id}",
            json.dumps(session_data),
            ex=self.ttl,
        )

    async def delete_session(self, session_id: str):
        await self.redis.delete(f"adk:session:{session_id}")

    async def list_sessions(self, user_id: str | None = None):
        keys = await self.redis.keys("adk:session:*")

        sessions = []
        for key in keys:
            data = await self.redis.get(key)
            if data:
                sessions.append(json.loads(data))

        return sessions
