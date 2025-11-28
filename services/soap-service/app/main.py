import os
import time
from wsgiref.simple_server import make_server

from spyne import Application, rpc, ServiceBase, Integer, Unicode
from spyne.protocol.soap import Soap11
from spyne.model.complex import ComplexModel
from spyne.server.wsgi import WsgiApplication

from sqlalchemy import create_engine, Column, Integer as SAInteger, String
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import OperationalError


database_url = os.getenv("DATABASE_URL")

engine = create_engine(database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


class Order(Base):
    __tablename__ = "orders"

    id = Column(SAInteger, primary_key=True, index=True)
    customer = Column(String, nullable=False)
    status = Column(String, nullable=False)


class OrderType(ComplexModel):
    id = Integer
    customer = Unicode
    status = Unicode
    error = Unicode


class OrderSoapService(ServiceBase):
    @rpc(Integer, _returns=OrderType)
    def GetOrder(ctx, id):
        session = SessionLocal()
        try:
            order = session.query(Order).filter(Order.id == id).first()
            if not order:
                return OrderType(
                    id=0,
                    customer=u"",
                    status=u"",
                    error=u"order not found",
                )
            return OrderType(
                id=order.id,
                customer=order.customer,
                status=order.status,
                error=u"",
            )
        finally:
            session.close()


for _ in range(10):
    try:
        Base.metadata.create_all(bind=engine)
        break
    except OperationalError:
        time.sleep(2)


soap_app = Application(
    [OrderSoapService],
    tns="qa.soap.orders",
    in_protocol=Soap11(validator="lxml"),
    out_protocol=Soap11(),
)

wsgi_app = WsgiApplication(soap_app)


if __name__ == "__main__":
    server = make_server("0.0.0.0", 8080, wsgi_app)
    print("SOAP service started on :8080 (/)")
    server.serve_forever()
