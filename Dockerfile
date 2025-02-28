FROM python:3.10-slim-buster

WORKDIR /app

RUN pip install --upgrade pip && \
    pip install --upgrade uv
COPY requirements.txt requirements.txt
RUN uv pip install -r requirements.txt --system
COPY . .
RUN pip install -e ./

CMD ["python", "src/naming.py"]
