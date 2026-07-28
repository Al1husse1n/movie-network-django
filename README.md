# Movie Network

> A social platform for film lovers — curate watchlists, rate films, write reviews, and connect with cinema communities in real time.

[![CI](https://github.com/Al1husse1n/movie-network-django/actions/workflows/ci.yml/badge.svg)](https://github.com/Al1husse1n/movie-network-django/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12-blue)
![Django](https://img.shields.io/badge/django-6.0-green)
![Coverage](https://img.shields.io/badge/coverage-92%25-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)

[**Live Demo**](https://movie-network-django.onrender.com) · [API Docs](https://movie-network-django.onrender.com/api/docs/) · [Development Guide](docs/DEVELOPMENT.md)

---

![Cinema Foyer Profile with Skills Progression](screenshots/profile.png)

## Features

### 🎬 Cinema & Discovery
- Search and browse thousands of films and TV shows (powered by TMDB)
- Add titles to your personal watchlist with "Now Showing" discovery
- Rate films and shows (0.0–10.0)
- Track your favorite genres across your library

### ✍️ Reviews & Critiques
- Write substantive reviews and critiques
- Mark reviews with spoiler warnings (blurred by default)
- Rate and review both movies and TV shows

### 👥 Communities
- Create and join public or private cinema circles
- Post in community feeds with spoiler protection
- Real-time feed updates via WebSockets (locally; see Limitations)
- Live notification bell with unread counts

### 🏆 Skill Progression
- **Cinephile** — level up by rating films
- **Critic** — level up by writing substantive reviews
- **Explorer** — level up by discovering new genres
- **Socialite** — level up through followers and community engagement
- Five tiers: *Extra → Speaking Role → Supporting → Lead → Auteur*
- Dynamic SVG progress rings on every profile

### 🔐 Authentication
- Email/password registration and login
- "Continue with Google" OAuth 2.0 via django-allauth
- Token-based authentication for API access

### 🛠️ Developer Experience
- Full REST API with **OpenAPI 3** schema and interactive **Swagger UI**
- 260 tests, 92% code coverage, ruff + pre-commit enforced
- Redis-backed cache for TMDB responses (24h TTL)
- Celery background workers with scheduled tasks
- Docker Compose for local Postgres + Redis
- GitHub Actions CI (lint + test on every push)
- Production deployed on **Render + Neon + Upstash**

---

## Architecture

```text
┌─────────────┐       ┌──────────────┐       ┌──────────────┐
│   Browser   │◄──WS──►│    Daphne    │◄──────►│   Postgres   │
│ (Alpine.js  │       │    (ASGI)    │       │    (Neon)    │
│   + HTMX)   │◄──HTTP►│              │       └──────────────┘
└─────────────┘       │   Django 6   │       ┌──────────────┐
                      │   Channels   │◄──────►│    Redis     │
                      │    Celery    │       │  (Upstash)   │
                      │     DRF      │       └──────────────┘
                      └──────────────┘       ┌──────────────┐
                                             │     TMDB     │
                                             │ API + cache  │
                                             └──────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Django 6.0, Django REST Framework, Django Channels |
| **Async** | Celery, Celery Beat, Redis |
| **Database** | PostgreSQL (Neon in production), SQLite (dev fallback) |
| **Cache** | Redis (Upstash in production) |
| **Frontend** | Django templates, Tailwind CSS (Cinema Foyer Design System), Alpine.js, HTMX |
| **Auth** | django-allauth, PyJWT, Google OAuth 2.0 |
| **Deployment** | Render (web), Neon (DB), Upstash (Redis) |
| **Quality** | pytest, pytest-django, ruff, pre-commit, GitHub Actions |

---

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/Al1husse1n/movie-network-django.git
cd movie-network-django
python -m venv venv
# Windows: .\venv\Scripts\Activate.ps1
# Unix: source venv/bin/activate
pip install -r requirements.txt

# 2. Environment
cp .env.example .env
# Edit .env — set SECRET_KEY, DATABASE_URL, TMDB_API_KEY
# (See docs/DEVELOPMENT.md for all required variables)

# 3. Spin up Postgres + Redis
docker compose up -d
python manage.py migrate
python manage.py runserver
```

Visit [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

Full setup, testing, deployment, and troubleshooting instructions are in the [Development Guide](docs/DEVELOPMENT.md).

---

## Testing

```bash
# Run entire test suite (260 tests, 92% coverage)
pytest -q

# Generate HTML coverage report
pytest --cov=myapp --cov-report=html

# Lint and formatting checks
ruff check . && ruff format --check .
```

---

## What I Learned Building This

This project was built as a portfolio piece over ~3 months (89 commits from May to July 2026). Key technical takeaways:

1. **Normalizing external data** — Replacing ad-hoc `JSONField` blobs with proper `Movie`, `Show`, and `Genre` models enabled features (top-rated queries, genre-based recommendations, and skill progression) that were previously impossible.
2. **Real-time at the consumer level** — Django Channels + Redis channel layers + Alpine.js gives a responsive, native-app feel without SPA complexity. The reconnect-with-backoff helper in `base.html` handles flaky network connections gracefully.
3. **Cache invalidation is hard** — A 24h TTL on TMDB responses reduced API latency from ~400ms to ~1ms (a 400x speedup), but required thoughtful cache key namespacing and strict test isolation.
4. **Fail fast, fail loud, fail safe** — Every WebSocket broadcast is wrapped in a fault-tolerant `broadcast_to_group` helper that logs exceptions but never propagates them. Background async glitches never break synchronous HTTP responses.
5. **Test-per-endpoint discipline** — Test coverage grew to 260 unit and integration tests (92% total coverage), catching critical boundary bugs (such as `update_watchlist` return values and missing ID parameters).

---

## Limitations

- **WebSocket real-time updates** are disabled on the free Render tier because the free HTTP reverse proxy strips the WebSocket `Upgrade` header. All other features work in the free deployment. Real-time features can be verified locally via `python manage.py runserver` and testing across two browser sessions.
- **Cold starts** on the free Render tier can take 30–60 seconds after periods of inactivity.
- **Google OAuth** in production requires authorized redirect URIs to be registered in Google Cloud Console.

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- [Django documentation](https://docs.djangoproject.com/)
- [TMDB API](https://www.themoviedb.org/documentation/api) for film and television metadata
- [django-allauth](https://docs.allauth.org/) for OAuth and social authentication
- [Django Channels](https://channels.readthedocs.io/) for WebSocket and real-time infrastructure
