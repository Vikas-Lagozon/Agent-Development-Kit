# React.js Frontend Architecture — Real-World Production Guide (TypeScript)

> Complete frontend in **TypeScript**, with both CSS Modules and Tailwind CSS styling options, full REST API integration with Axios + PyJWT backend, Dynamic RBAC UI guards, and complete CRUD flows.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Project Structure](#project-structure)
3. [Environment Setup](#environment-setup)
4. [TypeScript Configuration](#typescript-configuration)
5. [Styling — Option A: CSS Modules](#styling--option-a-css-modules)
6. [Styling — Option B: Tailwind CSS](#styling--option-b-tailwind-css)
7. [Types & Interfaces](#types--interfaces)
8. [API Layer & Axios (TypeScript)](#api-layer--axios-typescript)
9. [Zustand Auth Store (TypeScript)](#zustand-auth-store-typescript)
10. [RBAC — Permission & Role Gates (TypeScript)](#rbac--permission--role-gates-typescript)
11. [Custom Hooks (TypeScript)](#custom-hooks-typescript)
12. [Routing — React Router v6 (TypeScript)](#routing--react-router-v6-typescript)
13. [Layouts (TypeScript)](#layouts-typescript)
14. [Auth Pages (TypeScript)](#auth-pages-typescript)
15. [CRUD Pages (TypeScript)](#crud-pages-typescript)
16. [App Entry Point](#app-entry-point)

---

## Project Overview

- **TypeScript** throughout — all `.tsx` / `.ts` files, strict mode
- **CSS Modules** (Option A) or **Tailwind CSS** (Option B) — pick one
- **Axios** with automatic JWT Bearer injection + token refresh interceptor
- **Zustand** for typed auth state (persisted)
- **React Hook Form + Zod** for form validation
- Typed RBAC guards (`PermissionGate`, `RoleGate`, `PermissionRoute`)
- Works with all four backends: Flask, FastAPI, Django, Node.js

---

## Project Structure

```
react_project/
├── src/
│   ├── api/
│   │   ├── axios.ts               # Axios instance + interceptors
│   │   ├── auth.api.ts
│   │   ├── users.api.ts
│   │   ├── roles.api.ts
│   │   └── permissions.api.ts
│   │
│   ├── store/
│   │   ├── authStore.ts           # Zustand (typed)
│   │   └── uiStore.ts
│   │
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── usePermission.ts
│   │   ├── useCrud.ts             # Generic typed CRUD hook
│   │   └── usePagination.ts
│   │
│   ├── router/
│   │   ├── index.tsx
│   │   ├── ProtectedRoute.tsx
│   │   └── PermissionRoute.tsx
│   │
│   ├── layouts/
│   │   ├── MainLayout.tsx
│   │   └── AuthLayout.tsx
│   │
│   ├── pages/
│   │   ├── auth/
│   │   │   ├── Login.tsx
│   │   │   └── Register.tsx
│   │   ├── dashboard/
│   │   │   └── Dashboard.tsx
│   │   ├── users/
│   │   │   ├── UserList.tsx
│   │   │   └── UserForm.tsx
│   │   ├── roles/
│   │   │   ├── RoleList.tsx
│   │   │   └── RoleForm.tsx
│   │   └── permissions/
│   │       └── PermissionList.tsx
│   │
│   ├── components/
│   │   ├── rbac/
│   │   │   ├── PermissionGate.tsx
│   │   │   └── RoleGate.tsx
│   │   └── layout/
│   │       ├── Sidebar.tsx
│   │       └── Header.tsx
│   │
│   ├── styles/                    # CSS Modules path (Option A)
│   │   ├── globals.css
│   │   └── variables.css
│   │
│   ├── types/
│   │   ├── auth.types.ts
│   │   ├── user.types.ts
│   │   ├── role.types.ts
│   │   └── api.types.ts
│   │
│   ├── utils/
│   │   ├── token.ts
│   │   └── apiError.ts
│   │
│   ├── constants/
│   │   └── permissions.ts
│   │
│   ├── App.tsx
│   └── main.tsx
│
├── .env
├── .env.example
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.ts             # Option B only
├── postcss.config.js              # Option B only
├── package.json
└── README.md   # Complete information about setup and execution.
```

---

## Environment Setup

### package.json

```json
{
  "name": "react-rbac-frontend",
  "version": "1.0.0",
  "scripts": {
    "dev":     "vite",
    "build":   "tsc && vite build",
    "preview": "vite preview",
    "lint":    "eslint src --ext .ts,.tsx"
  },
  "dependencies": {
    "react":              "^18.3.1",
    "react-dom":          "^18.3.1",
    "react-router-dom":   "^6.24.1",
    "axios":              "^1.7.2",
    "zustand":            "^4.5.4",
    "react-hook-form":    "^7.52.1",
    "@hookform/resolvers": "^3.9.0",
    "zod":                "^3.23.8",
    "react-hot-toast":    "^2.4.1",
    "lucide-react":       "^0.408.0",
    "clsx":               "^2.1.1",
    "date-fns":           "^3.6.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react":  "^4.3.1",
    "vite":                  "^5.3.4",
    "typescript":            "^5.5.3",
    "@types/react":          "^18.3.3",
    "@types/react-dom":      "^18.3.0",
    "@types/node":           "^20.14.12",
    "eslint":                "^8.57.0",
    "tailwindcss":           "^3.4.6",
    "autoprefixer":          "^10.4.19",
    "postcss":               "^8.4.40"
  }
}
```

### .env

```env
VITE_API_BASE_URL=http://localhost:8000/api
VITE_APP_NAME="RBAC Admin Panel"
VITE_TOKEN_KEY=access_token
VITE_REFRESH_TOKEN_KEY=refresh_token
```

### .env.example

```env
VITE_API_BASE_URL=http://localhost:8000/api
VITE_APP_NAME="RBAC Admin Panel"
VITE_TOKEN_KEY=access_token
VITE_REFRESH_TOKEN_KEY=refresh_token
```

### vite.config.ts

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target:      "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
```

---

## TypeScript Configuration

### tsconfig.json

```json
{
  "compilerOptions": {
    "target":            "ES2022",
    "useDefineForClassFields": true,
    "lib":               ["ES2022", "DOM", "DOM.Iterable"],
    "module":            "ESNext",
    "skipLibCheck":      true,
    "moduleResolution":  "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules":   true,
    "noEmit":            true,
    "jsx":               "react-jsx",
    "strict":            true,
    "noUnusedLocals":    true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl":           ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

---

## Types & Interfaces

### src/types/api.types.ts

```typescript
export interface ApiResponse<T = unknown> {
  success:  boolean;
  message:  string;
  data?:    T;
  errors?:  Record<string, string[]> | null;
}

export interface PaginatedResponse<T> {
  items:    T[];
  total:    number;
  page:     number;
  pages:    number;
  per_page: number;
}
```

### src/types/auth.types.ts

```typescript
export interface LoginPayload {
  email:    string;
  password: string;
}

export interface RegisterPayload {
  username:   string;
  email:      string;
  password:   string;
  first_name?: string;
  last_name?:  string;
}

export interface AuthTokens {
  access_token:  string;
  refresh_token: string;
  token_type:    string;
}

export interface AuthUser {
  id:          number;
  username:    string;
  email:       string;
  first_name?: string;
  last_name?:  string;
  is_active:   boolean;
  roles:       string[];
  permissions: string[];
  created_at:  string;
  last_login?: string;
}
```

### src/types/user.types.ts

```typescript
export interface User {
  id:          number;
  username:    string;
  email:       string;
  first_name?: string;
  last_name?:  string;
  is_active:   boolean;
  is_verified: boolean;
  roles:       string[];
  permissions: string[];
  created_at:  string;
  last_login?: string;
}

export interface UserCreate {
  username:    string;
  email:       string;
  password:    string;
  first_name?: string;
  last_name?:  string;
}

export interface UserUpdate {
  first_name?: string;
  last_name?:  string;
  is_active?:  boolean;
  password?:   string;
}

export interface UserListResponse {
  users:    User[];
  total:    number;
  page:     number;
  pages:    number;
  per_page: number;
}
```

### src/types/role.types.ts

```typescript
import { Permission } from "./permission.types";

export interface Role {
  id:          number;
  name:        string;
  description?: string;
  permissions: Permission[];
  created_at:  string;
}

export interface RoleCreate {
  name:         string;
  description?: string;
}
```

### src/types/permission.types.ts (add to role.types.ts imports)

```typescript
export interface Permission {
  id:          number;
  name:        string;
  resource:    string;
  action:      string;
  description?: string;
  created_at:  string;
}

export interface PermissionCreate {
  name:         string;
  resource:     string;
  action:       string;
  description?: string;
}
```

---

## Styling — Option A: CSS Modules

Pick **one** option and use it throughout.

### src/styles/variables.css

```css
:root {
  --color-primary:       #2563eb;
  --color-primary-hover: #1d4ed8;
  --color-primary-light: #dbeafe;
  --color-danger:        #dc2626;
  --color-danger-hover:  #b91c1c;
  --color-success:       #16a34a;
  --color-warning:       #d97706;

  --bg-body:           #f8fafc;
  --bg-card:           #ffffff;
  --bg-sidebar:        #0f172a;
  --bg-sidebar-hover:  #1e293b;

  --text-primary:   #0f172a;
  --text-secondary: #64748b;
  --text-muted:     #94a3b8;
  --text-inverse:   #ffffff;

  --border-color:     #e2e8f0;
  --border-radius-sm: 4px;
  --border-radius-md: 8px;
  --border-radius-lg: 12px;

  --font-sans: "Inter", -apple-system, BlinkMacSystemFont, sans-serif;
  --text-xs:   0.75rem;
  --text-sm:   0.875rem;
  --text-base: 1rem;
  --text-lg:   1.125rem;
  --text-2xl:  1.5rem;

  --shadow-sm: 0 1px 2px rgba(0,0,0,.05);
  --shadow-md: 0 4px 6px rgba(0,0,0,.07);
  --shadow-lg: 0 10px 15px rgba(0,0,0,.1);

  --transition:     150ms ease;
  --sidebar-width:  260px;
  --header-height:  64px;
}
```

### src/styles/globals.css

```css
@import "./variables.css";
@import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap");

*, *::before, *::after { box-sizing: border-box; }

body {
  font-family: var(--font-sans);
  font-size:   var(--text-base);
  color:       var(--text-primary);
  background:  var(--bg-body);
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}
```

### src/pages/auth/Login.module.css (example component module)

```css
.container  { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: var(--bg-body); padding: 1rem; }
.card       { width: 100%; max-width: 420px; background: var(--bg-card); border-radius: var(--border-radius-lg); border: 1px solid var(--border-color); box-shadow: var(--shadow-lg); padding: 2rem; }
.header     { text-align: center; margin-bottom: 2rem; }
.title      { font-size: var(--text-2xl); font-weight: 700; color: var(--text-primary); margin: 0 0 0.5rem; }
.subtitle   { color: var(--text-secondary); font-size: var(--text-sm); margin: 0; }
.form       { display: flex; flex-direction: column; gap: 1.25rem; }
.field      { display: flex; flex-direction: column; gap: 0.5rem; }
.label      { font-size: var(--text-sm); font-weight: 500; color: var(--text-primary); }
.input      { padding: 0.625rem 0.875rem; font-size: var(--text-sm); border: 1px solid var(--border-color); border-radius: var(--border-radius-md); background: var(--bg-card); color: var(--text-primary); outline: none; transition: border-color var(--transition), box-shadow var(--transition); }
.input:focus     { border-color: var(--color-primary); box-shadow: 0 0 0 3px var(--color-primary-light); }
.inputError      { border-color: var(--color-danger); }
.error           { font-size: var(--text-xs); color: var(--color-danger); }
.submitBtn       { width: 100%; padding: 0.75rem; font-size: var(--text-sm); font-weight: 600; background: var(--color-primary); color: var(--text-inverse); border: none; border-radius: var(--border-radius-md); cursor: pointer; transition: background var(--transition); margin-top: 0.5rem; }
.submitBtn:hover:not(:disabled) { background: var(--color-primary-hover); }
.submitBtn:disabled              { opacity: 0.6; cursor: not-allowed; }
.footer     { text-align: center; font-size: var(--text-sm); color: var(--text-secondary); margin-top: 1.5rem; }
.link       { color: var(--color-primary); font-weight: 500; }
.link:hover { text-decoration: underline; }
```

---

## Styling — Option B: Tailwind CSS

### Installation

```bash
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

### tailwind.config.ts

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  content:   ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode:  "class",
  theme: {
    extend: {
      colors: {
        primary: {
          50:  "#eff6ff",
          100: "#dbeafe",
          500: "#3b82f6",
          600: "#2563eb",
          700: "#1d4ed8",
          900: "#1e3a8a",
        },
        sidebar: { DEFAULT: "#0f172a", hover: "#1e293b" },
      },
      fontFamily: { sans: ["Inter", "system-ui", "sans-serif"] },
      width:  { sidebar: "260px" },
      height: { header:  "64px" },
    },
  },
  plugins: [],
};

export default config;
```

### src/styles/globals.css (Tailwind)

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap");

@layer base {
  body { @apply font-sans text-slate-900 bg-slate-50 antialiased; }
  *, *::before, *::after { @apply box-border; }
}

@layer components {
  .btn-primary   { @apply inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-primary-600 text-white rounded-lg border border-transparent hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-150; }
  .btn-secondary { @apply inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-white text-slate-700 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-150; }
  .btn-danger    { @apply inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-red-600 text-white rounded-lg border border-transparent hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-150; }
  .input-field   { @apply w-full px-3 py-2 text-sm border border-slate-200 rounded-lg bg-white text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:bg-slate-50 transition-colors duration-150; }
  .card          { @apply bg-white rounded-xl border border-slate-200 shadow-sm; }
  .badge-success { @apply inline-flex items-center px-2 py-0.5 text-xs font-medium bg-green-100 text-green-700 rounded-full; }
  .badge-danger  { @apply inline-flex items-center px-2 py-0.5 text-xs font-medium bg-red-100 text-red-700 rounded-full; }
  .badge-primary { @apply inline-flex items-center px-2 py-0.5 text-xs font-medium bg-primary-100 text-primary-700 rounded-full; }
}
```

---

## API Layer & Axios (TypeScript)

### src/utils/token.ts

```typescript
const ACCESS_KEY  = import.meta.env.VITE_TOKEN_KEY         || "access_token";
const REFRESH_KEY = import.meta.env.VITE_REFRESH_TOKEN_KEY || "refresh_token";

export const tokenUtils = {
  getAccess:       (): string | null => localStorage.getItem(ACCESS_KEY),
  getRefresh:      (): string | null => localStorage.getItem(REFRESH_KEY),
  setTokens:       (access: string, refresh?: string | null): void => {
    localStorage.setItem(ACCESS_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  },
  clearTokens:     (): void => {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
  isAuthenticated: (): boolean => !!localStorage.getItem(ACCESS_KEY),
};
```

### src/api/axios.ts

```typescript
import axios, { AxiosInstance, AxiosResponse, InternalAxiosRequestConfig } from "axios";
import { tokenUtils } from "@/utils/token";

interface FailedRequest {
  resolve: (token: string) => void;
  reject:  (error: unknown)  => void;
}

let isRefreshing  = false;
let failedQueue:  FailedRequest[] = [];

function processQueue(error: unknown, token: string | null = null): void {
  failedQueue.forEach((prom) => {
    if (error) prom.reject(error);
    else if (token) prom.resolve(token);
  });
  failedQueue = [];
}

const api: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api",
  timeout: 15_000,
  headers: {
    "Content-Type": "application/json",
    "Accept":       "application/json",
  },
});

// ── Request interceptor: attach Bearer token ──────────────────────────────
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = tokenUtils.getAccess();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Response interceptor: auto-refresh on 401 ─────────────────────────────
api.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      tokenUtils.getRefresh()
    ) {
      if (isRefreshing) {
        return new Promise<string>((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        });
      }

      originalRequest._retry = true;
      isRefreshing            = true;

      try {
        const refresh = tokenUtils.getRefresh()!;
        const res     = await axios.post(
          `${import.meta.env.VITE_API_BASE_URL}/auth/refresh`,
          { refresh_token: refresh }
        );
        const newToken: string =
          res.data?.data?.access_token ?? res.data?.access_token;

        tokenUtils.setTokens(newToken);
        processQueue(null, newToken);
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        tokenUtils.clearTokens();
        window.location.href = "/login";
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default api;
```

### src/api/auth.api.ts

```typescript
import api from "./axios";
import type { ApiResponse } from "@/types/api.types";
import type { LoginPayload, RegisterPayload, AuthTokens, AuthUser } from "@/types/auth.types";

interface LoginResponse extends AuthTokens {
  user: AuthUser;
}

export const authApi = {
  register: (data: RegisterPayload) =>
    api.post<ApiResponse<AuthUser>>("/auth/register", data),

  login: (data: LoginPayload) =>
    api.post<ApiResponse<LoginResponse>>("/auth/login", data),

  logout: (refreshToken: string) =>
    api.delete<ApiResponse>("/auth/logout", { data: { refresh_token: refreshToken } }),

  refresh: (refreshToken: string) =>
    api.post<ApiResponse<{ access_token: string }>>("/auth/refresh", { refresh_token: refreshToken }),

  me: () =>
    api.get<ApiResponse<AuthUser>>("/auth/me"),
};
```

### src/api/users.api.ts

```typescript
import api from "./axios";
import type { ApiResponse } from "@/types/api.types";
import type { User, UserCreate, UserUpdate, UserListResponse } from "@/types/user.types";

export interface UserListParams {
  page?:     number;
  per_page?: number;
  search?:   string;
}

export const usersApi = {
  getAll:     (params?: UserListParams) =>
    api.get<ApiResponse<UserListResponse>>("/users/", { params }),

  getOne:     (id: number) =>
    api.get<ApiResponse<User>>(`/users/${id}`),

  create:     (data: UserCreate) =>
    api.post<ApiResponse<User>>("/users/", data),

  update:     (id: number, data: UserUpdate) =>
    api.put<ApiResponse<User>>(`/users/${id}`, data),

  delete:     (id: number) =>
    api.delete<ApiResponse>(`/users/${id}`),

  assignRole: (userId: number, roleId: number) =>
    api.post<ApiResponse<User>>(`/users/${userId}/roles`, { role_id: roleId }),

  removeRole: (userId: number, roleId: number) =>
    api.delete<ApiResponse<User>>(`/users/${userId}/roles/${roleId}`),
};
```

### src/api/roles.api.ts

```typescript
import api from "./axios";
import type { ApiResponse } from "@/types/api.types";
import type { Role, RoleCreate } from "@/types/role.types";

export const rolesApi = {
  getAll:            ()                          => api.get<ApiResponse<Role[]>>("/roles/"),
  getOne:            (id: number)               => api.get<ApiResponse<Role>>(`/roles/${id}`),
  create:            (data: RoleCreate)         => api.post<ApiResponse<Role>>("/roles/", data),
  update:            (id: number, data: Partial<RoleCreate>) => api.put<ApiResponse<Role>>(`/roles/${id}`, data),
  delete:            (id: number)               => api.delete<ApiResponse>(`/roles/${id}`),
  assignPermission:  (roleId: number, permId: number) =>
    api.post<ApiResponse<Role>>(`/roles/${roleId}/permissions`, { permission_id: permId }),
  removePermission:  (roleId: number, permId: number) =>
    api.delete<ApiResponse<Role>>(`/roles/${roleId}/permissions/${permId}`),
};
```

### src/api/permissions.api.ts

```typescript
import api from "./axios";
import type { ApiResponse }       from "@/types/api.types";
import type { Permission, PermissionCreate } from "@/types/permission.types";

export const permissionsApi = {
  getAll:  ()                            => api.get<ApiResponse<Permission[]>>("/permissions/"),
  getOne:  (id: number)                 => api.get<ApiResponse<Permission>>(`/permissions/${id}`),
  create:  (data: PermissionCreate)     => api.post<ApiResponse<Permission>>("/permissions/", data),
  update:  (id: number, data: Partial<PermissionCreate>) =>
    api.put<ApiResponse<Permission>>(`/permissions/${id}`, data),
  delete:  (id: number)                 => api.delete<ApiResponse>(`/permissions/${id}`),
};
```

---

## Zustand Auth Store (TypeScript)

### src/store/authStore.ts

```typescript
import { create } from "zustand";
import { persist, devtools } from "zustand/middleware";
import { immer } from "zustand/middleware/immer";
import toast from "react-hot-toast";

import { tokenUtils }           from "@/utils/token";
import { authApi }              from "@/api/auth.api";
import type { AuthUser, LoginPayload, RegisterPayload } from "@/types/auth.types";

interface AuthState {
  user:            AuthUser | null;
  isAuthenticated: boolean;
  isLoading:       boolean;
}

interface AuthActions {
  login:     (payload: LoginPayload)    => Promise<{ success: boolean }>;
  register:  (payload: RegisterPayload) => Promise<{ success: boolean }>;
  logout:    ()                         => Promise<void>;
  fetchMe:   ()                         => Promise<void>;
  hasPermission: (resource: string, action: string) => boolean;
  hasRole:       (roleName: string)                 => boolean;
  hasAnyRole:    (...roles: string[])               => boolean;
}

type AuthStore = AuthState & AuthActions;

const useAuthStore = create<AuthStore>()(
  devtools(
    persist(
      immer((set, get) => ({
        user:            null,
        isAuthenticated: false,
        isLoading:       false,

        login: async (payload) => {
          set((s) => { s.isLoading = true; });
          try {
            const res  = await authApi.login(payload);
            const data = res.data?.data;
            if (!data) throw new Error("No data returned");

            tokenUtils.setTokens(data.access_token, data.refresh_token);
            set((s) => {
              s.user            = data.user;
              s.isAuthenticated = true;
              s.isLoading       = false;
            });
            toast.success(`Welcome back, ${data.user.username}!`);
            return { success: true };
          } catch (err: any) {
            set((s) => { s.isLoading = false; });
            const msg = err.response?.data?.message || "Login failed";
            toast.error(msg);
            return { success: false };
          }
        },

        register: async (payload) => {
          set((s) => { s.isLoading = true; });
          try {
            await authApi.register(payload);
            set((s) => { s.isLoading = false; });
            toast.success("Account created! Please log in.");
            return { success: true };
          } catch (err: any) {
            set((s) => { s.isLoading = false; });
            toast.error(err.response?.data?.message || "Registration failed");
            return { success: false };
          }
        },

        logout: async () => {
          try {
            const refresh = tokenUtils.getRefresh();
            if (refresh) await authApi.logout(refresh);
          } catch {
            // logout regardless
          } finally {
            tokenUtils.clearTokens();
            set((s) => { s.user = null; s.isAuthenticated = false; });
            toast.success("Logged out successfully");
          }
        },

        fetchMe: async () => {
          try {
            const res  = await authApi.me();
            const user = res.data?.data;
            if (user) set((s) => { s.user = user; s.isAuthenticated = true; });
          } catch {
            tokenUtils.clearTokens();
            set((s) => { s.user = null; s.isAuthenticated = false; });
          }
        },

        hasPermission: (resource, action) => {
          const { user } = get();
          return user?.permissions?.includes(`${resource}:${action}`) ?? false;
        },

        hasRole: (roleName) => {
          const { user } = get();
          return user?.roles?.includes(roleName) ?? false;
        },

        hasAnyRole: (...roles) => {
          const { user } = get();
          return roles.some((r) => user?.roles?.includes(r));
        },
      })),
      {
        name:       "auth-storage",
        partialize: (state) => ({ user: state.user, isAuthenticated: state.isAuthenticated }),
      }
    )
  )
);

export default useAuthStore;
```

### src/store/uiStore.ts

```typescript
import { create } from "zustand";

interface UiState {
  sidebarOpen:    boolean;
  toggleSidebar:  () => void;
  setSidebar:     (open: boolean) => void;
}

const useUiStore = create<UiState>((set) => ({
  sidebarOpen:   true,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setSidebar:    (open) => set({ sidebarOpen: open }),
}));

export default useUiStore;
```

---

## RBAC — Permission & Role Gates (TypeScript)

### src/components/rbac/PermissionGate.tsx

```tsx
import type { ReactNode } from "react";
import useAuthStore from "@/store/authStore";

interface PermissionGateProps {
  resource?:    string;
  action?:      string;
  permissions?: string[];        // alternative: ["users:read", "roles:create"]
  every?:       boolean;         // require ALL permissions (default: any)
  children:     ReactNode;
  fallback?:    ReactNode;
}

/**
 * Renders children only if the current user has the required permission(s).
 *
 * Usage:
 *   <PermissionGate resource="users" action="create">
 *     <CreateButton />
 *   </PermissionGate>
 *
 *   <PermissionGate permissions={["users:delete"]} fallback={<DisabledBtn />}>
 *     <DeleteButton />
 *   </PermissionGate>
 */
const PermissionGate = ({
  resource, action, permissions = [], every = false, children, fallback = null,
}: PermissionGateProps): JSX.Element => {
  const { hasPermission } = useAuthStore();

  let allowed: boolean;

  if (permissions.length > 0) {
    allowed = every
      ? permissions.every((p) => { const [r, a] = p.split(":"); return hasPermission(r, a); })
      : permissions.some((p)  => { const [r, a] = p.split(":"); return hasPermission(r, a); });
  } else {
    allowed = !!(resource && action && hasPermission(resource, action));
  }

  return <>{allowed ? children : fallback}</>;
};

export default PermissionGate;
```

### src/components/rbac/RoleGate.tsx

```tsx
import type { ReactNode } from "react";
import useAuthStore from "@/store/authStore";

interface RoleGateProps {
  roles:     string[];
  children:  ReactNode;
  fallback?: ReactNode;
}

/**
 * Renders children only if the current user has one of the given roles.
 *
 *   <RoleGate roles={["admin", "super_admin"]}>
 *     <AdminPanel />
 *   </RoleGate>
 */
const RoleGate = ({ roles, children, fallback = null }: RoleGateProps): JSX.Element => {
  const { hasAnyRole } = useAuthStore();
  return <>{hasAnyRole(...roles) ? children : fallback}</>;
};

export default RoleGate;
```

### src/hooks/usePermission.ts

```typescript
import useAuthStore from "@/store/authStore";

interface UsePermissionReturn {
  can:         (resource: string, action: string) => boolean;
  hasRole:     (roleName: string)                 => boolean;
  hasAnyRole:  (...roles: string[])               => boolean;
  isAdmin:     ()                                 => boolean;
  isSuperAdmin:()                                 => boolean;
  user:        ReturnType<typeof useAuthStore>["user"];
}

export const usePermission = (): UsePermissionReturn => {
  const { hasPermission, hasRole, hasAnyRole, user } = useAuthStore();

  return {
    can:          (resource, action) => hasPermission(resource, action),
    hasRole,
    hasAnyRole,
    isAdmin:      () => hasAnyRole("admin", "super_admin"),
    isSuperAdmin: () => hasRole("super_admin"),
    user,
  };
};
```

---

## Custom Hooks (TypeScript)

### src/hooks/useCrud.ts

```typescript
import { useState, useEffect, useCallback } from "react";
import toast from "react-hot-toast";
import type { ApiResponse } from "@/types/api.types";

interface CrudApiModule<T, TCreate = Partial<T>, TUpdate = Partial<T>> {
  getAll:  (params?: Record<string, unknown>) => Promise<{ data: ApiResponse<any> }>;
  create?: (data: TCreate)            => Promise<{ data: ApiResponse<T> }>;
  update?: (id: number, data: TUpdate)=> Promise<{ data: ApiResponse<T> }>;
  delete?: (id: number)               => Promise<{ data: ApiResponse }>;
}

interface Pagination {
  total:    number;
  page:     number;
  pages:    number;
  per_page: number;
}

interface UseCrudOptions {
  fetchOnMount?: boolean;
  params?:       Record<string, unknown>;
  listKey?:      string;   // key inside data (e.g. "users", "roles")
}

interface UseCrudReturn<T> {
  items:      T[];
  pagination: Pagination | null;
  loading:    boolean;
  error:      Error | null;
  refetch:    (params?: Record<string, unknown>) => Promise<void>;
  create:     (data: unknown, msg?: string) => Promise<{ success: boolean; data?: T }>;
  update:     (id: number, data: unknown, msg?: string) => Promise<{ success: boolean; data?: T }>;
  remove:     (id: number, msg?: string) => Promise<{ success: boolean }>;
}

function useCrud<T extends { id: number }>(
  apiModule: CrudApiModule<T>,
  options: UseCrudOptions = {}
): UseCrudReturn<T> {
  const { fetchOnMount = true, params = {}, listKey } = options;
  const [items,      setItems]      = useState<T[]>([]);
  const [pagination, setPagination] = useState<Pagination | null>(null);
  const [loading,    setLoading]    = useState(false);
  const [error,      setError]      = useState<Error | null>(null);

  const refetch = useCallback(async (extraParams: Record<string, unknown> = {}) => {
    setLoading(true);
    setError(null);
    try {
      const res  = await apiModule.getAll({ ...params, ...extraParams });
      const raw  = res.data?.data;
      if (!raw) return;

      // Detect list — either raw is array, or contains a known list key
      const key  = listKey || Object.keys(raw).find((k) => Array.isArray((raw as any)[k]));
      const list = key ? (raw as any)[key] : Array.isArray(raw) ? raw : [];
      setItems(list as T[]);

      if (raw && typeof raw === "object" && "total" in raw) {
        setPagination({
          total:    (raw as any).total,
          page:     (raw as any).page,
          pages:    (raw as any).pages,
          per_page: (raw as any).per_page,
        });
      }
    } catch (err) {
      const e = err as Error;
      setError(e);
      toast.error((err as any).response?.data?.message || "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, []);

  const create = useCallback(async (data: unknown, msg = "Created successfully") => {
    try {
      const res  = await apiModule.create!(data as any);
      const item = res.data?.data as T;
      setItems((prev) => [item, ...prev]);
      toast.success(msg);
      return { success: true, data: item };
    } catch (err) {
      toast.error((err as any).response?.data?.message || "Create failed");
      return { success: false };
    }
  }, [apiModule]);

  const update = useCallback(async (id: number, data: unknown, msg = "Updated successfully") => {
    try {
      const res     = await apiModule.update!(id, data as any);
      const updated = res.data?.data as T;
      setItems((prev) => prev.map((i) => (i.id === id ? updated : i)));
      toast.success(msg);
      return { success: true, data: updated };
    } catch (err) {
      toast.error((err as any).response?.data?.message || "Update failed");
      return { success: false };
    }
  }, [apiModule]);

  const remove = useCallback(async (id: number, msg = "Deleted successfully") => {
    try {
      await apiModule.delete!(id);
      setItems((prev) => prev.filter((i) => i.id !== id));
      toast.success(msg);
      return { success: true };
    } catch (err) {
      toast.error((err as any).response?.data?.message || "Delete failed");
      return { success: false };
    }
  }, [apiModule]);

  useEffect(() => {
    if (fetchOnMount) refetch();
  }, [fetchOnMount]);

  return { items, pagination, loading, error, refetch, create, update, remove };
}

export default useCrud;
```

### src/hooks/usePagination.ts

```typescript
import { useState, useCallback } from "react";

interface PaginationState {
  page:    number;
  pages:   number;
  total:   number;
  perPage: number;
}

interface UsePaginationReturn<T> {
  data:             T[];
  pagination:       PaginationState;
  loading:          boolean;
  search:           string;
  handleSearch:     (term: string)  => void;
  handlePageChange: (page: number)  => void;
  reload:           (page?: number, searchTerm?: string) => void;
}

function usePagination<T>(
  apiCall: (params: Record<string, unknown>) => Promise<{ data: { data: any } }>,
  initialParams: Record<string, unknown> = {},
  listKey = ""
): UsePaginationReturn<T> {
  const [data,       setData]       = useState<T[]>([]);
  const [pagination, setPagination] = useState<PaginationState>({ page: 1, pages: 1, total: 0, perPage: 10 });
  const [loading,    setLoading]    = useState(false);
  const [search,     setSearch]     = useState("");

  const load = useCallback(async (page = 1, searchTerm = search, extra: Record<string, unknown> = {}) => {
    setLoading(true);
    try {
      const res  = await apiCall({ ...initialParams, page, per_page: pagination.perPage, search: searchTerm, ...extra });
      const raw  = res.data?.data;
      if (!raw) return;

      const key  = listKey || Object.keys(raw).find((k) => Array.isArray((raw as any)[k])) || "";
      const list = key ? (raw as any)[key] : Array.isArray(raw) ? raw : [];
      setData(list as T[]);
      setPagination({
        page:    raw.page     ?? page,
        pages:   raw.pages    ?? 1,
        total:   raw.total    ?? list.length,
        perPage: raw.per_page ?? 10,
      });
    } finally {
      setLoading(false);
    }
  }, [search, pagination.perPage]);

  const handleSearch     = (term: string)  => { setSearch(term); load(1, term); };
  const handlePageChange = (page: number)  => load(page);

  return { data, pagination, loading, search, handleSearch, handlePageChange, reload: load };
}

export default usePagination;
```

---

## Routing — React Router v6 (TypeScript)

### src/router/ProtectedRoute.tsx

```tsx
import { Navigate, useLocation } from "react-router-dom";
import useAuthStore from "@/store/authStore";
import type { JSX } from "react";

interface ProtectedRouteProps { children: JSX.Element; }

const ProtectedRoute = ({ children }: ProtectedRouteProps): JSX.Element => {
  const { isAuthenticated } = useAuthStore();
  const location            = useLocation();
  if (!isAuthenticated) return <Navigate to="/login" state={{ from: location }} replace />;
  return children;
};

export default ProtectedRoute;
```

### src/router/PermissionRoute.tsx

```tsx
import { Navigate } from "react-router-dom";
import useAuthStore from "@/store/authStore";
import type { JSX } from "react";

interface PermissionRouteProps {
  resource?:   string;
  action?:     string;
  roles?:      string[];
  children:    JSX.Element;
  redirectTo?: string;
}

const PermissionRoute = ({
  resource, action, roles, children, redirectTo = "/403",
}: PermissionRouteProps): JSX.Element => {
  const { hasPermission, hasAnyRole } = useAuthStore();

  let allowed = true;
  if (resource && action) allowed = hasPermission(resource, action);
  if (roles?.length)      allowed = allowed && hasAnyRole(...roles);

  return allowed ? children : <Navigate to={redirectTo} replace />;
};

export default PermissionRoute;
```

### src/router/index.tsx

```tsx
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import MainLayout      from "@/layouts/MainLayout";
import AuthLayout      from "@/layouts/AuthLayout";
import ProtectedRoute  from "./ProtectedRoute";
import PermissionRoute from "./PermissionRoute";

import Login           from "@/pages/auth/Login";
import Register        from "@/pages/auth/Register";
import Dashboard       from "@/pages/dashboard/Dashboard";
import UserList        from "@/pages/users/UserList";
import UserForm        from "@/pages/users/UserForm";
import RoleList        from "@/pages/roles/RoleList";
import RoleForm        from "@/pages/roles/RoleForm";
import PermissionList  from "@/pages/permissions/PermissionList";

const router = createBrowserRouter([
  {
    element:  <AuthLayout />,
    children: [
      { path: "/login",    element: <Login /> },
      { path: "/register", element: <Register /> },
    ],
  },
  {
    element: <ProtectedRoute><MainLayout /></ProtectedRoute>,
    children: [
      { index: true, element: <Dashboard /> },
      {
        path: "users",
        element: <PermissionRoute resource="users" action="read"><UserList /></PermissionRoute>,
      },
      {
        path: "users/new",
        element: <PermissionRoute resource="users" action="create"><UserForm /></PermissionRoute>,
      },
      {
        path: "users/:id/edit",
        element: <PermissionRoute resource="users" action="update"><UserForm /></PermissionRoute>,
      },
      {
        path: "roles",
        element: <PermissionRoute resource="roles" action="read"><RoleList /></PermissionRoute>,
      },
      {
        path: "roles/new",
        element: <PermissionRoute resource="roles" action="create"><RoleForm /></PermissionRoute>,
      },
      {
        path: "permissions",
        element: <PermissionRoute resource="permissions" action="read"><PermissionList /></PermissionRoute>,
      },
    ],
  },
]);

export const AppRouter = (): JSX.Element => <RouterProvider router={router} />;
```

---

## Layouts (TypeScript)

### src/layouts/MainLayout.tsx

```tsx
import { Outlet } from "react-router-dom";
import Sidebar   from "@/components/layout/Sidebar";
import Header    from "@/components/layout/Header";
import useUiStore from "@/store/uiStore";

const MainLayout = (): JSX.Element => {
  const { sidebarOpen } = useUiStore();
  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      <Sidebar />
      <div
        className="flex-1 flex flex-col overflow-hidden transition-all duration-300"
        style={{ marginLeft: sidebarOpen ? "260px" : "0" }}
      >
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default MainLayout;
```

### src/components/layout/Sidebar.tsx

```tsx
import { NavLink }     from "react-router-dom";
import { LayoutDashboard, Users, Shield, Key, LogOut, Menu } from "lucide-react";
import clsx            from "clsx";
import useAuthStore    from "@/store/authStore";
import useUiStore      from "@/store/uiStore";
import PermissionGate  from "@/components/rbac/PermissionGate";

interface NavItem {
  to:        string;
  icon:      React.ComponentType<{ size: number }>;
  label:     string;
  resource?: string;
  action?:   string;
}

const navItems: NavItem[] = [
  { to: "/",            icon: LayoutDashboard, label: "Dashboard" },
  { to: "/users",       icon: Users,           label: "Users",       resource: "users",       action: "read" },
  { to: "/roles",       icon: Shield,          label: "Roles",       resource: "roles",       action: "read" },
  { to: "/permissions", icon: Key,             label: "Permissions", resource: "permissions", action: "read" },
];

const Sidebar = (): JSX.Element => {
  const { user, logout }        = useAuthStore();
  const { sidebarOpen, toggleSidebar } = useUiStore();

  if (!sidebarOpen) return <></>;

  return (
    <aside className="fixed left-0 top-0 h-screen w-[260px] bg-slate-900 flex flex-col z-40">
      {/* Logo */}
      <div className="flex items-center justify-between h-16 px-4 border-b border-slate-700/50">
        <span className="text-white font-semibold text-lg">🔐 RBAC Admin</span>
        <button onClick={toggleSidebar} className="text-slate-400 hover:text-white transition-colors">
          <Menu size={18} />
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {navItems.map(({ to, icon: Icon, label, resource, action }) => {
          const linkEl = (
            <NavLink
              key={to} to={to} end={to === "/"}
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary-600 text-white"
                    : "text-slate-400 hover:text-white hover:bg-slate-800"
                )
              }
            >
              <Icon size={17} />
              {label}
            </NavLink>
          );
          return resource && action ? (
            <PermissionGate key={to} resource={resource} action={action}>{linkEl}</PermissionGate>
          ) : linkEl;
        })}
      </nav>

      {/* User footer */}
      <div className="p-4 border-t border-slate-700/50">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-8 h-8 rounded-full bg-primary-600 flex items-center justify-center text-white text-xs font-semibold">
            {user?.username?.[0]?.toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">{user?.username}</p>
            <p className="text-xs text-slate-400 truncate">{user?.email}</p>
          </div>
        </div>
        <button
          onClick={logout}
          className="flex items-center gap-2 w-full px-3 py-2 text-sm text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
        >
          <LogOut size={16} />
          Sign out
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
```

---

## Auth Pages (TypeScript)

### src/pages/auth/Login.tsx (Tailwind version)

```tsx
import { useForm }                    from "react-hook-form";
import { zodResolver }                from "@hookform/resolvers/zod";
import { z }                          from "zod";
import { useNavigate, Link, useLocation } from "react-router-dom";
import { LogIn }                      from "lucide-react";
import useAuthStore                   from "@/store/authStore";
import type { LoginPayload }          from "@/types/auth.types";

const schema = z.object({
  email:    z.string().email("Invalid email"),
  password: z.string().min(6, "Password too short"),
});

type FormData = z.infer<typeof schema>;

const Login = (): JSX.Element => {
  const { login, isLoading } = useAuthStore();
  const navigate             = useNavigate();
  const location             = useLocation();
  const from                 = (location.state as { from?: { pathname: string } })?.from?.pathname || "/";

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormData): Promise<void> => {
    const result = await login(data as LoginPayload);
    if (result.success) navigate(from, { replace: true });
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
      <div className="w-full max-w-md bg-white rounded-2xl border border-slate-200 shadow-lg p-8">
        <div className="text-center mb-8">
          <div className="text-4xl mb-4">🔐</div>
          <h1 className="text-2xl font-bold text-slate-900 mb-1">Sign in</h1>
          <p className="text-sm text-slate-500">Access your admin panel</p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Email</label>
            <input
              {...register("email")}
              type="email"
              placeholder="admin@example.com"
              autoComplete="email"
              className={`input-field ${errors.email ? "border-red-500 focus:ring-red-500" : ""}`}
            />
            {errors.email && <p className="text-xs text-red-600 mt-1">{errors.email.message}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Password</label>
            <input
              {...register("password")}
              type="password"
              placeholder="••••••••"
              autoComplete="current-password"
              className={`input-field ${errors.password ? "border-red-500 focus:ring-red-500" : ""}`}
            />
            {errors.password && <p className="text-xs text-red-600 mt-1">{errors.password.message}</p>}
          </div>

          <button type="submit" disabled={isLoading} className="btn-primary w-full justify-center py-3 mt-2">
            <LogIn size={16} />
            {isLoading ? "Signing in..." : "Sign In"}
          </button>
        </form>

        <p className="text-center text-sm text-slate-500 mt-6">
          No account?{" "}
          <Link to="/register" className="text-primary-600 font-medium hover:underline">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
};

export default Login;
```

---

## CRUD Pages (TypeScript)

### src/pages/users/UserList.tsx

```tsx
import { useState }         from "react";
import { useNavigate }      from "react-router-dom";
import { Plus, Search, Edit2, Trash2 } from "lucide-react";
import toast                from "react-hot-toast";
import usePagination        from "@/hooks/usePagination";
import PermissionGate       from "@/components/rbac/PermissionGate";
import { usersApi }         from "@/api/users.api";
import type { User }        from "@/types/user.types";

const UserList = (): JSX.Element => {
  const navigate             = useNavigate();
  const [searchInput, setSearchInput] = useState("");

  const {
    data: users,
    pagination,
    loading,
    handleSearch,
    handlePageChange,
    reload,
  } = usePagination<User>(usersApi.getAll as any, {}, "users");

  const handleDelete = async (user: User): Promise<void> => {
    if (!window.confirm(`Delete ${user.username}?`)) return;
    try {
      await usersApi.delete(user.id);
      toast.success("User deleted");
      reload();
    } catch {
      toast.error("Delete failed");
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Users</h1>
          <p className="text-sm text-slate-500 mt-0.5">{pagination.total} total users</p>
        </div>
        <PermissionGate resource="users" action="create">
          <button onClick={() => navigate("/users/new")} className="btn-primary">
            <Plus size={16} /> New User
          </button>
        </PermissionGate>
      </div>

      {/* Search */}
      <div className="card p-4">
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search by name or email..."
            value={searchInput}
            onChange={(e) => { setSearchInput(e.target.value); handleSearch(e.target.value); }}
            className="input-field pl-9"
          />
        </div>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="text-left px-4 py-3 font-semibold text-slate-600">User</th>
                <th className="text-left px-4 py-3 font-semibold text-slate-600">Email</th>
                <th className="text-left px-4 py-3 font-semibold text-slate-600">Roles</th>
                <th className="text-left px-4 py-3 font-semibold text-slate-600">Status</th>
                <th className="text-right px-4 py-3 font-semibold text-slate-600">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr><td colSpan={5} className="text-center py-12 text-slate-400">Loading...</td></tr>
              ) : users.length === 0 ? (
                <tr><td colSpan={5} className="text-center py-12 text-slate-400">No users found</td></tr>
              ) : users.map((user) => (
                <tr key={user.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center text-primary-700 font-semibold text-xs">
                        {user.username?.[0]?.toUpperCase()}
                      </div>
                      <span className="font-medium text-slate-900">{user.username}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{user.email}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {user.roles?.map((role) => <span key={role} className="badge-primary">{role}</span>)}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {user.is_active ? <span className="badge-success">Active</span> : <span className="badge-danger">Inactive</span>}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-2">
                      <PermissionGate resource="users" action="update">
                        <button onClick={() => navigate(`/users/${user.id}/edit`)} className="p-1.5 text-slate-500 hover:text-primary-600 hover:bg-primary-50 rounded-md transition-colors" title="Edit">
                          <Edit2 size={15} />
                        </button>
                      </PermissionGate>
                      <PermissionGate resource="users" action="delete">
                        <button onClick={() => handleDelete(user)} className="p-1.5 text-slate-500 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors" title="Delete">
                          <Trash2 size={15} />
                        </button>
                      </PermissionGate>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {pagination.pages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-slate-200">
            <p className="text-sm text-slate-500">Showing {users.length} of {pagination.total}</p>
            <div className="flex gap-1">
              {Array.from({ length: pagination.pages }, (_, i) => i + 1).map((p) => (
                <button
                  key={p} onClick={() => handlePageChange(p)}
                  className={`w-8 h-8 text-sm rounded-md transition-colors ${p === pagination.page ? "bg-primary-600 text-white" : "text-slate-600 hover:bg-slate-100"}`}
                >{p}</button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default UserList;
```

### src/pages/users/UserForm.tsx

```tsx
import { useEffect, useState }  from "react";
import { useForm }              from "react-hook-form";
import { zodResolver }          from "@hookform/resolvers/zod";
import { z }                   from "zod";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Save }      from "lucide-react";
import toast                    from "react-hot-toast";
import { usersApi }             from "@/api/users.api";

const createSchema = z.object({
  username:   z.string().min(3),
  email:      z.string().email(),
  password:   z.string().min(8),
  first_name: z.string().optional(),
  last_name:  z.string().optional(),
});

const editSchema = createSchema.omit({ password: true }).extend({
  password: z.string().min(8).optional().or(z.literal("")),
});

type CreateForm = z.infer<typeof createSchema>;
type EditForm   = z.infer<typeof editSchema>;

const UserForm = (): JSX.Element => {
  const { id }        = useParams<{ id?: string }>();
  const isEdit        = !!id;
  const navigate      = useNavigate();
  const [submitting, setSubmitting] = useState(false);

  const { register, handleSubmit, reset, formState: { errors } } = useForm<CreateForm | EditForm>({
    resolver: zodResolver(isEdit ? editSchema : createSchema),
  });

  useEffect(() => {
    if (isEdit && id) {
      usersApi.getOne(parseInt(id)).then((res) => {
        const u = res.data?.data;
        if (u) reset({ username: u.username, email: u.email, first_name: u.first_name ?? "", last_name: u.last_name ?? "" });
      });
    }
  }, [id]);

  const onSubmit = async (data: CreateForm | EditForm): Promise<void> => {
    setSubmitting(true);
    try {
      if (isEdit && id) {
        await usersApi.update(parseInt(id), data);
        toast.success("User updated");
      } else {
        await usersApi.create(data as CreateForm);
        toast.success("User created");
      }
      navigate("/users");
    } catch (err: any) {
      toast.error(err.response?.data?.message || "Operation failed");
    } finally {
      setSubmitting(false);
    }
  };

  const Field = ({ label, name, type = "text", placeholder, required }: {
    label: string; name: keyof (CreateForm & EditForm);
    type?: string; placeholder?: string; required?: boolean;
  }) => (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1.5">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      <input
        {...register(name)}
        type={type}
        placeholder={placeholder}
        className={`input-field ${errors[name] ? "border-red-500" : ""}`}
      />
      {errors[name] && <p className="text-xs text-red-600 mt-1">{errors[name]?.message as string}</p>}
    </div>
  );

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <button onClick={() => navigate(-1)} className="p-2 text-slate-500 hover:bg-slate-100 rounded-lg transition-colors">
          <ArrowLeft size={18} />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">{isEdit ? "Edit User" : "Create User"}</h1>
          <p className="text-sm text-slate-500">{isEdit ? "Update user information" : "Add a new user"}</p>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="card p-6 space-y-5">
        <div className="grid grid-cols-2 gap-4">
          <Field label="First Name" name="first_name" placeholder="John" />
          <Field label="Last Name"  name="last_name"  placeholder="Doe" />
        </div>
        <Field label="Username" name="username" placeholder="johndoe" required />
        <Field label="Email"    name="email"    type="email" placeholder="john@example.com" required />
        <Field
          label={isEdit ? "New Password (leave blank to keep)" : "Password"}
          name="password" type="password" placeholder="••••••••" required={!isEdit}
        />

        <div className="flex items-center justify-end gap-3 pt-2 border-t border-slate-200">
          <button type="button" onClick={() => navigate(-1)} className="btn-secondary">Cancel</button>
          <button type="submit" disabled={submitting} className="btn-primary">
            <Save size={16} />
            {submitting ? "Saving..." : isEdit ? "Update User" : "Create User"}
          </button>
        </div>
      </form>
    </div>
  );
};

export default UserForm;
```

---

## Constants

### src/constants/permissions.ts

```typescript
export const PERMISSIONS = {
  USERS: {
    READ:   "users:read",
    CREATE: "users:create",
    UPDATE: "users:update",
    DELETE: "users:delete",
  },
  ROLES: {
    READ:   "roles:read",
    CREATE: "roles:create",
    UPDATE: "roles:update",
    DELETE: "roles:delete",
  },
  PERMISSIONS: {
    READ:   "permissions:read",
    CREATE: "permissions:create",
    UPDATE: "permissions:update",
    DELETE: "permissions:delete",
  },
} as const;

export const ROLES = {
  SUPER_ADMIN: "super_admin",
  ADMIN:       "admin",
  VIEWER:      "viewer",
} as const;
```

---

## App Entry Point

### src/App.tsx

```tsx
import { useEffect }    from "react";
import { Toaster }      from "react-hot-toast";
import { AppRouter }    from "@/router";
import useAuthStore     from "@/store/authStore";

const App = (): JSX.Element => {
  const { isAuthenticated, fetchMe } = useAuthStore();

  useEffect(() => {
    if (isAuthenticated) {
      fetchMe();   // refresh permissions from server on every app load
    }
  }, []);

  return (
    <>
      <AppRouter />
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: { fontSize: "14px", borderRadius: "8px", boxShadow: "0 4px 12px rgba(0,0,0,.1)" },
        }}
      />
    </>
  );
};

export default App;
```

### src/main.tsx

```tsx
import React   from "react";
import ReactDOM from "react-dom/client";
import App     from "./App";
import "./styles/globals.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

---

## Key TypeScript Patterns Used

All files follow strict TypeScript:

- **Typed Axios responses** — `api.get<ApiResponse<User[]>>()` gives full type inference
- **Typed Zustand store** — `AuthStore = AuthState & AuthActions` interface
- **Typed Zod forms** — `type FormData = z.infer<typeof schema>` for React Hook Form
- **Typed custom hooks** — generics: `useCrud<T extends { id: number }>`, `usePagination<T>`
- **Typed RBAC gates** — `PermissionGateProps`, `RoleGateProps` interfaces
- **Typed route guards** — `ProtectedRouteProps`, `PermissionRouteProps`
- **Typed constants** — `as const` on PERMISSIONS/ROLES objects
- **No `any` except at API boundary** — all API responses typed via `ApiResponse<T>`
