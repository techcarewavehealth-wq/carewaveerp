# app/models/docs.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from app.db import Base


class DepartmentDocument(Base):
    """
    Documento interno por departamento (CareWave Doc).
    No es Word: es texto guardado en la base de datos.
    """
    __tablename__ = "department_documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    department = Column(String(50), nullable=False)   # contabilidad, finanzas, legal, etc.
    created_by = Column(String(50), nullable=False)   # username JSON
    created_at = Column(DateTime, default=datetime.utcnow)
