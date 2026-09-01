from sqlalchemy import Column, DateTime, ForeignKey, String

from ..database import Base


class Record(Base):
    __tablename__ = "records"

    id = Column(String, primary_key=True)
    employee_id = Column(String, ForeignKey("employees.id"))
    employee_name = Column(String)
    type = Column(String)
    timestamp = Column(DateTime)
    source_ip = Column(String, nullable=True)
    photo_path = Column(String, nullable=True)


class DayNote(Base):
    __tablename__ = "day_notes"

    employee_id = Column(String, primary_key=True)
    date = Column(String, primary_key=True)
    note = Column(String, nullable=True)
