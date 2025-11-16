# app/models/reports.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from app.db import Base

class Report(Base):
    _tablename_ = "reports"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    department = Column(String(50), nullable=False)  # accounting, finance, legal...
    content = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class ReportDeleteLog(Base):
    _tablename_ = "report_delete_log"

    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    department = Column(String(50), nullable=False)
    deleted_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    deleted_at = Column(DateTime, default=datetime.utcnow)