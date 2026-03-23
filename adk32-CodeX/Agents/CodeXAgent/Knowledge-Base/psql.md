# PostgreSQL Knowledge Base

---

## 1. Beginner → Moderate

### Core Data Types
| Category  | Types |
|-----------|-------|
| Integer   | `SMALLINT`, `INTEGER`, `BIGINT`, `SERIAL`, `BIGSERIAL` |
| Float     | `REAL`, `DOUBLE PRECISION`, `NUMERIC(p,s)` |
| String    | `CHAR(n)`, `VARCHAR(n)`, `TEXT` |
| Date/Time | `DATE`, `TIME`, `TIMESTAMP`, `TIMESTAMPTZ`, `INTERVAL` |
| Boolean   | `BOOLEAN` (true/false) |
| UUID      | `UUID` |
| JSON      | `JSON`, `JSONB` (indexed, preferred) |
| Array     | `INTEGER[]`, `TEXT[]` |
| Other     | `BYTEA`, `INET`, `CIDR`, `TSVECTOR` |

### DDL — Create Tables
```sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- for gen_random_uuid()

CREATE TABLE IF NOT EXISTS users (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    username    VARCHAR(50)  NOT NULL,
    email       VARCHAR(255) NOT NULL,
    password    TEXT         NOT NULL,
    role        TEXT         NOT NULL DEFAULT 'user'
                             CHECK (role IN ('user', 'admin', 'moderator')),
    active      BOOLEAN      NOT NULL DEFAULT TRUE,
    preferences JSONB        NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_users_username UNIQUE (username),
    CONSTRAINT uq_users_email    UNIQUE (email)
);

CREATE TABLE IF NOT EXISTS posts (
    id         BIGSERIAL    PRIMARY KEY,
    user_id    UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title      VARCHAR(500) NOT NULL,
    body       TEXT         NOT NULL DEFAULT '',
    tags       TEXT[]       NOT NULL DEFAULT '{}',
    published  BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_posts_user_id   ON posts(user_id);
CREATE INDEX IF NOT EXISTS idx_posts_tags      ON posts USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_users_prefs     ON users USING GIN(preferences);
CREATE INDEX IF NOT EXISTS idx_posts_published ON posts(published, created_at DESC)
    WHERE published = TRUE;

-- Auto-update updated_at via trigger
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE OR REPLACE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

### CRUD
```sql
-- INSERT ... RETURNING
INSERT INTO users (username, email, password)
VALUES ('alice', 'alice@example.com', 'hashed_pw')
RETURNING id, username, created_at;

-- UPSERT (INSERT ... ON CONFLICT)
INSERT INTO users (username, email, password)
VALUES ('alice', 'alice@example.com', 'new_pw')
ON CONFLICT (username)
DO UPDATE SET password = EXCLUDED.password, updated_at = NOW()
RETURNING *;

-- SELECT
SELECT id, username, email
FROM   users
WHERE  active = TRUE
  AND  role = 'admin'
ORDER  BY created_at DESC
LIMIT  20 OFFSET 0;

-- UPDATE ... RETURNING
UPDATE users
SET    email = 'new@example.com'
WHERE  id = '...'
RETURNING id, email, updated_at;

-- DELETE ... RETURNING
DELETE FROM users WHERE id = '...' RETURNING id;
```

### Joins & Aggregates
```sql
-- JOIN with array column
SELECT p.id, p.title, u.username, p.tags
FROM   posts p
JOIN   users u ON u.id = p.user_id
WHERE  p.published = TRUE
  AND  'python' = ANY(p.tags)
ORDER  BY p.created_at DESC;

-- GROUP BY with HAVING
SELECT u.id, u.username, COUNT(p.id) AS post_count
FROM   users u
LEFT   JOIN posts p ON p.user_id = u.id AND p.published = TRUE
GROUP  BY u.id, u.username
HAVING COUNT(p.id) > 5
ORDER  BY post_count DESC;

-- ARRAY aggregation
SELECT user_id, ARRAY_AGG(title ORDER BY created_at) AS all_titles
FROM   posts
GROUP  BY user_id;
```

---

## 2. Moderate → Advanced

### JSONB Queries
```sql
-- Access field
SELECT preferences->>'theme' AS theme FROM users;
SELECT preferences->'notifications'->>'email' AS email_notifs FROM users;

-- Filter by JSONB key/value
SELECT * FROM users WHERE preferences @> '{"theme": "dark"}';
SELECT * FROM users WHERE preferences ? 'notifications';

-- Modify JSONB
UPDATE users
SET preferences = preferences || '{"theme": "light"}'
WHERE id = '...';

UPDATE users
SET preferences = jsonb_set(preferences, '{notifications,email}', 'true')
WHERE id = '...';

-- Remove key
UPDATE users
SET preferences = preferences - 'old_key'
WHERE id = '...';
```

### Full-Text Search
```sql
-- Add tsvector column
ALTER TABLE posts ADD COLUMN search_vector TSVECTOR;

-- Populate
UPDATE posts
SET search_vector = to_tsvector('english', title || ' ' || body);

-- Create GIN index
CREATE INDEX idx_posts_fts ON posts USING GIN(search_vector);

-- Search
SELECT id, title, ts_rank(search_vector, query) AS rank
FROM   posts, to_tsquery('english', 'python & async') query
WHERE  search_vector @@ query
ORDER  BY rank DESC;

-- Auto-update via trigger
CREATE OR REPLACE FUNCTION posts_search_vector_trigger()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.search_vector = to_tsvector('english', NEW.title || ' ' || NEW.body);
    RETURN NEW;
END;
$$;

CREATE OR REPLACE TRIGGER trg_posts_search_vector
    BEFORE INSERT OR UPDATE ON posts
    FOR EACH ROW EXECUTE FUNCTION posts_search_vector_trigger();
```

### CTEs & Window Functions
```sql
-- CTE (Common Table Expression)
WITH active_authors AS (
    SELECT id, username
    FROM   users
    WHERE  active = TRUE AND role = 'user'
),
post_counts AS (
    SELECT user_id, COUNT(*) AS cnt
    FROM   posts WHERE published = TRUE
    GROUP  BY user_id
)
SELECT a.username, COALESCE(p.cnt, 0) AS published_posts
FROM   active_authors a
LEFT   JOIN post_counts p ON p.user_id = a.id
ORDER  BY published_posts DESC;

-- Recursive CTE (hierarchy/tree)
WITH RECURSIVE category_tree AS (
    SELECT id, name, parent_id, 0 AS depth
    FROM   categories WHERE parent_id IS NULL
    UNION ALL
    SELECT c.id, c.name, c.parent_id, ct.depth + 1
    FROM   categories c
    JOIN   category_tree ct ON ct.id = c.parent_id
)
SELECT * FROM category_tree ORDER BY depth, name;

-- Window functions
SELECT
    id, user_id, amount, created_at,
    SUM(amount)   OVER (PARTITION BY user_id ORDER BY created_at) AS running_total,
    AVG(amount)   OVER (PARTITION BY user_id)                    AS user_avg,
    ROW_NUMBER()  OVER (PARTITION BY user_id ORDER BY created_at DESC) AS rn,
    LAG(amount)   OVER (PARTITION BY user_id ORDER BY created_at)      AS prev_amount
FROM transactions;

-- DISTINCT ON (PostgreSQL-specific)
SELECT DISTINCT ON (user_id)
    user_id, id AS latest_post_id, title, created_at
FROM   posts
ORDER  BY user_id, created_at DESC;
```

### Partitioning (Table Inheritance)
```sql
-- Range-partitioned table
CREATE TABLE events (
    id         BIGSERIAL,
    user_id    UUID NOT NULL,
    event_type TEXT NOT NULL,
    payload    JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);

CREATE TABLE events_2024 PARTITION OF events
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

CREATE TABLE events_2025 PARTITION OF events
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
```

---

## 3. Advanced → Project Level

### Python — asyncpg (low-level, fast)
```python
import asyncpg
from contextlib import asynccontextmanager

@asynccontextmanager
async def get_pool(dsn: str):
    pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)
    try:
        yield pool
    finally:
        await pool.close()

async def get_user(pool: asyncpg.Pool, user_id: str) -> dict | None:
    row = await pool.fetchrow(
        "SELECT id, username, email FROM users WHERE id = $1", user_id
    )
    return dict(row) if row else None

async def create_user(pool: asyncpg.Pool, username: str, email: str) -> dict:
    row = await pool.fetchrow(
        "INSERT INTO users (username, email, password) VALUES ($1, $2, $3) RETURNING *",
        username, email, "placeholder",
    )
    return dict(row)
```

### Python — SQLAlchemy 2.x Async ORM
```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy import String, Boolean, Text, ForeignKey, func
import uuid
from datetime import datetime

DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/myapp"

engine = create_async_engine(DATABASE_URL, echo=False, pool_size=10)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id:          Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username:    Mapped[str]        = mapped_column(String(50), unique=True, nullable=False)
    email:       Mapped[str]        = mapped_column(String(255), unique=True, nullable=False)
    preferences: Mapped[dict]       = mapped_column(JSONB, default=dict, nullable=False)
    active:      Mapped[bool]       = mapped_column(Boolean, default=True, nullable=False)
    created_at:  Mapped[datetime]   = mapped_column(server_default=func.now())

    posts: Mapped[list["Post"]] = relationship("Post", back_populates="author", cascade="all, delete-orphan")

class Post(Base):
    __tablename__ = "posts"

    id:        Mapped[int]       = mapped_column(primary_key=True, autoincrement=True)
    user_id:   Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    title:     Mapped[str]       = mapped_column(String(500), nullable=False)
    body:      Mapped[str]       = mapped_column(Text, default="")
    tags:      Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    published: Mapped[bool]      = mapped_column(Boolean, default=False)

    author: Mapped["User"] = relationship("User", back_populates="posts")
```

### Alembic Migrations
```python
# alembic/env.py (key section)
from src.models import Base
target_metadata = Base.metadata

# Generate migration
# alembic revision --autogenerate -m "add_avatar_url_to_users"

# alembic/versions/xxxx_add_avatar_url.py
def upgrade() -> None:
    op.add_column("users", sa.Column("avatar_url", sa.Text(), nullable=True))

def downgrade() -> None:
    op.drop_column("users", "avatar_url")
```

### .env for PostgreSQL
```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=myapp_user
POSTGRES_PASSWORD=strong_password_here
POSTGRES_DB=myapp
DATABASE_URL=postgresql+asyncpg://myapp_user:strong_password_here@localhost:5432/myapp
POOL_SIZE=10
MAX_OVERFLOW=20
```

### requirements.txt for PostgreSQL
```text
sqlalchemy>=2.0
asyncpg>=0.29        # async PostgreSQL driver
psycopg2-binary>=2.9 # sync driver (for alembic)
alembic>=1.13
```
