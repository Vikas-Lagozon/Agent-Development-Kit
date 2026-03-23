# Node.js Backend — Production Guide (TypeScript)

> jsonwebtoken · MySQL default · `.env` credentials · Dynamic RBAC · TypeScript · Windows + Linux compatible

---

## Verified Package Versions (Node.js 20 LTS + TypeScript 5.x)

```json
{
  "dependencies": {
    "express": "^4.19.2",
    "sequelize": "^6.37.3",
    "mysql2": "^3.10.1",
    "jsonwebtoken": "^9.0.2",
    "bcryptjs": "^2.4.3",
    "dotenv": "^16.4.5",
    "cors": "^2.8.5",
    "helmet": "^7.1.0",
    "uuid": "^10.0.0",
    "express-rate-limit": "^7.3.1"
  },
  "devDependencies": {
    "typescript": "^5.5.3",
    "ts-node-dev": "^2.0.0",
    "@types/express": "^4.17.21",
    "@types/jsonwebtoken": "^9.0.6",
    "@types/bcryptjs": "^2.4.6",
    "@types/cors": "^2.8.17",
    "@types/uuid": "^10.0.0",
    "@types/node": "^20.14.12",
    "sequelize-cli": "^6.6.2"
  }
}
```

---

## Project Structure

```
nodejs_project/
├── src/
│   ├── config/
│   │   ├── env.ts             # typed .env loader
│   │   └── database.ts        # Sequelize config (MySQL default)
│   ├── models/
│   │   ├── index.ts           # model loader + associations
│   │   ├── User.ts
│   │   ├── Role.ts
│   │   ├── Permission.ts
│   │   ├── RolePermission.ts
│   │   ├── UserRole.ts
│   │   └── TokenBlacklist.ts
│   ├── middleware/
│   │   ├── authenticate.ts    # jwt_required
│   │   └── authorize.ts       # RBAC guards
│   ├── controllers/
│   │   ├── auth.controller.ts
│   │   ├── user.controller.ts
│   │   ├── role.controller.ts
│   │   └── permission.controller.ts
│   ├── routes/
│   │   ├── index.ts
│   │   ├── auth.routes.ts
│   │   ├── user.routes.ts
│   │   ├── role.routes.ts
│   │   └── permission.routes.ts
│   ├── utils/
│   │   └── jwt.ts
│   ├── types/
│   │   └── express.d.ts
│   └── app.ts
├── .env
├── .env.example
├── package.json
├── tsconfig.json
└── server.ts
```

---

## Minimum Steps to Run (Windows CMD)

```cmd
:: Step 1 — Create project and install
mkdir nodejs_project
cd nodejs_project
npm init -y
npm install express sequelize mysql2 jsonwebtoken bcryptjs dotenv cors helmet uuid express-rate-limit
npm install -D typescript ts-node-dev @types/express @types/jsonwebtoken @types/bcryptjs @types/cors @types/uuid @types/node sequelize-cli

:: Step 2 — Create MySQL database
mysql -u root -p -e "CREATE DATABASE nodejs_rbac_db CHARACTER SET utf8mb4;"

:: Step 3 — Copy .env (Windows)
copy .env.example .env
:: Edit .env and set DB_PASSWORD, JWT_SECRET, JWT_REFRESH_SECRET

:: Step 4 — Run server (auto-sync tables on start)
npm run dev
:: → http://localhost:3000
```

---

## .env

```env
NODE_ENV=development
PORT=3000

JWT_SECRET=change-this-jwt-secret-min-64-random-chars
JWT_REFRESH_SECRET=change-this-refresh-secret-min-64-random-chars
JWT_ACCESS_EXPIRES_IN=1h
JWT_REFRESH_EXPIRES_IN=30d

DB_DIALECT=mysql
DB_HOST=localhost
DB_PORT=3306
DB_NAME=nodejs_rbac_db
DB_USER=root
DB_PASSWORD=yourpassword

CORS_ORIGIN=http://localhost:3000,http://localhost:5173
```

## .env.example

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
CORS_ORIGIN=http://localhost:3000
```

---

## tsconfig.json

```json
{
  "compilerOptions": {
    "target":           "ES2022",
    "module":           "CommonJS",
    "outDir":           "./dist",
    "rootDir":          "./src",
    "strict":           true,
    "esModuleInterop":  true,
    "resolveJsonModule": true,
    "skipLibCheck":     true
  },
  "include": ["src/**/*", "server.ts"],
  "exclude": ["node_modules", "dist"]
}
```

---

## package.json scripts

```json
{
  "scripts": {
    "dev":   "ts-node-dev --respawn --transpile-only server.ts",
    "build": "tsc",
    "start": "node dist/server.js"
  }
}
```

---

## src/types/express.d.ts

```typescript
import { UserModel } from "../models/User";

declare global {
  namespace Express {
    interface Request {
      user?:         UserModel;
      tokenPayload?: Record<string, unknown>;
    }
  }
}
```

---

## src/config/env.ts

```typescript
import dotenv from "dotenv";
dotenv.config();

export const env = {
  NODE_ENV:    process.env.NODE_ENV    || "development",
  PORT:        parseInt(process.env.PORT || "3000"),

  JWT_SECRET:          process.env.JWT_SECRET          || "",
  JWT_REFRESH_SECRET:  process.env.JWT_REFRESH_SECRET  || "",
  JWT_ACCESS_EXPIRES:  process.env.JWT_ACCESS_EXPIRES_IN  || "1h",
  JWT_REFRESH_EXPIRES: process.env.JWT_REFRESH_EXPIRES_IN || "30d",

  DB_DIALECT:  (process.env.DB_DIALECT  || "mysql") as "mysql" | "postgres" | "sqlite",
  DB_HOST:     process.env.DB_HOST     || "localhost",
  DB_PORT:     parseInt(process.env.DB_PORT || "3306"),
  DB_NAME:     process.env.DB_NAME     || "nodejs_rbac_db",
  DB_USER:     process.env.DB_USER     || "root",
  DB_PASSWORD: process.env.DB_PASSWORD || "",
  DB_STORAGE:  process.env.DB_STORAGE  || "./dev.db",

  // Split comma string — avoids JSON parse issues
  CORS_ORIGIN: (process.env.CORS_ORIGIN || "http://localhost:3000")
                 .split(",")
                 .map((o) => o.trim()),
};

if (!env.JWT_SECRET || !env.JWT_REFRESH_SECRET) {
  console.error("❌ JWT_SECRET and JWT_REFRESH_SECRET must be set in .env");
  process.exit(1);
}
```

---

## src/config/database.ts

```typescript
import { Sequelize, Options, Dialect } from "sequelize";
import { env } from "./env";

const config: Options = env.DB_DIALECT === "sqlite"
  ? { dialect: "sqlite" as Dialect, storage: env.DB_STORAGE, logging: false }
  : {
      dialect:  env.DB_DIALECT as Dialect,
      host:     env.DB_HOST,
      port:     env.DB_PORT,
      database: env.DB_NAME,
      username: env.DB_USER,
      password: env.DB_PASSWORD,
      logging:  env.NODE_ENV === "development" ? console.log : false,
      pool:     { max: 10, min: 2, acquire: 30000, idle: 10000 },
      ...(env.DB_DIALECT === "mysql" && {
        dialectOptions: { charset: "utf8mb4" },
      }),
    };

export const sequelize = new Sequelize(config);
```

---

## src/models/Permission.ts

```typescript
import { DataTypes, Model, Optional, Sequelize } from "sequelize";

interface PermissionAttrs {
  id:          number;
  name:        string;
  resource:    string;
  action:      string;
  description?: string;
}

type PermissionCreation = Optional<PermissionAttrs, "id">;

export class PermissionModel extends Model<PermissionAttrs, PermissionCreation> {
  declare id:          number;
  declare name:        string;
  declare resource:    string;
  declare action:      string;
  declare description: string | undefined;

  toJSON() {
    return {
      id: this.id, name: this.name, resource: this.resource,
      action: this.action, description: this.description,
    };
  }
}

export function initPermission(seq: Sequelize) {
  PermissionModel.init(
    {
      id:          { type: DataTypes.INTEGER, autoIncrement: true, primaryKey: true },
      name:        { type: DataTypes.STRING(100), allowNull: false, unique: true },
      resource:    { type: DataTypes.STRING(100), allowNull: false },
      action:      { type: DataTypes.STRING(50),  allowNull: false },
      description: { type: DataTypes.STRING(255) },
    },
    { sequelize: seq, tableName: "permissions", timestamps: false,
      indexes: [{ unique: true, fields: ["resource", "action"] }] }
  );
}
```

---

## src/models/Role.ts

```typescript
import { DataTypes, Model, Optional, Sequelize } from "sequelize";

interface RoleAttrs { id: number; name: string; description?: string; }
type RoleCreation = Optional<RoleAttrs, "id">;

export class RoleModel extends Model<RoleAttrs, RoleCreation> {
  declare id:          number;
  declare name:        string;
  declare description: string | undefined;
  declare permissions?: any[];

  toJSON() {
    return {
      id: this.id, name: this.name, description: this.description,
      permissions: (this.permissions || []).map((p: any) => p.toJSON?.() ?? p),
    };
  }
}

export function initRole(seq: Sequelize) {
  RoleModel.init(
    {
      id:          { type: DataTypes.INTEGER, autoIncrement: true, primaryKey: true },
      name:        { type: DataTypes.STRING(100), allowNull: false, unique: true },
      description: { type: DataTypes.STRING(255) },
    },
    { sequelize: seq, tableName: "roles", timestamps: true,
      createdAt: "created_at", updatedAt: "updated_at" }
  );
}
```

---

## src/models/User.ts

```typescript
import { DataTypes, Model, Optional, Sequelize } from "sequelize";
import bcrypt from "bcryptjs";

interface UserAttrs {
  id:           number;
  username:     string;
  email:        string;
  passwordHash: string;
  firstName?:   string;
  lastName?:    string;
  isActive:     boolean;
  lastLogin?:   Date;
}

type UserCreation = Optional<UserAttrs, "id" | "isActive">;

export class UserModel extends Model<UserAttrs, UserCreation> {
  declare id:           number;
  declare username:     string;
  declare email:        string;
  declare passwordHash: string;
  declare firstName:    string | undefined;
  declare lastName:     string | undefined;
  declare isActive:     boolean;
  declare lastLogin:    Date | undefined;
  declare roles?:       any[];

  async verifyPassword(plain: string): Promise<boolean> {
    return bcrypt.compare(plain, this.passwordHash);
  }

  async getAllPermissions(): Promise<Set<string>> {
    const perms = new Set<string>();
    const roles = (this.roles ?? await (this as any).getRoles({ include: ["permissions"] })) as any[];
    for (const role of roles) {
      for (const perm of (role.permissions ?? [])) {
        perms.add(`${perm.resource}:${perm.action}`);
      }
    }
    return perms;
  }

  async hasPermission(resource: string, action: string): Promise<boolean> {
    return (await this.getAllPermissions()).has(`${resource}:${action}`);
  }

  async hasRole(roleName: string): Promise<boolean> {
    const roles = (this.roles ?? await (this as any).getRoles()) as any[];
    return roles.some((r) => r.name === roleName);
  }

  async toSafeDict() {
    const perms = await this.getAllPermissions();
    const roles = (this.roles ?? await (this as any).getRoles()) as any[];
    return {
      id: this.id, username: this.username, email: this.email,
      firstName: this.firstName, lastName: this.lastName, isActive: this.isActive,
      roles: roles.map((r: any) => r.name), permissions: [...perms],
      lastLogin: this.lastLogin?.toISOString() ?? null,
    };
  }

  toJSON() {
    const v = super.toJSON() as Record<string, unknown>;
    delete v["passwordHash"];
    return v;
  }
}

export function initUser(seq: Sequelize) {
  UserModel.init(
    {
      id:           { type: DataTypes.INTEGER, autoIncrement: true, primaryKey: true },
      username:     { type: DataTypes.STRING(80),  allowNull: false, unique: true },
      email:        { type: DataTypes.STRING(120), allowNull: false, unique: true },
      passwordHash: { type: DataTypes.STRING(255), allowNull: false, field: "password_hash" },
      firstName:    { type: DataTypes.STRING(80),  field: "first_name" },
      lastName:     { type: DataTypes.STRING(80),  field: "last_name" },
      isActive:     { type: DataTypes.BOOLEAN, defaultValue: true, field: "is_active" },
      lastLogin:    { type: DataTypes.DATE, field: "last_login" },
    },
    {
      sequelize: seq, tableName: "users",
      timestamps: true, createdAt: "created_at", updatedAt: "updated_at",
      hooks: {
        beforeCreate: async (u) => {
          u.passwordHash = await bcrypt.hash(u.passwordHash, 12);
        },
        beforeUpdate: async (u) => {
          if (u.changed("passwordHash") && !u.passwordHash.startsWith("$2")) {
            u.passwordHash = await bcrypt.hash(u.passwordHash, 12);
          }
        },
      },
    }
  );
}
```

---

## src/models/RolePermission.ts

```typescript
import { DataTypes, Model, Sequelize } from "sequelize";

export class RolePermissionModel extends Model {}

export function initRolePermission(seq: Sequelize) {
  RolePermissionModel.init(
    {
      roleId:       { type: DataTypes.INTEGER, field: "role_id" },
      permissionId: { type: DataTypes.INTEGER, field: "permission_id" },
    },
    { sequelize: seq, tableName: "role_permissions", timestamps: false }
  );
}
```

---

## src/models/UserRole.ts

```typescript
import { DataTypes, Model, Sequelize } from "sequelize";

export class UserRoleModel extends Model {}

export function initUserRole(seq: Sequelize) {
  UserRoleModel.init(
    {
      userId: { type: DataTypes.INTEGER, field: "user_id" },
      roleId: { type: DataTypes.INTEGER, field: "role_id" },
    },
    { sequelize: seq, tableName: "user_roles", timestamps: false }
  );
}
```

---

## src/models/TokenBlacklist.ts

```typescript
import { DataTypes, Model, Sequelize } from "sequelize";

export class TokenBlacklistModel extends Model {
  declare jti:       string;
  declare expiresAt: Date;

  static async isRevoked(jti: string): Promise<boolean> {
    return !!(await TokenBlacklistModel.findOne({ where: { jti } }));
  }

  static async revoke(jti: string, tokenType: string, expiresAt: Date): Promise<void> {
    if (!(await TokenBlacklistModel.isRevoked(jti))) {
      await TokenBlacklistModel.create({ jti, tokenType, expiresAt });
    }
  }
}

export function initTokenBlacklist(seq: Sequelize) {
  TokenBlacklistModel.init(
    {
      id:        { type: DataTypes.INTEGER, autoIncrement: true, primaryKey: true },
      jti:       { type: DataTypes.STRING(36), unique: true, allowNull: false },
      tokenType: { type: DataTypes.STRING(20), defaultValue: "access", field: "token_type" },
      revokedAt: { type: DataTypes.DATE, defaultValue: DataTypes.NOW, field: "revoked_at" },
      expiresAt: { type: DataTypes.DATE, allowNull: false, field: "expires_at" },
    },
    { sequelize: seq, tableName: "token_blacklist", timestamps: false }
  );
}
```

---

## src/models/index.ts

```typescript
import { sequelize } from "../config/database";
import { UserModel,        initUser }          from "./User";
import { RoleModel,        initRole }          from "./Role";
import { PermissionModel,  initPermission }    from "./Permission";
import { RolePermissionModel, initRolePermission } from "./RolePermission";
import { UserRoleModel,    initUserRole }      from "./UserRole";
import { TokenBlacklistModel, initTokenBlacklist } from "./TokenBlacklist";

// Init models
initUser(sequelize);
initRole(sequelize);
initPermission(sequelize);
initRolePermission(sequelize);
initUserRole(sequelize);
initTokenBlacklist(sequelize);

// Associations
RoleModel.belongsToMany(PermissionModel, {
  through: RolePermissionModel, foreignKey: "roleId", otherKey: "permissionId", as: "permissions",
});
PermissionModel.belongsToMany(RoleModel, {
  through: RolePermissionModel, foreignKey: "permissionId", otherKey: "roleId", as: "roles",
});
UserModel.belongsToMany(RoleModel, {
  through: UserRoleModel, foreignKey: "userId", otherKey: "roleId", as: "roles",
});
RoleModel.belongsToMany(UserModel, {
  through: UserRoleModel, foreignKey: "roleId", otherKey: "userId", as: "users",
});

export { sequelize, UserModel, RoleModel, PermissionModel,
         RolePermissionModel, UserRoleModel, TokenBlacklistModel };
```

---

## src/utils/jwt.ts

```typescript
import jwt, { SignOptions } from "jsonwebtoken";
import { v4 as uuidv4 }    from "uuid";
import { env }             from "../config/env";

export interface JwtPayload {
  sub:         string;
  jti:         string;
  type:        "access" | "refresh";
  username?:   string;
  roles?:      string[];
  permissions?: string[];
  iat?:        number;
  exp?:        number;
}

export function createAccessToken(userId: number, extra: Partial<JwtPayload> = {}): string {
  const payload: JwtPayload = { sub: String(userId), jti: uuidv4(), type: "access", ...extra };
  return jwt.sign(payload, env.JWT_SECRET, { expiresIn: env.JWT_ACCESS_EXPIRES as SignOptions["expiresIn"] });
}

export function createRefreshToken(userId: number): string {
  const payload: JwtPayload = { sub: String(userId), jti: uuidv4(), type: "refresh" };
  return jwt.sign(payload, env.JWT_REFRESH_SECRET, { expiresIn: env.JWT_REFRESH_EXPIRES as SignOptions["expiresIn"] });
}

export function verifyAccessToken(token: string): JwtPayload {
  return jwt.verify(token, env.JWT_SECRET) as JwtPayload;
}

export function verifyRefreshToken(token: string): JwtPayload {
  return jwt.verify(token, env.JWT_REFRESH_SECRET) as JwtPayload;
}

export function extractBearer(header?: string): string {
  return header?.startsWith("Bearer ") ? header.slice(7) : header ?? "";
}
```

---

## src/middleware/authenticate.ts

```typescript
import { Request, Response, NextFunction } from "express";
import jwt from "jsonwebtoken";
import { verifyAccessToken, extractBearer } from "../utils/jwt";
import { UserModel, TokenBlacklistModel }   from "../models";

export async function authenticate(req: Request, res: Response, next: NextFunction): Promise<void> {
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

  if (await TokenBlacklistModel.isRevoked(payload.jti)) {
    res.status(401).json({ error: "Token has been revoked" });
    return;
  }

  const user = await UserModel.findByPk(parseInt(payload.sub), {
    include: [{ association: "roles", include: ["permissions"] }],
  });

  if (!user) { res.status(401).json({ error: "User not found" }); return; }
  if (!user.isActive) { res.status(403).json({ error: "Account is disabled" }); return; }

  req.user          = user;
  req.tokenPayload  = payload as Record<string, unknown>;
  next();
}
```

---

## src/middleware/authorize.ts

```typescript
import { Request, Response, NextFunction, RequestHandler } from "express";

export function authorize(resource: string, action: string): RequestHandler {
  return async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    if (!req.user) { res.status(401).json({ error: "Unauthorized" }); return; }
    if (!(await req.user.hasPermission(resource, action))) {
      res.status(403).json({ error: `Requires ${resource}:${action}` });
      return;
    }
    next();
  };
}

export function authorizeRole(...roleNames: string[]): RequestHandler {
  return async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    if (!req.user) { res.status(401).json({ error: "Unauthorized" }); return; }
    const checks = await Promise.all(roleNames.map((r) => req.user!.hasRole(r)));
    if (!checks.some(Boolean)) {
      res.status(403).json({ error: `Requires role: ${roleNames.join(", ")}` });
      return;
    }
    next();
  };
}
```

---

## src/controllers/auth.controller.ts

```typescript
import { Request, Response } from "express";
import jwt                   from "jsonwebtoken";
import { UserModel, TokenBlacklistModel } from "../models";
import { createAccessToken, createRefreshToken, verifyRefreshToken, extractBearer } from "../utils/jwt";

export const AuthController = {

  async register(req: Request, res: Response): Promise<void> {
    const { username, email, password, firstName, lastName } = req.body;
    if (!username || !email || !password) {
      res.status(400).json({ success: false, message: "username, email, password required" });
      return;
    }
    if (await UserModel.findOne({ where: { email } })) {
      res.status(409).json({ success: false, message: "Email already registered" });
      return;
    }
    const user = await UserModel.create({ username, email, passwordHash: password, firstName, lastName });
    res.status(201).json({ success: true, data: { id: user.id, email: user.email } });
  },

  async login(req: Request, res: Response): Promise<void> {
    const { email, password } = req.body;
    const user = await UserModel.findOne({
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
    const roles       = (user.roles ?? []).map((r: any) => r.name);
    res.json({
      success: true,
      data: {
        access_token:  createAccessToken(user.id, { username: user.username, roles, permissions: [...permissions] }),
        refresh_token: createRefreshToken(user.id),
        token_type:    "Bearer",
        user: await user.toSafeDict(),
      },
    });
  },

  async logout(req: Request, res: Response): Promise<void> {
    const payload = req.tokenPayload as any;
    await TokenBlacklistModel.revoke(payload.jti, "access", new Date(payload.exp * 1000));
    res.json({ success: true, message: "Logged out" });
  },

  async refresh(req: Request, res: Response): Promise<void> {
    const { refresh_token } = req.body;
    if (!refresh_token) { res.status(400).json({ success: false, message: "refresh_token required" }); return; }

    let payload: any;
    try {
      payload = verifyRefreshToken(refresh_token);
    } catch (err) {
      if (err instanceof jwt.TokenExpiredError) {
        res.status(401).json({ success: false, message: "Refresh token expired" });
      } else {
        res.status(401).json({ success: false, message: "Invalid refresh token" });
      }
      return;
    }

    if (payload.type !== "refresh") { res.status(401).json({ success: false, message: "Refresh token required" }); return; }
    if (await TokenBlacklistModel.isRevoked(payload.jti)) { res.status(401).json({ success: false, message: "Token revoked" }); return; }

    const user = await UserModel.findByPk(parseInt(payload.sub), {
      include: [{ association: "roles", include: ["permissions"] }],
    });
    if (!user) { res.status(404).json({ success: false, message: "User not found" }); return; }

    const permissions = await user.getAllPermissions();
    const roles       = (user.roles ?? []).map((r: any) => r.name);
    res.json({ success: true, data: { access_token: createAccessToken(user.id, { username: user.username, roles, permissions: [...permissions] }) } });
  },

  async me(req: Request, res: Response): Promise<void> {
    res.json({ success: true, data: await req.user!.toSafeDict() });
  },
};
```

---

## src/controllers/user.controller.ts

```typescript
import { Request, Response } from "express";
import { Op } from "sequelize";
import { UserModel, RoleModel, UserRoleModel } from "../models";

export const UserController = {

  async list(req: Request, res: Response): Promise<void> {
    const page    = parseInt(req.query.page as string)     || 1;
    const perPage = parseInt(req.query.per_page as string) || 10;
    const search  = (req.query.search as string)           || "";
    const where   = search ? { [Op.or]: [
      { username: { [Op.like]: `%${search}%` } },
      { email:    { [Op.like]: `%${search}%` } },
    ]} : {};
    const { count, rows } = await UserModel.findAndCountAll({
      where, include: [{ association: "roles" }],
      limit: perPage, offset: (page - 1) * perPage, order: [["created_at", "DESC"]],
    });
    res.json({ success: true, data: {
      users: await Promise.all(rows.map((u) => u.toSafeDict())),
      total: count, page, pages: Math.ceil(count / perPage), per_page: perPage,
    }});
  },

  async getOne(req: Request, res: Response): Promise<void> {
    const user = await UserModel.findByPk(req.params.id, {
      include: [{ association: "roles", include: ["permissions"] }],
    });
    if (!user) { res.status(404).json({ success: false, message: "Not found" }); return; }
    res.json({ success: true, data: await user.toSafeDict() });
  },

  async create(req: Request, res: Response): Promise<void> {
    const { username, email, password, firstName, lastName } = req.body;
    if (await UserModel.findOne({ where: { email } })) {
      res.status(409).json({ success: false, message: "Email exists" }); return;
    }
    const user = await UserModel.create({ username, email, passwordHash: password, firstName, lastName });
    res.status(201).json({ success: true, data: await user.toSafeDict() });
  },

  async update(req: Request, res: Response): Promise<void> {
    const user = await UserModel.findByPk(req.params.id);
    if (!user) { res.status(404).json({ success: false, message: "Not found" }); return; }
    const { firstName, lastName, isActive, password } = req.body;
    const updates: Record<string, unknown> = {};
    if (firstName !== undefined) updates.firstName = firstName;
    if (lastName  !== undefined) updates.lastName  = lastName;
    if (isActive  !== undefined) updates.isActive  = isActive;
    if (password)                updates.passwordHash = password;
    await user.update(updates);
    res.json({ success: true, data: await user.toSafeDict() });
  },

  async remove(req: Request, res: Response): Promise<void> {
    const user = await UserModel.findByPk(req.params.id);
    if (!user) { res.status(404).json({ success: false, message: "Not found" }); return; }
    await user.destroy();
    res.status(204).send();
  },

  async assignRole(req: Request, res: Response): Promise<void> {
    const user = await UserModel.findByPk(req.params.id);
    const role = await RoleModel.findByPk(req.body.roleId);
    if (!user || !role) { res.status(404).json({ success: false, message: "Not found" }); return; }
    await UserRoleModel.findOrCreate({ where: { userId: user.id, roleId: role.id } });
    res.json({ success: true, message: "Role assigned" });
  },

  async removeRole(req: Request, res: Response): Promise<void> {
    await UserRoleModel.destroy({ where: { userId: req.params.id, roleId: req.params.roleId } });
    res.json({ success: true, message: "Role removed" });
  },
};
```

---

## src/controllers/role.controller.ts

```typescript
import { Request, Response } from "express";
import { RoleModel, PermissionModel, RolePermissionModel } from "../models";

export const RoleController = {

  async list(req: Request, res: Response): Promise<void> {
    const roles = await RoleModel.findAll({ include: ["permissions"] });
    res.json({ success: true, data: roles.map((r) => r.toJSON()) });
  },

  async getOne(req: Request, res: Response): Promise<void> {
    const role = await RoleModel.findByPk(req.params.id, { include: ["permissions"] });
    if (!role) { res.status(404).json({ success: false, message: "Not found" }); return; }
    res.json({ success: true, data: role.toJSON() });
  },

  async create(req: Request, res: Response): Promise<void> {
    const existing = await RoleModel.findOne({ where: { name: req.body.name } });
    if (existing) { res.status(409).json({ success: false, message: "Role exists" }); return; }
    const role = await RoleModel.create({ name: req.body.name, description: req.body.description });
    res.status(201).json({ success: true, data: role.toJSON() });
  },

  async update(req: Request, res: Response): Promise<void> {
    const role = await RoleModel.findByPk(req.params.id, { include: ["permissions"] });
    if (!role) { res.status(404).json({ success: false, message: "Not found" }); return; }
    if (req.body.name)        role.name        = req.body.name;
    if (req.body.description) role.description = req.body.description;
    await role.save();
    res.json({ success: true, data: role.toJSON() });
  },

  async remove(req: Request, res: Response): Promise<void> {
    const role = await RoleModel.findByPk(req.params.id);
    if (!role) { res.status(404).json({ success: false, message: "Not found" }); return; }
    await role.destroy();
    res.status(204).send();
  },

  async assignPermission(req: Request, res: Response): Promise<void> {
    const role = await RoleModel.findByPk(req.params.id, { include: ["permissions"] });
    const perm = await PermissionModel.findByPk(req.params.permId);
    if (!role || !perm) { res.status(404).json({ success: false, message: "Not found" }); return; }
    await RolePermissionModel.findOrCreate({ where: { roleId: role.id, permissionId: perm.id } });
    const updated = await RoleModel.findByPk(role.id, { include: ["permissions"] });
    res.json({ success: true, data: updated?.toJSON() });
  },

  async removePermission(req: Request, res: Response): Promise<void> {
    await RolePermissionModel.destroy({ where: { roleId: req.params.id, permissionId: req.params.permId } });
    const role = await RoleModel.findByPk(req.params.id, { include: ["permissions"] });
    res.json({ success: true, data: role?.toJSON() });
  },
};
```

---

## src/controllers/permission.controller.ts

```typescript
import { Request, Response } from "express";
import { PermissionModel } from "../models";

export const PermissionController = {

  async list(req: Request, res: Response): Promise<void> {
    const perms = await PermissionModel.findAll();
    res.json({ success: true, data: perms.map((p) => p.toJSON()) });
  },

  async getOne(req: Request, res: Response): Promise<void> {
    const perm = await PermissionModel.findByPk(req.params.id);
    if (!perm) { res.status(404).json({ success: false, message: "Not found" }); return; }
    res.json({ success: true, data: perm.toJSON() });
  },

  async create(req: Request, res: Response): Promise<void> {
    const perm = await PermissionModel.create({
      name: req.body.name, resource: req.body.resource,
      action: req.body.action, description: req.body.description,
    });
    res.status(201).json({ success: true, data: perm.toJSON() });
  },

  async update(req: Request, res: Response): Promise<void> {
    const perm = await PermissionModel.findByPk(req.params.id);
    if (!perm) { res.status(404).json({ success: false, message: "Not found" }); return; }
    await perm.update(req.body);
    res.json({ success: true, data: perm.toJSON() });
  },

  async remove(req: Request, res: Response): Promise<void> {
    const perm = await PermissionModel.findByPk(req.params.id);
    if (!perm) { res.status(404).json({ success: false, message: "Not found" }); return; }
    await perm.destroy();
    res.status(204).send();
  },
};
```

---

## src/routes/auth.routes.ts

```typescript
import { Router }          from "express";
import { AuthController }  from "../controllers/auth.controller";
import { authenticate }    from "../middleware/authenticate";

const router = Router();
router.post("/register", AuthController.register);
router.post("/login",    AuthController.login);
router.delete("/logout", authenticate, AuthController.logout);
router.post("/refresh",  AuthController.refresh);
router.get("/me",        authenticate, AuthController.me);
export default router;
```

---

## src/routes/user.routes.ts

```typescript
import { Router }             from "express";
import { UserController }     from "../controllers/user.controller";
import { authenticate }       from "../middleware/authenticate";
import { authorize, authorizeRole } from "../middleware/authorize";

const router = Router();
router.get("/",                authenticate, authorize("users","read"),   UserController.list);
router.get("/:id",             authenticate, authorize("users","read"),   UserController.getOne);
router.post("/",               authenticate, authorize("users","create"), UserController.create);
router.put("/:id",             authenticate, authorize("users","update"), UserController.update);
router.delete("/:id",          authenticate, authorize("users","delete"), UserController.remove);
router.post("/:id/roles",      authenticate, authorizeRole("admin","super_admin"), UserController.assignRole);
router.delete("/:id/roles/:roleId", authenticate, authorizeRole("admin","super_admin"), UserController.removeRole);
export default router;
```

---

## src/routes/role.routes.ts

```typescript
import { Router }         from "express";
import { RoleController } from "../controllers/role.controller";
import { authenticate }   from "../middleware/authenticate";
import { authorize }      from "../middleware/authorize";

const router = Router();
router.get("/",                     authenticate, authorize("roles","read"),   RoleController.list);
router.get("/:id",                  authenticate, authorize("roles","read"),   RoleController.getOne);
router.post("/",                    authenticate, authorize("roles","create"), RoleController.create);
router.put("/:id",                  authenticate, authorize("roles","update"), RoleController.update);
router.delete("/:id",               authenticate, authorize("roles","delete"), RoleController.remove);
router.post("/:id/permissions/:permId",   authenticate, authorize("roles","update"), RoleController.assignPermission);
router.delete("/:id/permissions/:permId", authenticate, authorize("roles","update"), RoleController.removePermission);
export default router;
```

---

## src/routes/permission.routes.ts

```typescript
import { Router }               from "express";
import { PermissionController } from "../controllers/permission.controller";
import { authenticate }         from "../middleware/authenticate";
import { authorize }            from "../middleware/authorize";

const router = Router();
router.get("/",     authenticate, authorize("permissions","read"),   PermissionController.list);
router.get("/:id",  authenticate, authorize("permissions","read"),   PermissionController.getOne);
router.post("/",    authenticate, authorize("permissions","create"), PermissionController.create);
router.put("/:id",  authenticate, authorize("permissions","update"), PermissionController.update);
router.delete("/:id", authenticate, authorize("permissions","delete"), PermissionController.remove);
export default router;
```

---

## src/routes/index.ts

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

## src/app.ts

```typescript
import express, { Request, Response, NextFunction } from "express";
import cors         from "cors";
import helmet       from "helmet";
import rateLimit    from "express-rate-limit";
import { env }      from "./config/env";
import routes       from "./routes";

const app = express();

app.use(helmet());
app.use(cors({
  origin:         env.CORS_ORIGIN,
  credentials:    true,
  methods:        ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
  allowedHeaders: ["Content-Type", "Authorization"],
}));
app.use(rateLimit({ windowMs: 15 * 60 * 1000, max: 100 }));
app.use(express.json({ limit: "10mb" }));

app.use("/api", routes);
app.get("/health", (_req, res) => res.json({ status: "ok" }));

// Error handler
app.use((err: Error & { status?: number }, _req: Request, res: Response, _next: NextFunction) => {
  console.error(err.stack);
  res.status(err.status || 500).json({ success: false, message: err.message || "Server error" });
});

export default app;
```

---

## server.ts

```typescript
import "dotenv/config";
import app                 from "./src/app";
import { sequelize }       from "./src/models";
import { env }             from "./src/config/env";

async function bootstrap() {
  await sequelize.authenticate();
  console.log("✅ Database connected");

  // Sync all models (create tables if they don't exist)
  await sequelize.sync({ alter: env.NODE_ENV === "development" });
  console.log("✅ Tables synced");

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

## Database Switching (change .env only)

```env
# MySQL (default)
DB_DIALECT=mysql
DB_HOST=localhost
DB_PORT=3306
DB_NAME=nodejs_rbac_db
DB_USER=root
DB_PASSWORD=yourpassword

# SQLite (no server needed)
DB_DIALECT=sqlite
DB_STORAGE=./dev.db

# PostgreSQL
DB_DIALECT=postgres
DB_HOST=localhost
DB_PORT=5432
```

---

## API Endpoints

| Method | URL | Auth |
|--------|-----|------|
| POST | /api/auth/register | Public |
| POST | /api/auth/login | Public |
| DELETE | /api/auth/logout | Bearer |
| POST | /api/auth/refresh | Public |
| GET | /api/auth/me | Bearer |
| GET | /api/users?page=1&per_page=10&search= | authorize:users:read |
| POST | /api/users | authorize:users:create |
| GET | /api/users/:id | authorize:users:read |
| PUT | /api/users/:id | authorize:users:update |
| DELETE | /api/users/:id | authorize:users:delete |
| POST | /api/users/:id/roles | authorizeRole:admin |
| DELETE | /api/users/:id/roles/:roleId | authorizeRole:admin |
| GET | /api/roles | authorize:roles:read |
| POST | /api/roles | authorize:roles:create |
| PUT | /api/roles/:id | authorize:roles:update |
| DELETE | /api/roles/:id | authorize:roles:delete |
| POST | /api/roles/:id/permissions/:permId | authorize:roles:update |
| DELETE | /api/roles/:id/permissions/:permId | authorize:roles:update |
| GET | /api/permissions | authorize:permissions:read |
| POST | /api/permissions | authorize:permissions:create |
| PUT | /api/permissions/:id | authorize:permissions:update |
| DELETE | /api/permissions/:id | authorize:permissions:delete |
