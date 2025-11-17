# app/models/legal.py

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    ForeignKey,   # 👈 añadido
)
from sqlalchemy.orm import relationship   # 👈 añadido

from app.db import Base


class LegalDocument(Base):
    """
    Documento legal general (NDA, política, DPA, AI ACT, etc.).
    Se puede firmar (con usuario y fecha/hora) y tiene un archivo asociado.
    """
    __tablename__ = "legal_documents"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)  # NDA, DPA, AI_ACT, PRIVACY_POLICY, etc.
    file_path = Column(String(500), nullable=True)

    created_by = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    is_signed = Column(Boolean, default=False)
    signed_by = Column(String(50), nullable=True)
    signed_at = Column(DateTime, nullable=True)

    # 👇 relación opcional con firmas individuales (para tu signatures_map)
    signatures = relationship(
        "LegalSignature",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class LegalSignature(Base):
    """
    Firma individual de un usuario sobre un documento legal.
    Esto es lo que están importando tus routers.
    """
    __tablename__ = "legal_signatures"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("legal_documents.id"), nullable=False)
    user_name = Column(String(50), nullable=False)
    signed_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("LegalDocument", back_populates="signatures")


class RGPDRecord(Base):
    """
    Registro de actividades de tratamiento (RAT) para RGPD.
    """
    __tablename__ = "rgpd_records"

    id = Column(Integer, primary_key=True, index=True)

    activity_name = Column(String(255), nullable=False)
    responsible = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    risk_level = Column(String(50), nullable=False)  # bajo / medio / alto

    created_by = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class RiskAnalysis(Base):
    """
    Análisis de riesgos (RGPD / AI ACT / cumplimiento en general).
    """
    __tablename__ = "risk_analysis"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(255), nullable=False)
    risk = Column(String(500), nullable=False)
    mitigation = Column(String(500), nullable=False)

    created_by = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class HealthNorm(Base):
    """
    Normativas sanitarias UE / EEUU.
    Se puede adjuntar documentación de referencia.
    """
    __tablename__ = "health_norms"

    id = Column(Integer, primary_key=True, index=True)

    region = Column(String(50), nullable=False)  # UE / US
    title = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    file_path = Column(String(500), nullable=True)

    created_by = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class CarewaveContract(Base):
    """
    Contratos internos de CareWave Health
    (con partners, empleados, proveedores, etc.).
    """
    __tablename__ = "carewave_contracts"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=True)

    signed_by_company = Column(Boolean, default=False)
    signed_by_partner = Column(Boolean, default=False)

    created_by = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
