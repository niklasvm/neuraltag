FROM python:3.10-slim-buster as builder

FROM armv7/python:3.10-slim-buster

COPY --from=builder /usr/local/lib/python3.10 /usr/local/lib/python3.10
COPY --from=builder /usr/local/bin /usr/local/bin


WORKDIR /app

RUN pip install --upgrade pip && \
    pip install --upgrade uv
COPY requirements.txt requirements.txt
RUN uv pip install -r requirements.txt --system
COPY . .
RUN pip install -e ./

CMD ["python", "src/naming.py"]
