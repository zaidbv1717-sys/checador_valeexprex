from sqlalchemy import Column, DateTime, Integer, String

from ..database import Base


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
