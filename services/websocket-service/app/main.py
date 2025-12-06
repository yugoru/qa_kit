from __future__ import annotations

import os
import json
import logging
from datetime import datetime, timezone
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware

from .manager import hub

# --- OPTIONAL: DB integration ---
# Если у тебя уже добавлены database.py и models.py в websocket-service
# оставь эти импорты. Если нет — закомментируй блок.
try:
    from .database import SessionLocal, engine
    from .models import Base, Order
    DB_ENABLED = True
except Exception:
    SessionLocal = None
    engine = None
    Base = None
    Order = None
    DB_ENABLED = False

# --- OPTIONAL: Kafka integration ---
# Если у тебя есть kafka_client.py в websocket-service
# оставь. Если нет — закомментируй.
try:
    from .kafka_client import emit
    KAFKA_ENABLED = True
except Exception:
    def emit(_: dict) -> bool:
        return False
    KAFKA_ENABLED = False


APP_NAME = "qa-websocket"
DEFAULT_CHANNEL = os.getenv("WS_DEFAULT_CHANNEL", "general")

# ---------------- Logging ----------------
logger = logging.getLogger("qa_ws")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Uvicorn тоже будет писать access logs, если включены стандартно.


def now():
    return datetime.now(timezone.utc).isoformat()


def jdump(obj) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return str(obj)


# Создаём таблицы для учебного стенда, если DB подключена
if DB_ENABLED:
    Base.metadata.create_all(bind=engine)


app = FastAPI(title="QA Kit WebSocket Service", version="0.2.0")

# Для учебки можно оставить *, но если хочешь строже — ограничь портал/плейграунд.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    logger.info("HTTP /health")
    return {"status": "ok", "service": APP_NAME}


@app.get("/stats")
def stats():
    s = hub.stats()
    logger.info("HTTP /stats %s", jdump(s))
    return s


@app.post("/broadcast")
async def broadcast(message: str, channel: str = DEFAULT_CHANNEL):
    payload = {"type": "broadcast", "channel": channel, "message": message, "ts": now()}

    logger.info("HTTP BROADCAST IN channel=%s message=%s", channel, message)

    sent = await hub.broadcast_json(channel, payload)

    logger.info("HTTP BROADCAST OUT channel=%s connections=%s payload=%s",
                channel, sent, jdump(payload))

    emit({"source": APP_NAME, **payload})

    return {"ok": True, "channel": channel, "connections": sent}


# ---------------- WS helpers ----------------

async def send_ack(ws: WebSocket, request_id: str):
    out = {"type": "ack", "request_id": request_id, "ts": now()}
    await ws.send_json(out)
    logger.info("WS OUT payload=%s", jdump(out))


async def send_event(ws: WebSocket, name: str, request_id: str, extra=None):
    out = {
        "type": "event",
        "name": name,
        "request_id": request_id,
        "ts": now(),
        "extra": extra or {},
    }
    await ws.send_json(out)
    logger.info("WS OUT payload=%s", jdump(out))
    emit({"source": APP_NAME, **out})


@app.websocket("/ws")
async def ws_endpoint(
    websocket: WebSocket,
    channel: str = Query(DEFAULT_CHANNEL),
):
    await hub.connect(websocket, channel)

    hello = {
        "type": "system",
        "message": f"connected to '{channel}'",
        "ts": now(),
    }
    await websocket.send_json(hello)
    logger.info("WS CONNECT channel=%s", channel)
    logger.info("WS OUT payload=%s", jdump(hello))

    try:
        while True:
            msg = await websocket.receive_json()
            logger.info("WS IN channel=%s payload=%s", channel, jdump(msg))

            action = msg.get("action")
            payload = msg.get("payload") or {}
            request_id = msg.get("request_id") or "no-id"

            # 1) ACK первым
            await send_ack(websocket, request_id)

            # ---- учебные команды ----

            if action == "echo":
                out = {
                    "type": "echo",
                    "request_id": request_id,
                    "data": payload,
                    "ts": now(),
                }
                await websocket.send_json(out)
                logger.info("WS OUT payload=%s", jdump(out))

                await send_event(websocket, "ws.echo", request_id, extra=payload)

            elif action == "triplet_demo":
                step1 = {
                    "type": "step",
                    "request_id": request_id,
                    "step": 1,
                    "message": "first response",
                    "ts": now(),
                }
                step2 = {
                    "type": "step",
                    "request_id": request_id,
                    "step": 2,
                    "message": "second response",
                    "ts": now(),
                }

                await websocket.send_json(step1)
                logger.info("WS OUT payload=%s", jdump(step1))

                await websocket.send_json(step2)
                logger.info("WS OUT payload=%s", jdump(step2))

                await send_event(websocket, "ws.triplet_demo", request_id)

            elif action == "broadcast":
                text = payload.get("message", "")
                out = {
                    "type": "message",
                    "channel": channel,
                    "message": text,
                    "ts": now(),
                }
                # broadcast всем в канале
                await hub.broadcast_json(channel, out)

                logger.info("WS BROADCAST channel=%s payload=%s", channel, jdump(out))
                emit({"source": APP_NAME, **out})

            elif action == "get_order":
                if not DB_ENABLED:
                    err = {
                        "type": "error",
                        "request_id": request_id,
                        "message": "db integration is disabled",
                        "ts": now(),
                    }
                    await websocket.send_json(err)
                    logger.info("WS OUT payload=%s", jdump(err))
                    continue

                order_id = payload.get("id")

                with SessionLocal() as db:
                    order = db.get(Order, order_id)

                out = {
                    "type": "order",
                    "request_id": request_id,
                    "data": None if not order else {
                        "id": order.id,
                        "customer": order.customer,
                        "status": order.status,
                        "created_at": str(order.created_at),
                    },
                    "ts": now(),
                }

                await websocket.send_json(out)
                logger.info("WS OUT payload=%s", jdump(out))

                await send_event(websocket, "order.viewed", request_id, extra={"id": order_id})

            elif action == "list_orders":
                if not DB_ENABLED:
                    err = {
                        "type": "error",
                        "request_id": request_id,
                        "message": "db integration is disabled",
                        "ts": now(),
                    }
                    await websocket.send_json(err)
                    logger.info("WS OUT payload=%s", jdump(err))
                    continue

                with SessionLocal() as db:
                    orders = db.query(Order).order_by(Order.id.desc()).limit(5).all()

                out = {
                    "type": "orders",
                    "request_id": request_id,
                    "data": [
                        {"id": o.id, "customer": o.customer, "status": o.status}
                        for o in orders
                    ],
                    "ts": now(),
                }

                await websocket.send_json(out)
                logger.info("WS OUT payload=%s", jdump(out))

                await send_event(websocket, "order.listed", request_id)

            else:
                err = {
                    "type": "error",
                    "request_id": request_id,
                    "message": f"unknown action: {action}",
                    "ts": now(),
                }
                await websocket.send_json(err)
                logger.info("WS OUT payload=%s", jdump(err))

    except WebSocketDisconnect:
        hub.disconnect(websocket, channel)
        logger.info("WS DISCONNECT channel=%s", channel)

    except Exception as e:
        hub.disconnect(websocket, channel)
        logger.exception("WS ERROR channel=%s err=%s", channel, str(e))
        try:
            await websocket.close()
        except Exception:
            pass
