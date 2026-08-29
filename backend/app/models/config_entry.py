from sqlalchemy import Column, String

from ..database import Base


class ConfigEntry(Base):
    __tablename__ = "config"

    key = Column(String, primary_key=True)
    value = Column(String)
