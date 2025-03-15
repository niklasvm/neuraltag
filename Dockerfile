FROM python:3.11-slim-bookworm

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN pip install --upgrade pip


ENV UV_PROJECT_ENVIRONMENT="/uv_venv/"
ENV PATH="/${UV_PROJECT_ENVIRONMENT}/bin:$PATH"

COPY ../../pyproject.toml ../../uv.lock ../../README.md ./
RUN uv sync --frozen

COPY ../../ ./
RUN uv sync --frozen

EXPOSE 8000

