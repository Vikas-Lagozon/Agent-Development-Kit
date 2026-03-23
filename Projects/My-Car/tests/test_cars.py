import pytest
import httpx
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.car import Car
from app.models.user import User
from app.schemas.car import CarCreate, CarUpdate, CarResponse
from typing import Dict, Any, List


@pytest.mark.asyncio
async def test_create_car(
    async_client: httpx.AsyncClient,
    async_db: AsyncSession,
    test_user: User,
    auth_header: Dict[str, str],
):
    """Tests the creation of a new car listing."""
    payload: Dict[str, Any] = {
        "make": "Toyota",
        "model": "Camry",
        "year": 2020,
        "price": 25000.0,
        "description": "A reliable sedan.",
    }
    response = await async_client.post("/api/cars/", json=payload, headers=auth_header)
    assert response.status_code == status.HTTP_201_CREATED

    car = CarResponse.model_validate(response.json())
    assert car.make == payload["make"]
    assert car.model == payload["model"]
    assert car.owner_id == test_user.id

    # Verify the car exists in the database
    result = await async_db.execute(select(Car).where(Car.id == car.id))
    db_car = result.scalar_one_or_none()
    assert db_car is not None
    assert db_car.make == payload["make"]


@pytest.mark.asyncio
async def test_list_cars(
    async_client: httpx.AsyncClient,
    async_db: AsyncSession,
    test_user: User,
    auth_header: Dict[str, str],
    test_car: Car,
):
    """Tests listing all car listings."""
    response = await async_client.get("/api/cars/", headers=auth_header)
    assert response.status_code == status.HTTP_200_OK
    cars: List[CarResponse] = [CarResponse.model_validate(car) for car in response.json()]
    assert len(cars) >= 1
    assert cars[0].make == test_car.make
    assert cars[0].model == test_car.model


@pytest.mark.asyncio
async def test_get_car(
    async_client: httpx.AsyncClient,
    async_db: AsyncSession,
    test_user: User,
    auth_header: Dict[str, str],
    test_car: Car,
):
    """Tests retrieving a specific car listing by ID."""
    response = await async_client.get(f"/api/cars/{test_car.id}", headers=auth_header)
    assert response.status_code == status.HTTP_200_OK

    car = CarResponse.model_validate(response.json())
    assert car.id == test_car.id
    assert car.make == test_car.make
    assert car.model == test_car.model


@pytest.mark.asyncio
async def test_get_car_not_found(
    async_client: httpx.AsyncClient,
    async_db: AsyncSession,
    test_user: User,
    auth_header: Dict[str, str],
):
    """Tests retrieving a car listing that does not exist."""
    response = await async_client.get("/api/cars/999", headers=auth_header)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Car not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_update_car(
    async_client: httpx.AsyncClient,
    async_db: AsyncSession,
    test_user: User,
    auth_header: Dict[str, str],
    test_car: Car,
):
    """Tests updating an existing car listing."""
    payload: Dict[str, Any] = {"price": 26000.0, "is_available": False}
    response = await async_client.put(
        f"/api/cars/{test_car.id}", json=payload, headers=auth_header
    )
    assert response.status_code == status.HTTP_200_OK

    car = CarResponse.model_validate(response.json())
    assert car.id == test_car.id
    assert car.price == payload["price"]
    assert car.is_available == payload["is_available"]

    # Verify the car was updated in the database
    result = await async_db.execute(select(Car).where(Car.id == test_car.id))
    db_car = result.scalar_one_or_none()
    assert db_car is not None
    assert db_car.price == payload["price"]
    assert db_car.is_available == payload["is_available"]


@pytest.mark.asyncio
async def test_update_car_not_found(
    async_client: httpx.AsyncClient,
    async_db: AsyncSession,
    test_user: User,
    auth_header: Dict[str, str],
):
    """Tests updating a car listing that does not exist."""
    payload: Dict[str, Any] = {"price": 26000.0}
    response = await async_client.put("/api/cars/999", json=payload, headers=auth_header)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Car not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_car(
    async_client: httpx.AsyncClient,
    async_db: AsyncSession,
    test_user: User,
    auth_header: Dict[str, str],
    test_car: Car,
):
    """Tests deleting a car listing."""
    response = await async_client.delete(f"/api/cars/{test_car.id}", headers=auth_header)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify the car is deleted from the database
    result = await async_db.execute(select(Car).where(Car.id == test_car.id))
    db_car = result.scalar_one_or_none()
    assert db_car is None


@pytest.mark.asyncio
async def test_delete_car_not_found(
    async_client: httpx.AsyncClient,
    async_db: AsyncSession,
    test_user: User,
    auth_header: Dict[str, str],
):
    """Tests deleting a car listing that does not exist."""
    response = await async_client.delete("/api/cars/999", headers=auth_header)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Car not found" in response.json()["detail"]
