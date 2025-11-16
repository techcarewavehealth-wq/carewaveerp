# app/models/files.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from app.db import Base


class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    department = Column(String(50), nullable=False)    # accounting, legal, hr, etc.
    stored_path = Column(String(500), nullable=False)  # ruta en disco
    uploaded_by = Column(String(50), nullable=False)   # username (BrainAgyeman, etc.)
    uploaded_at = Column(DateTime, default=datetime.utcnow)