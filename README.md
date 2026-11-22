# CloudVault

CloudVault is a cloud file-storage web application. Users keep their files in **buckets**
(personal or shared with other users), organise them in **folders**, and share single files
through public links.

Main features:

- **Tiers** (`free`, `standard`, `premium`) with a storage quota, a maximum file size and a
  maximum number of shared buckets; paid tiers are bought through subscriptions.
- **Personal and shared buckets**: personal buckets count toward the owner's quota, shared
  buckets have members (`owner` / `member`) invited by e-mail.
- **Folders and files**: folder trees inside a bucket. File contents live in object storage
  (MinIO, S3-compatible); the database keeps only the metadata.
- **Deduplication**: identical uploads are detected by their SHA-256 hash.
- **Public share links** with optional expiry and an access counter.
- **Points system**: users earn points (uploads, login streaks, referrals, ...) and spend them on rewards.
- **Referrals, notifications and audit logs.**

## Project structure

```
cloud_vault/
├── app/
│   ├── main.py           FastAPI app factory (create_app)
│   ├── core/             settings (pydantic-settings) and security helpers
│   ├── db/               engine, session factory, get_db dependency
│   ├── models/           SQLAlchemy models: one file per table, plus base.py
│   ├── repositories/     data access: database queries only
│   ├── services/         business logic: rules, quotas, points; owns commit / rollback
│   ├── schemas/          Pydantic request / response models
│   ├── api/
│   │   ├── deps.py       shared FastAPI dependencies (DbSession, AppSettings)
│   │   └── routers/      one router per resource, all collected into api_router
│   └── views/            Jinja2 templates
├── migrations/           Alembic environment and versions
├── alembic.ini
├── requirements.txt
└── .env.example
```

How a request flows through the layers: **router → service → repository → model / database**.
Routers handle HTTP only, services contain the business rules, and repositories contain the queries.

## Getting started

### 1. Prerequisites

- Python 3.12 or newer
- PostgreSQL 15 or newer, running locally

### 2. Virtual environment and dependencies

Windows (cmd / PowerShell):

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configuration

Copy the example file, then set your PostgreSQL user and password in `DATABASE_URL`:

```bash
copy .env.example .env
```

On Linux / macOS use `cp .env.example .env` instead.

Set `JWT_SECRET_KEY` to a random value of at least 32 characters; the app does not start without it:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

`.env` is ignored by git, so never commit real credentials.

### 4. Database

Create an empty database. The default name is `cloud_vault`:

```bash
psql -U postgres -c "CREATE DATABASE cloud_vault"
```

Apply all migrations:

```bash
alembic upgrade head
```

### 5. Run the application

```bash
uvicorn app.main:app --reload
```

| URL | Description |
|-----|-------------|
| http://127.0.0.1:8000/health | health check (also tests the database connection) |
| http://127.0.0.1:8000/docs | interactive API documentation (Swagger UI) |
| http://127.0.0.1:8000/login | login for the admin pages |

To run it in production mode so other devices on the network can open it, see
[docs/deployment.md](docs/deployment.md).

## Admin pages

The server-rendered pages under `/users`, `/buckets` and `/files` are for administrators only
(`users.is_admin = true`). Without a session they redirect to `/login`; logged-in users who are
not administrators get `403`.

- The migrations create a demo administrator: `admin@example.com`, password `CloudVault-demo-2026`
  (the same password as the other demo accounts). Change it outside development.
- The session is a JWT kept in an HttpOnly, SameSite=Strict cookie, valid for
  `ADMIN_SESSION_EXPIRE_MINUTES` (60 by default). It is marked Secure when `DEBUG=false`.
- Admin sessions and API access tokens are not interchangeable: the cookie does not work as a
  Bearer token and an API token does not open the admin pages.
- The **Log out** button in the navigation bar removes the cookie.

## Authentication API

| Method | Endpoint | Body | Response |
|--------|----------|------|----------|
| POST | `/api/auth/register` | `email`, `username`, `password` | `201` user, `409` if email or username is taken |
| POST | `/api/auth/login` | `email`, `password` | `200` `access_token`, `refresh_token`, `expires_in`; `401` on wrong credentials |
| POST | `/api/auth/refresh` | `refresh_token` | `200` new token pair (the old refresh token is revoked) |
| POST | `/api/auth/logout` | `refresh_token` | `204` |
| GET | `/api/auth/me` | header `Authorization: Bearer <access_token>` | `200` current user |

- The **access token** is a JWT valid for `ACCESS_TOKEN_EXPIRE_MINUTES` (15 by default).
- The **refresh token** is a random string valid for `REFRESH_TOKEN_EXPIRE_DAYS` (7 by default).
  Only its SHA-256 hash is stored. Every refresh replaces it; reusing an old one revokes all
  of the user's refresh tokens.
- In `/docs`, click **Authorize** and paste the access token to call protected endpoints.

## Buckets API

All endpoints need `Authorization: Bearer <access_token>`.

| Method | Endpoint | Body | Response |
|--------|----------|------|----------|
| GET | `/api/buckets` | - | `200` buckets the user owns or is a member of |
| GET | `/api/buckets/{id}` | - | `200` bucket, `404` if it does not exist or the user has no access |
| POST | `/api/buckets` | `name`, `description`, `is_shared` | `201` bucket, `409` duplicate name, `400` shared bucket limit of the tier |
| PUT | `/api/buckets/{id}` | `name`, `description` | `200` bucket, `403` if the user is not the owner |
| DELETE | `/api/buckets/{id}` | - | `204`, `403` if the user is not the owner; also deletes the bucket's folders and files |

## Database migrations (Alembic)

1. Edit a model in `app/models/`. A new model must also be imported in `app/models/__init__.py`,
   otherwise Alembic will not see it.
2. Generate a migration:

   ```bash
   alembic revision --autogenerate -m "add avatar to buckets"
   ```

3. Review the generated file in `migrations/versions/`. Autogenerate does not detect everything:
   renames, for example, appear as a drop plus an add.
4. Apply it:

   ```bash
   alembic upgrade head
   ```

5. Run `alembic check`. It should report `No new upgrade operations detected.`

For data-only migrations (seed data), create an empty revision and write the inserts yourself:

```bash
alembic revision -m "seed bonus rules"
```
