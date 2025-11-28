import os
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import Order
from .schemas import OrderCreate, OrderResponse
from .kafka_client import publish
from .websocket_manager import manager

router = APIRouter(prefix="/orders", tags=["Orders"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


STATUS_CREATED = "created"
STATUS_PAID = "paid"
STATUS_SHIPPED = "shipped"
STATUS_DELIVERED = "delivered"
STATUS_CANCELLED = "cancelled"

ALLOWED_TRANSITIONS = {
    STATUS_CREATED: {STATUS_PAID, STATUS_CANCELLED},
    STATUS_PAID: {STATUS_SHIPPED, STATUS_CANCELLED},
    STATUS_SHIPPED: {STATUS_DELIVERED},
    STATUS_DELIVERED: set(),
    STATUS_CANCELLED: set(),
}

KAFKA_ORDER_TOPIC = os.getenv("KAFKA_ORDER_TOPIC", "order_events")


def get_order_or_404(order_id: int, db: Session) -> Order:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


def build_event_payload(event_type: str, order: Order) -> dict:
    return {
        "type": event_type,
        "order_id": order.id,
        "customer": order.customer,
        "status": order.status,
    }


def send_kafka_event(payload: dict):
    publish(KAFKA_ORDER_TOPIC, payload)


async def emit_event(event_type: str, order: Order):
    payload = build_event_payload(event_type, order)
    send_kafka_event(payload)
    await manager.broadcast(json.dumps(payload))


async def change_status(order: Order, new_status: str, db: Session) -> Order:
    allowed = ALLOWED_TRANSITIONS.get(order.status, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot change status from '{order.status}' to '{new_status}'",
        )
    order.status = new_status
    db.add(order)
    db.commit()
    db.refresh(order)
    await emit_event("order_status_changed", order)
    return order


@router.post("", response_model=OrderResponse)
async def create_order(payload: OrderCreate, db: Session = Depends(get_db)):
    order = Order(customer=payload.customer, status=STATUS_CREATED)
    db.add(order)
    db.commit()
    db.refresh(order)
    await emit_event("order_created", order)
    return order


@router.get("", response_model=list[OrderResponse])
async def list_orders(db: Session = Depends(get_db)):
    orders = db.query(Order).order_by(Order.id).all()
    return orders


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: int, db: Session = Depends(get_db)):
    order = get_order_or_404(order_id, db)
    return order


@router.post("/{order_id}/pay", response_model=OrderResponse)
async def pay_order(order_id: int, db: Session = Depends(get_db)):
    order = get_order_or_404(order_id, db)
    return await change_status(order, STATUS_PAID, db)


@router.post("/{order_id}/ship", response_model=OrderResponse)
async def ship_order(order_id: int, db: Session = Depends(get_db)):
    order = get_order_or_404(order_id, db)
    return await change_status(order, STATUS_SHIPPED, db)


@router.post("/{order_id}/deliver", response_model=OrderResponse)
async def deliver_order(order_id: int, db: Session = Depends(get_db)):
    order = get_order_or_404(order_id, db)
    return await change_status(order, STATUS_DELIVERED, db)


@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(order_id: int, db: Session = Depends(get_db)):
    order = get_order_or_404(order_id, db)
    return await change_status(order, STATUS_CANCELLED, db)
