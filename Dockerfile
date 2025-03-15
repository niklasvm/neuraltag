FROM python:3.11-slim-bookworm

WORKDIR /app


RUN pip install uv --extra-index-url https://www.piwheels.org/simple


ENV UV_PROJECT_ENVIRONMENT="/uv_venv/"
ENV PATH="/${UV_PROJECT_ENVIRONMENT}/bin:$PATH"

COPY ../../pyproject.toml ../../uv.lock ../../README.md ./
RUN uv sync --frozen

COPY ../../ ./
RUN uv sync --frozen

EXPOSE 8000
