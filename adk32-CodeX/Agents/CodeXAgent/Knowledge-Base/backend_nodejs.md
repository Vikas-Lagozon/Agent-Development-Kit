# Node.js Backend Architecture — Real-World Production Guide (TypeScript)

> Complete REST API in **TypeScript**, using **jsonwebtoken** (manual JWT), **MySQL as default database**, all credentials from `.env`, Sequelize ORM, Mongoose for MongoDB, and full Dynamic RBAC.

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Project Structure](#project-structure)
3. [Environment Setup](#environment-setup)
4. [TypeScript Configuration](#typescript-configuration)
5. [Database Configuration](#database-configuration)
6. [Models (TypeScript + Sequelize)](#models-typescript--sequelize)
7. [JWT Utilities](#jwt-utilities)
8. [Auth Middleware](#auth-middleware)
9. [Authentication Controller & Routes](#authentication-controller--routes)
10. [CRUD Controllers & Routes](#crud-controllers--routes)
11. [MongoDB Model (Mongoose + TS)](#mongodb-model-mongoose--ts)
12. [Error Handling](#error-handling)
13. [Server Entry Point](#server-entry-point)
14. [Database Switching Guide](#database-switching-guide)
15. [API Endpoint Summary](#api-endpoint-summary)

---

## Project Overview

- **TypeScript** throughout — all `.ts` files, strict mode enabled
- **jsonwebtoken** for manual JWT (no Passport, no express-jwt)
- **MySQL** as default SQL database (Sequelize dialect switch via `.env`)
- All secrets and DB credentials from `.env`
- Mongoose + TypeScript for MongoDB activity logs
- Full Dynamic RBAC: Permission → Role → RolePermission → UserRole

---

## Project Structure

```
nodejs_project/
├── src/
│   ├── config/
│   │   ├── database.ts         # Sequelize config (MySQL default)
│   │   ├── mongo.ts            # Mongoose connection
│   │   └── env.ts              # Typed .env loader
│   │
│   ├── models/                 # Sequelize models (TypeScript)
│   │   ├── index.ts            # Model loader + associations
│   │   ├── User.ts
│   │   ├── Role.ts
│   │   ├── Permission.ts
│   │   ├── RolePermission.ts
│   │   ├── UserRole.ts
│   │   └── TokenBlacklist.ts
│   │
│   ├── mongo_models/
│   │   └── UserActivity.ts     # Mongoose schema (TypeScript)
│   │
│   ├── controllers/
│   │   ├── auth.controller.ts
│   │   ├── user.controller.ts
│   │   ├── role.controller.ts
│   │   └── permission.controller.ts
│   │
│   ├── services/
│   │   ├── auth.service.ts
│   │   ├── user.service.ts
│   │   └── role.service.ts
│   │
│   ├── routes/
│   │   ├── index.ts
│   │   ├── auth.routes.ts
│   │   ├── user.routes.ts
│   │   ├── role.routes.ts
│   │   └── permission.routes.ts
│   │
│   ├── middleware/
│   │   ├── authenticate.ts     # jwt_required (matches spec pattern)
│   │   ├── authorize.ts        # RBAC guards
│   │   └── errorHandler.ts
│   │
│   ├── utils/
│   │   ├── jwt.ts              # Token create / decode helpers
│   │   └── response.ts
│   │
│   ├── types/
│   │   ├── express.d.ts        # Extend Express Request
│   │   └── jwt.types.ts
│   │
│   └── app.ts
│
├── dist/                       # Compiled JS output
├── .env
├── .env.example
├── package.json
├── tsconfig.json
├── server.ts
└── README.md   # Complete information about setup and execution.
```

---

## Environment Setup

### package.json

```json
{
  "name": "nodejs-rbac-api",
  "version": "1.0.0",
  "scripts": {
    "dev":   "ts-node-dev --respawn --transpile-only src/server.ts",
    "build": "tsc",
    "start": "node dist/server.js",
    "migrate": "npx sequelize-cli db:migrate",
    "seed":    "npx sequelize-cli db:seed:all"
  },
  "dependencies": {
    "express":          "^4.19.2",
    "sequelize":        "^6.37.3",
    "mysql2":           "^3.10.1",
    "pg":               "^8.12.0",
    "pg-hstore":        "^2.3.4",
    "sqlite3":          "^5.1.7",
    "mongoose":         "^8.5.1",
    "jsonwebtoken":     "^9.0.2",
    "bcryptjs":         "^2.4.3",
    "dotenv":           "^16.4.5",
    "cors":             "^2.8.5",
    "helmet":           "^7.1.0",
    "morgan":           "^1.10.0",
    "express-rate-limit": "^7.3.1",
    "uuid":             "^10.0.0"
  },
  "devDependencies": {
    "typescript":        "^5.5.3",
    "ts-node-dev":       "^2.0.0",
    "ts-node":           "^10.9.2",
    "@types/express":    "^4.17.21",
    "@types/jsonwebtoken": "^9.0.6",
    "@types/bcryptjs":   "^2.4.6",
    "@types/cors":       "^2.8.17",
    "@types/morgan":     "^1.9.9",
    "@types/uuid":       "^10.0.0",
    "@types/node":       "^20.14.12",
    "sequelize-cli":     "^6.6.2"
  }
}
```

### .env

```env
# ─── App ─────────────────────────────────────────────────────────────────────
NODE_ENV=development
PORT=3000
APP_NAME="Node.js RBAC API"

# ─── JWT (jsonwebtoken) ───────────────────────────────────────────────────────
JWT_SECRET=change-this-jwt-secret-min-64-random-chars
JWT_REFRESH_SECRET=change-this-refresh-secret-min-64-random-chars
JWT_ACCESS_EXPIRES_IN=1h
JWT_REFRESH_EXPIRES_IN=30d

# ─── MySQL (Default Database) ────────────────────────────────────────────────
DB_DIALECT=mysql
DB_HOST=localhost
DB_PORT=3306
DB_NAME=nodejs_rbac_db
DB_USER=root
DB_PASSWORD=yourpassword

# ─── Switch to SQLite (change DB_DIALECT + DB_STORAGE) ───────────────────────
# DB_DIALECT=sqlite
# DB_STORAGE=./dev.db

# ─── Switch to PostgreSQL (change DB_DIALECT) ────────────────────────────────
# DB_DIALECT=postgres
# DB_HOST=localhost
# DB_PORT=5432
# DB_NAME=nodejs_rbac_db
# DB_USER=postgres
# DB_PASSWORD=yourpassword

# ─── MongoDB ─────────────────────────────────────────────────────────────────
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DB=nodejs_rbac_db
# MONGO_USER=mongouser
# MONGO_PASSWORD=mongopassword

# ─── CORS ────────────────────────────────────────────────────────────────────
CORS_ORIGIN=http://localhost:3000,http://localhost:5173
```

### .env.example

```env
NODE_ENV=development
PORT=3000
JWT_SECRET=changeme
JWT_REFRESH_SECRET=changeme
JWT_ACCESS_EXPIRES_IN=1h
JWT_REFRESH_EXPIRES_IN=30d
DB_DIALECT=mysql
DB_HOST=localhost
DB_PORT=3306
DB_NAME=nodejs_rbac_db
DB_USER=root
DB_PASSWORD=
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DB=nodejs_rbac_db
CORS_ORIGIN=http://localhost:3000
```

---

## TypeScript Configuration

### tsconfig.json

```json
{
  "compilerOptions": {
    "target":           "ES2022",
    "module":           "CommonJS",
    "lib":              ["ES2022"],
    "outDir":           "./dist",
    "rootDir":          "./src",
    "strict":           true,
    "esModuleInterop":  true,
    "resolveJsonModule": true,
    "skipLibCheck":     true,
    "baseUrl":          "./src",
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

### src/types/express.d.ts

```typescript
import { UserInstance } from "../models/User";

declare global {
  namespace Express {
    interface Request {
      user?:         UserInstance;
      tokenPayload?: Record<string, unknown>;
    }
  }
}
```

---

## Database Configuration

### src/config/env.ts

```typescript
import dotenv from "dotenv";
dotenv.config();

export const env = {
  NODE_ENV:    process.env.NODE_ENV    || "development",
  PORT:        parseInt(process.env.PORT || "3000"),
  APP_NAME:    process.env.APP_NAME    || "Node.js RBAC API",

  // JWT — read from .env
  JWT_SECRET:          process.env.JWT_SECRET          || "",
  JWT_REFRESH_SECRET:  process.env.JWT_REFRESH_SECRET  || "",
  JWT_ACCESS_EXPIRES:  process.env.JWT_ACCESS_EXPIRES_IN  || "1h",
  JWT_REFRESH_EXPIRES: process.env.JWT_REFRESH_EXPIRES_IN || "30d",

  // Database — read from .env
  DB_DIALECT:  (process.env.DB_DIALECT  || "mysql") as "mysql" | "postgres" | "sqlite",
  DB_HOST:     process.env.DB_HOST     || "localhost",
  DB_PORT:     parseInt(process.env.DB_PORT || "3306"),
  DB_NAME:     process.env.DB_NAME     || "nodejs_rbac_db",
  DB_USER:     process.env.DB_USER     || "root",
  DB_PASSWORD: process.env.DB_PASSWORD || "",
  DB_STORAGE:  process.env.DB_STORAGE  || "./dev.db",

  // MongoDB — read from .env
  MONGO_HOST:     process.env.MONGO_HOST     || "localhost",
  MONGO_PORT:     parseInt(process.env.MONGO_PORT || "27017"),
  MONGO_DB:       process.env.MONGO_DB       || "nodejs_rbac_db",
  MONGO_USER:     process.env.MONGO_USER,
  MONGO_PASSWORD: process.env.MONGO_PASSWORD,

  // CORS
  CORS_ORIGIN: (process.env.CORS_ORIGIN || "http://localhost:3000").split(","),
};

// Guard: fail fast if JWT secrets are missing
if (!env.JWT_SECRET || !env.JWT_REFRESH_SECRET) {
  throw new Error("JWT_SECRET and JWT_REFRESH_SECRET must be set in .env");
}
```

### src/config/database.ts

```typescript
import { Options, Dialect } from "sequelize";
import { env } from "./env";

const dbConfig: Options = (() => {
  const base: Options = {
    dialect:  env.DB_DIALECT as Dialect,
    logging:  env.NODE_ENV === "development" ? console.log : false,
    pool:     { max: 10, min: 2, acquire: 30000, idle: 10000 },
  };

  if (env.DB_DIALECT === "sqlite") {
    return { ...base, storage: env.DB_STORAGE };
  }

  return {
    ...base,
    host:     env.DB_HOST,
    port:     env.DB_PORT,
    database: env.DB_NAME,
    username: env.DB_USER,
    password: env.DB_PASSWORD,
    // MySQL-specific
    ...(env.DB_DIALECT === "mysql" && {
      dialectOptions: {
        charset:        "utf8mb4",
        connectTimeout: 60000,
      },
      define: { charset: "utf8mb4" },
    }),
    // PostgreSQL-specific
    ...(env.DB_DIALECT === "postgres" && {
      dialectOptions: {
        ssl: env.NODE_ENV === "production"
          ? { require: true, rejectUnauthorized: false }
          : false,
      },
    }),
  };
})();

export default dbConfig;
```

### src/config/mongo.ts

```typescript
import mongoose from "mongoose";
import { env } from "./env";

function buildMongoUri(): string {
  const { MONGO_USER, MONGO_PASSWORD, MONGO_HOST, MONGO_PORT, MONGO_DB } = env;
  if (MONGO_USER && MONGO_PASSWORD) {
    return `mongodb://${MONGO_USER}:${MONGO_PASSWORD}@${MONGO_HOST}:${MONGO_PORT}/${MONGO_DB}`;
  }
  return `mongodb://${MONGO_HOST}:${MONGO_PORT}/${MONGO_DB}`;
}

export async function connectMongo(): Promise<void> {
  await mongoose.connect(buildMongoUri(), {
    maxPoolSize:              10,
    serverSelectionTimeoutMS: 5000,
  });
  console.log("✅ MongoDB connected");
}

mongoose.connection.on("error", (err) => console.error("MongoDB error:", err));
```

---

## Models (TypeScript + Sequelize)

### src/models/index.ts

```typescript
import { Sequelize } from "sequelize";
import dbConfig from "../config/database";

import defineUser,           { UserInstance }          from "./User";
import defineRole,           { RoleInstance }          from "./Role";
import definePermission,     { PermissionInstance }    from "./Permission";
import defineRolePermission, { RolePermissionInstance } from "./RolePermission";
import defineUserRole,       { UserRoleInstance }      from "./UserRole";
import defineTokenBlacklist, { TokenBlacklistInstance } from "./TokenBlacklist";

const sequelize = new Sequelize(dbConfig);

const User           = defineUser(sequelize);
const Role           = defineRole(sequelize);
const Permission     = definePermission(sequelize);
const RolePermission = defineRolePermission(sequelize);
const UserRole       = defineUserRole(sequelize);
const TokenBlacklist = defineTokenBlacklist(sequelize);

// Role ↔ Permission (through RolePermission)
Role.belongsToMany(Permission, { through: RolePermission, foreignKey: "roleId",       otherKey: "permissionId", as: "permissions" });
Permission.belongsToMany(Role, { through: RolePermission, foreignKey: "permissionId", otherKey: "roleId",       as: "roles" });

// User ↔ Role (through UserRole)
User.belongsToMany(Role, { through: UserRole, foreignKey: "userId", otherKey: "roleId", as: "roles" });
Role.belongsToMany(User, { through: UserRole, foreignKey: "roleId", otherKey: "userId", as: "users" });

export { sequelize, User, Role, Permission, RolePermission, UserRole, TokenBlacklist };
export type { UserInstance, RoleInstance, PermissionInstance, RolePermissionInstance, UserRoleInstance, TokenBlacklistInstance };
```

### src/models/User.ts

```typescript
import {
  DataTypes, Model, Optional, Sequelize, Association,
} from "sequelize";
import bcrypt from "bcryptjs";
import { RoleInstance } from "./Role";

interface UserAttributes {
  id:           number;
  username:     string;
  email:        string;
  passwordHash: string;
  firstName?:   string;
  lastName?:    string;
  isActive:     boolean;
  isVerified:   boolean;
  lastLogin?:   Date;
  createdAt?:   Date;
  updatedAt?:   Date;
}

interface UserCreationAttributes extends Optional<UserAttributes, "id" | "isActive" | "isVerified"> {}

export class UserInstance extends Model<UserAttributes, UserCreationAttributes>
  implements UserAttributes {
  declare id:           number;
  declare username:     string;
  declare email:        string;
  declare passwordHash: string;
  declare firstName:    string | undefined;
  declare lastName:     string | undefined;
  declare isActive:     boolean;
  declare isVerified:   boolean;
  declare lastLogin:    Date | undefined;
  declare createdAt:    Date;
  declare updatedAt:    Date;

  // Eager-loaded associations
  declare roles?: RoleInstance[];

  static associations: {
    roles: Association<UserInstance, RoleInstance>;
  };

  async verifyPassword(plain: string): Promise<boolean> {
    return bcrypt.compare(plain, this.passwordHash);
  }

  async getAllPermissions(): Promise<Set<string>> {
    const roles = (this.roles ?? await (this as any).getRoles({ include: ["permissions"] })) as RoleInstance[];
    const perms = new Set<string>();
    for (const role of roles) {
      const permissions = (role as any).permissions ?? [];
      for (const perm of permissions) {
        perms.add(`${perm.resource}:${perm.action}`);
      }
    }
    return perms;
  }

  async hasPermission(resource: string, action: string): Promise<boolean> {
    const perms = await this.getAllPermissions();
    return perms.has(`${resource}:${action}`);
  }

  async hasRole(roleName: string): Promise<boolean> {
    const roles = (this.roles ?? await (this as any).getRoles()) as RoleInstance[];
    return roles.some((r) => r.name === roleName);
  }

  toJSON(): Record<string, unknown> {
    const values = super.toJSON() as Record<string, unknown>;
    delete values["passwordHash"];
    return values;
  }
}

export default function defineUser(sequelize: Sequelize) {
  UserInstance.init(
    {
      id:           { type: DataTypes.INTEGER, autoIncrement: true, primaryKey: true },
      username:     { type: DataTypes.STRING(80),  allowNull: false, unique: true },
      email:        { type: DataTypes.STRING(120), allowNull: false, unique: true },
      passwordHash: { type: DataTypes.STRING(255), allowNull: false, field: "password_hash" },
      firstName:    { type: DataTypes.STRING(80),  field: "first_name" },
      lastName:     { type: DataTypes.STRING(80),  field: "last_name" },
      isActive:     { type: DataTypes.BOOLEAN, defaultValue: true,  field: "is_active" },
      isVerified:   { type: DataTypes.BOOLEAN, defaultValue: false, field: "is_verified" },
      lastLogin:    { type: DataTypes.DATE, field: "last_login" },
    },
    {
      sequelize,
      tableName:  "users",
      timestamps: true,
      createdAt:  "created_at",
      updatedAt:  "updated_at",
      hooks: {
        beforeCreate: async (user) => {
          user.passwordHash = await bcrypt.hash(user.passwordHash, 12);
        },
        beforeUpdate: async (user) => {
          if (user.changed("passwordHash") && !user.passwordHash.startsWith("$2")) {
            user.passwordHash = await bcrypt.hash(user.passwordHash, 12);
          }
        },
      },
    }
  );
  return UserInstance;
}
```

### src/models/Permission.ts

```typescript
import { DataTypes, Model, Optional, Sequelize } from "sequelize";

interface PermissionAttributes {
  id:          number;
  name:        string;
  resource:    string;
  action:      string;
  description?: string;
  createdAt?:  Date;
}

interface PermissionCreationAttributes extends Optional<PermissionAttributes, "id"> {}

export class PermissionInstance extends Model<PermissionAttributes, PermissionCreationAttributes>
  implements PermissionAttributes {
  declare id:          number;
  declare name:        string;
  declare resource:    string;
  declare action:      string;
  declare description: string | undefined;
  declare createdAt:   Date;
}

export default function definePermission(sequelize: Sequelize) {
  PermissionInstance.init(
    {
      id:          { type: DataTypes.INTEGER, autoIncrement: true, primaryKey: true },
      name:        { type: DataTypes.STRING(100), allowNull: false, unique: true },
      resource:    { type: DataTypes.STRING(100), allowNull: false },
      action:      { type: DataTypes.STRING(50),  allowNull: false },
      description: { type: DataTypes.STRING(255) },
    },
    {
      sequelize,
      tableName:  "permissions",
      timestamps: true,
      createdAt:  "created_at",
      updatedAt:  false,
      indexes:    [{ unique: true, fields: ["resource", "action"] }],
    }
  );
  return PermissionInstance;
}
```

### src/models/Role.ts

```typescript
import { DataTypes, Model, Optional, Sequelize } from "sequelize";

interface RoleAttributes {
  id:          number;
  name:        string;
  description?: string;
  createdAt?:  Date;
  updatedAt?:  Date;
}

interface RoleCreationAttributes extends Optional<RoleAttributes, "id"> {}

export class RoleInstance extends Model<RoleAttributes, RoleCreationAttributes>
  implements RoleAttributes {
  declare id:          number;
  declare name:        string;
  declare description: string | undefined;
  declare createdAt:   Date;
  declare updatedAt:   Date;
  declare permissions?: any[];
}

export default function defineRole(sequelize: Sequelize) {
  RoleInstance.init(
    {
      id:          { type: DataTypes.INTEGER, autoIncrement: true, primaryKey: true },
      name:        { type: DataTypes.STRING(100), allowNull: false, unique: true },
      description: { type: DataTypes.STRING(255) },
    },
    {
      sequelize,
      tableName:  "roles",
      timestamps: true,
      createdAt:  "created_at",
      updatedAt:  "updated_at",
    }
  );
  return RoleInstance;
}
```

### src/models/RolePermission.ts

```typescript
import { DataTypes, Model, Sequelize } from "sequelize";

export class RolePermissionInstance extends Model {}

export default function defineRolePermission(sequelize: Sequelize) {
  RolePermissionInstance.init(
    {
      roleId:       { type: DataTypes.INTEGER, field: "role_id" },
      permissionId: { type: DataTypes.INTEGER, field: "permission_id" },
      grantedAt:    { type: DataTypes.DATE, defaultValue: DataTypes.NOW, field: "granted_at" },
    },
    { sequelize, tableName: "role_permissions", timestamps: false }
  );
  return RolePermissionInstance;
}
```

### src/models/UserRole.ts

```typescript
import { DataTypes, Model, Sequelize } from "sequelize";

export class UserRoleInstance extends Model {}

export default function defineUserRole(sequelize: Sequelize) {
  UserRoleInstance.init(
    {
      userId:     { type: DataTypes.INTEGER, field: "user_id" },
      roleId:     { type: DataTypes.INTEGER, field: "role_id" },
      assignedAt: { type: DataTypes.DATE, defaultValue: DataTypes.NOW, field: "assigned_at" },
    },
    { sequelize, tableName: "user_roles", timestamps: false }
  );
  return UserRoleInstance;
}
```

### src/models/TokenBlacklist.ts

```typescript
import { DataTypes, Model, Sequelize } from "sequelize";

export class TokenBlacklistInstance extends Model {
  declare jti:       string;
  declare tokenType: string;
  declare expiresAt: Date;

  static async isRevoked(jti: string): Promise<boolean> {
    const row = await TokenBlacklistInstance.findOne({ where: { jti } });
    return !!row;
  }

  static async revoke(jti: string, tokenType: string, expiresAt: Date): Promise<void> {
    const exists = await TokenBlacklistInstance.isRevoked(jti);
    if (!exists) {
      await TokenBlacklistInstance.create({ jti, tokenType, expiresAt });
    }
  }
}

export default function defineTokenBlacklist(sequelize: Sequelize) {
  TokenBlacklistInstance.init(
    {
      id:        { type: DataTypes.INTEGER, autoIncrement: true, primaryKey: true },
      jti:       { type: DataTypes.STRING(36), unique: true, allowNull: false },
      tokenType: { type: DataTypes.STRING(20), defaultValue: "access", field: "token_type" },
      revokedAt: { type: DataTypes.DATE, defaultValue: DataTypes.NOW,  field: "revoked_at" },
      expiresAt: { type: DataTypes.DATE, allowNull: false, field: "expires_at" },
    },
    { sequelize, tableName: "token_blacklist", timestamps: false }
  );
  return TokenBlacklistInstance;
}
```

---

## JWT Utilities

### src/utils/jwt.ts

```typescript
import jwt, { SignOptions } from "jsonwebtoken";
import { v4 as uuidv4 }   from "uuid";
import { env }            from "../config/env";

export interface JwtPayload {
  sub:         string;
  jti:         string;
  type:        "access" | "refresh";
  iat?:        number;
  exp?:        number;
  username?:   string;
  roles?:      string[];
  permissions?: string[];
}

export function createAccessToken(userId: number, extra: Partial<JwtPayload> = {}): string {
  const payload: JwtPayload = {
    sub:  String(userId),
    jti:  uuidv4(),
    type: "access",
    ...extra,
  };
  return jwt.sign(payload, env.JWT_SECRET, {
    expiresIn: env.JWT_ACCESS_EXPIRES as SignOptions["expiresIn"],
    issuer: "rbac-api",
  });
}

export function createRefreshToken(userId: number): string {
  const payload: JwtPayload = {
    sub:  String(userId),
    jti:  uuidv4(),
    type: "refresh",
  };
  return jwt.sign(payload, env.JWT_REFRESH_SECRET, {
    expiresIn: env.JWT_REFRESH_EXPIRES as SignOptions["expiresIn"],
    issuer: "rbac-api",
  });
}

export function verifyAccessToken(token: string): JwtPayload {
  return jwt.verify(token, env.JWT_SECRET) as JwtPayload;
}

export function verifyRefreshToken(token: string): JwtPayload {
  return jwt.verify(token, env.JWT_REFRESH_SECRET) as JwtPayload;
}

export function extractBearer(headerValue: string | undefined): string {
  if (headerValue && headerValue.startsWith("Bearer ")) {
    return headerValue.slice(7);
  }
  return headerValue ?? "";
}
```

---

## Auth Middleware

### src/middleware/authenticate.ts

```typescript
import { Request, Response, NextFunction } from "express";
import jwt from "jsonwebtoken";
import { verifyAccessToken, extractBearer } from "../utils/jwt";
import { User, TokenBlacklist }             from "../models";

/**
 * jwt_required middleware — attaches req.user (UserInstance).
 * Mirrors the decorator pattern from the project spec:
 *   token = request.headers.get("Authorization")
 *   if token.startsWith("Bearer "): token = token[7:]
 *   payload = jwt.decode(token, SECRET_KEY, ...)
 *   user = User.objects.get(id=payload["sub"])
 *   request.user = user
 */
export async function authenticate(
  req: Request,
  res: Response,
  next: NextFunction,
): Promise<void> {
  const token = extractBearer(req.headers.authorization);

  if (!token) {
    res.status(401).json({ error: "Token is missing" });
    return;
  }

  let payload;
  try {
    payload = verifyAccessToken(token);
  } catch (err) {
    if (err instanceof jwt.TokenExpiredError) {
      res.status(401).json({ error: "Token has expired" });
    } else {
      res.status(401).json({ error: "Invalid token" });
    }
    return;
  }

  if (payload.type !== "access") {
    res.status(401).json({ error: "Access token required" });
    return;
  }

  // DB-backed blacklist check
  const revoked = await TokenBlacklist.isRevoked(payload.jti);
  if (revoked) {
    res.status(401).json({ error: "Token has been revoked" });
    return;
  }

  // Load user from DB — attach to request
  const user = await User.findByPk(parseInt(payload.sub), {
    include: [{ association: "roles", include: ["permissions"] }],
  });

  if (!user) {
    res.status(401).json({ error: "User not found" });
    return;
  }
  if (!user.isActive) {
    res.status(403).json({ error: "Account is disabled" });
    return;
  }

  req.user          = user;
  req.tokenPayload  = payload as Record<string, unknown>;
  next();
}
```

### src/middleware/authorize.ts

```typescript
import { Request, Response, NextFunction, RequestHandler } from "express";

/**
 * RBAC middleware factories.
 *
 * Usage:
 *   router.get("/", authenticate, authorize("users", "read"), controller.list)
 *   router.delete("/:id", authenticate, authorizeRole("admin"), controller.delete)
 */

export function authorize(resource: string, action: string): RequestHandler {
  return async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    if (!req.user) {
      res.status(401).json({ error: "Unauthorized" });
      return;
    }
    const allowed = await req.user.hasPermission(resource, action);
    if (!allowed) {
      res.status(403).json({ error: `Forbidden — requires ${resource}:${action}` });
      return;
    }
    next();
  };
}

export function authorizeRole(...roleNames: string[]): RequestHandler {
  return async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    if (!req.user) {
      res.status(401).json({ error: "Unauthorized" });
      return;
    }
    const checks = await Promise.all(roleNames.map((r) => req.user!.hasRole(r)));
    if (!checks.some(Boolean)) {
      res.status(403).json({ error: `Forbidden — required roles: ${roleNames.join(", ")}` });
      return;
    }
    next();
  };
}
```

---

## Authentication Controller & Routes

### src/controllers/auth.controller.ts

```typescript
import { Request, Response } from "express";
import bcrypt  from "bcryptjs";
import jwt     from "jsonwebtoken";
import { v4 as uuidv4 } from "uuid";

import { User, TokenBlacklist }          from "../models";
import { createAccessToken, createRefreshToken, verifyRefreshToken, extractBearer } from "../utils/jwt";

export class AuthController {

  static async register(req: Request, res: Response): Promise<void> {
    const { username, email, password, firstName, lastName } = req.body;
    if (!username || !email || !password) {
      res.status(400).json({ success: false, message: "username, email, password required" });
      return;
    }
    const existing = await User.findOne({ where: { email } });
    if (existing) { res.status(409).json({ success: false, message: "Email already registered" }); return; }

    const user = await User.create({
      username, email,
      passwordHash: password,   // hashed in beforeCreate hook
      firstName, lastName,
    });
    res.status(201).json({ success: true, message: "Registered", data: { id: user.id, email: user.email } });
  }

  static async login(req: Request, res: Response): Promise<void> {
    const { email, password } = req.body;
    const user = await User.findOne({
      where: { email },
      include: [{ association: "roles", include: ["permissions"] }],
    });

    if (!user || !(await user.verifyPassword(password))) {
      res.status(401).json({ success: false, message: "Invalid credentials" });
      return;
    }
    if (!user.isActive) {
      res.status(403).json({ success: false, message: "Account disabled" });
      return;
    }

    await user.update({ lastLogin: new Date() });

    const permissions = await user.getAllPermissions();
    const roles       = (user.roles ?? []).map((r) => r.name);

    const accessToken  = createAccessToken(user.id, { username: user.username, roles, permissions: [...permissions] });
    const refreshToken = createRefreshToken(user.id);

    res.json({
      success: true,
      message: "Login successful",
      data:    { access_token: accessToken, refresh_token: refreshToken, token_type: "Bearer" },
    });
  }

  static async logout(req: Request, res: Response): Promise<void> {
    const payload  = req.tokenPayload as any;
    const exp      = new Date(payload.exp * 1000);
    await TokenBlacklist.revoke(payload.jti, "access", exp);
    res.json({ success: true, message: "Logged out" });
  }

  static async refresh(req: Request, res: Response): Promise<void> {
    const { refresh_token } = req.body;
    if (!refresh_token) { res.status(400).json({ success: false, message: "refresh_token required" }); return; }

    let payload: any;
    try {
      payload = verifyRefreshToken(refresh_token);
    } catch (err) {
      if (err instanceof jwt.TokenExpiredError) {
        res.status(401).json({ success: false, message: "Refresh token expired" }); return;
      }
      res.status(401).json({ success: false, message: "Invalid refresh token" }); return;
    }

    if (payload.type !== "refresh") { res.status(401).json({ success: false, message: "Refresh token required" }); return; }
    if (await TokenBlacklist.isRevoked(payload.jti)) { res.status(401).json({ success: false, message: "Token revoked" }); return; }

    const user = await User.findByPk(parseInt(payload.sub), {
      include: [{ association: "roles", include: ["permissions"] }],
    });
    if (!user) { res.status(404).json({ success: false, message: "User not found" }); return; }

    const permissions = await user.getAllPermissions();
    const roles       = (user.roles ?? []).map((r) => r.name);
    const newToken    = createAccessToken(user.id, { username: user.username, roles, permissions: [...permissions] });

    res.json({ success: true, data: { access_token: newToken, token_type: "Bearer" } });
  }

  static async me(req: Request, res: Response): Promise<void> {
    const user  = req.user!;
    const perms = await user.getAllPermissions();
    res.json({
      success: true,
      data: {
        ...user.toJSON(),
        roles:       (user.roles ?? []).map((r) => r.name),
        permissions: [...perms],
      },
    });
  }
}
```

### src/routes/auth.routes.ts

```typescript
import { Router }         from "express";
import { AuthController } from "../controllers/auth.controller";
import { authenticate }   from "../middleware/authenticate";

const router = Router();

router.post("/register", AuthController.register);
router.post("/login",    AuthController.login);
router.delete("/logout", authenticate, AuthController.logout);
router.post("/refresh",  AuthController.refresh);
router.get("/me",        authenticate, AuthController.me);

export default router;
```

### src/routes/user.routes.ts

```typescript
import { Router }       from "express";
import { authenticate } from "../middleware/authenticate";
import { authorize, authorizeRole } from "../middleware/authorize";
import { User, Role, UserRole } from "../models";
import { Op }           from "sequelize";

const router = Router();

router.get("/", authenticate, authorize("users", "read"), async (req, res) => {
  const page    = parseInt(req.query.page as string)     || 1;
  const perPage = parseInt(req.query.per_page as string) || 10;
  const search  = (req.query.search as string)           || "";

  const where = search ? { [Op.or]: [
    { username: { [Op.like]: `%${search}%` } },
    { email:    { [Op.like]: `%${search}%` } },
  ]} : {};

  const { count, rows } = await User.findAndCountAll({
    where,
    include: [{ association: "roles", attributes: ["id", "name"] }],
    limit:  perPage,
    offset: (page - 1) * perPage,
    order:  [["created_at", "DESC"]],
  });

  res.json({ success: true, data: {
    users:    rows.map((u) => u.toJSON()),
    total:    count,
    page,
    pages:    Math.ceil(count / perPage),
    per_page: perPage,
  }});
});

router.get("/:id", authenticate, authorize("users", "read"), async (req, res) => {
  const user = await User.findByPk(req.params.id, { include: [{ association: "roles", include: ["permissions"] }] });
  if (!user) { res.status(404).json({ success: false, message: "User not found" }); return; }
  res.json({ success: true, data: user.toJSON() });
});

router.post("/", authenticate, authorize("users", "create"), async (req, res) => {
  const { username, email, password, firstName, lastName } = req.body;
  const dup = await User.findOne({ where: { email } });
  if (dup) { res.status(409).json({ success: false, message: "Email exists" }); return; }
  const user = await User.create({ username, email, passwordHash: password, firstName, lastName });
  res.status(201).json({ success: true, data: user.toJSON() });
});

router.put("/:id", authenticate, authorize("users", "update"), async (req, res) => {
  const user = await User.findByPk(req.params.id);
  if (!user) { res.status(404).json({ success: false, message: "Not found" }); return; }
  const { firstName, lastName, isActive, password } = req.body;
  const updates: Record<string, unknown> = {};
  if (firstName !== undefined) updates.firstName = firstName;
  if (lastName  !== undefined) updates.lastName  = lastName;
  if (isActive  !== undefined) updates.isActive  = isActive;
  if (password)                updates.passwordHash = password;
  await user.update(updates);
  res.json({ success: true, data: user.toJSON() });
});

router.delete("/:id", authenticate, authorize("users", "delete"), async (req, res) => {
  const user = await User.findByPk(req.params.id);
  if (!user) { res.status(404).json({ success: false, message: "Not found" }); return; }
  await user.destroy();
  res.status(204).send();
});

router.post("/:id/roles", authenticate, authorizeRole("admin", "super_admin"), async (req, res) => {
  const user = await User.findByPk(req.params.id);
  const role = await Role.findByPk(req.body.roleId);
  if (!user || !role) { res.status(404).json({ success: false, message: "Not found" }); return; }
  await UserRole.findOrCreate({ where: { userId: user.id, roleId: role.id } });
  res.json({ success: true, message: "Role assigned" });
});

router.delete("/:id/roles/:roleId", authenticate, authorizeRole("admin", "super_admin"), async (req, res) => {
  await UserRole.destroy({ where: { userId: req.params.id, roleId: req.params.roleId } });
  res.json({ success: true, message: "Role removed" });
});

export default router;
```

### src/routes/index.ts

```typescript
import { Router }    from "express";
import authRoutes    from "./auth.routes";
import userRoutes    from "./user.routes";
import roleRoutes    from "./role.routes";
import permissionRoutes from "./permission.routes";

const router = Router();
router.use("/auth",        authRoutes);
router.use("/users",       userRoutes);
router.use("/roles",       roleRoutes);
router.use("/permissions", permissionRoutes);
export default router;
```

---

## MongoDB Model (Mongoose + TS)

### src/mongo_models/UserActivity.ts

```typescript
import mongoose, { Schema, Document } from "mongoose";

export interface IUserActivity extends Document {
  userId:    string;
  action:    string;
  resource?: string;
  metadata:  Record<string, unknown>;
  ipAddress?: string;
  userAgent?: string;
  createdAt: Date;
}

const UserActivitySchema = new Schema<IUserActivity>(
  {
    userId:    { type: String, required: true, index: true },
    action:    { type: String, required: true, index: true },
    resource:  { type: String },
    metadata:  { type: Schema.Types.Mixed, default: {} },
    ipAddress: { type: String },
    userAgent: { type: String },
  },
  {
    timestamps:  { createdAt: "createdAt", updatedAt: false },
    collection:  "user_activities",
  }
);

UserActivitySchema.index({ userId: 1, createdAt: -1 });

export const UserActivity = mongoose.model<IUserActivity>("UserActivity", UserActivitySchema);
```

---

## Error Handling

### src/middleware/errorHandler.ts

```typescript
import { Request, Response, NextFunction } from "express";

export function notFound(req: Request, res: Response): void {
  res.status(404).json({ success: false, message: `Route ${req.originalUrl} not found` });
}

export function errorHandler(
  err: Error & { status?: number },
  req: Request,
  res: Response,
  next: NextFunction,
): void {
  console.error(err.stack);
  const status = err.status || 500;
  res.status(status).json({ success: false, message: err.message || "Internal server error" });
}
```

---

## App & Server Entry Point

### src/app.ts

```typescript
import express      from "express";
import cors         from "cors";
import helmet       from "helmet";
import morgan       from "morgan";
import rateLimit    from "express-rate-limit";
import { env }      from "./config/env";
import routes       from "./routes";
import { notFound, errorHandler } from "./middleware/errorHandler";

const app = express();

app.use(helmet());
app.use(cors({
  origin:      env.CORS_ORIGIN,
  credentials: true,
  methods:     ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
  allowedHeaders: ["Content-Type", "Authorization"],
}));
app.use(rateLimit({ windowMs: 15 * 60 * 1000, max: 100 }));
app.use(express.json({ limit: "10mb" }));
app.use(express.urlencoded({ extended: true }));
app.use(morgan(env.NODE_ENV === "production" ? "combined" : "dev"));

app.use("/api", routes);
app.get("/health", (_req, res) => res.json({ status: "ok" }));

app.use(notFound);
app.use(errorHandler);

export default app;
```

### server.ts

```typescript
import "dotenv/config";
import app                   from "./src/app";
import { sequelize }         from "./src/models";
import { connectMongo }      from "./src/config/mongo";
import { env }               from "./src/config/env";

async function bootstrap(): Promise<void> {
  await sequelize.authenticate();
  console.log("✅ MySQL connected");
  await sequelize.sync({ alter: env.NODE_ENV === "development" });
  console.log("✅ Models synced");
  await connectMongo();

  app.listen(env.PORT, () => {
    console.log(`🚀 Server running on http://localhost:${env.PORT}`);
  });
}

bootstrap().catch((err) => {
  console.error("❌ Startup failed:", err);
  process.exit(1);
});
```

---

## Database Switching Guide

Only `.env` changes needed — TypeScript models are dialect-agnostic.

```env
# MySQL (default)
DB_DIALECT=mysql
DB_HOST=localhost
DB_PORT=3306
DB_NAME=nodejs_rbac_db
DB_USER=root
DB_PASSWORD=yourpassword

# SQLite (development only)
DB_DIALECT=sqlite
DB_STORAGE=./dev.db

# PostgreSQL
DB_DIALECT=postgres
DB_HOST=localhost
DB_PORT=5432
DB_NAME=nodejs_rbac_db
DB_USER=postgres
DB_PASSWORD=yourpassword
```

```bash
# MySQL: create the database first
mysql -u root -p -e "CREATE DATABASE nodejs_rbac_db CHARACTER SET utf8mb4;"

npm run dev
```

---

## API Endpoint Summary

| Method | Endpoint | Description | Middleware |
|--------|----------|-------------|------------|
| POST | /api/auth/register | Register | Public |
| POST | /api/auth/login | Login → JWT | Public |
| DELETE | /api/auth/logout | Revoke token | authenticate |
| POST | /api/auth/refresh | New access token | Public |
| GET | /api/auth/me | Current user | authenticate |
| GET | /api/users | List users | authorize("users","read") |
| POST | /api/users | Create user | authorize("users","create") |
| GET | /api/users/:id | Get user | authorize("users","read") |
| PUT | /api/users/:id | Update user | authorize("users","update") |
| DELETE | /api/users/:id | Delete user | authorize("users","delete") |
| POST | /api/users/:id/roles | Assign role | authorizeRole("admin") |
| DELETE | /api/users/:id/roles/:rid | Remove role | authorizeRole("admin") |
| GET | /api/roles | List roles | authorize("roles","read") |
| POST | /api/roles | Create role | authorize("roles","create") |
| PUT | /api/roles/:id | Update role | authorize("roles","update") |
| DELETE | /api/roles/:id | Delete role | authorize("roles","delete") |
| POST | /api/roles/:id/permissions | Assign permission | authorize("roles","update") |
| DELETE | /api/roles/:id/permissions/:pid | Remove permission | authorize("roles","update") |
| GET | /api/permissions | List permissions | authorize("permissions","read") |
| POST | /api/permissions | Create permission | authorize("permissions","create") |
