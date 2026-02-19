import asyncio
from config import config
from agent_app.redis_session_service import RedisSessionService

async def view_redis_data():
    session_service = RedisSessionService(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        password=config.REDIS_PASSWORD,
        ttl=config.REDIS_TTL,
    )

    print("\n--- 🔎 CURRENT SESSIONS IN REDIS ---")
    # list_sessions() now returns clean Session objects thanks to our fix
    sessions = await session_service.list_sessions()
    
    if not sessions:
        print("No active sessions found in Redis.")
        return

    for s in sessions:
        print(f"\nID: {s.id}")
        print(f"User: {s.userId} | App: {s.appName}")
        print(f"State: {s.state}")
        print(f"Messages: {len(s.events)} events recorded")

if __name__ == "__main__":
    asyncio.run(view_redis_data())

