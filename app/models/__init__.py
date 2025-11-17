# app/models/__init__.py

from .files import File

# ⚖️ Modelos de Legal & Compliance
from .legal import (
    LegalDocument,   # documentos legales generales (NDA, contratos, etc.)
    RGPDRecord,      # registros de actividades de tratamiento (RAT / ROPA)
    RiskAnalysis,    # análisis de riesgos
    HealthNorm,      # normativas sanitarias (UE / EEUU)
    CarewaveContract # contratos propios de CareWave Health
)

# 📊 Modelos de Contabilidad & Finanzas
from .accounting import (
    Account,
    JournalEntry,
    JournalLine,
    Budget,
    Investor,
)

# 💻 Modelos de Tecnología
from .technology import (
    ITSystem,
    SupportTicket,
    DevProject,
    SecurityIncident,
    InnovationIdea,
)

# 📁 Documentos internos por departamento
from .docs import DepartmentDocument


__all__ = [
    # Files
    "File",

    # Legal
    "LegalDocument",
    "RGPDRecord",
    "RiskAnalysis",
    "HealthNorm",
    "CarewaveContract",

    # Accounting
    "Account",
    "JournalEntry",
    "JournalLine",
    "Budget",
    "Investor",

    # Technology
    "ITSystem",
    "SupportTicket",
    "DevProject",
    "SecurityIncident",
    "InnovationIdea",

    # Dept docs
    "DepartmentDocument",
]
