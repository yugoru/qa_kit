from pydantic import BaseModel


class OrderCreate(BaseModel):
    customer: str


class OrderResponse(BaseModel):
    id: int
    customer: str
    status: str

    class Config:
        from_attributes = True
