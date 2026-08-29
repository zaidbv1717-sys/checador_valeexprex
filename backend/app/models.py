from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from .database import Base


class Employee(Base):
    __tablename__ = "employees"

    id = Column(String, primary_key=True)
    name = Column(String)
    pin = Column(String(4), unique=True)
    sched_in = Column(String, default="09:00")
    sched_out = Column(String, default="18:00")
    category = Column(String, default="trabajador")
    lunch_minutes = Column(Integer, nullable=True)


class Record(Base):
    __tablename__ = "records"

    id = Column(String, primary_key=True)
    employee_id = Column(String, ForeignKey("employees.id"))
    employee_name = Column(String)
    type = Column(String)
    timestamp = Column(DateTime)
    source_ip = Column(String, nullable=True)


class ConfigEntry(Base):
    __tablename__ = "config"

    key = Column(String, primary_key=True)
    value = Column(String)


class DeviceAlert(Base):
    __tablename__ = "device_alerts"

    id = Column(String, primary_key=True)
    ip = Column(String, nullable=True)
    emp1_name = Column(String)
    emp1_time = Column(DateTime)
    emp2_name = Column(String)
    emp2_time = Column(DateTime)
    created_at = Column(DateTime)
    resolved = Column(Integer, default=0)


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


class DayNote(Base):
    __tablename__ = "day_notes"

    employee_id = Column(String, primary_key=True)
    date = Column(String, primary_key=True)
    note = Column(String, nullable=True)
