# app/models/technology.py
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, DateTime, Date, Boolean
from app.db import Base


class ITSystem(Base):
    """
    Administración de sistemas:
    Servidores, redes, herramientas críticas, etc.
    """
    __tablename__ = "it_systems"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)   # servidor, red, base de datos, etc.
    status = Column(String(50), nullable=False, default="operativo")  # operativo, degradado, caído
    criticality = Column(String(50), nullable=False, default="media") # baja, media, alta
    owner = Column(String(100), nullable=True)       # responsable
    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SupportTicket(Base):
    """
    Soporte técnico:
    Incidencias de usuarios internos / clientes.
    """
    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    status = Column(String(50), nullable=False, default="abierto")  # abierto, en progreso, resuelto, cerrado
    priority = Column(String(50), nullable=False, default="media")  # baja, media, alta, crítica
    category = Column(String(100), nullable=True)                   # hardware, software, acceso, etc.
    requester = Column(String(100), nullable=False)                 # quién lo pide (usuario JSON)
    assigned_to = Column(String(100), nullable=True)                # técnico asignado
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)


class DevProject(Base):
    """
    Desarrollo de software:
    Proyectos, productos internos, etc.
    """
    __tablename__ = "dev_projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    status = Column(String(50), nullable=False, default="en diseño")  # en diseño, en desarrollo, en prueba, en producción, cerrado
    repo_url = Column(String(255), nullable=True)
    owner = Column(String(100), nullable=True)                        # PM / Tech Lead
    start_date = Column(Date, nullable=True)
    due_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SecurityIncident(Base):
    """
    Seguridad informática:
    Incidentes, brechas, intentos, etc.
    """
    __tablename__ = "security_incidents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    severity = Column(String(50), nullable=False, default="media")   # baja, media, alta, crítica
    status = Column(String(50), nullable=False, default="abierto")   # abierto, investigando, mitigado, cerrado
    description = Column(String(1000), nullable=True)
    impacted_system = Column(String(255), nullable=True)
    detected_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    reported_by = Column(String(100), nullable=False)                # usuario JSON que lo reporta


class InnovationIdea(Base):
    """
    Innovación y estrategia:
    Ideas, propuestas, mejoras.
    """
    __tablename__ = "innovation_ideas"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    status = Column(String(50), nullable=False, default="propuesta")  # propuesta, en análisis, aprobada, en marcha, descartada
    impact_score = Column(Integer, nullable=True)                     # 1-10 impacto
    effort_score = Column(Integer, nullable=True)                     # 1-10 esfuerzo
    created_by = Column(String(100), nullable=False)                  # usuario JSON
    created_at = Column(DateTime, default=datetime.utcnow)