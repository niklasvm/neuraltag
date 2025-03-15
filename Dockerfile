FROM python:3.11-bookworm

WORKDIR /app

RUN pip install --upgrade pip && \
    pip install --no-cache-dir uv


ENV UV_PROJECT_ENVIRONMENT="/uv_venv/"
ENV PATH="/${UV_PROJECT_ENVIRONMENT}/bin:$PATH"

COPY ../../pyproject.toml ../../uv.lock ../../README.md ./
RUN uv sync --frozen

COPY ../../ ./
RUN uv sync --frozen

EXPOSE 8000

