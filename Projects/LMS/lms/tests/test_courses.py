import pytest
import httpx
from fastapi import status
from typing import Dict, Any

BASE_URL = "http://localhost:8000/api/courses"  # Adjust if needed

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

async def create_course(client: httpx.AsyncClient, course_data: Dict[str, str], access_token: str) -> httpx.Response:
    """Helper function to create a course."""
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await client.post("/api/courses", json=course_data, headers=headers)
    return response

@pytest.mark.asyncio
async def test_create_course(client: httpx.AsyncClient):
    # First, create a user
    user_data = {
        "username": "coursetest",
        "email": "course@example.com",
        "password": "password123",
        "first_name": "Course",
        "last_name": "User"
    }
    await create_user(client, user_data)

    # Now log in to get token
    login_data = {"email": "course@example.com", "password": "password123"}
    access_token = await get_access_token(client, login_data)

    course_data = {
        "name": "New Course",
        "description": "A new course description"
    }
    response = await create_course(client, course_data, access_token)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["name"] == "New Course"

@pytest.mark.asyncio
async def test_get_course(client: httpx.AsyncClient):
    # First, create a user
    user_data = {
        "username": "getcoursetest",
        "email": "getcourse@example.com",
        "password": "password123",
        "first_name": "GetCourse",
        "last_name": "User"
    }
    await create_user(client, user_data)

    # Login to get token
    login_data = {"email": "getcourse@example.com", "password": "password123"}
    access_token = await get_access_token(client, login_data)

    # Create a course
    course_data = {
        "name": "Get Course Test",
        "description": "A get course test description"
    }
    create_response = await create_course(client, course_data, access_token)
    assert create_response.status_code == status.HTTP_201_CREATED
    course_id = create_response.json()["id"]

    # Get the course
    headers = {"Authorization": f"Bearer {access_token}"}
    get_response = await client.get(f"/api/courses/{course_id}", headers=headers)
    assert get_response.status_code == status.HTTP_200_OK
    assert get_response.json()["name"] == "Get Course Test"

@pytest.mark.asyncio
async def test_update_course(client: httpx.AsyncClient):
    # First, create a user
    user_data = {
        "username": "updatecoursetest",
        "email": "updatecourse@example.com",
        "password": "password123",
        "first_name": "UpdateCourse",
        "last_name": "User"
    }
    await create_user(client, user_data)

    # Login to get token
    login_data = {"email": "updatecourse@example.com", "password": "password123"}
    access_token = await get_access_token(client, login_data)

    # Create a course
    course_data = {
        "name": "Original Course Name",
        "description": "Original description"
    }
    create_response = await create_course(client, course_data, access_token)
    assert create_response.status_code == status.HTTP_201_CREATED
    course_id = create_response.json()["id"]

    # Update the course
    update_data = {
        "name": "Updated Course Name",
        "description": "Updated description",
        "is_active": False
    }
    headers = {"Authorization": f"Bearer {access_token}"}
    put_response = await client.put(f"/api/courses/{course_id}", json=update_data, headers=headers)
    assert put_response.status_code == status.HTTP_200_OK
    assert put_response.json()["name"] == "Updated Course Name"
    assert put_response.json()["description"] == "Updated description"
    assert put_response.json()["is_active"] == False

@pytest.mark.asyncio
async def test_delete_course(client: httpx.AsyncClient):
    # First, create a user
    user_data = {
        "username": "deletecoursetest",
        "email": "deletecourse@example.com",
        "password": "password123",
        "first_name": "DeleteCourse",
        "last_name": "User"
    }
    await create_user(client, user_data)

    # Login to get token
    login_data = {"email": "deletecourse@example.com", "password": "password123"}
    access_token = await get_access_token(client, login_data)

    # Create a course
    course_data = {
        "name": "Course to Delete",
        "description": "Description of course to delete"
    }
    create_response = await create_course(client, course_data, access_token)
    assert create_response.status_code == status.HTTP_201_CREATED
    course_id = create_response.json()["id"]

    # Delete the course
    headers = {"Authorization": f"Bearer {access_token}"}
    delete_response = await client.delete(f"/api/courses/{course_id}", headers=headers)
    assert delete_response.status_code == status.HTTP_204_NO_CONTENT

    # Verify that the course is deleted
    get_response = await client.get(f"/api/courses/{course_id}", headers=headers)
    assert get_response.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.asyncio
async def test_list_courses(client: httpx.AsyncClient):
    # First, create a user
    user_data = {
        "username": "listcoursetest",
        "email": "listcourse@example.com",
        "password": "password123",
        "first_name": "ListCourse",
        "last_name": "User"
    }
    await create_user(client, user_data)

    # Login to get token
    login_data = {"email": "listcourse@example.com", "password": "password123"}
    access_token = await get_access_token(client, login_data)

    # List courses
    headers = {"Authorization": f"Bearer {access_token}"}
    list_response = await client.get("/api/courses", headers=headers)
    assert list_response.status_code == status.HTTP_200_OK
    assert isinstance(list_response.json(), list) # Expecting a list of courses