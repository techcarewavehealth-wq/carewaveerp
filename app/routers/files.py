# app/routers/files.py
from datetime import datetime
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    Form,
    Request,
    UploadFile,
    File as FastAPIFile,   # helper de FastAPI para subir archivos
    HTTPException,         # ✅ NUEVO
)
from fastapi.responses import RedirectResponse, FileResponse  # ✅ añadimos FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.files import File as StoredFile          # modelo de BD
from app.models.docs import DepartmentDocument
from app.security import get_current_user

router = APIRouter(prefix="/files", tags=["Archivos & Docs"])
templates = Jinja2Templates(directory="app/templates")

# 🟢 LISTA DE DEPARTAMENTOS (incluye Producto tecnológico / Marketing)
DEPARTMENTS = [
    ("general", "General"),
    ("contabilidad", "Contabilidad"),
    ("finanzas", "Finanzas"),
    ("legal", "Legal"),
    ("talento_humano", "Talento Humano"),
    ("tecnologia", "Tecnología"),
    ("reuniones_estrategia", "Reuniones y Estrategias"),
    ("producto_marketing", "Producto tecnológico / Marketing"),
]

STORAGE_ROOT = Path("storage")
STORAGE_ROOT.mkdir(parents=True, exist_ok=True)


@router.get("/ui", name="files_ui")
def files_ui(
    request: Request,
    department: str = "general",
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Normalizamos departamento: si viene uno raro, forzamos a general
    valid_departments = {d[0] for d in DEPARTMENTS}
    if department not in valid_departments:
        department = "general"

    # Archivos subidos (ficheros físicos)
    files_q = (
        db.query(StoredFile)
        .filter(StoredFile.department == department)
        .order_by(StoredFile.uploaded_at.desc())
    )
    files = files_q.all()

    # Documentos internos (CareWave Docs)
    docs_q = (
        db.query(DepartmentDocument)
        .filter(DepartmentDocument.department == department)
        .order_by(DepartmentDocument.created_at.desc())
    )
    docs = docs_q.all()

    return templates.TemplateResponse(
        "files.html",
        {
            "request": request,
            "user": current_user,
            "departments": DEPARTMENTS,
            "selected_department": department,
            "files": files,
            "docs": docs,
        },
    )


# ============== SUBIDA DE ARCHIVOS ==============

@router.post("/upload")
async def upload_file(
    request: Request,
    department: str = Form(...),
    uploaded_file: UploadFile = FastAPIFile(...),   # aquí estaba el error y ya está bien
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not uploaded_file.filename:
        return RedirectResponse(
            url=f"/files/ui?department={department}", status_code=303
        )

    # Carpeta por departamento
    dept_dir = STORAGE_ROOT / department
    dept_dir.mkdir(parents=True, exist_ok=True)

    stored_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uploaded_file.filename}"
    stored_path = dept_dir / stored_name

    # Guardamos el archivo físicamente
    with stored_path.open("wb") as f:
        content = await uploaded_file.read()
        f.write(content)

    # Guardamos metadatos en BD
    db_file = StoredFile(
        filename=uploaded_file.filename,
        department=department,
        stored_path=str(stored_path),
        uploaded_by=current_user,
    )
    db.add(db_file)
    db.commit()

    return RedirectResponse(
        url=f"/files/ui?department={department}", status_code=303
    )


# ============== BORRADO DE ARCHIVOS ==============

@router.post("/files/{file_id}/delete")
def delete_file(
    file_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    f = db.query(StoredFile).get(file_id)
    if not f:
        return RedirectResponse(url="/files/ui", status_code=303)

    # Intentamos borrar el archivo físico
    try:
        p = Path(f.stored_path)
        if p.exists():
            p.unlink()
    except Exception:
        # Si falla el borrado físico no tiramos la app
        pass

    department = f.department or "general"
    db.delete(f)
    db.commit()

    return RedirectResponse(
        url=f"/files/ui?department={department}", status_code=303
    )


# ============== VER / DESCARGAR ARCHIVO ==============  ✅ NUEVO

@router.get("/files/{file_id}/view")
def view_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Devuelve el archivo subido para verlo o descargarlo.
    """
    f = db.query(StoredFile).get(file_id)
    if not f:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    file_path = Path(f.stored_path)

    # En Render a veces la ruta es relativa, la hacemos absoluta
    if not file_path.is_absolute():
        file_path = Path.cwd() / file_path

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Archivo no encontrado en el servidor",
        )

    # Detección simple del tipo MIME
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        media_type = "application/pdf"
    elif suffix in {".png", ".jpg", ".jpeg"}:
        media_type = "image/" + suffix.lstrip(".")
    elif suffix in {".doc", ".docx"}:
        media_type = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    elif suffix in {".xls", ".xlsx"}:
        media_type = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        media_type = "application/octet-stream"

    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type=media_type,
    )


# ============== DOCUMENTOS INTERNOS (CareWave Docs) ==============

@router.post("/docs/create")
def create_doc(
    request: Request,
    department: str = Form(...),
    title: str = Form(...),
    content: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    title = title.strip()
    if not title:
        return RedirectResponse(
            url=f"/files/ui?department={department}", status_code=303
        )

    doc = DepartmentDocument(
        title=title,
        content=content,
        department=department,
        created_by=current_user,
    )
    db.add(doc)
    db.commit()

    return RedirectResponse(
        url=f"/files/ui?department={department}", status_code=303
    )


@router.post("/docs/{doc_id}/delete")
def delete_doc(
    doc_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    doc = db.query(DepartmentDocument).get(doc_id)
    if not doc:
        return RedirectResponse(url="/files/ui", status_code=303)

    department = doc.department or "general"
    db.delete(doc)
    db.commit()

    return RedirectResponse(
        url=f"/files/ui?department={department}", status_code=303
    )
