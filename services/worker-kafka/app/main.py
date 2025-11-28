import os
import time
import json

from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable
from sqlalchemy import create_engine, Column, Integer, String, DateTime, func
from sqlalchemy.orm import declarative_base, sessionmaker

database_url = os.getenv("DATABASE_URL")
bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
topic = os.getenv("KAFKA_ORDER_TOPIC", "order_events")

engine = create_engine(database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


class OrderEvent(Base):
    __tablename__ = "order_events"

    id = Column(Integer, primary_key=True)
    type = Column(String, nullable=False)
    order_id = Column(Integer, nullable=False)
    customer = Column(String, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


for _ in range(10):
    try:
        Base.metadata.create_all(bind=engine)
        break
    except Exception:
        time.sleep(2)


consumer = None

for _ in range(10):
    try:
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            group_id="qa_worker",
        )
        break
    except NoBrokersAvailable:
        time.sleep(2)


def main():
    if consumer is None:
        time.sleep(60)
        return
    for message in consumer:
        data = message.value
        session = SessionLocal()
        try:
            event = OrderEvent(
                type=data.get("type", ""),
                order_id=data.get("order_id"),
                customer=data.get("customer", ""),
                status=data.get("status", ""),
            )
            session.add(event)
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()


if __name__ == "__main__":
    main()
