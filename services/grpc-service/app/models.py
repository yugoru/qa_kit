from sqlalchemy import Column, Integer, String

from .db import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer = Column(String, nullable=False)
    status = Column(String, nullable=False)
