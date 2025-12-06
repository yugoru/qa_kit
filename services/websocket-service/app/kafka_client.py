import os
import json
from kafka import KafkaProducer

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
KAFKA_TOPIC = os.getenv("KAFKA_WS_TOPIC", "ws_events")

producer = None

def get_producer():
    global producer
    if producer is None and KAFKA_BOOTSTRAP:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
    return producer

def emit(event: dict):
    p = get_producer()
    if not p:
        return False
    p.send(KAFKA_TOPIC, event)
    return True
