from sqlalchemy import Column, DateTime, ForeignKey, Index, String

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

    # Sin estos indices cada reporte hacia un scan completo de la tabla, y los
    # tres filtros de todas las consultas son justo estas columnas.
    __table_args__ = (
        Index("ix_records_employee_timestamp", "employee_id", "timestamp"),
        Index("ix_records_timestamp", "timestamp"),
        Index("ix_records_employee_type_timestamp", "employee_id", "type", "timestamp"),
    )


class DayNote(Base):
    __tablename__ = "day_notes"

    employee_id = Column(String, primary_key=True)
    date = Column(String, primary_key=True)
    note = Column(String, nullable=True)
