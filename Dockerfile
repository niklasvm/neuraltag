FROM python:3.11-slim-bookworm@sha256:614c8691ab74150465ec9123378cd4dde7a6e57be9e558c3108df40664667a4c

WORKDIR /app

RUN pip install uv==0.6.3

ENV UV_PROJECT_ENVIRONMENT="/uv_venv/"
ENV PATH="/${UV_PROJECT_ENVIRONMENT}/bin:$PATH"

COPY ../../pyproject.toml ../../uv.lock ../../README.md ./
RUN uv sync --frozen

COPY ../../ ./
RUN uv sync --frozen

EXPOSE 8000
