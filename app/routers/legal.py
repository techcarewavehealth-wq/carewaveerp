# app/routers/legal.py
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    Request,
    Form,
    HTTPException,
    UploadFile,
    File as FastFile,
)
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, FileResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.legal import LegalDocument, LegalSignature
from app.security import get_current_user

templates = Jinja2Templates(directory="app/templates")

router = APIRouter(prefix="/legal", tags=["Legal & Compliance"])

# Carpeta donde se guardan los documentos legales
LEGAL_DIR = Path("storage/legal_docs")
LEGAL_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/ui", name="legal_ui")
def legal_ui(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    docs = db.query(LegalDocument).order_by(LegalDocument.created_at.desc()).all()
    signatures_map = {doc.id: [s.user_name for s in doc.signatures] for doc in docs}

    return templates.TemplateResponse(
        "legal.html",
        {
            "request": request,
            "user": current_user,
            "docs": docs,
            "signatures_map": signatures_map,
        },
    )


@router.post("/documents/create")
async def create_document(
    request: Request,
    title: str = Form(...),
    file: UploadFile | None = FastFile(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    title = title.strip()
    if not title:
        return RedirectResponse(url="/legal/ui", status_code=303)

    filename = None
    stored_path = None

    # Guardar archivo adjunto (opcional)
    if file and file.filename:
        dst = LEGAL_DIR / file.filename
        with dst.open("wb") as f:
            f.write(await file.read())
        filename = file.filename
        stored_path = str(dst)

    doc = LegalDocument(
        title=title,
        filename=filename,
        stored_path=stored_path,
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

    # ¿ya ha firmado este usuario?
    already = (
        db.query(LegalSignature)
        .filter(
            LegalSignature.document_id == doc.id,
            LegalSignature.user_name == current_user,
        )
        .first()
    )
    if already:
        return RedirectResponse(url="/legal/ui", status_code=303)

    sig = LegalSignature(document_id=doc.id, user_name=current_user)
    db.add(sig)
    doc.status = "signed"
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

    # intentar borrar archivo físico si existe
    if doc.stored_path:
        try:
            p = Path(doc.stored_path)
            if p.exists():
                p.unlink()
        except Exception:
            # si falla, no tumbamos el servidor
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

    if not doc.stored_path:
        raise HTTPException(
            status_code=404,
            detail="Este documento no tiene archivo adjunto",
        )

    file_path = Path(doc.stored_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Archivo no encontrado en el servidor",
        )

    return FileResponse(
        path=str(file_path),
        filename=doc.filename,
        media_type="application/octet-stream",
    )