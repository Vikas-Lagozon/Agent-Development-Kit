# SQLite Knowledge Base

---

## 1. Beginner → Moderate

### What is SQLite
- Serverless, file-based relational database
- Single file (`.db` or `.sqlite`), zero configuration
- ACID-compliant, supports most SQL standard
- Best for: local apps, prototyping, embedded systems, small-to-medium applications

### Core Data Types
| SQLite Type | Typical Use |
|-------------|-------------|
| `INTEGER`   | int, bool (0/1) |
| `REAL`      | float/double |
| `TEXT`      | string / datetime as ISO string |
| `BLOB`      | binary data |
| `NULL`      | null value |

### Create & Connect (Python `sqlite3`)
```python
import sqlite3
from pathlib import Path

DB_PATH = Path("app.db")

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # rows behave like dicts
    conn.execute("PRAGMA foreign_keys = ON")  # enforce FK constraints
    conn.execute("PRAGMA journal_mode = WAL")  # better concurrency
    return conn
```

### DDL — Create Tables
```sql
-- Users table
CREATE TABLE IF NOT EXISTS users (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    username  TEXT    NOT NULL UNIQUE,
    email     TEXT    NOT NULL UNIQUE,
    password  TEXT    NOT NULL,
    role      TEXT    NOT NULL DEFAULT 'user',
    active    INTEGER NOT NULL DEFAULT 1,
    created_at TEXT   NOT NULL DEFAULT (datetime('now'))
);

-- Posts table with FK
CREATE TABLE IF NOT EXISTS posts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title      TEXT    NOT NULL,
    body       TEXT    NOT NULL DEFAULT '',
    published  INTEGER NOT NULL DEFAULT 0,
    created_at TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Index
CREATE INDEX IF NOT EXISTS idx_posts_user_id ON posts(user_id);
CREATE INDEX IF NOT EXISTS idx_posts_published ON posts(published, created_at DESC);
```

### CRUD Operations
```python
# INSERT
with get_connection() as conn:
    cursor = conn.execute(
        "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
        ("alice", "alice@example.com", "hashed_password"),
    )
    new_id = cursor.lastrowid

# INSERT OR IGNORE / INSERT OR REPLACE
conn.execute(
    "INSERT OR IGNORE INTO users (username, email, password) VALUES (?, ?, ?)",
    ("alice", "alice@example.com", "hashed_password"),
)

# SELECT
row = conn.execute("SELECT * FROM users WHERE id = ?", (1,)).fetchone()
print(dict(row))  # {'id': 1, 'username': 'alice', ...}

rows = conn.execute("SELECT * FROM users WHERE active = 1").fetchall()
for row in rows:
    print(row["username"])

# UPDATE
conn.execute(
    "UPDATE users SET email = ? WHERE id = ?",
    ("new@example.com", 1),
)

# DELETE
conn.execute("DELETE FROM users WHERE id = ?", (1,))

# executemany — bulk insert
users = [("bob", "bob@example.com", "pw"), ("carol", "carol@example.com", "pw")]
conn.executemany(
    "INSERT INTO users (username, email, password) VALUES (?, ?, ?)", users
)
```

### Querying
```sql
-- Filtering and ordering
SELECT id, username, email
FROM   users
WHERE  active = 1
  AND  role = 'admin'
ORDER  BY created_at DESC
LIMIT  20 OFFSET 0;

-- LIKE search
SELECT * FROM users WHERE username LIKE 'ali%';

-- COUNT and aggregates
SELECT COUNT(*) AS total, role FROM users GROUP BY role;
SELECT MAX(created_at) AS latest FROM posts;

-- JOIN
SELECT p.id, p.title, u.username
FROM   posts  p
JOIN   users  u ON u.id = p.user_id
WHERE  p.published = 1
ORDER  BY p.created_at DESC;

-- LEFT JOIN
SELECT u.username, COUNT(p.id) AS post_count
FROM   users u
LEFT JOIN posts p ON p.user_id = u.id
GROUP BY u.id;

-- Subquery
SELECT * FROM users
WHERE id IN (
    SELECT DISTINCT user_id FROM posts WHERE published = 1
);
```

---

## 2. Moderate → Advanced

### Transactions
```python
# Context manager auto-commits on success, rolls back on exception
with get_connection() as conn:
    conn.execute("UPDATE accounts SET balance = balance - 100 WHERE id = 1")
    conn.execute("UPDATE accounts SET balance = balance + 100 WHERE id = 2")
    # commits here automatically

# Manual transaction control
conn = get_connection()
try:
    conn.execute("BEGIN")
    conn.execute("INSERT INTO orders ...")
    conn.execute("UPDATE inventory ...")
    conn.execute("COMMIT")
except Exception:
    conn.execute("ROLLBACK")
    raise
finally:
    conn.close()
```

### Migrations (manual pattern)
```python
MIGRATIONS = [
    """
    CREATE TABLE IF NOT EXISTS schema_version (
        version INTEGER PRIMARY KEY
    );
    """,
    """
    ALTER TABLE users ADD COLUMN avatar_url TEXT;
    """,
    """
    CREATE TABLE IF NOT EXISTS tags (
        id   INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    );
    """,
]

def run_migrations(conn: sqlite3.Connection) -> None:
    conn.execute(MIGRATIONS[0])
    current = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] or 0
    for i, sql in enumerate(MIGRATIONS[1:], start=1):
        if i > current:
            conn.execute(sql)
            conn.execute("INSERT INTO schema_version (version) VALUES (?)", (i,))
            conn.commit()
```

### Full-Text Search (FTS5)
```sql
CREATE VIRTUAL TABLE posts_fts USING fts5(
    title, body,
    content='posts',
    content_rowid='id'
);

-- Rebuild index
INSERT INTO posts_fts(posts_fts) VALUES ('rebuild');

-- Search
SELECT p.*
FROM   posts p
JOIN   posts_fts f ON f.rowid = p.id
WHERE  posts_fts MATCH 'python AND async'
ORDER  BY rank;
```

### JSON Support (SQLite 3.38+)
```sql
-- Store JSON
INSERT INTO settings (user_id, preferences)
VALUES (1, '{"theme": "dark", "lang": "en"}');

-- Extract JSON field
SELECT json_extract(preferences, '$.theme') AS theme
FROM   settings
WHERE  user_id = 1;

-- JSON array operations
SELECT json_each.value
FROM   settings,
       json_each(json_extract(preferences, '$.notifications'));
```

---

## 3. Advanced → Project Level

### Repository Pattern (Python)
```python
import sqlite3
from dataclasses import dataclass
from typing import Optional
from contextlib import contextmanager

@dataclass
class User:
    id: int
    username: str
    email: str
    active: bool = True

class UserRepository:
    def __init__(self, db_path: str = "app.db"):
        self._db_path = db_path

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def create_tables(self) -> None:
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    username   TEXT NOT NULL UNIQUE,
                    email      TEXT NOT NULL UNIQUE,
                    active     INTEGER NOT NULL DEFAULT 1
                )
            """)

    def insert(self, username: str, email: str) -> User:
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO users (username, email) VALUES (?, ?)",
                (username, email),
            )
            return User(id=cur.lastrowid, username=username, email=email)

    def get_by_id(self, user_id: int) -> Optional[User]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            return User(**dict(row)) if row else None

    def list_active(self, limit: int = 100, offset: int = 0) -> list[User]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM users WHERE active = 1 ORDER BY id LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            return [User(**dict(r)) for r in rows]

    def deactivate(self, user_id: int) -> bool:
        with self._conn() as conn:
            cur = conn.execute(
                "UPDATE users SET active = 0 WHERE id = ?", (user_id,)
            )
            return cur.rowcount > 0
```

### Async SQLite (aiosqlite)
```python
import aiosqlite

async def get_user(db_path: str, user_id: int) -> dict | None:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def bulk_insert(db_path: str, users: list[tuple]) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.executemany(
            "INSERT OR IGNORE INTO users (username, email) VALUES (?, ?)", users
        )
        await db.commit()
```

### SQLite with SQLAlchemy (ORM)
```python
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import DeclarativeBase, Session

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id       = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False, unique=True)
    email    = Column(String, nullable=False, unique=True)
    active   = Column(Boolean, default=True, nullable=False)

engine = create_engine("sqlite:///app.db", echo=False)
Base.metadata.create_all(engine)

with Session(engine) as session:
    user = User(username="alice", email="alice@example.com")
    session.add(user)
    session.commit()
    session.refresh(user)
    print(user.id)
```
