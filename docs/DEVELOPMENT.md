# Development Guide

This guide walks you through setting up and running **movie-network-django** locally using Docker Compose for PostgreSQL 16.

---

## 1. Prerequisites

Before starting, ensure you have the following installed on your machine:
- **Python 3.12+**
- **Docker Desktop** (with Docker Compose v2+)
- **Git**
- *(Optional)* `make` (standard on macOS/Linux; available via Git Bash on Windows)

---

## 2. One-Time Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Al1husse1n/movie-network-django.git
   cd movie-network-django
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # Windows PowerShell
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # macOS / Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   For local development with the Docker Postgres container, verify that your `.env` contains:
   ```env
   DJANGO_SETTINGS_MODULE=movie_network.settings.dev
   DEBUG=True
   SECRET_KEY=dev-insecure-secret-key-change-in-prod
   ALLOWED_HOSTS=localhost,127.0.0.1,[::1]
   DATABASE_URL=postgresql://movie_network:movie_network_dev_password@localhost:5432/movie_network
   TMDB_API_KEY=your-tmdb-api-key-here
   ```
   *(Refer to `.env.docker.example` for container credentials).*

5. **Start the local PostgreSQL container:**
   ```bash
   # Using Docker Compose directly:
   docker compose up -d

   # Or using Makefile:
   make up

   # Or using PowerShell helper (Windows):
   .\scripts\db-up.ps1
   ```

6. **Apply database migrations:**
   ```bash
   python manage.py migrate
   ```

7. **Create a superuser (optional):**
   ```bash
   python manage.py createsuperuser
   ```

8. **Start the Django development server:**
   ```bash
   python manage.py runserver
   ```
   Visit `http://127.0.0.1:8000/` in your browser.

---

## 3. Daily Workflow

| Task | Using Makefile | Using PowerShell Helper / CLI |
|---|---|---|
| **Start database** | `make up` | `.\scripts\db-up.ps1` or `docker compose up -d` |
| **Stop database** | `make down` | `.\scripts\db-down.ps1` or `docker compose down` |
| **Database logs** | `make logs` | `docker compose logs -f db` |
| **Interactive psql shell** | `make psql` | `.\scripts\db-psql.ps1` |
| **Run migrations** | `make migrate` | `python manage.py migrate` |
| **Django shell** | `make shell` | `python manage.py shell` |
| **Run test suite** | `make test` | `python manage.py test` |
| **System check** | `make check` | `python manage.py check` |
| **Reset local database** | `make reset-db` | `.\scripts\db-reset.ps1` |

---

## 4. Switching Between Local Postgres and Neon (Cloud Postgres)

The project uses `DATABASE_URL` exclusively to route database connections.

- **To run against Local Docker Postgres:**
  ```env
  DATABASE_URL=postgresql://movie_network:movie_network_dev_password@localhost:5432/movie_network
  ```
- **To run against Neon (Cloud Postgres) for staging/pre-prod testing:**
  Set `DATABASE_URL` in your `.env` to your Neon connection string:
  ```env
  DATABASE_URL=postgresql://neondb_owner:<password>@<neon-hostname>/neondb?sslmode=require
  ```
  *(Remember to stop your local Docker container with `docker compose down` if testing Neon directly).*

---

## 5. Troubleshooting

### Port 5432 already in use
If another PostgreSQL instance is already running locally on port 5432:
1. Update `POSTGRES_PORT` in your `.env`:
   ```env
   POSTGRES_PORT=5433
   ```
2. Update the port in your `DATABASE_URL`:
   ```env
   DATABASE_URL=postgresql://movie_network:movie_network_dev_password@localhost:5433/movie_network
   ```
3. Restart container: `docker compose up -d`

### Docker Desktop not running
If running `docker compose up -d` gives an API pipe or socket error:
- Ensure Docker Desktop is launched and the Docker engine is running (look for the green indicator in Docker Desktop).

### `make` command not found on Windows
Windows PowerShell does not bundle `make` by default. You can:
- Use the provided PowerShell helper scripts under `scripts/` (e.g. `.\scripts\db-up.ps1`, `.\scripts\db-down.ps1`).
- Or run commands via Git Bash.
- Or install make via Chocolatey (`choco install make`) or winget.

### Password authentication failed for user "movie_network"
If credentials changed after the container volume was initialized, PostgreSQL will not update user credentials on an existing volume.
- Reset the volume to recreate the database with clean credentials:
  ```bash
  make reset-db
  # or
  .\scripts\db-reset.ps1
  ```
- Re-run migrations: `python manage.py migrate`
