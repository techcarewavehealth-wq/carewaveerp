# app/routers/technology.py
from datetime import datetime, date

from fastapi import APIRouter, Depends, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.technology import (
    ITSystem,
    SupportTicket,
    DevProject,
    SecurityIncident,
    InnovationIdea,
)
from app.security import get_current_user

router = APIRouter(prefix="/technology", tags=["Departamento Tecnológico"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/ui", name="technology_ui")
def technology_ui(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    systems = db.query(ITSystem).order_by(ITSystem.criticality.desc(), ITSystem.name).all()
    tickets = db.query(SupportTicket).order_by(SupportTicket.created_at.desc()).all()
    projects = db.query(DevProject).order_by(DevProject.created_at.desc()).all()
    incidents = db.query(SecurityIncident).order_by(SecurityIncident.detected_at.desc()).all()
    ideas = db.query(InnovationIdea).order_by(InnovationIdea.created_at.desc()).all()

    # pequeños KPIs básicos
    open_tickets = sum(1 for t in tickets if t.status != "cerrado")
    open_incidents = sum(1 for i in incidents if i.status != "cerrado")
    active_projects = sum(1 for p in projects if p.status not in ("cerrado", "en producción"))

    return templates.TemplateResponse(
        "technology.html",
        {
            "request": request,
            "user": current_user,
            "systems": systems,
            "tickets": tickets,
            "projects": projects,
            "incidents": incidents,
            "ideas": ideas,
            "open_tickets": open_tickets,
            "open_incidents": open_incidents,
            "active_projects": active_projects,
        },
    )


# ================== Administración de sistemas ==================

@router.post("/systems/create")
def create_system(
    request: Request,
    name: str = Form(...),
    category: str = Form(...),
    status: str = Form("operativo"),
    criticality: str = Form("media"),
    owner: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    s = ITSystem(
        name=name.strip(),
        category=category.strip(),
        status=status.strip(),
        criticality=criticality.strip(),
        owner=owner.strip() or None,
        notes=notes.strip() or None,
    )
    db.add(s)
    db.commit()
    return RedirectResponse(url="/technology/ui", status_code=303)


@router.post("/systems/{system_id}/delete")
def delete_system(
    system_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    s = db.query(ITSystem).get(system_id)
    if s:
        db.delete(s)
        db.commit()
    return RedirectResponse(url="/technology/ui", status_code=303)


# ================== Soporte Técnico ==================

@router.post("/tickets/create")
def create_ticket(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    priority: str = Form("media"),
    category: str = Form(""),
    assigned_to: str = Form(""),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    t = SupportTicket(
        title=title.strip(),
        description=description.strip() or None,
        status="abierto",
        priority=priority.strip(),
        category=category.strip() or None,
        requester=current_user,
        assigned_to=assigned_to.strip() or None,
    )
    db.add(t)
    db.commit()
    return RedirectResponse(url="/technology/ui", status_code=303)


@router.post("/tickets/{ticket_id}/change_status")
def change_ticket_status(
    ticket_id: int,
    request: Request,
    new_status: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    t = db.query(SupportTicket).get(ticket_id)
    if not t:
        return RedirectResponse(url="/technology/ui", status_code=303)

    t.status = new_status.strip()
    if t.status in ("resuelto", "cerrado") and not t.closed_at:
        t.closed_at = datetime.utcnow()
    db.commit()
    return RedirectResponse(url="/technology/ui", status_code=303)


@router.post("/tickets/{ticket_id}/delete")
def delete_ticket(
    ticket_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    t = db.query(SupportTicket).get(ticket_id)
    if t:
        db.delete(t)
        db.commit()
    return RedirectResponse(url="/technology/ui", status_code=303)


# ================== Desarrollo de Software ==================

@router.post("/projects/create")
def create_project(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    status: str = Form("en diseño"),
    repo_url: str = Form(""),
    owner: str = Form(""),
    start_date_str: str = Form(""),
    due_date_str: str = Form(""),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    def parse_date(x: str):
        x = x.strip()
        if not x:
            return None
        try:
            return date.fromisoformat(x)
        except Exception:
            return None

    p = DevProject(
        name=name.strip(),
        description=description.strip() or None,
        status=status.strip(),
        repo_url=repo_url.strip() or None,
        owner=owner.strip() or None,
        start_date=parse_date(start_date_str),
        due_date=parse_date(due_date_str),
    )
    db.add(p)
    db.commit()
    return RedirectResponse(url="/technology/ui", status_code=303)


@router.post("/projects/{project_id}/delete")
def delete_project(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    p = db.query(DevProject).get(project_id)
    if p:
        db.delete(p)
        db.commit()
    return RedirectResponse(url="/technology/ui", status_code=303)


# ================== Seguridad Informática ==================

@router.post("/incidents/create")
def create_incident(
    request: Request,
    title: str = Form(...),
    severity: str = Form("media"),
    status: str = Form("abierto"),
    description: str = Form(""),
    impacted_system: str = Form(""),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    i = SecurityIncident(
        title=title.strip(),
        severity=severity.strip(),
        status=status.strip(),
        description=description.strip() or None,
        impacted_system=impacted_system.strip() or None,
        reported_by=current_user,
    )
    db.add(i)
    db.commit()
    return RedirectResponse(url="/technology/ui", status_code=303)


@router.post("/incidents/{incident_id}/change_status")
def change_incident_status(
    incident_id: int,
    request: Request,
    new_status: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    i = db.query(SecurityIncident).get(incident_id)
    if not i:
        return RedirectResponse(url="/technology/ui", status_code=303)

    i.status = new_status.strip()
    if i.status in ("mitigado", "cerrado") and not i.resolved_at:
        i.resolved_at = datetime.utcnow()
    db.commit()
    return RedirectResponse(url="/technology/ui", status_code=303)


@router.post("/incidents/{incident_id}/delete")
def delete_incident(
    incident_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    i = db.query(SecurityIncident).get(incident_id)
    if i:
        db.delete(i)
        db.commit()
    return RedirectResponse(url="/technology/ui", status_code=303)


# ================== Innovación & Estrategia ==================

@router.post("/ideas/create")
def create_idea(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    status: str = Form("propuesta"),
    impact_score: int = Form(0),
    effort_score: int = Form(0),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    idea = InnovationIdea(
        title=title.strip(),
        description=description.strip() or None,
        status=status.strip(),
        impact_score=impact_score or None,
        effort_score=effort_score or None,
        created_by=current_user,
    )
    db.add(idea)
    db.commit()
    return RedirectResponse(url="/technology/ui", status_code=303)


@router.post("/ideas/{idea_id}/delete")
def delete_idea(
    idea_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    idea = db.query(InnovationIdea).get(idea_id)
    if idea:
        db.delete(idea)
        db.commit()
    return RedirectResponse(url="/technology/ui", status_code=303)