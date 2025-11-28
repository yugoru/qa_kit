from typing import Optional, List

import strawberry
from sqlalchemy.orm import Session

from .db import SessionLocal, Base, engine
from .models import Order


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


def get_session() -> Session:
    return SessionLocal()


@strawberry.type
class OrderType:
    id: int
    customer: str
    status: str


@strawberry.type
class Query:
    @strawberry.field
    def orders(self) -> List[OrderType]:
        session = get_session()
        try:
            items = session.query(Order).order_by(Order.id).all()
            return [OrderType(id=o.id, customer=o.customer, status=o.status) for o in items]
        finally:
            session.close()

    @strawberry.field
    def order(self, id: int) -> Optional[OrderType]:
        session = get_session()
        try:
            o = session.query(Order).filter(Order.id == id).first()
            if not o:
                return None
            return OrderType(id=o.id, customer=o.customer, status=o.status)
        finally:
            session.close()


@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_order(self, customer: str) -> OrderType:
        session = get_session()
        try:
            order = Order(customer=customer, status=STATUS_CREATED)
            session.add(order)
            session.commit()
            session.refresh(order)
            return OrderType(id=order.id, customer=order.customer, status=order.status)
        finally:
            session.close()

    @strawberry.mutation
    def change_status(self, id: int, status: str) -> OrderType:
        new_status = status.strip()
        session = get_session()
        try:
            order = session.query(Order).filter(Order.id == id).first()
            if not order:
                raise ValueError("order not found")

            allowed = ALLOWED_TRANSITIONS.get(order.status, set())
            if new_status not in allowed:
                raise ValueError(
                    f"Cannot change status from '{order.status}' to '{new_status}'"
                )

            order.status = new_status
            session.add(order)
            session.commit()
            session.refresh(order)
            return OrderType(id=order.id, customer=order.customer, status=order.status)
        finally:
            session.close()


schema = strawberry.Schema(query=Query, mutation=Mutation)

Base.metadata.create_all(bind=engine)
