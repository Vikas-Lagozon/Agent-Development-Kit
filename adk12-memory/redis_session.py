import asyncio
import json
import time
import uuid
import redis.asyncio as redis

# =====================================================
# CONFIGURATION
# =====================================================
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_PASSWORD = "myredispassword"   # MUST match docker-compose
SESSION_TTL = 120  # 2 minutes for testing


# =====================================================
# REDIS CONNECTION
# =====================================================
async def get_redis():
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        decode_responses=True
    )


# =====================================================
# SESSION FUNCTIONS
# =====================================================
async def create_session(redis_client, session_id: str, user_id: str):
    session_key = f"session:{session_id}"

    data = {
        "user_id": user_id,
        "created_at": int(time.time())
    }

    await redis_client.set(session_key, json.dumps(data), ex=SESSION_TTL)
    await redis_client.sadd(f"user:{user_id}:sessions", session_id)

    print(f"✅ Session created: {session_id}")


async def add_message(redis_client, session_id: str, role: str, content: str):
    key = f"session:{session_id}:messages"

    message = {
        "role": role,
        "content": content,
        "timestamp": int(time.time())
    }

    await redis_client.rpush(key, json.dumps(message))
    await redis_client.expire(key, SESSION_TTL)

    print(f"💬 Message added: {role} -> {content}")


async def get_session(redis_client, session_id: str):
    data = await redis_client.get(f"session:{session_id}")
    return json.loads(data) if data else None


async def get_messages(redis_client, session_id: str):
    key = f"session:{session_id}:messages"
    messages = await redis_client.lrange(key, 0, -1)
    return [json.loads(m) for m in messages]


async def delete_session(redis_client, session_id: str):
    await redis_client.delete(f"session:{session_id}")
    await redis_client.delete(f"session:{session_id}:messages")
    print("🗑 Session deleted")


# =====================================================
# MAIN TEST FLOW
# =====================================================
async def main():
    print("\n🔌 Connecting to Redis...")

    redis_client = await get_redis()

    # Test connection first
    try:
        pong = await redis_client.ping()
        print("✅ Redis connection successful:", pong)
    except Exception as e:
        print("❌ Redis connection failed:", e)
        return

    session_id = str(uuid.uuid4())
    user_id = "user-123"

    print("\n--- STEP 1: Create Session ---")
    await create_session(redis_client, session_id, user_id)

    print("\n--- STEP 2: Add Messages ---")
    await add_message(redis_client, session_id, "user", "Hello Redis")
    await add_message(redis_client, session_id, "assistant", "Hi! Persistence working.")

    print("\n--- STEP 3: Fetch Data (Before Restart) ---")
    session = await get_session(redis_client, session_id)
    messages = await get_messages(redis_client, session_id)

    print("Session Data:", session)
    print("Messages:", messages)

    print("\n--- STEP 4: Simulate App Restart ---")
    await redis_client.close()

    # Reconnect
    redis_client = await get_redis()

    print("\n--- STEP 5: Fetch Data (After Restart) ---")
    session = await get_session(redis_client, session_id)
    messages = await get_messages(redis_client, session_id)

    print("Session Data:", session)
    print("Messages:", messages)

    if session and messages:
        print("\n🎉 SUCCESS: Session persistence is working!")
    else:
        print("\n❌ ERROR: Session persistence failed!")

    print("\n--- STEP 6: TTL Remaining ---")
    ttl = await redis_client.ttl(f"session:{session_id}")
    print("Remaining TTL (seconds):", ttl)

    print("\n--- STEP 7: Cleanup ---")
    await delete_session(redis_client, session_id)

    await redis_client.close()
    print("\n✅ Test Completed Successfully.")


if __name__ == "__main__":
    asyncio.run(main())

