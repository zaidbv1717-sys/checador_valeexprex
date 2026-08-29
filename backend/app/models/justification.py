from sqlalchemy import Column, DateTime, String

from ..database import Base


class Justification(Base):
    __tablename__ = "justifications"

    id = Column(String, primary_key=True)
    employee_id = Column(String)
    employee_name = Column(String)
    date_start = Column(String)
    date_end = Column(String)
    type = Column(String)
    status = Column(String)
    note = Column(String, nullable=True)
    created_at = Column(DateTime)
