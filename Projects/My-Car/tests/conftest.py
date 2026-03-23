import pytest
import asyncio
import httpx
from typing import AsyncGenerator, Generator, Dict
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import insert
from app.database.base import Base
from app.config import settings
from app.models.user import User
from app.core.security import hash_password
from datetime import datetime, timezone


DATABASE_URL = settings.DATABASE_URL

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def async_engine():
    """Create an async engine for testing."""
    engine = create_async_engine(DATABASE_URL, echo=False)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session", autouse=True)
async def create_test_database(async_engine):
    """Create the database and tables for testing."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # drop all tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def async_session(async_engine):
    """Create a new session for each test function."""
    AsyncSessionLocal = sessionmaker(
        bind=async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()  # Rollback any changes after the test


@pytest.fixture(scope="function")
async def async_db(async_session: AsyncSession):
    """Provide a dependency injection point for the database session."""
    yield async_session


@pytest.fixture(scope="function")
async def test_user(async_db: AsyncSession) -> User:
    """Create a test user in the database."""
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=hash_password("testpassword"),
        first_name="Test",
        last_name="User",
        is_active=True,
        is_verified=True,
        created_at=datetime.now(timezone.utc),
        last_login=datetime.now(timezone.utc),
    )
    async_db.add(user)
    await async_db.flush()
    return user


@pytest.fixture(scope="function")
async def test_car(async_db: AsyncSession, test_user: User):
    """Create a test car in the database."""
    from app.models.car import Car
    car = Car(
        owner_id=test_user.id,
        make="Toyota",
        model="Corolla",
        year=2018,
        price=18000.0,
        description="A compact car.",
        is_available=True,
        created_at=datetime.now(timezone.utc),
    )
    async_db.add(car)
    await async_db.flush()
    return car


@pytest.fixture(scope="session")
async def async_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """
    Create a httpx AsyncClient instance for testing endpoints.
    """
    from app.main import app

    async with httpx.AsyncClient(
        app=app, base_url="http://test"
    ) as client:
        yield client


@pytest.fixture(scope="function")
async def auth_header(
    async_client: httpx.AsyncClient, test_user: User
) -> Dict[str, str]:
    """
    Fixture to return authentication token for a test user.
    """
    login_data = {"email": test_user.email, "password": "testpassword"}
    response = await async_client.post("/api/auth/login", json=login_data)
    tokens = response.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}
