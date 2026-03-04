FROM python:3.12-bookworm as build

ARG UID=1000
ARG GID=1000
ARG ENV=development
ENV ENV=${ENV}
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV POETRY_VIRTUALENVS_CREATE=false
ENV POETRY_CACHE_DIR='/var/cache/pypoetry'

WORKDIR /backend

RUN apt-get update -q && apt-get install -yq \
    ffmpeg \
    libmagic1 \
    build-essential \
 && apt-get autoremove -yq && apt-get clean -yq && rm -rf /var/lib/apt/lists/*

RUN pip install --root-user-action=ignore --upgrade pip poetry

# Kopiujemy najpierw sam plik konfiguracyjny (optymalizacja cache Dockera)
COPY pyproject.toml ./

RUN if [ "$ENV" = 'development' ]; then \
      poetry install --no-interaction --no-ansi --no-root; \
    else \
      poetry install --only main --no-interaction --no-ansi --no-root && rm -rf "$POETRY_CACHE_DIR"; \
    fi

RUN groupadd -g $GID -o user && \
    useradd --no-log-init -u $UID -g $GID -o -s /bin/bash -m user

# Nadajemy uprawnienia dla nowego katalogu
RUN chown -R user:user /backend "$POETRY_CACHE_DIR"

USER user

FROM build as development
COPY . /backend

FROM build as production
COPY . /backend
CMD ["gunicorn", "src.asgi:application", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]

