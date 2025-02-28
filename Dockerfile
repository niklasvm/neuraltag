FROM python:3.10-slim-buster

WORKDIR /app

RUN pip install --upgrade pip && \
    pip install uv
COPY pyproject.toml .
COPY uv.lock .

# install
RUN uv pip install --system --no-cache-dir .

COPY . .

CMD ["python", "src/naming.py"]
