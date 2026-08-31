from sqlalchemy import Column, Integer, String

from ..database import Base


class Employee(Base):
    __tablename__ = "employees"

    id = Column(String, primary_key=True)
    name = Column(String)
    pin = Column(String(4), unique=True)
    sched_in = Column(String, default="09:00")
    sched_out = Column(String, default="18:00")
    category = Column(String, default="trabajador")
    lunch_minutes = Column(Integer, nullable=True)
    photo_path = Column(String, nullable=True)
