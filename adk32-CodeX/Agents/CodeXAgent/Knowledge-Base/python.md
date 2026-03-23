# Python Knowledge Base

---

## 1. Beginner → Moderate

### Syntax & Data Types
```python
# Variables — dynamically typed
name: str = "Alice"
age: int = 30
score: float = 95.5
active: bool = True
nothing: None = None

# Strings
greeting = f"Hello, {name}!"          # f-string (preferred)
multi = """Line one
Line two"""
upper = name.upper()
joined = ", ".join(["a", "b", "c"])   # "a, b, c"
split_parts = "a,b,c".split(",")      # ["a", "b", "c"]

# Type casting
n = int("42")
s = str(3.14)
```

### Collections
```python
# List — ordered, mutable
nums = [1, 2, 3, 4, 5]
nums.append(6)
nums.extend([7, 8])
nums.pop()           # removes last
nums.remove(1)       # removes by value
sliced = nums[1:4]   # [2, 3, 4]
reversed_nums = nums[::-1]

# Tuple — ordered, immutable
coords = (10.0, 20.0)
x, y = coords        # unpacking

# Dict — key-value pairs
person = {"name": "Alice", "age": 30}
person["city"] = "Delhi"
person.get("missing", "default")
keys = list(person.keys())
items = list(person.items())

# Set — unique, unordered
unique = {1, 2, 3, 2, 1}   # {1, 2, 3}
unique.add(4)
unique.discard(2)

# Comprehensions
squares = [x**2 for x in range(10)]
even_squares = [x**2 for x in range(10) if x % 2 == 0]
word_lengths = {w: len(w) for w in ["hello", "world"]}
unique_evens = {x for x in range(20) if x % 2 == 0}
```

### Control Flow
```python
# if / elif / else
if age >= 18:
    print("Adult")
elif age >= 13:
    print("Teen")
else:
    print("Child")

# Ternary
label = "adult" if age >= 18 else "minor"

# for loop
for i, val in enumerate(nums):
    print(i, val)

for k, v in person.items():
    print(k, v)

# while loop
count = 0
while count < 5:
    count += 1

# break / continue / else on loop
for n in range(10):
    if n == 5:
        break
else:
    print("Loop completed without break")
```

### Functions
```python
def greet(name: str, greeting: str = "Hello") -> str:
    """Return a greeting string."""
    return f"{greeting}, {name}!"

# *args and **kwargs
def summarise(*args: int, **kwargs: str) -> None:
    print(sum(args), kwargs)

# Lambda
square = lambda x: x ** 2

# Higher-order functions
doubled = list(map(lambda x: x * 2, [1, 2, 3]))
evens = list(filter(lambda x: x % 2 == 0, [1, 2, 3, 4]))
from functools import reduce
total = reduce(lambda a, b: a + b, [1, 2, 3, 4])
```

### Error Handling
```python
try:
    result = 10 / 0
except ZeroDivisionError as e:
    print(f"Error: {e}")
except (TypeError, ValueError) as e:
    print(f"Type/Value error: {e}")
else:
    print("No error occurred")
finally:
    print("Always runs")

# Raising exceptions
def divide(a: float, b: float) -> float:
    if b == 0:
        raise ValueError("Divisor cannot be zero")
    return a / b

# Custom exception
class AppError(Exception):
    def __init__(self, message: str, code: int = 0):
        super().__init__(message)
        self.code = code
```

### File I/O
```python
from pathlib import Path

# Reading
path = Path("data.txt")
text = path.read_text(encoding="utf-8")
lines = path.read_text().splitlines()

# Writing
path.write_text("Hello, World!", encoding="utf-8")

# Context manager (preferred for append/binary)
with open("data.txt", "a", encoding="utf-8") as f:
    f.write("New line\n")

# JSON
import json
data = {"key": "value", "nums": [1, 2, 3]}
json_str = json.dumps(data, indent=2)
parsed = json.loads(json_str)
Path("config.json").write_text(json_str)
loaded = json.loads(Path("config.json").read_text())
```

---

## 2. Moderate → Advanced

### Classes & OOP
```python
from dataclasses import dataclass, field
from typing import ClassVar

class Animal:
    species_count: ClassVar[int] = 0

    def __init__(self, name: str, sound: str):
        self.name = name
        self.sound = sound
        Animal.species_count += 1

    def __repr__(self) -> str:
        return f"Animal(name={self.name!r})"

    def __str__(self) -> str:
        return self.name

    def speak(self) -> str:
        return f"{self.name} says {self.sound}"

class Dog(Animal):
    def __init__(self, name: str, breed: str):
        super().__init__(name, sound="Woof")
        self.breed = breed

    def speak(self) -> str:           # override
        return f"{super().speak()}!"

# Dataclass — auto __init__, __repr__, __eq__
@dataclass
class Point:
    x: float
    y: float
    label: str = ""
    _cache: dict = field(default_factory=dict, repr=False)

    def distance_to(self, other: "Point") -> float:
        return ((self.x - other.x)**2 + (self.y - other.y)**2) ** 0.5

# Properties
class Temperature:
    def __init__(self, celsius: float):
        self._celsius = celsius

    @property
    def celsius(self) -> float:
        return self._celsius

    @celsius.setter
    def celsius(self, value: float) -> None:
        if value < -273.15:
            raise ValueError("Below absolute zero")
        self._celsius = value

    @property
    def fahrenheit(self) -> float:
        return self._celsius * 9/5 + 32
```

### Typing & Generics
```python
from typing import Optional, Union, Any, TypeVar, Generic
from collections.abc import Callable, Iterator, Generator, Sequence

T = TypeVar("T")

def first(items: Sequence[T]) -> Optional[T]:
    return items[0] if items else None

class Stack(Generic[T]):
    def __init__(self) -> None:
        self._items: list[T] = []

    def push(self, item: T) -> None:
        self._items.append(item)

    def pop(self) -> T:
        return self._items.pop()

    def __len__(self) -> int:
        return len(self._items)

# Union and Optional (Python 3.10+ syntax)
def parse(value: str | int | None) -> str:
    if value is None:
        return "none"
    return str(value)
```

### Iterators, Generators & Context Managers
```python
# Generator function
def fibonacci(n: int) -> Generator[int, None, None]:
    a, b = 0, 1
    for _ in range(n):
        yield a
        a, b = b, a + b

# Generator expression
gen = (x**2 for x in range(1000))  # lazy, memory-efficient

# Custom iterator
class Counter:
    def __init__(self, start: int, stop: int):
        self.current = start
        self.stop = stop

    def __iter__(self) -> "Counter":
        return self

    def __next__(self) -> int:
        if self.current >= self.stop:
            raise StopIteration
        val = self.current
        self.current += 1
        return val

# Context manager
from contextlib import contextmanager

@contextmanager
def managed_resource(name: str):
    print(f"Acquiring {name}")
    try:
        yield name
    finally:
        print(f"Releasing {name}")

# Class-based context manager
class DBConnection:
    def __enter__(self):
        print("Opening connection")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        print("Closing connection")
        return False  # do not suppress exceptions
```

### Decorators
```python
import functools
import time
from typing import Callable

# Simple decorator
def timer(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"{func.__name__} took {elapsed:.4f}s")
        return result
    return wrapper

# Decorator with arguments
def retry(times: int = 3, exceptions: tuple = (Exception,)):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, times + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == times:
                        raise
                    print(f"Attempt {attempt} failed: {e}. Retrying...")
        return wrapper
    return decorator

@retry(times=3, exceptions=(ConnectionError,))
@timer
def fetch_data(url: str) -> dict:
    ...
```

### Concurrency & Async
```python
import asyncio
from asyncio import TaskGroup
import httpx

# async / await basics
async def fetch(url: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text

# Running multiple coroutines concurrently
async def fetch_all(urls: list[str]) -> list[str]:
    async with TaskGroup() as tg:            # Python 3.11+
        tasks = [tg.create_task(fetch(url)) for url in urls]
    return [t.result() for t in tasks]

# asyncio.gather (Python 3.8+)
async def main():
    results = await asyncio.gather(
        fetch("https://example.com"),
        fetch("https://httpbin.org/get"),
        return_exceptions=True,
    )
    return results

# Async generator
async def stream_lines(path: str):
    async with await anyio.open_file(path) as f:
        async for line in f:
            yield line.strip()

# Async context manager
class AsyncDB:
    async def __aenter__(self):
        self.conn = await connect()
        return self.conn

    async def __aexit__(self, *args):
        await self.conn.close()

asyncio.run(main())
```

### Modules, Packages & Imports
```python
# Absolute import (preferred)
from pathlib import Path
from collections import defaultdict, Counter

# Relative import (inside a package)
from .config import config
from ..utils import helpers

# Conditional import
try:
    import ujson as json
except ImportError:
    import json

# __all__ controls public API
__all__ = ["MyClass", "my_function"]
```

### Environment Variables & .env
```python
import os
from dotenv import load_dotenv   # pip install python-dotenv

load_dotenv()  # loads .env from current directory

DB_URL  = os.environ["DATABASE_URL"]             # raises if missing
API_KEY = os.getenv("API_KEY", "default-value")  # safe fallback
DEBUG   = os.getenv("DEBUG", "false").lower() == "true"
```

---

## 3. Advanced → Project Level

### Project Structure (recommended)
```
my_project/
├── src/
│   └── my_package/
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       ├── models/
│       │   ├── __init__.py
│       │   └── user.py
│       ├── services/
│       │   ├── __init__.py
│       │   └── user_service.py
│       ├── repositories/
│       │   ├── __init__.py
│       │   └── user_repo.py
│       └── utils/
│           ├── __init__.py
│           └── logger.py
├── tests/
│   ├── conftest.py
│   └── test_user_service.py
├── .env
├── .env.example
├── requirements.txt
├── pyproject.toml
└── README.md
```

### Logging (production pattern)
```python
import logging
import sys
from pathlib import Path

def setup_logger(name: str, log_dir: Path = Path("logs")) -> logging.Logger:
    log_dir.mkdir(exist_ok=True)
    formatter = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    fh = logging.FileHandler(log_dir / f"{name}.log", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger

logger = setup_logger("my_app")
```

### Configuration (Pydantic Settings)
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "MyApp"
    debug: bool = False
    database_url: str
    secret_key: str
    allowed_origins: list[str] = ["http://localhost:3000"]
    max_connections: int = 10

config = Settings()   # reads .env automatically
```

### Dependency Injection Pattern
```python
from typing import Protocol

class UserRepository(Protocol):
    def get_by_id(self, user_id: int) -> dict | None: ...
    def save(self, user: dict) -> dict: ...

class UserService:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    def get_user(self, user_id: int) -> dict:
        user = self._repo.get_by_id(user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")
        return user
```

### Testing (pytest)
```python
# tests/conftest.py
import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_repo() -> MagicMock:
    repo = MagicMock()
    repo.get_by_id.return_value = {"id": 1, "name": "Alice"}
    return repo

# tests/test_user_service.py
from src.my_package.services.user_service import UserService

def test_get_user_returns_correct_user(mock_repo):
    service = UserService(repo=mock_repo)
    user = service.get_user(1)
    assert user["name"] == "Alice"
    mock_repo.get_by_id.assert_called_once_with(1)

def test_get_user_raises_when_not_found(mock_repo):
    mock_repo.get_by_id.return_value = None
    service = UserService(repo=mock_repo)
    with pytest.raises(ValueError, match="not found"):
        service.get_user(999)

# Async tests
import pytest_asyncio

@pytest.mark.asyncio
async def test_async_fetch():
    result = await some_async_function()
    assert result is not None
```

### requirements.txt (standard patterns)
```text
# Core
pydantic>=2.0
pydantic-settings>=2.0
python-dotenv>=1.0

# HTTP
httpx>=0.27
fastapi>=0.111
uvicorn[standard]>=0.29

# Database
sqlalchemy>=2.0
alembic>=1.13
asyncpg>=0.29        # PostgreSQL async
pymysql>=1.1         # MySQL
motor>=3.4           # MongoDB async

# Testing
pytest>=8.0
pytest-asyncio>=0.23
pytest-cov>=5.0

# Dev
ruff>=0.4
mypy>=1.10
```

### .env template
```env
# Application
APP_NAME=MyApp
DEBUG=false
SECRET_KEY=change-me-in-production
ALLOWED_ORIGINS=http://localhost:3000,https://myapp.com

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/mydb

# External APIs
OPENAI_API_KEY=
GOOGLE_API_KEY=

# Logging
LOG_LEVEL=INFO
LOG_DIR=logs
```
