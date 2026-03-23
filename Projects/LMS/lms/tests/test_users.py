import pytest
import httpx
from fastapi import status
from typing import Dict, Any

BASE_URL = "http://localhost:8000/api/users"  # Adjust if needed

@pytest.fixture
async def client():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        yield client

async def create_user(client: httpx.AsyncClient, user_data: Dict[str, Any]) -> httpx.Response:
    """Helper function to create a user."""
    response = await client.post("/api/auth/register", json=user_data)
    return response

async def get_access_token(client: httpx.AsyncClient, login_data: Dict[str, str]) -> str:
    """Helper function to obtain an access token."""
    response = await client.post("/api/auth/login", json=login_data)
    response.raise_for_status()  # Ensure login was successful
    return response.json()["access_token"]

@pytest.mark.asyncio
async def test_create_user(client: httpx.AsyncClient):
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "password123",
        "first_name": "Test",
        "last_name": "User"
    }
    response = await create_user(client, user_data)
    assert response.status_code == status.HTTP_201_CREATED

    # Now log in to get token
    login_data = {"email": "test@example.com", "password": "password123"}
    access_token = await get_access_token(client, login_data)

    # Fetch user
    user_id = response.json()["data"]["id"]
    headers = {"Authorization": f"Bearer {access_token}"}
    get_response = await client.get(f"/api/users/{user_id}", headers=headers)
    assert get_response.status_code == status.HTTP_200_OK
    assert get_response.json()["username"] == "testuser"
    assert get_response.json()["email"] == "test@example.com"

@pytest.mark.asyncio
async def test_get_user(client: httpx.AsyncClient):
    # First, create a user
    user_data = {
        "username": "getusertest",
        "email": "get@example.com",
        "password": "password123",
        "first_name": "Get",
        "last_name": "User"
    }
    await create_user(client, user_data)

    # Login to get token
    login_data = {"email": "get@example.com", "password": "password123"}
    access_token = await get_access_token(client, login_data)

    # Fetch user list.
    headers = {"Authorization": f"Bearer {access_token}"}
    list_response = await client.get("/api/users", headers=headers)
    assert list_response.status_code == status.HTTP_200_OK

    users = list_response.json()
    assert isinstance(users, list)
    # Can't guarantee user is first, check each.
    found = False
    for user in users:
        if user["username"] == "getusertest":
            found = True
            break
    assert found

@pytest.mark.asyncio
async def test_update_user(client: httpx.AsyncClient):
    # First, create a user
    user_data = {
        "username": "updatetest",
        "email": "update@example.com",
        "password": "password123",
        "first_name": "Update",
        "last_name": "User"
    }
    create_response = await create_user(client, user_data)
    assert create_response.status_code == status.HTTP_201_CREATED
    user_id = create_response.json()["data"]["id"]

    # Login to get token
    login_data = {"email": "update@example.com", "password": "password123"}
    access_token = await get_access_token(client, login_data)

    # Update the user
    update_data = {"first_name": "Updated", "last_name": "User"}
    headers = {"Authorization": f"Bearer {access_token}"}
    update_response = await client.put(f"/api/users/{user_id}", json=update_data, headers=headers)

    assert update_response.status_code == status.HTTP_200_OK
    assert update_response.json()["first_name"] == "Updated"

@pytest.mark.asyncio
async def test_list_users(client: httpx.AsyncClient):
    # First, create a user
    user_data = {
        "username": "listtest",
        "email": "list@example.com",
        "password": "password123",
        "first_name": "List",
        "last_name": "User"
    }
    await create_user(client, user_data)

    # Login to get token
    login_data = {"email": "list@example.com", "password": "password123"}
    access_token = await get_access_token(client, login_data)

    # List users
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await client.get("/api/users", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_list_users_pagination(client: httpx.AsyncClient):
    # First, create some users (at least 11 for pagination testing)
    for i in range(11):
        user_data = {
            "username": f"pagetest{i}",
            "email": f"page{i}@example.com",
            "password": "password123",
            "first_name": "Page",
            "last_name": f"User{i}"
        }
        await create_user(client, user_data)

    # Login to get token (using the last user created)
    login_data = {"email": "page10@example.com", "password": "password123"}
    access_token = await get_access_token(client, login_data)

    # List users with pagination (page 1, per_page 5)
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await client.get("/api/users?page=1&per_page=5", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    users = response.json()
    assert isinstance(users, list)
    assert len(users) == 5

    # List users with pagination (page 2, per_page 5)
    response = await client.get("/api/users?page=2&per_page=5", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    users = response.json()
    assert isinstance(users, list)
    assert len(users) == 5

    # List users with pagination (page 3, per_page 5)
    response = await client.get("/api/users?page=3&per_page=5", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    users = response.json()
    assert isinstance(users, list)
    assert len(users) == 1

@pytest.mark.asyncio
async def test_delete_user(client: httpx.AsyncClient):
    # First, create a user
    user_data = {
        "username": "deletetest",
        "email": "delete@example.com",
        "password": "password123",
        "first_name": "Delete",
        "last_name": "User"
    }
    create_response = await create_user(client, user_data)
    assert create_response.status_code == status.HTTP_201_CREATED
    user_id = create_response.json()["data"]["id"]

    # Login to get token
    login_data = {"email": "delete@example.com", "password": "password123"}
    access_token = await get_access_token(client, login_data)

    # Delete the user
    headers = {"Authorization": f"Bearer {access_token}"}
    delete_response = await client.delete(f"/api/users/{user_id}", headers=headers)
    assert delete_response.status_code == status.HTTP_204_NO_CONTENT

    # Try to get the deleted user
    get_response = await client.get(f"/api/users/{user_id}", headers=headers)
    assert get_response.status_code == status.HTTP_404_NOT_FOUND