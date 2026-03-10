# RedisDatabaseSessionService.py
import os
import json
from typing import List, Optional
from google.adk.sessions import BaseSessionService, Session
from google.adk.events import Event

class RedisSessionService(BaseSessionService):
    def __init__(self, redis_client):
        self.redis = redis_client

    async def create_session(self, app_name: str, user_id: str, **kwargs) -> Session:
        session_id = kwargs.pop("session_id", None) or f"sess_{user_id}_{app_name}_{os.urandom(4).hex()}"
        
        # Create the session
        session = Session(id=session_id, app_name=app_name, user_id=user_id, **kwargs)
        
        # Save metadata to a Redis Hash
        await self.redis.hset(f"session:{session_id}:meta", mapping={
            "app_name": app_name,
            "user_id": user_id,
            "state": json.dumps(kwargs.get("state", {}))
        })
        return session

    async def append_event(self, session: Session, event: Event):
        event_data = event.model_dump_json()
        await self.redis.rpush(f"session:{session.id}:events", event_data)
        
        if event.actions and event.actions.state_delta:
            meta_key = f"session:{session.id}:meta"
            current_state_raw = await self.redis.hget(meta_key, "state")
            current_state = json.loads(current_state_raw) if current_state_raw else {}
            current_state.update(event.actions.state_delta)
            await self.redis.hset(meta_key, "state", json.dumps(current_state))

    # Accept arbitrary kwargs to match ADK signature
    async def get_session(self, session_id: str, **kwargs) -> Optional[Session]:
        meta = await self.redis.hgetall(f"session:{session_id}:meta")
        if not meta:
            return None
        
        raw_events = await self.redis.lrange(f"session:{session_id}:events", 0, -1)
        events = [Event.model_validate_json(e) for e in raw_events]
        
        return Session(
            id=session_id,
            app_name=meta.get("app_name"),
            user_id=meta.get("user_id"),
            events=events,
            state=json.loads(meta.get("state", "{}"))
        )

    async def list_sessions(self, user_id: str, **kwargs) -> List[Session]:
        sessions = []
        async for key in self.redis.scan_iter("session:*:meta"):
            meta = await self.redis.hgetall(key)
            if meta.get("user_id") == user_id:
                sid = key.split(":")[1]
                sessions.append(await self.get_session(sid))
        return sessions

    async def delete_session(self, session_id: str):
        await self.redis.delete(f"session:{session_id}:meta")
        await self.redis.delete(f"session:{session_id}:events")
