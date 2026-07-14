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

---

## 6. Deployment (Render)

The project is configured for deployment to [Render](https://render.com) as a Python web service running Daphne (ASGI) to support both HTTP traffic and WebSockets (Django Channels).

### Infrastructure Architecture
- **Web Service / ASGI Host:** Render (`daphne -b 0.0.0.0 -p $PORT movie_network.asgi:application`)
- **Database:** Neon Cloud PostgreSQL (configured via `DATABASE_URL`)
- **Cache & Channel Layer:** Upstash Redis (configured via `REDIS_URL`, `CHANNEL_LAYERS_URL`, `CELERY_BROKER_URL`)
- **Static Assets:** WhiteNoise / `manage.py collectstatic`

### Declarative Service Configuration (`render.yaml`)
Deployment is managed via the blueprint defined in `render.yaml`:
- **Build Command:** `./build.sh` (upgrades pip, installs dependencies, runs `collectstatic`, and runs `migrate`)
- **Start Command:** `daphne -b 0.0.0.0 -p $PORT movie_network.asgi:application`
- **Health Check Path:** `/`
- **Auto Deploy:** Enabled on pushes to `main`

### Required Environment Variables
Set these secret variables in the **Render Dashboard → Environment** tab (defined with `sync: false` in `render.yaml`):

| Variable | Description / Example |
|---|---|
| `DJANGO_SETTINGS_MODULE` | `movie_network.settings.prod` (defined in `render.yaml`) |
| `DEBUG` | `False` (defined in `render.yaml`) |
| `PYTHON_VERSION` | `3.12.0` (defined in `render.yaml`) |
| `SECRET_KEY` | Strong random key (`python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`) |
| `ALLOWED_HOSTS` | `movie-network-django.onrender.com` (or your custom domain) |
| `CSRF_TRUSTED_ORIGINS` | `https://movie-network-django.onrender.com` |
| `DATABASE_URL` | Neon PostgreSQL pooled connection string (with `?sslmode=require`) |
| `REDIS_URL` | Upstash Redis connection string (`rediss://...`) |
| `CHANNEL_LAYERS_URL` | Upstash Redis connection string (`rediss://...`) |
| `CELERY_BROKER_URL` | Upstash Redis connection string (`rediss://...`) |
| `TMDB_API_KEY` | TMDB API v3 key |
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth Client Secret |

### Upstash Redis Configuration
Create a free database on [Upstash Redis](https://upstash.com):
- Use the rediss URL format with SSL certificate verification disabled for cloud compatibility:
  ```env
  rediss://default:<password>@<region>.upstash.io:6379?ssl_cert_reqs=none
  ```
- Use the same URL for `REDIS_URL`, `CHANNEL_LAYERS_URL`, and `CELERY_BROKER_URL` (or assign separate database indices if preferred, e.g. `/0`, `/2`).

### Google OAuth Production Setup
1. In the [Google Cloud Console](https://console.cloud.google.com/apis/credentials), select your OAuth 2.0 Client ID.
2. Under **Authorized redirect URIs**, add your production callback URL:
   ```
   https://<your-app>.onrender.com/accounts/google/login/callback/
   ```
3. Under **Authorized JavaScript origins**, add:
   ```
   https://<your-app>.onrender.com
   ```

### Triggering Deployments
- **Automatic Deployment:** Pushing commits to the `main` branch triggers an automated build and deploy via Render's GitHub integration.
- **Manual Deployment:** Navigate to the service in the Render Dashboard and click **Manual Deploy** → **Deploy latest commit** (or **Clear build cache & deploy** if requirements changed).

### Cold Start Behavior (Free Tier)
Render's free tier spins down the web service after 15 minutes of inactivity. When a new request arrives, a cold start occurs, which may take 30–60 seconds for Daphne and Django to initialize. Subsequent requests will respond immediately.
