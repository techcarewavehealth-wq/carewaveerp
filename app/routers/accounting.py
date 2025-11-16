# app/routers/accounting.py
from datetime import date
from decimal import Decimal
from collections import defaultdict

from fastapi import APIRouter, Depends, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.accounting import Account, JournalEntry, JournalLine, Budget, Investor
from app.security import get_current_user

router = APIRouter(prefix="/accounting", tags=["Contabilidad & Finanzas"])
templates = Jinja2Templates(directory="app/templates")


ACCOUNT_TYPES = [
    ("asset", "Activo"),
    ("liability", "Pasivo"),
    ("equity", "Patrimonio neto"),
    ("income", "Ingresos"),
    ("expense", "Gastos"),
]


@router.get("/ui", name="accounting_ui")
def accounting_ui(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    account_id: int = None,
):
    # ===== Plan contable =====
    accounts = db.query(Account).order_by(Account.code).all()

    # ===== Libro mayor de una cuenta =====
    ledger_lines = []
    ledger_account = None
    ledger_balance = Decimal("0.00")

    if account_id:
        ledger_account = db.query(Account).get(account_id)
        if ledger_account:
            q = (
                db.query(JournalLine)
                .join(JournalEntry)
                .filter(JournalLine.account_id == ledger_account.id)
                .order_by(JournalEntry.date, JournalEntry.id)
            )
            for line in q.all():
                debit = Decimal(line.debit or 0)
                credit = Decimal(line.credit or 0)
                amount = debit - credit
                ledger_balance += amount
                ledger_lines.append(
                    {
                        "date": line.entry.date,
                        "description": line.entry.description,
                        "debit": debit,
                        "credit": credit,
                        "balance": ledger_balance,
                    }
                )

    # ===== Estados financieros avanzados =====
    lines = db.query(JournalLine).all()

    total_income = Decimal("0.00")
    total_expense = Decimal("0.00")
    assets_total = Decimal("0.00")
    liabilities_total = Decimal("0.00")
    equity_total = Decimal("0.00")
    cash_balance = Decimal("0.00")

    # para burn rate (gastos por mes)
    monthly_expenses = defaultdict(Decimal)

    # desglose de patrimonio neto
    equity_breakdown = defaultdict(Decimal)

    for line in lines:
        acc = line.account
        entry = line.entry
        debit = Decimal(line.debit or 0)
        credit = Decimal(line.credit or 0)

        # Pérdidas y ganancias
        if acc.type == "income":
            total_income += credit - debit
        elif acc.type == "expense":
            total_expense += debit - credit
            if entry.date:
                key = (entry.date.year, entry.date.month)
                monthly_expenses[key] += debit - credit

        # Balance de situación
        if acc.type == "asset":
            balance = debit - credit
            assets_total += balance
            if acc.is_cash:
                cash_balance += balance
        elif acc.type == "liability":
            balance = credit - debit
            liabilities_total += balance
        elif acc.type == "equity" or acc.is_equity:
            balance = credit - debit
            equity_total += balance
            equity_breakdown[f"{acc.code} - {acc.name}"] += balance

    # Resultado del ejercicio
    net_income = total_income - total_expense

    # Burn rate & runway
    burn_rate = Decimal("0.00")
    runway_months = None

    if monthly_expenses:
        sorted_keys = sorted(monthly_expenses.keys())
        # últimos hasta 3 meses con datos
        last_keys = sorted_keys[-3:]
        total_recent = sum(monthly_expenses[k] for k in last_keys)
        months = len(last_keys)
        if months > 0:
            burn_rate = total_recent / months
        if burn_rate > 0:
            runway_months = cash_balance / burn_rate

    # ===== Presupuesto & control de gastos =====
    budgets = db.query(Budget).order_by(Budget.year.desc(), Budget.month.desc().nullslast()).all()
    budgets_info = []
    for b in budgets:
        actual_expense = Decimal("0.00")
        for line in lines:
            acc = line.account
            entry = line.entry
            if acc.type != "expense" or not entry.date:
                continue
            if entry.date.year != b.year:
                continue
            if b.month is not None and entry.date.month != b.month:
                continue
            actual_expense += Decimal(line.debit or 0) - Decimal(line.credit or 0)
        variance = actual_expense - Decimal(b.expense_target or 0)
        budgets_info.append(
            {
                "budget": b,
                "actual_expense": actual_expense,
                "variance": variance,
            }
        )

    # ===== Inversores =====
    investors = db.query(Investor).order_by(Investor.id).all()
    total_invested = sum(Decimal(i.invested_amount or 0) for i in investors)
    total_ownership = sum(Decimal(i.ownership_percent or 0) for i in investors)

    investors_info = []
    for inv in investors:
        pct = Decimal(inv.ownership_percent or 0)
        amt = Decimal(inv.invested_amount or 0)
        implied_valuation = None
        if pct > 0:
            implied_valuation = (amt / pct) * Decimal("100.00")
        investors_info.append(
            {
                "investor": inv,
                "implied_valuation": implied_valuation,
            }
        )

    # ===== Balance por cuentas (balance contable) =====
    balance_rows = []
    for acc in accounts:
        sums = db.query(JournalLine).filter(JournalLine.account_id == acc.id).all()
        debit_total = sum(Decimal(l.debit or 0) for l in sums)
        credit_total = sum(Decimal(l.credit or 0) for l in sums)
        saldo = debit_total - credit_total
        if debit_total != 0 or credit_total != 0:
            balance_rows.append(
                {
                    "account": acc,
                    "debit_total": debit_total,
                    "credit_total": credit_total,
                    "saldo": saldo,
                }
            )

    return templates.TemplateResponse(
        "accounting.html",
        {
            "request": request,
            "user": current_user,

            "accounts": accounts,
            "account_types": ACCOUNT_TYPES,

            "ledger_account": ledger_account,
            "ledger_lines": ledger_lines,
            "ledger_balance": ledger_balance,
            "selected_account_id": account_id,

            "balance_rows": balance_rows,

            # Presupuestos
            "budgets_info": budgets_info,

            # Inversores
            "investors_info": investors_info,
            "total_invested": total_invested,
            "total_ownership": total_ownership,

            # Estados financieros / memoria financiera
            "total_income": total_income,
            "total_expense": total_expense,
            "net_income": net_income,
            "assets_total": assets_total,
            "liabilities_total": liabilities_total,
            "equity_total": equity_total,
            "cash_balance": cash_balance,
            "equity_breakdown": equity_breakdown,
            "burn_rate": burn_rate,
            "runway_months": runway_months,
        },
    )


# ================== Cuentas ==================

@router.post("/accounts/create")
def create_account(
    request: Request,
    code: str = Form(...),
    name: str = Form(...),
    type: str = Form(...),
    scheme: str = Form("ES"),
    is_cash: bool = Form(False),
    is_equity: bool = Form(False),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    code = code.strip()
    name = name.strip()
    if not code or not name:
        return RedirectResponse(url="/accounting/ui", status_code=303)

    existing = db.query(Account).filter(Account.code == code).first()
    if existing:
        return RedirectResponse(url="/accounting/ui", status_code=303)

    acc = Account(
        code=code,
        name=name,
        type=type,
        country_scheme=scheme,
        is_cash=is_cash,
        is_equity=is_equity,
    )
    db.add(acc)
    db.commit()

    return RedirectResponse(url="/accounting/ui", status_code=303)


@router.post("/accounts/{account_id}/delete")
def delete_account(
    account_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    acc = db.query(Account).get(account_id)
    if not acc:
        return RedirectResponse(url="/accounting/ui", status_code=303)

    # Solo permitir borrar si no tiene movimientos
    has_lines = db.query(JournalLine).filter(JournalLine.account_id == acc.id).first()
    if has_lines:
        return RedirectResponse(url="/accounting/ui", status_code=303)

    db.delete(acc)
    db.commit()
    return RedirectResponse(url="/accounting/ui", status_code=303)


# ================== Asientos (Libro diario) ==================

@router.post("/journal/create")
def create_journal_entry(
    request: Request,
    date_str: str = Form(...),
    description: str = Form(...),
    debit_account_id: int = Form(...),
    debit_amount: str = Form(...),
    credit_account_id: int = Form(...),
    credit_amount: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        d = date.fromisoformat(date_str)
    except Exception:
        d = date.today()

    description = description.strip()
    if not description:
        description = "Asiento manual"

    try:
        debit = Decimal(debit_amount.replace(",", "."))
        credit = Decimal(credit_amount.replace(",", "."))
    except Exception:
        return RedirectResponse(url="/accounting/ui", status_code=303)

    if debit <= 0 or credit <= 0 or debit != credit:
        # pedimos que cuadre
        return RedirectResponse(url="/accounting/ui", status_code=303)

    entry = JournalEntry(
        date=d,
        description=description,
        created_by=current_user,
    )
    db.add(entry)
    db.flush()

    line_debit = JournalLine(
        entry_id=entry.id,
        account_id=debit_account_id,
        debit=debit,
        credit=0,
    )
    line_credit = JournalLine(
        entry_id=entry.id,
        account_id=credit_account_id,
        debit=0,
        credit=credit,
    )
    db.add_all([line_debit, line_credit])
    db.commit()

    return RedirectResponse(url="/accounting/ui", status_code=303)


@router.post("/journal/{entry_id}/delete")
def delete_journal_entry(
    entry_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    entry = db.query(JournalEntry).get(entry_id)
    if not entry:
        return RedirectResponse(url="/accounting/ui", status_code=303)

    db.delete(entry)  # las líneas se borran por cascade
    db.commit()
    return RedirectResponse(url="/accounting/ui", status_code=303)


# ================== Presupuestos ==================

@router.post("/budgets/create")
def create_budget(
    request: Request,
    name: str = Form(...),
    year: int = Form(...),
    month: str = Form(""),
    expense_target: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    name = name.strip()
    if not name:
        return RedirectResponse(url="/accounting/ui", status_code=303)

    try:
        y = int(year)
    except Exception:
        return RedirectResponse(url="/accounting/ui", status_code=303)

    m = None
    if month:
        try:
            m = int(month)
        except Exception:
            m = None

    try:
        target = Decimal(expense_target.replace(",", "."))
    except Exception:
        return RedirectResponse(url="/accounting/ui", status_code=303)

    b = Budget(
        name=name,
        year=y,
        month=m,
        expense_target=target,
        created_by=current_user,
    )
    db.add(b)
    db.commit()

    return RedirectResponse(url="/accounting/ui", status_code=303)


@router.post("/budgets/{budget_id}/delete")
def delete_budget(
    budget_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    b = db.query(Budget).get(budget_id)
    if not b:
        return RedirectResponse(url="/accounting/ui", status_code=303)

    db.delete(b)
    db.commit()
    return RedirectResponse(url="/accounting/ui", status_code=303)


# ================== Inversores ==================

@router.post("/investors/create")
def create_investor(
    request: Request,
    name: str = Form(...),
    ownership_percent: str = Form(...),
    invested_amount: str = Form(...),
    notes: str = Form(""),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    name = name.strip()
    if not name:
        return RedirectResponse(url="/accounting/ui", status_code=303)

    try:
        pct = Decimal(ownership_percent.replace(",", "."))
        amt = Decimal(invested_amount.replace(",", "."))
    except Exception:
        return RedirectResponse(url="/accounting/ui", status_code=303)

    inv = Investor(
        name=name,
        ownership_percent=pct,
        invested_amount=amt,
        notes=notes.strip() or None,
    )
    db.add(inv)
    db.commit()

    return RedirectResponse(url="/accounting/ui", status_code=303)


@router.post("/investors/{investor_id}/delete")
def delete_investor(
    investor_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    inv = db.query(Investor).get(investor_id)
    if not inv:
        return RedirectResponse(url="/accounting/ui", status_code=303)

    db.delete(inv)
    db.commit()
    return RedirectResponse(url="/accounting/ui", status_code=303)