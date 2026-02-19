import json
import time
import redis.asyncio as redis
from google.adk.sessions import BaseSessionService, Session

class RedisSessionService(BaseSessionService):
    def __init__(self, host, port, password, ttl=3600):
        self.redis = redis.Redis(
            host=host,
            port=port,
            password=password,
            decode_responses=True,
        )
        self.ttl = ttl

    async def get_session(self, session_id: str, **kwargs):
        data = await self.redis.get(f"adk:session:{session_id}")
        if not data:
            return None
        
        session_dict = json.loads(data)
        
        # 1. Strip forbidden fields to pass Pydantic validation
        session_dict.pop("created_at", None) 

        # 2. STRICT NORMALIZATION: Ensure only camelCase keys (appName, userId) exist
        if "app_name" in session_dict:
            session_dict["appName"] = session_dict.pop("app_name")
        if "user_id" in session_dict:
            session_dict["userId"] = session_dict.pop("user_id")

        # 3. Prevent crash from corrupted old manual event data
        if "events" in session_dict and isinstance(session_dict["events"], list):
            if len(session_dict["events"]) > 0 and "author" not in session_dict["events"][0]:
                session_dict["events"] = [] 

        return Session(**session_dict)

    async def create_session(self, session_id: str, **kwargs):
        app_name = kwargs.get("appName") or kwargs.get("app_name") or "default_app"
        user_id  = kwargs.get("userId") or kwargs.get("user_id") or "anonymous"

        session_dict = {
            "id": session_id,
            "appName": app_name,
            "userId": user_id,
            "state": {},
            "events": [],
            "created_at": int(time.time()),
        }

        await self.redis.set(
            f"adk:session:{session_id}",
            json.dumps(session_dict),
            ex=self.ttl,
        )

        session_dict.pop("created_at", None)
        return Session(**session_dict)

    async def update_session(self, session_id: str, session_data: dict | Session, **kwargs):
        # FIX: Check if session_data is a Session object and convert it properly for Redis
        if hasattr(session_data, "model_dump"):
            data_to_save = session_data.model_dump()
        else:
            data_to_save = session_data

        # Normalize keys before final save to keep Redis clean
        if "app_name" in data_to_save:
            data_to_save["appName"] = data_to_save.pop("app_name")
        if "user_id" in data_to_save:
            data_to_save["userId"] = data_to_save.pop("user_id")

        await self.redis.set(
            f"adk:session:{session_id}",
            json.dumps(data_to_save),
            ex=self.ttl,
        )

    async def delete_session(self, session_id: str, **kwargs):
        await self.redis.delete(f"adk:session:{session_id}")

    async def list_sessions(self, user_id: str | None = None, **kwargs):
        keys = await self.redis.keys("adk:session:*")
        sessions = []
        for key in keys:
            data = await self.redis.get(key)
            if data:
                s_dict = json.loads(data)
                s_dict.pop("created_at", None)
                if user_id and s_dict.get("userId") != user_id:
                    continue
                sessions.append(Session(**s_dict))
        return sessions
