# MongoDB Knowledge Base

---

## 1. Beginner → Moderate

### Core Concepts
| SQL Term    | MongoDB Equivalent |
|-------------|-------------------|
| Database    | Database          |
| Table       | Collection        |
| Row         | Document (BSON)   |
| Column      | Field             |
| Primary Key | `_id` field       |
| JOIN        | `$lookup` (aggregation) |
| Index       | Index             |

### BSON Types
```
String, Integer (int32/int64), Double, Boolean, Date,
ObjectId, Array, Embedded Document, Null, Binary,
Decimal128, UUID, Timestamp
```

### Connection (Python — PyMongo / Motor)
```python
# Sync — PyMongo
from pymongo import MongoClient
from pymongo.database import Database

client = MongoClient("mongodb://localhost:27017")
db: Database = client["myapp"]
users = db["users"]

# Async — Motor
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client["myapp"]
users = db["users"]

# With URI (auth + replica set)
MONGO_URI = "mongodb://user:password@host:27017/myapp?authSource=admin"
client = AsyncIOMotorClient(MONGO_URI)
```

### CRUD
```python
from bson import ObjectId
from datetime import datetime, UTC

# INSERT
result = await users.insert_one({
    "username": "alice",
    "email":    "alice@example.com",
    "role":     "user",
    "active":   True,
    "preferences": {"theme": "dark", "lang": "en"},
    "tags":     [],
    "created_at": datetime.now(UTC),
})
print(result.inserted_id)  # ObjectId

# INSERT MANY
result = await users.insert_many([
    {"username": "bob",   "email": "bob@example.com",   "role": "user"},
    {"username": "carol", "email": "carol@example.com", "role": "admin"},
])

# FIND ONE
doc = await users.find_one({"_id": ObjectId("...")})
doc = await users.find_one({"email": "alice@example.com"})

# FIND MANY
cursor = users.find({"active": True, "role": "user"})
all_users = await cursor.to_list(length=100)

# With projection (include/exclude fields)
cursor = users.find(
    {"active": True},
    {"username": 1, "email": 1, "_id": 0}   # 1=include, 0=exclude
)

# With sort + limit + skip
cursor = users.find({"active": True}).sort("created_at", -1).limit(20).skip(0)

# UPDATE ONE
result = await users.update_one(
    {"_id": ObjectId("...")},
    {"$set": {"email": "new@example.com", "updated_at": datetime.now(UTC)}}
)
print(result.modified_count)

# UPDATE MANY
await users.update_many(
    {"role": "user"},
    {"$set": {"newsletter": True}}
)

# UPSERT
await users.update_one(
    {"email": "alice@example.com"},
    {"$set": {"username": "alice", "active": True}},
    upsert=True,
)

# DELETE ONE
await users.delete_one({"_id": ObjectId("...")})

# DELETE MANY
await users.delete_many({"active": False})

# COUNT
count = await users.count_documents({"role": "admin"})

# EXISTS CHECK
exists = await users.find_one({"email": "alice@example.com"}, {"_id": 1}) is not None
```

### Query Operators
```python
from pymongo import ASCENDING, DESCENDING

# Comparison
{"age":  {"$gt": 18}}              # greater than
{"age":  {"$gte": 18}}             # >=
{"age":  {"$lt": 65}}              # <
{"age":  {"$lte": 65}}             # <=
{"age":  {"$ne": 0}}               # not equal
{"role": {"$in":  ["admin", "moderator"]}}
{"role": {"$nin": ["banned", "suspended"]}}

# Logical
{"$and": [{"active": True}, {"role": "admin"}]}
{"$or":  [{"role": "admin"}, {"role": "moderator"}]}
{"$not": {"active": True}}
{"$nor": [{"active": False}, {"deleted": True}]}

# Element
{"avatar": {"$exists": True}}
{"age":    {"$type": "int"}}

# String (Regex)
{"username": {"$regex": "^ali", "$options": "i"}}

# Array operators
{"tags": "python"}                     # contains element
{"tags": {"$all": ["python", "async"]}} # contains all
{"tags": {"$size": 3}}                 # array length
{"scores.0": {"$gt": 90}}             # index access
```

---

## 2. Moderate → Advanced

### Indexes
```python
from pymongo import ASCENDING, DESCENDING, TEXT

# Single field
await users.create_index("email", unique=True)
await users.create_index([("created_at", DESCENDING)])

# Compound
await posts.create_index([("user_id", ASCENDING), ("published", DESCENDING)])

# Text index (full-text search)
await posts.create_index([("title", TEXT), ("body", TEXT)])

# Sparse index (only documents where field exists)
await users.create_index("avatar_url", sparse=True)

# TTL index (auto-delete after N seconds)
await sessions.create_index("created_at", expireAfterSeconds=3600)

# Background creation (non-blocking)
await posts.create_index("user_id", background=True)

# List indexes
indexes = await users.list_indexes().to_list(None)

# Drop index
await users.drop_index("email_1")
```

### Update Operators
```python
# $set / $unset
{"$set":   {"name": "Alice", "updated_at": datetime.now(UTC)}}
{"$unset": {"old_field": ""}}

# $inc / $mul
{"$inc": {"views": 1, "likes": -1}}
{"$mul": {"price": 1.1}}          # multiply by 1.1

# $push / $pull / $addToSet
{"$push":     {"tags": "newTag"}}
{"$pull":     {"tags": "oldTag"}}
{"$addToSet": {"tags": "unique"}}  # push only if not exists

# $push with $each
{"$push": {"tags": {"$each": ["a", "b", "c"], "$slice": -10}}}

# Array element update (positional)
{"$set": {"scores.$": 95}}         # first matching element
{"$set": {"scores.$[]": 100}}      # all elements
{"$set": {"scores.$[elem]": 100}}  # filtered positional
```

### Aggregation Pipeline
```python
# Basic pipeline
pipeline = [
    {"$match":   {"published": True}},
    {"$sort":    {"created_at": -1}},
    {"$skip":    0},
    {"$limit":   20},
    {"$project": {"title": 1, "user_id": 1, "_id": 0}},
]
results = await posts.aggregate(pipeline).to_list(None)

# $group
pipeline = [
    {"$match": {"active": True}},
    {"$group": {
        "_id":        "$role",
        "count":      {"$sum": 1},
        "avg_posts":  {"$avg": "$post_count"},
        "usernames":  {"$push": "$username"},
    }},
    {"$sort": {"count": -1}},
]

# $lookup (JOIN equivalent)
pipeline = [
    {"$match": {"published": True}},
    {"$lookup": {
        "from":         "users",
        "localField":   "user_id",
        "foreignField": "_id",
        "as":           "author",
    }},
    {"$unwind": "$author"},
    {"$project": {
        "title":            1,
        "author.username":  1,
        "author.email":     1,
    }},
]

# $facet (multiple pipelines)
pipeline = [
    {"$facet": {
        "total":      [{"$count": "count"}],
        "by_role":    [{"$group": {"_id": "$role", "n": {"$sum": 1}}}],
        "recent":     [{"$sort": {"created_at": -1}}, {"$limit": 5}],
    }}
]

# $addFields / $set
pipeline = [
    {"$addFields": {
        "full_name": {"$concat": ["$first_name", " ", "$last_name"]},
        "age_group": {
            "$switch": {
                "branches": [
                    {"case": {"$lt": ["$age", 18]}, "then": "minor"},
                    {"case": {"$lt": ["$age", 65]}, "then": "adult"},
                ],
                "default": "senior",
            }
        }
    }}
]
```

### Transactions (multi-document)
```python
async def transfer(from_id: str, to_id: str, amount: float) -> None:
    async with await client.start_session() as session:
        async with session.start_transaction():
            await accounts.update_one(
                {"_id": ObjectId(from_id)},
                {"$inc": {"balance": -amount}},
                session=session,
            )
            await accounts.update_one(
                {"_id": ObjectId(to_id)},
                {"$inc": {"balance": amount}},
                session=session,
            )
        # auto-commits on __aexit__, auto-aborts on exception
```

---

## 3. Advanced → Project Level

### Repository Pattern
```python
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from bson import ObjectId
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, UTC
import pymongo

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

# Pydantic model
class UserDocument(BaseModel):
    id:         Optional[PyObjectId] = Field(default=None, alias="_id")
    username:   str
    email:      str
    role:       str = "user"
    active:     bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# Repository
class UserRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self._col: AsyncIOMotorCollection = db["users"]

    async def ensure_indexes(self) -> None:
        await self._col.create_index("email", unique=True)
        await self._col.create_index("username", unique=True)
        await self._col.create_index([("created_at", pymongo.DESCENDING)])

    async def insert(self, user: UserDocument) -> UserDocument:
        doc = user.model_dump(by_alias=True, exclude={"id"})
        result = await self._col.insert_one(doc)
        user.id = result.inserted_id
        return user

    async def get_by_id(self, user_id: str) -> UserDocument | None:
        doc = await self._col.find_one({"_id": ObjectId(user_id)})
        return UserDocument(**doc) if doc else None

    async def get_by_email(self, email: str) -> UserDocument | None:
        doc = await self._col.find_one({"email": email})
        return UserDocument(**doc) if doc else None

    async def list_active(self, skip: int = 0, limit: int = 50) -> list[UserDocument]:
        cursor = self._col.find({"active": True}).sort("created_at", -1).skip(skip).limit(limit)
        return [UserDocument(**doc) async for doc in cursor]

    async def deactivate(self, user_id: str) -> bool:
        result = await self._col.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"active": False}},
        )
        return result.modified_count > 0
```

### .env for MongoDB
```env
MONGO_URI=mongodb://localhost:27017
MONGO_DB=myapp
MONGO_USERNAME=myapp_user
MONGO_PASSWORD=strong_password_here
# With auth:
MONGO_URI=mongodb://myapp_user:strong_password_here@localhost:27017/myapp?authSource=admin
```

### requirements.txt for MongoDB
```text
motor>=3.4         # async MongoDB driver
pymongo>=4.7       # sync driver (also a motor dependency)
pydantic>=2.0
dnspython>=2.6     # needed for mongodb+srv:// URIs
```
