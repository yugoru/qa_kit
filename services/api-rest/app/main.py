import time

from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy.exc import OperationalError

from .models import Base
from .database import engine
from .routes_orders import router as orders_router


class HealthResponse(BaseModel):
    status: str


app = FastAPI(
    title="QA Kit REST API",
    version="0.1.0"
)


for attempt in range(10):
    try:
        Base.metadata.create_all(bind=engine)
        break
    except OperationalError:
        time.sleep(2)


@app.get("/health", response_model=HealthResponse)
async def health():
    return {"status": "ok"}


app.include_router(orders_router)
