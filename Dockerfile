FROM arm32v7/python:3.10-bookworm

WORKDIR /app

RUN pip install --upgrade pip && \
    pip install --upgrade uv
COPY requirements.txt requirements.txt
RUN uv pip install -r requirements.txt --system
COPY . .
RUN pip install -e ./

CMD ["python", "src/naming.py"]
