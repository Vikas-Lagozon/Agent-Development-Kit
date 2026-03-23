# LMS - Learning Management System

A simple Learning Management System (LMS) built with FastAPI and SQLite.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Running the Application](#running-the-application)
- [API Endpoints](#api-endpoints)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

## Features

- User registration and authentication (JWT).
- User management (create, read, update, delete).
- Course management (create, read, update, delete).
- Secure password handling using bcrypt.
- Asynchronous database operations with SQLAlchemy.
- Pydantic schemas for request and response validation.
- CORS enabled for cross-origin requests.
- SQLite database for data storage.
- Dockerfile for containerization.

## Prerequisites

- Python 3.10+
- pip
- [Poetry](https://python-poetry.org/) (recommended) or venv
- Docker (optional, for containerization)

## Setup

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd lms
    ```

2.  **Create a virtual environment (optional but recommended):**

    Using `venv`:

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate  # On Linux/macOS
    .venv\Scripts\activate  # On Windows
    ```

    Using Poetry:

    ```bash
    poetry install
    poetry shell
    ```

3.  **Install dependencies:**

    If using `venv`:

    ```bash
    # Install or upgrade dependencies, ensuring SQLAlchemy is v2.0 or higher
    pip install --upgrade -r requirements.txt
    ```

    **Important Note:** Ensure your `requirements.txt` specifies `SQLAlchemy[asyncio]>=2.0.0` to enable asynchronous features like `AsyncAttrs`.

    If using Poetry (steps already done).

4.  **Configure the environment:**

    Copy `.env.example` to `.env` and modify the variables as needed.

    ```bash
    cp .env.example .env
    ```

    Ensure the `JWT_SECRET_KEY` is changed to a secure, random string in `.env`.

    ```env
    APP_NAME="LMS"
    DEBUG=true

    JWT_SECRET_KEY=your_secure_jwt_secret_key
    JWT_ALGORITHM=HS256
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

    DB_DRIVER=sqlite+aiosqlite
    DB_NAME=lms.db

    CORS_ORIGINS=http://localhost:3000
    ```

5.  **Run database migrations:**

    ```bash
5.  **Run database migrations (from project root):**

    First, initialize the Alembic environment if you haven't already. This creates the `migrations` directory and `alembic.ini`.

    ```bash
    alembic init migrations
    ```

    Then, generate the initial migration script:

    ```bash
    alembic revision --autogenerate -m "Initial database schema"
    ```

    Finally, apply the migrations to your database:

    ```bash
    alembic upgrade head
    ```

## Running the Application

1.  **Run the application using Uvicorn:**

    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ```

    Alternatively, using `run.py`:

    ```bash
    python run.py
    ```

    This starts the FastAPI application on `http://localhost:8000`. The `--reload` flag enables automatic reloading upon code changes.

## API Endpoints

### Authentication

-   **POST** `/api/auth/register`: Register a new user.

    ```json
    {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "securepassword",
        "first_name": "New",
        "last_name": "User"
    }
    ```

-   **POST** `/api/auth/login`: Log in and retrieve JWT tokens.

    ```json
    {
        "email": "newuser@example.com",
        "password": "securepassword"
    }
    ```

    Response:

    ```json
    {
        "access_token": "...",
        "refresh_token": "...",
        "token_type": "Bearer"
    }
    ```

-   **POST** `/api/auth/refresh`: Refresh the access token using the refresh token.

    ```json
    {
        "refresh_token": "..."
    }
    ```

-   **GET** `/api/auth/me`: Get current user information (requires authentication).

    **Headers:**

    ```
    Authorization: Bearer <access_token>
    ```

### Users

-   **GET** `/api/users/`: List all users (requires authentication).
    - Query parameters: `page`, `per_page`, `search`
    **Headers:**

    ```
    Authorization: Bearer <access_token>
    ```

-   **GET** `/api/users/{user_id}`: Get a specific user by ID (requires authentication).
    **Headers:**

    ```
    Authorization: Bearer <access_token>
    ```

-   **POST** `/api/users/`: Create a new user (requires authentication).
    **Headers:**

    ```
    Authorization: Bearer <access_token>
    ```

    ```json
    {
        "username": "adminuser",
        "email": "admin@example.com",
        "password": "adminpassword",
        "first_name": "Admin",
        "last_name": "User"
    }
    ```

-   **PUT** `/api/users/{user_id}`: Update an existing user (requires authentication).
     **Headers:**

    ```
    Authorization: Bearer <access_token>
    ```
    ```json
    {
        "first_name": "Updated",
        "last_name": "Name"
    }
    ```

### Courses

-   **POST** `/api/courses/`: Create a new course (requires authentication).
     **Headers:**

    ```
    Authorization: Bearer <access_token>
    ```

    ```json
    {
        "name": "Introduction to Python",
        "description": "A beginner-friendly Python course."
    }
    ```

-   **GET** `/api/courses/{course_id}`: Get a specific course by ID (requires authentication).
     **Headers:**

    ```
    Authorization: Bearer <access_token>
    ```

-   **PUT** `/api/courses/{course_id}`: Update an existing course (requires authentication).
     **Headers:**

    ```
    Authorization: Bearer <access_token>
    ```

    ```json
    {
        "description": "An updated description."
    }
    ```

-   **DELETE** `/api/courses/{course_id}`: Delete a course (requires authentication).
     **Headers:**

    ```
    Authorization: Bearer <access_token>
    ```

-   **GET** `/api/courses/`: List all courses (requires authentication).
     **Headers:**

    ```
    Authorization: Bearer <access_token>
    ```
    - Query parameters: `page`, `per_page`

## Testing

1.  Install pytest and httpx:

    ```bash
    pip install pytest httpx pytest-asyncio
    ```

2.  Run the tests:

    ```bash
    pytest
    ```

## Contributing

Contributions are welcome! Please follow these steps:

1.  Fork the repository.
2.  Create a new branch for your feature or bug fix.
3.  Make your changes.
4.  Write tests to cover your changes.
5.  Submit a pull request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.