import time
from concurrent import futures

import grpc
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

from . import db
from .models import Order
from . import order_pb2
from . import order_pb2_grpc


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


class OrderService(order_pb2_grpc.OrderServiceServicer):
    def _get_session(self) -> Session:
        return db.SessionLocal()

    def _to_response(self, order: Order) -> order_pb2.OrderResponse:
        return order_pb2.OrderResponse(
            id=order.id,
            customer=order.customer,
            status=order.status,
            error="",
        )

    def GetOrder(self, request, context):
        session = self._get_session()
        try:
            order = session.query(Order).filter(Order.id == request.id).first()
            if not order:
                return order_pb2.OrderResponse(
                    id=0,
                    customer="",
                    status="",
                    error="order not found",
                )
            return self._to_response(order)
        finally:
            session.close()

    def CreateOrder(self, request, context):
        customer = request.customer.strip()
        if not customer:
            return order_pb2.OrderResponse(
                id=0,
                customer="",
                status="",
                error="customer is required",
            )
        session = self._get_session()
        try:
            order = Order(customer=customer, status=STATUS_CREATED)
            session.add(order)
            session.commit()
            session.refresh(order)
            return self._to_response(order)
        finally:
            session.close()

    def ChangeStatus(self, request, context):
        new_status = request.status.strip()
        session = self._get_session()
        try:
            order = session.query(Order).filter(Order.id == request.id).first()
            if not order:
                return order_pb2.OrderResponse(
                    id=0,
                    customer="",
                    status="",
                    error="order not found",
                )
            allowed = ALLOWED_TRANSITIONS.get(order.status, set())
            if new_status not in allowed:
                return order_pb2.OrderResponse(
                    id=order.id,
                    customer=order.customer,
                    status=order.status,
                    error=f"Cannot change status from '{order.status}' to '{new_status}'",
                )
            order.status = new_status
            session.add(order)
            session.commit()
            session.refresh(order)
            return self._to_response(order)
        finally:
            session.close()


def serve():
    for _ in range(10):
        try:
            db.Base.metadata.create_all(bind=db.engine)
            break
        except OperationalError:
            time.sleep(2)

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    order_pb2_grpc.add_OrderServiceServicer_to_server(OrderService(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    print("gRPC OrderService started on :50051")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
