# app/routers/legal.py

from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    Request,
    Form,
    HTTPException,
    UploadFile,
    File,
)
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, FileResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.legal import (
    LegalDocument,
    RGPDRecord,
    RiskAnalysis,
    HealthNorm,
    CarewaveContract,
)
from app.security import get_current_user

# ===================== CATEGORÍAS DE DOCUMENTOS =====================

LEGAL_CATEGORIES = [
    ("rgpd", "RGPD / Protección de datos"),
    ("health_eu", "Normativas Sanitarias UE"),
    ("health_us", "Normativas Sanitarias EEUU"),
    ("nda", "NDA – Acuerdo de confidencialidad"),
    ("dpa", "DPA – Data Processing Agreement"),
    ("privacy_policy", "Política de privacidad"),
    ("ai_act", "AI ACT / Inteligencia Artificial"),
    ("ip_dataset", "Propiedad intelectual de datasets"),
    ("service_contract", "Contrato de prestación de servicios"),
]

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(prefix="/legal", tags=["Legal & Compliance"])

# Carpetas de almacenamiento
LEGAL_DIR = Path("storage/legal_docs")
HEALTH_DIR = Path("storage/health_norms")
CAREWAVE_DIR = Path("storage/carewave_contracts")

for d in (LEGAL_DIR, HEALTH_DIR, CAREWAVE_DIR):
    d.mkdir(parents=True, exist_ok=True)


# ========================= UI PRINCIPAL =========================

@router.get("/ui", name="legal_ui")
def legal_ui(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Documentos legales generales
    docs = (
        db.query(LegalDocument)
        .order_by(LegalDocument.created_at.desc())
        .all()
    )

    # Compatibilidad con la plantilla: doc.stored_path -> file_path
    for doc in docs:
        # atributo "virtual" solo para la vista
        doc.stored_path = doc.file_path

    # RGPD – RAT
    rgpd_records = (
        db.query(RGPDRecord)
        .order_by(RGPDRecord.created_at.desc())
        .all()
    )

    # RGPD – Análisis de riesgos
    risk_analyses = (
        db.query(RiskAnalysis)
        .order_by(RiskAnalysis.created_at.desc())
        .all()
    )

    # Normativas sanitarias
    health_norms = (
        db.query(HealthNorm)
        .order_by(HealthNorm.created_at.desc())
        .all()
    )

    # Contratos CareWave
    carewave_contracts = (
        db.query(CarewaveContract)
        .order_by(CarewaveContract.created_at.desc())
        .all()
    )

    return templates.TemplateResponse(
        "legal.html",
        {
            "request": request,
            "user": current_user,
            "documents": docs,
            "rgpd_records": rgpd_records,
            "risk_analyses": risk_analyses,
            "health_norms": health_norms,
            "carewave_contracts": carewave_contracts,
            "legal_categories": LEGAL_CATEGORIES,  # 👈 para el <select>
        },
    )


# ========================= DOCUMENTOS LEGALES =========================

@router.post("/documents/create")
async def create_document(
    request: Request,
    title: str = Form(...),
    category: str = Form(...),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    title = title.strip()
    if not title:
        return RedirectResponse(url="/legal/ui", status_code=303)

    # Validamos categoría (si viene algo raro, ponemos "rgpd")
    valid_keys = {k for k, _ in LEGAL_CATEGORIES}
    if category not in valid_keys:
        category = "rgpd"

    file_path: Optional[str] = None

    if file and file.filename:
        safe_name = file.filename.replace("/", "_").replace("\\", "_")
        ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        stored_name = f"{ts}_{safe_name}"
        dst = LEGAL_DIR / stored_name

        content = await file.read()
        with dst.open("wb") as f:
            f.write(content)

        # guardamos ruta relativa para poder servirla
        file_path = str(dst)

    doc = LegalDocument(
        title=title,
        category=category,
        file_path=file_path,
        created_by=current_user,
    )
    db.add(doc)
    db.commit()

    return RedirectResponse(url="/legal/ui", status_code=303)


@router.post("/documents/{doc_id}/sign")
def sign_document(
    doc_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    doc = db.query(LegalDocument).get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    # Si ya está firmado, no hacemos nada
    if doc.is_signed:
        return RedirectResponse(url="/legal/ui", status_code=303)

    doc.is_signed = True
    doc.signed_by = current_user
    doc.signed_at = datetime.utcnow()
    db.commit()

    return RedirectResponse(url="/legal/ui", status_code=303)


@router.post("/documents/{doc_id}/delete")
def delete_document(
    doc_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    doc = db.query(LegalDocument).get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    if doc.file_path:
        try:
            p = Path(doc.file_path)
            if p.exists():
                p.unlink()
        except Exception:
            pass

    db.delete(doc)
    db.commit()
    return RedirectResponse(url="/legal/ui", status_code=303)


@router.get("/documents/{doc_id}/file")
def get_document_file(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    doc = db.query(LegalDocument).get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    if not doc.file_path:
        raise HTTPException(
            status_code=404,
            detail="Este documento no tiene archivo adjunto",
        )

    file_path = Path(doc.file_path)
    if not file_path.is_absolute():
        file_path = Path.cwd() / file_path

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Archivo no encontrado en el servidor",
        )

    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        media_type = "application/pdf"
    elif suffix in {".png", ".jpg", ".jpeg"}:
        media_type = "image/" + suffix.lstrip(".")
    elif suffix in {".doc", ".docx"}:
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif suffix in {".xls", ".xlsx"}:
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        media_type = "application/octet-stream"

    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type=media_type,
    )


# ========================= RGPD – RAT =========================

@router.post("/rgpd/rat/create")
def create_rgpd_record(
    request: Request,
    activity_name: str = Form(...),
    responsible: str = Form(...),
    description: str = Form(""),
    risk_level: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rec = RGPDRecord(
        activity_name=activity_name.strip(),
        responsible=responsible.strip(),
        description=description.strip() or None,
        risk_level=risk_level,
        created_by=current_user,
    )
    db.add(rec)
    db.commit()
    return RedirectResponse(url="/legal/ui", status_code=303)


@router.post("/rgpd/rat/{record_id}/delete")
def delete_rgpd_record(
    record_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rec = db.query(RGPDRecord).get(record_id)
    if not rec:
        return RedirectResponse(url="/legal/ui", status_code=303)

    db.delete(rec)
    db.commit()
    return RedirectResponse(url="/legal/ui", status_code=303)


# ========================= RGPD – Análisis de riesgos =========================

@router.post("/rgpd/risk/create")
def create_risk_analysis(
    request: Request,
    title: str = Form(...),
    risk: str = Form(...),
    mitigation: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ra = RiskAnalysis(
        title=title.strip(),
        risk=risk.strip(),
        mitigation=mitigation.strip(),
        created_by=current_user,
    )
    db.add(ra)
    db.commit()
    return RedirectResponse(url="/legal/ui", status_code=303)


@router.post("/rgpd/risk/{analysis_id}/delete")
def delete_risk_analysis(
    analysis_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ra = db.query(RiskAnalysis).get(analysis_id)
    if not ra:
        return RedirectResponse(url="/legal/ui", status_code=303)

    db.delete(ra)
    db.commit()
    return RedirectResponse(url="/legal/ui", status_code=303)


# ========================= Normativas sanitarias =========================

@router.post("/health/create")
async def create_health_norm(
    request: Request,
    region: str = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    file_path: Optional[str] = None

    if file and file.filename:
        safe_name = file.filename.replace("/", "_").replace("\\", "_")
        ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        stored_name = f"{ts}_{safe_name}"
        dst = HEALTH_DIR / stored_name

        content = await file.read()
        with dst.open("wb") as f:
            f.write(content)

        file_path = str(dst)

    norm = HealthNorm(
        region=region,
        title=title.strip(),
        description=description.strip() or None,
        file_path=file_path,
        created_by=current_user,
    )
    db.add(norm)
    db.commit()
    return RedirectResponse(url="/legal/ui", status_code=303)


@router.post("/health/{norm_id}/delete")
def delete_health_norm(
    norm_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    norm = db.query(HealthNorm).get(norm_id)
    if not norm:
        return RedirectResponse(url="/legal/ui", status_code=303)

    if norm.file_path:
        try:
            p = Path(norm.file_path)
            if p.exists():
                p.unlink()
        except Exception:
            pass

    db.delete(norm)
    db.commit()
    return RedirectResponse(url="/legal/ui", status_code=303)


# ========================= Contratos CareWave =========================

@router.post("/carewave/create")
async def create_carewave_contract(
    request: Request,
    title: str = Form(...),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    file_path: Optional[str] = None

    if file and file.filename:
        safe_name = file.filename.replace("/", "_").replace("\\", "_")
        ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        stored_name = f"{ts}_{safe_name}"
        dst = CAREWAVE_DIR / stored_name

        content = await file.read()
        with dst.open("wb") as f:
            f.write(content)

        file_path = str(dst)

    c = CarewaveContract(
        title=title.strip(),
        file_path=file_path,
        created_by=current_user,
    )
    db.add(c)
    db.commit()
    return RedirectResponse(url="/legal/ui", status_code=303)


@router.post("/carewave/{contract_id}/sign/company")
def sign_carewave_company(
    contract_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    c = db.query(CarewaveContract).get(contract_id)
    if not c:
        return RedirectResponse(url="/legal/ui", status_code=303)

    c.signed_by_company = True
    db.commit()
    return RedirectResponse(url="/legal/ui", status_code=303)


@router.post("/carewave/{contract_id}/sign/partner")
def sign_carewave_partner(
    contract_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    c = db.query(CarewaveContract).get(contract_id)
    if not c:
        return RedirectResponse(url="/legal/ui", status_code=303)

    c.signed_by_partner = True
    db.commit()
    return RedirectResponse(url="/legal/ui", status_code=303)


@router.post("/carewave/{contract_id}/delete")
def delete_carewave_contract(
    contract_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    c = db.query(CarewaveContract).get(contract_id)
    if not c:
        return RedirectResponse(url="/legal/ui", status_code=303)

    if c.file_path:
        try:
            p = Path(c.file_path)
            if p.exists():
                p.unlink()
        except Exception:
            pass

    db.delete(c)
    db.commit()
    return RedirectResponse(url="/legal/ui", status_code=303)
