FROM python:3.10-slim-buster

WORKDIR /app

RUN pip install uv
COPY pyproject.toml .
COPY poetry.lock .
RUN uv pip install -v .

COPY . .

CMD ["python", "src/naming.py"]
