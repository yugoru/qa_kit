import os
import time
import json

from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

producer = None

for _ in range(10):
    try:
        producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        break
    except NoBrokersAvailable:
        time.sleep(2)


def publish(topic: str, value: dict):
    if producer is None:
        return
    producer.send(topic, value)
