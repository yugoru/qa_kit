import os
import time
import json
from fastapi.middleware.cors import CORSMiddleware

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import OperationalError
from prometheus_fastapi_instrumentator import Instrumentator

from .models import Base, Order
from .database import engine, SessionLocal
from .routes_orders import router as orders_router, STATUS_CREATED, change_status, emit_event
from .websocket_manager import manager

RESET_ORDERS = os.getenv("RESET_ORDERS_ON_START", "false").lower() == "true"

for _ in range(10):
    try:
        if RESET_ORDERS:
            Order.__table__.drop(bind=engine, checkfirst=True)
        Base.metadata.create_all(bind=engine)
        break
    except OperationalError:
        time.sleep(2)


class HealthResponse(BaseModel):
    status: str


app = FastAPI(
    title="QA Kit REST API",
    version="0.1.0"
)

for _ in range(10):
    try:
        Base.metadata.create_all(bind=engine)
        break
    except OperationalError:
        time.sleep(2)

origins = os.getenv(
    "CORS_ALLOW_ORIGINS",
    "http://localhost:8090,http://localhost:8091,http://127.0.0.1:8090,http://127.0.0.1:8091",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)


@app.get("/health", response_model=HealthResponse)
async def health():
    return {"status": "ok"}


@app.websocket("/ws/orders")
async def orders_ws(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except Exception:
                await websocket.send_text(
                    json.dumps({"type": "error", "error": "invalid_json"})
                )
                continue

            action = data.get("action")

            if action == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
                continue

            if action == "create_order":
                customer = data.get("customer")
                if not customer:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "error",
                                "action": "create_order",
                                "error": "customer is required",
                            }
                        )
                    )
                    continue

                db = SessionLocal()
                try:
                    order = Order(customer=customer, status=STATUS_CREATED)
                    db.add(order)
                    db.commit()
                    db.refresh(order)
                finally:
                    db.close()

                await emit_event("order_created", order)

                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "result",
                            "action": "create_order",
                            "order": {
                                "id": order.id,
                                "customer": order.customer,
                                "status": order.status,
                            },
                        }
                    )
                )
                continue

            if action == "change_status":
                order_id = data.get("order_id")
                new_status = data.get("status")

                if order_id is None or new_status is None:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "error",
                                "action": "change_status",
                                "error": "order_id and status are required",
                            }
                        )
                    )
                    continue

                try:
                    order_id_int = int(order_id)
                except Exception:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "error",
                                "action": "change_status",
                                "error": "order_id must be integer",
                            }
                        )
                    )
                    continue

                db = SessionLocal()
                try:
                    order = (
                        db.query(Order)
                        .filter(Order.id == order_id_int)
                        .first()
                    )
                    if not order:
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "error",
                                    "action": "change_status",
                                    "error": "order not found",
                                }
                            )
                        )
                        continue

                    try:
                        updated = await change_status(order, new_status, db)
                    except HTTPException as exc:
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "error",
                                    "action": "change_status",
                                    "error": exc.detail,
                                }
                            )
                        )
                        continue

                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "result",
                                "action": "change_status",
                                "order": {
                                    "id": updated.id,
                                    "customer": updated.customer,
                                    "status": updated.status,
                                },
                            }
                        )
                    )
                finally:
                    db.close()
                continue

            if action == "get_order":
                order_id = data.get("order_id")
                if order_id is None:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "error",
                                "action": "get_order",
                                "error": "order_id is required",
                            }
                        )
                    )
                    continue

                try:
                    order_id_int = int(order_id)
                except Exception:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "error",
                                "action": "get_order",
                                "error": "order_id must be integer",
                            }
                        )
                    )
                    continue

                db = SessionLocal()
                try:
                    order = (
                        db.query(Order)
                        .filter(Order.id == order_id_int)
                        .first()
                    )
                    if not order:
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "error",
                                    "action": "get_order",
                                    "error": "order not found",
                                }
                            )
                        )
                        continue

                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "result",
                                "action": "get_order",
                                "order": {
                                    "id": order.id,
                                    "customer": order.customer,
                                    "status": order.status,
                                },
                            }
                        )
                    )
                finally:
                    db.close()
                continue

            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "error": "unknown_action",
                        "raw_action": action,
                    }
                )
            )
    except WebSocketDisconnect:
        manager.disconnect(websocket)


app.include_router(orders_router)
