from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional

from app.database.base import get_db
from app.models.car import Car
from app.schemas.car import CarCreate, CarUpdate, CarResponse
from app.models.user import User
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/cars", tags=["Cars"])


def _car_dict(car: Car) -> dict:
    return {
        "id":          car.id,
        "owner_id":    car.owner_id,
        "make":        car.make,
        "model":       car.model,
        "year":        car.year,
        "price":       car.price,
        "description": car.description,
        "is_available":car.is_available,
        "created_at":  car.created_at.isoformat(),
    }


@router.post("/", response_model=CarResponse, status_code=status.HTTP_201_CREATED)
async def create_car(
    payload: CarCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Creates a new car listing."""
    try:
        car = Car(
            owner_id=current_user.id,
            make=payload.make,
            model=payload.model,
            year=payload.year,
            price=payload.price,
            description=payload.description,
        )
        db.add(car)
        await db.flush()
        await db.refresh(car)
        return car
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/", response_model=List[CarResponse])
async def list_cars(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Lists all car listings with pagination."""
    try:
        q = select(Car)
        total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar()
        result = await db.execute(q.offset((page - 1) * per_page).limit(per_page))
        cars = result.scalars().all()
        return cars
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/{car_id}", response_model=CarResponse)
async def get_car(car_id: int, db: AsyncSession = Depends(get_db)):
    """Retrieves a specific car listing by ID."""
    try:
        result = await db.execute(select(Car).where(Car.id == car_id))
        car = result.scalar_one_or_none()
        if not car:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Car not found"
            )
        return car
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.put("/{car_id}", response_model=CarResponse)
async def update_car(
    car_id: int,
    payload: CarUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Updates a specific car listing by ID."""
    try:
        result = await db.execute(select(Car).where(Car.id == car_id))
        car = result.scalar_one_or_none()
        if not car:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Car not found"
            )

        if car.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to update this car",
            )

        update_data = payload.model_dump(exclude_unset=True)
        for k, v in update_data.items():
            setattr(car, k, v)

        await db.flush()
        await db.refresh(car)
        return car
    except HTTPException as e:
        await db.rollback()
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.delete("/{car_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_car(
    car_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deletes a specific car listing by ID."""
    try:
        result = await db.execute(select(Car).where(Car.id == car_id))
        car = result.scalar_one_or_none()
        if not car:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Car not found"
            )

        if car.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this car",
            )

        await db.delete(car)
        await db.flush()
    except HTTPException as e:
        await db.rollback()
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
