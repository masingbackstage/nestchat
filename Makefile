BACKEND_CONTAINER = backend
DB_CONTAINER = db
CELERY_CONTAINER = celery

-include .env

DOCKER_COMPOSE = docker compose
DOCKER_RUN = $(DOCKER_COMPOSE) run --rm $(BACKEND_CONTAINER)
DOCKER_EXEC = $(DOCKER_COMPOSE) exec $(BACKEND_CONTAINER)

DJANGO_MANAGE = python manage.py

.PHONY: build up up-build migrate migrations backend-bash django-shell format superuser restart-celery static test test-chat-gateway

build:
	$(DOCKER_COMPOSE) build

up:
	$(DOCKER_COMPOSE) up

up-build:
	$(DOCKER_COMPOSE) up --build
	make static
	make migrate

static:
	$(DOCKER_RUN) $(DJANGO_MANAGE) collectstatic --noinput

showmigrations:
	$(DOCKER_RUN) $(DJANGO_MANAGE) showmigrations

migrate:
	$(DOCKER_RUN) $(DJANGO_MANAGE) migrate

migrations:
	$(DOCKER_RUN) $(DJANGO_MANAGE) makemigrations
	make migrate

backend-bash:
	$(DOCKER_EXEC) bash

django-shell:
	$(DOCKER_EXEC) $(DJANGO_MANAGE) shell

format:
	$(DOCKER_RUN) bash -c "isort . && black . --line-length 100"

superuser:
	$(DOCKER_RUN) $(DJANGO_MANAGE) createsuperuser

recreate-db:
	$(DOCKER_COMPOSE) stop $(BACKEND_CONTAINER) $(CELERY_CONTAINER)
	$(DOCKER_COMPOSE) exec $(DB_CONTAINER) dropdb -U $(POSTGRES_USER) --if-exists $(POSTGRES_DB)
	$(DOCKER_COMPOSE) exec $(DB_CONTAINER) createdb -U $(POSTGRES_USER) $(POSTGRES_DB)
	$(DOCKER_COMPOSE) up -d $(BACKEND_CONTAINER) $(CELERY_CONTAINER)
	make migrate

test:
	$(DOCKER_COMPOSE) up -d $(DB_CONTAINER) $(BACKEND_CONTAINER)
	$(DOCKER_EXEC) bash -lc "cd /backend && poetry run pytest -q"

test-chat-gateway:
	$(DOCKER_COMPOSE) up -d $(DB_CONTAINER) $(BACKEND_CONTAINER)
	$(DOCKER_EXEC) bash -lc "cd /backend && poetry run pytest -q src/apps/chat/tests src/apps/gateway/tests"

restart-celery:
	$(DOCKER_COMPOSE) restart $(CELERY_CONTAINER)

logs:
	$(DOCKER_COMPOSE) logs -f $(BACKEND_CONTAINER) $(CELERY_CONTAINER)
