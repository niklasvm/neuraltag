FROM python:3.11-slim-bookworm

WORKDIR /app

RUN pip install --upgrade pip
RUN curl -LsSf https://astral.sh/uv/install.sh | sh -s -- -b /usr/local/bin

ENV UV_PROJECT_ENVIRONMENT="/uv_venv/"
ENV PATH="/${UV_PROJECT_ENVIRONMENT}/bin:$PATH"

COPY ../../pyproject.toml ../../uv.lock ../../README.md ./
RUN uv sync --frozen

COPY ../../ ./
RUN uv sync --frozen

EXPOSE 8000

