# app/models/accounting.py

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    DateTime,
    Numeric,
    Boolean,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from app.db import Base


# =============================================================
# PLAN DE CUENTAS (ES / US / OTROS)
# =============================================================

class Account(Base):
    """
    Cuenta contable.

    type:
      - asset     -> Activo
      - liability -> Pasivo
      - equity    -> Patrimonio neto
      - income    -> Ingresos
      - expense   -> Gastos

    country_scheme:
      - 'ES' -> PGC español
      - 'US' -> US GAAP
      - etc.

    Con esto puedes tener el plan contable para España y EEUU en la misma tabla.
    """
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)

    # Código de cuenta (430, 700, 600, 1000, etc.)
    code = Column(String(20), unique=True, nullable=False, index=True)

    # Nombre descriptivo
    name = Column(String(255), nullable=False)

    # asset / liability / equity / income / expense
    type = Column(String(30), nullable=False)

    # Esquema contable: ES (PGC), US (US GAAP), etc.
    country_scheme = Column(String(10), default="ES")

    # Marcas útiles para informes rápidos
    is_cash = Column(Boolean, default=False)    # bancos, caja
    is_equity = Column(Boolean, default=False)  # capital, reservas, etc.

    # Relación con líneas de asiento
    lines = relationship("JournalLine", back_populates="account")

    def __repr__(self) -> str:
        return f"<Account {self.code} - {self.name} ({self.country_scheme})>"


# =============================================================
# ASIENTOS CONTABLES: LIBRO DIARIO / LIBRO MAYOR
# =============================================================

class JournalEntry(Base):
    """
    Asiento contable (cabecera).
    Sirve para libro diario: cada entrada tiene N líneas (JournalLine).

    De aquí se derivan:
      - Libro diario
      - Libro mayor
      - Pérdidas y ganancias
      - Balance de situación
      - Balance contable
      - Flujos de efectivo (según tipo de cuenta)
      - Estado de cambios en patrimonio neto
    """
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, index=True)

    date = Column(Date, default=date.today, nullable=False)
    description = Column(String(255), nullable=False)

    # ES / US: por si quieres forzar que el asiento pertenece a un esquema
    country_scheme = Column(String(10), default="ES")

    # Puede ser útil tener un diario (GENERAL, VENTAS, COBROS, etc.)
    journal = Column(String(50), default="GENERAL")

    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(50), nullable=False)  # username

    # Líneas de asiento (doble partida)
    lines = relationship(
        "JournalLine",
        back_populates="entry",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<JournalEntry {self.id} {self.date} {self.description}>"

    @property
    def total_debit(self) -> Decimal:
        return sum((line.debit or Decimal("0.00")) for line in self.lines)

    @property
    def total_credit(self) -> Decimal:
        return sum((line.credit or Decimal("0.00")) for line in self.lines)


class JournalLine(Base):
    """
    Línea de asiento (detalle).
    Una línea hace referencia a una cuenta concreta.
    """
    __tablename__ = "journal_lines"

    id = Column(Integer, primary_key=True, index=True)

    entry_id = Column(Integer, ForeignKey("journal_entries.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)

    # Importes
    debit = Column(Numeric(14, 2), default=Decimal("0.00"))
    credit = Column(Numeric(14, 2), default=Decimal("0.00"))

    # Relaciones
    entry = relationship("JournalEntry", back_populates="lines")
    account = relationship("Account", back_populates="lines")

    def __repr__(self) -> str:
        return f"<JournalLine entry={self.entry_id} acc={self.account_id} D={self.debit} H={self.credit}>"


# =============================================================
# PRESUPUESTO / CONTROL DE GASTOS
# =============================================================

class Budget(Base):
    """
    Presupuesto global de gastos para un año/mes concreto.
    Sirve para:
      - Presupuesto & control de gastos
      - Comparar gasto real (a partir de JournalLine de tipo expense)
      - Calcular burn rate y runway.
    """
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(255), nullable=False)

    # Ej: 2025
    year = Column(Integer, nullable=False)

    # 1-12 o None para presupuesto anual
    month = Column(Integer, nullable=True)

    # Presupuesto de gastos (importe objetivo)
    expense_target = Column(Numeric(14, 2), nullable=False)

    created_by = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Budget {self.name} {self.year}-{self.month or 'ANUAL'} {self.expense_target}>"


# =============================================================
# INVERSORES / MEMORIA FINANCIERA
# =============================================================

class Investor(Base):
    """
    Inversores y % de participación.
    Sirve para:
      - Porcentaje de inversores
      - Memoria financiera
      - Cálculo de equity / capitalización aproximada.
    """
    __tablename__ = "investors"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(255), nullable=False)

    # % de participación (0-100)
    ownership_percent = Column(Numeric(5, 2), nullable=False)

    # Importe total invertido
    invested_amount = Column(Numeric(14, 2), nullable=False)

    notes = Column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<Investor {self.name} {self.ownership_percent}% {self.invested_amount}>"


# =============================================================
# KPIs MENSUALES (BURN RATE / RUNWAY / MEMORIA)
# =============================================================

class MonthlyKPI(Base):
    """
    KPIs financieros mensuales calculados a partir de los asientos:
      - burn_rate: gasto medio mensual (cash out)
      - runway_months: meses de vida estimados según caja disponible
      - recurring_revenue: ingresos recurrentes (opcional)
      - notes: cualquier comentario para la memoria financiera
    """
    __tablename__ = "monthly_kpis"

    id = Column(Integer, primary_key=True, index=True)

    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)  # 1-12

    burn_rate = Column(Numeric(14, 2), nullable=True)       # €
    runway_months = Column(Numeric(6, 2), nullable=True)    # meses
    recurring_revenue = Column(Numeric(14, 2), nullable=True)

    # Guardar quién calculó / validó este KPI
    calculated_by = Column(String(50), nullable=True)
    calculated_at = Column(DateTime, default=datetime.utcnow)

    notes = Column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<MonthlyKPI {self.year}-{self.month} burn={self.burn_rate} runway={self.runway_months}>"
