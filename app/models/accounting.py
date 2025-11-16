# app/models/accounting.py
from datetime import date, datetime

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


class Account(Base):
    """
    Cuenta contable.
    type:
      - asset    -> Activo
      - liability-> Pasivo
      - equity   -> Patrimonio neto
      - income   -> Ingresos
      - expense  -> Gastos
    """
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(30), nullable=False)  # asset, liability, equity, income, expense
    country_scheme = Column(String(10), default="ES")  # ES, US, etc.
    is_cash = Column(Boolean, default=False)   # marcar bancos / caja
    is_equity = Column(Boolean, default=False) # marcar cuentas de patrimonio

    # relación con líneas de asiento
    lines = relationship("JournalLine", back_populates="account")


class JournalEntry(Base):
    """
    Asiento contable (cabecera).
    """
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, default=date.today, nullable=False)
    description = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(50), nullable=False)  # username (JSON)

    lines = relationship(
        "JournalLine",
        back_populates="entry",
        cascade="all, delete-orphan",
    )


class JournalLine(Base):
    """
    Línea de asiento (detalle).
    """
    __tablename__ = "journal_lines"

    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(Integer, ForeignKey("journal_entries.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)

    debit = Column(Numeric(12, 2), default=0)
    credit = Column(Numeric(12, 2), default=0)

    entry = relationship("JournalEntry", back_populates="lines")
    account = relationship("Account", back_populates="lines")


class Budget(Base):
    """
    Presupuesto global de gastos para un año/mes concreto.
    Sirve para Presupuesto + Control de gastos.
    """
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    year = Column(Integer, nullable=False)              # ej. 2025
    month = Column(Integer, nullable=True)              # 1-12 o None para anual
    expense_target = Column(Numeric(12, 2), nullable=False)  # presupuesto de gastos
    created_by = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Investor(Base):
    """
    Inversores y % de participación.
    Sirve para Porcentaje inversores + memoria financiera.
    """
    __tablename__ = "investors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    ownership_percent = Column(Numeric(5, 2), nullable=False)  # 0-100
    invested_amount = Column(Numeric(12, 2), nullable=False)
    notes = Column(String(255), nullable=True)