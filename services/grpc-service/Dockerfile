FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY proto ./proto
COPY app ./app

RUN python -m grpc_tools.protoc \
    -I./proto \
    --python_out=./app \
    --grpc_python_out=./app \
    ./proto/order.proto

CMD ["python", "-m", "app.server"]
