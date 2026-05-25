# ==============================================================================
# Makefile for movie-network-django
# NOTE: Recipe lines MUST be indented with real TAB characters (\t), not spaces.
# ==============================================================================

.PHONY: help up down logs psql reset-db migrate shell test check superuser

help:
	@echo "Available commands:"
	@echo "  make up        - Start local Postgres container in background"
	@echo "  make down      - Stop local Postgres container"
	@echo "  make logs      - Follow Postgres container logs"
	@echo "  make psql      - Connect to database via psql inside container"
	@echo "  make reset-db  - Destroy database volume and restart fresh instance"
	@echo "  make migrate   - Run Django database migrations"
	@echo "  make shell     - Open Django interactive shell"
	@echo "  make test      - Run Django test suite"
	@echo "  make check     - Run Django system checks"
	@echo "  make superuser - Create Django superuser account"

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f db

psql:
	docker compose exec db psql -U movie_network -d movie_network

reset-db:
	docker compose down -v && docker compose up -d

migrate:
	python manage.py migrate

shell:
	python manage.py shell

test:
	python manage.py test

check:
	python manage.py check

superuser:
	python manage.py createsuperuser
