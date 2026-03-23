import pytest
import httpx
from fastapi import status
from app.core.security import hash_password
from app.models.user import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.auth import TokenResponse
from typing import Dict, Any


@pytest.mark.asyncio
async def test_register_user(async_client: httpx.AsyncClient, async_db: AsyncSession):
    """Tests the user registration endpoint."""
    payload = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword",
        "first_name": "Test",
        "last_name": "User",
    }
    response = await async_client.post("/api/auth/register", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["success"] is True

    # Verify user exists in the database
    result = await async_db.execute(select(User).where(User.email == payload["email"]))
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.username == payload["username"]


@pytest.mark.asyncio
async def test_register_duplicate_email(async_client: httpx.AsyncClient):
    """Tests registration with a duplicate email."""
    payload = {
        "username": "testuser2",
        "email": "test@example.com",  # Using same email as above
        "password": "testpassword",
        "first_name": "Test",
        "last_name": "User",
    }
    response = await async_client.post("/api/auth/register", json=payload)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "Email already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_user(
    async_client: httpx.AsyncClient, async_db: AsyncSession, test_user: User
):
    """Tests the user login endpoint."""
    payload = {"email": test_user.email, "password": "testpassword"}
    response = await async_client.post("/api/auth/login", json=payload)
    assert response.status_code == status.HTTP_200_OK

    token_response = TokenResponse.model_validate(response.json())
    assert token_response.access_token is not None
    assert token_response.refresh_token is not None
    assert token_response.token_type == "Bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials(async_client: httpx.AsyncClient, test_user: User):
    """Tests login with invalid credentials."""
    payload = {"email": test_user.email, "password": "wrongpassword"}
    response = await async_client.post("/api/auth/login", json=payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid credentials" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_current_user(
    async_client: httpx.AsyncClient,
    async_db: AsyncSession,
    test_user: User,
    auth_header: Dict[str, str],
):
    """Tests retrieving the current user's information."""
    response = await async_client.get("/api/auth/me", headers=auth_header)
    assert response.status_code == status.HTTP_200_OK
    user_data: Dict[str, Any] = response.json()["data"]
    assert user_data["username"] == test_user.username
    assert user_data["email"] == test_user.email


@pytest.mark.asyncio
async def test_get_current_user_unauthorized(async_client: httpx.AsyncClient):
    """Tests that an unauthenticated user cannot access the /me endpoint."""
    response = await async_client.get("/api/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Not authenticated" in response.json()["detail"]


@pytest.mark.asyncio
async def test_refresh_token(
    async_client: httpx.AsyncClient,
    async_db: AsyncSession,
    test_user: User,
):
    """Tests refreshing an access token using a refresh token."""
    # First, login to get the refresh token
    login_payload = {"email": test_user.email, "password": "testpassword"}
    login_response = await async_client.post("/api/auth/login", json=login_payload)
    login_response.raise_for_status()
    token_response = TokenResponse.model_validate(login_response.json())
    refresh_token = token_response.refresh_token

    # Then, use the refresh token to get a new access token
    refresh_payload = {"refresh_token": refresh_token}
    refresh_response = await async_client.post("/api/auth/refresh", json=refresh_payload)
    assert refresh_response.status_code == status.HTTP_200_OK
    assert "access_token" in refresh_response.json()["data"]


@pytest.mark.asyncio
async def test_refresh_token_invalid(
    async_client: httpx.AsyncClient,
    async_db: AsyncSession,
    test_user: User,
):
    """Tests refreshing an access token using an invalid refresh token."""
    refresh_payload = {"refresh_token": "invalid_refresh_token"}
    refresh_response = await async_client.post("/api/auth/refresh", json=refresh_payload)
    assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid refresh token" in refresh_response.json()["detail"]
