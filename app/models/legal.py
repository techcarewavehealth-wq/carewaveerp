# app/models/legal.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.db import Base


class LegalDocument(Base):
    __tablename__ = "legal_documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    status = Column(String(20), default="draft")  # draft, signed, cancelled...
    created_at = Column(DateTime, default=datetime.utcnow)

    # NUEVO: info del archivo adjunto (opcional)
    filename = Column(String(255), nullable=True)       # nombre del archivo
    stored_path = Column(String(500), nullable=True)    # ruta física en disco

    signatures = relationship(
        "LegalSignature",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class LegalSignature(Base):
    __tablename__ = "legal_signatures"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("legal_documents.id"), nullable=False)
    user_name = Column(String(50), nullable=False)  # username del JSON
    signed_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("LegalDocument", back_populates="signatures")