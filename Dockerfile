FROM python:3.11-slim-bookworm

WORKDIR /app

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain none
ENV PATH="/root/.cargo/bin:${PATH}"
RUN rustup toolchain install stable-armv7-unknown-linux-gnueabihf
RUN rustup target add arm-unknown-linux-gnueabi
RUN rustup default stable-armv7-unknown-linux-gnueabihf

RUN pip install uv


ENV UV_PROJECT_ENVIRONMENT="/uv_venv/"
ENV PATH="/${UV_PROJECT_ENVIRONMENT}/bin:$PATH"

COPY ../../pyproject.toml ../../uv.lock ../../README.md ./
RUN uv sync --frozen

COPY ../../ ./
RUN uv sync --frozen

EXPOSE 8000
