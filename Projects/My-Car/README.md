# FastAPI Car Selling and Buying Website

This project implements a REST API using FastAPI with SQLite as the database. It provides endpoints for user authentication and management, as well as for managing car listings.

## Features

- User registration and authentication with JWT
- CRUD operations for car listings
- User roles and permissions (basic)
- SQLite database for persistence
- Asynchronous database operations with SQLAlchemy
- Pydantic for data validation and serialization
- Dockerfile for containerization

## Project Structure

```
fastapi_car_selling/
├── app/
│   ├── main.py         # FastAPI application entry point
│   ├── config.py       # Application settings (reads .env)
│   ├── database/
│   │   └── base.py     # SQLAlchemy engine and session
│   ├── models/
│   │   ├── car.py      # SQLAlchemy model for cars
│   │   └── user.py     # SQLAlchemy model for users
│   ├── schemas/
│   │   ├── car.py      # Pydantic schemas for car data
│   │   └── user.py     # Pydantic schemas for user data
│   ├── core/
│   │   └── security.py # Password hashing
│   ├── routers/
│   │   ├── auth.py     # Authentication routes
│   │   ├── cars.py     # Car-related routes
│   │   └── users.py    # User management routes
│   └── .env            # Environment variables
├── tests/
│   ├── test_auth.py    # Tests for authentication
│   ├── test_cars.py    # Tests for car endpoints
│   └── conftest.py     # Test fixtures
├── requirements.txt    # Python dependencies
├── alembic.ini       # Alembic configuration
├── alembic/          # Alembic migrations
├── setup.py          # Script to set up the virtual environment and install dependencies
├── README.md         # This file
└── Dockerfile        # Dockerfile for the project
```

## Setup

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd fastapi_car_selling
    ```

2.  **Create a virtual environment:**

    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Linux/macOS
    .venv\Scripts\activate  # On Windows
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure environment variables:**

    -   Create a `.env` file in the `app/` directory based on the `.env.example` file.
    -   Update the `.env` file with your desired settings, especially the `JWT_SECRET_KEY`.

    ```bash
    cp app/.env.example app/.env
    nano app/.env  # Or your preferred editor
    ```

5. **Initialize Alembic:**

    ```bash
    alembic init alembic
    ```

6. **Generate the first migration:**

    ```bash
    alembic revision --autogenerate -m "Initial migration"
    ```

7. **Run database migrations:**

    ```bash
    alembic upgrade head
    ```

## Running the Application

1.  **Run the application using Uvicorn:**

    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ```

    This command starts the FastAPI application with:

    -   `app.main:app`: Specifies the module `app.main` and the `app` object (FastAPI instance) to run.
    -   `--host 0.0.0.0`:  Binds the application to all available network interfaces, making it accessible from other machines.
    -   `--port 8000`:  Runs the application on port 8000.
    -   `--reload`: Enables automatic reloading of the server upon code changes, which is helpful during development.

## Running Tests

1.  **Install pytest and pytest-asyncio:**

    ```bash
    pip install pytest pytest-asyncio
    ```

2.  **Run the tests:**

    ```bash
    pytest tests/
    ```

## API Endpoints

### Authentication

-   `POST /api/auth/register`: Register a new user.
-   `POST /api/auth/login`: Log in and receive JWT tokens.

### Users

-   `GET /api/users/me`: Get the current user's information.

### Cars

-   `GET /api/cars/`: List all cars.
-   `GET /api/cars/{car_id}`: Get a specific car by ID.
-   `POST /api/cars/`: Create a new car listing.
-   `PUT /api/cars/{car_id}`: Update a car listing.
-   `DELETE /api/cars/{car_id}`: Delete a car listing.

## Docker

1.  **Build the Docker image:**

    ```bash
    docker build -t fastapi_car_selling .
    ```

2.  **Run the Docker container:**

    ```bash
    docker run -p 8000:8000 fastapi_car_selling
    ```

## Notes

-   This project uses SQLite for simplicity. For production environments, consider using a more robust database like PostgreSQL or MySQL.
-   Implement more robust error handling and validation as needed.
-   Expand user roles and permissions for more fine-grained access control.
-   Consider adding features like image uploads for car listings.
