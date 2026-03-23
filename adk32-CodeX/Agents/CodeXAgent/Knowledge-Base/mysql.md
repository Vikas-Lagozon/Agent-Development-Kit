# MySQL Knowledge Base

---

## 1. Beginner → Moderate

### Core Data Types
| Category | Types |
|----------|-------|
| Integer  | `TINYINT`, `SMALLINT`, `INT`, `BIGINT` |
| Float    | `FLOAT`, `DOUBLE`, `DECIMAL(p,s)` |
| String   | `CHAR(n)`, `VARCHAR(n)`, `TEXT`, `LONGTEXT` |
| Date/Time| `DATE`, `TIME`, `DATETIME`, `TIMESTAMP` |
| Binary   | `BLOB`, `LONGBLOB` |
| Other    | `BOOLEAN` (alias TINYINT(1)), `JSON`, `ENUM(...)` |

### DDL — Create Database & Tables
```sql
CREATE DATABASE IF NOT EXISTS myapp
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE myapp;

CREATE TABLE IF NOT EXISTS users (
    id         INT          UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    username   VARCHAR(50)  NOT NULL,
    email      VARCHAR(255) NOT NULL,
    password   VARCHAR(255) NOT NULL,
    role       ENUM('user','admin','moderator') NOT NULL DEFAULT 'user',
    active     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
                            ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_users_username (username),
    UNIQUE KEY uq_users_email    (email),
    INDEX      idx_users_role    (role),
    INDEX      idx_users_active  (active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS posts (
    id         INT      UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id    INT      UNSIGNED NOT NULL,
    title      VARCHAR(500) NOT NULL,
    body       LONGTEXT,
    published  BOOLEAN  NOT NULL DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_posts_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_posts_user_id   (user_id),
    INDEX idx_posts_published (published, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### CRUD
```sql
-- INSERT
INSERT INTO users (username, email, password) VALUES
    ('alice', 'alice@example.com', 'hashed_pw');

-- INSERT ... ON DUPLICATE KEY UPDATE (upsert)
INSERT INTO users (username, email, password)
VALUES ('alice', 'alice@example.com', 'new_pw')
ON DUPLICATE KEY UPDATE password = VALUES(password);

-- SELECT
SELECT id, username, email
FROM   users
WHERE  active = TRUE
  AND  role = 'admin'
ORDER  BY created_at DESC
LIMIT  20 OFFSET 0;

-- UPDATE
UPDATE users
SET    email = 'new@example.com', updated_at = NOW()
WHERE  id = 1;

-- DELETE
DELETE FROM users WHERE id = 1;

-- TRUNCATE (fast, non-transactional)
TRUNCATE TABLE logs;
```

### Joins & Aggregates
```sql
-- INNER JOIN
SELECT p.id, p.title, u.username
FROM   posts  p
INNER  JOIN users u ON u.id = p.user_id
WHERE  p.published = TRUE
ORDER  BY p.created_at DESC;

-- LEFT JOIN with count
SELECT u.id, u.username, COUNT(p.id) AS post_count
FROM   users u
LEFT   JOIN posts p ON p.user_id = u.id
GROUP  BY u.id, u.username
HAVING post_count > 0
ORDER  BY post_count DESC;

-- Aggregate functions
SELECT
    role,
    COUNT(*)        AS total,
    SUM(active)     AS active_count,
    MIN(created_at) AS first_joined
FROM users
GROUP BY role;

-- DISTINCT
SELECT DISTINCT role FROM users;
```

---

## 2. Moderate → Advanced

### Indexes & Performance
```sql
-- Composite index
CREATE INDEX idx_posts_user_published ON posts(user_id, published, created_at DESC);

-- Full-text index
ALTER TABLE posts ADD FULLTEXT INDEX ft_posts_content (title, body);

-- Full-text search
SELECT * FROM posts
WHERE MATCH(title, body) AGAINST('python async' IN BOOLEAN MODE);

-- EXPLAIN query
EXPLAIN SELECT * FROM posts WHERE user_id = 1 AND published = TRUE;

-- Show indexes
SHOW INDEX FROM posts;

-- Drop index
DROP INDEX idx_posts_user_published ON posts;
```

### Stored Procedures
```sql
DELIMITER $$

CREATE PROCEDURE get_user_stats(IN p_user_id INT, OUT p_post_count INT)
BEGIN
    SELECT COUNT(*) INTO p_post_count
    FROM   posts
    WHERE  user_id = p_user_id AND published = TRUE;
END$$

DELIMITER ;

-- Call
CALL get_user_stats(1, @count);
SELECT @count;
```

### Views
```sql
CREATE OR REPLACE VIEW active_user_posts AS
SELECT
    u.id        AS user_id,
    u.username,
    p.id        AS post_id,
    p.title,
    p.created_at
FROM   users u
JOIN   posts  p ON p.user_id = u.id
WHERE  u.active = TRUE AND p.published = TRUE;

-- Query the view
SELECT * FROM active_user_posts WHERE username = 'alice';
```

### Transactions
```sql
START TRANSACTION;

UPDATE accounts SET balance = balance - 500 WHERE id = 1;
UPDATE accounts SET balance = balance + 500 WHERE id = 2;

-- Check for error
-- On success:
COMMIT;
-- On error:
ROLLBACK;
```

```python
# Python transaction with PyMySQL
import pymysql

conn = pymysql.connect(host="localhost", user="root", password="pw", db="myapp")
try:
    with conn.cursor() as cur:
        cur.execute("UPDATE accounts SET balance = balance - %s WHERE id = %s", (500, 1))
        cur.execute("UPDATE accounts SET balance = balance + %s WHERE id = %s", (500, 2))
    conn.commit()
except Exception:
    conn.rollback()
    raise
finally:
    conn.close()
```

### JSON Column
```sql
ALTER TABLE users ADD COLUMN preferences JSON;

-- Insert JSON
UPDATE users SET preferences = '{"theme":"dark","lang":"en"}' WHERE id = 1;

-- Extract
SELECT JSON_EXTRACT(preferences, '$.theme') AS theme FROM users WHERE id = 1;
-- Shorthand:
SELECT preferences->>'$.theme' AS theme FROM users WHERE id = 1;

-- Modify
UPDATE users
SET preferences = JSON_SET(preferences, '$.notifications', TRUE)
WHERE id = 1;

-- Search inside JSON array
SELECT * FROM users WHERE JSON_CONTAINS(preferences->'$.roles', '"admin"');
```

### Window Functions (MySQL 8+)
```sql
-- ROW_NUMBER
SELECT
    id, username, created_at,
    ROW_NUMBER() OVER (ORDER BY created_at) AS row_num
FROM users;

-- RANK per group
SELECT
    user_id, title, created_at,
    RANK() OVER (PARTITION BY user_id ORDER BY created_at DESC) AS rk
FROM posts;

-- Running total
SELECT
    id, amount, created_at,
    SUM(amount) OVER (ORDER BY created_at ROWS UNBOUNDED PRECEDING) AS running_total
FROM transactions;

-- LAG / LEAD
SELECT
    id, amount,
    LAG(amount)  OVER (ORDER BY created_at) AS prev_amount,
    LEAD(amount) OVER (ORDER BY created_at) AS next_amount
FROM transactions;
```

---

## 3. Advanced → Project Level

### Python — SQLAlchemy 2.x (Async, ORM)
```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, ForeignKey, func
from datetime import datetime

DATABASE_URL = "mysql+aiomysql://user:password@localhost:3306/myapp"

engine = create_async_engine(DATABASE_URL, echo=False, pool_size=10, max_overflow=20)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id:         Mapped[int]      = mapped_column(primary_key=True, autoincrement=True)
    username:   Mapped[str]      = mapped_column(String(50), unique=True, nullable=False)
    email:      Mapped[str]      = mapped_column(String(255), unique=True, nullable=False)
    active:     Mapped[bool]     = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    posts: Mapped[list["Post"]] = relationship("Post", back_populates="author", cascade="all, delete-orphan")

class Post(Base):
    __tablename__ = "posts"

    id:        Mapped[int]  = mapped_column(primary_key=True, autoincrement=True)
    user_id:   Mapped[int]  = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title:     Mapped[str]  = mapped_column(String(500), nullable=False)
    published: Mapped[bool] = mapped_column(Boolean, default=False)

    author: Mapped["User"] = relationship("User", back_populates="posts")

# Usage
async def create_user(username: str, email: str) -> User:
    async with AsyncSessionLocal() as session:
        user = User(username=username, email=email)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user
```

### Repository Pattern
```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

class UserRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, user_id: int) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def list_active(self, limit: int = 50, offset: int = 0) -> list[User]:
        result = await self._session.execute(
            select(User).where(User.active == True).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def deactivate(self, user_id: int) -> bool:
        user = await self.get_by_id(user_id)
        if not user:
            return False
        user.active = False
        await self._session.commit()
        return True
```

### .env for MySQL
```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=myapp_user
MYSQL_PASSWORD=strong_password_here
MYSQL_DATABASE=myapp
DATABASE_URL=mysql+aiomysql://${MYSQL_USER}:${MYSQL_PASSWORD}@${MYSQL_HOST}:${MYSQL_PORT}/${MYSQL_DATABASE}
POOL_SIZE=10
MAX_OVERFLOW=20
```

### requirements.txt for MySQL
```text
sqlalchemy>=2.0
aiomysql>=0.2       # async MySQL driver
pymysql>=1.1        # sync MySQL driver
alembic>=1.13       # migrations
```
