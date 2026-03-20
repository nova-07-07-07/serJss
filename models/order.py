from sqlalchemy import Column, Integer, Date
from models.user import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    load = Column(Integer)
    empty = Column(Integer)
    created_at = Column(Date)
