# app/routers/files.py
from pathlib import Path

from fastapi import (
    APIRouter,
    Request,
    UploadFile,
    File as FastFile,
    Depends,
    Form,
)
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.files import File as FileModel
from app.models.docs import DepartmentDocument
from app.security import get_current_user

templates = Jinja2Templates(directory="app/templates")

UPLOAD_DIR = Path("storage")
UPLOAD_DIR.mkdir(exist_ok=True)

router = APIRouter(prefix="/files", tags=["Files"])

# Lista fija de departamentos internos
DEPARTMENTS = [
    ("general", "General"),
    ("contabilidad", "Contabilidad"),
    ("finanzas", "Finanzas"),
    ("legal", "Legal"),
    ("talento_humano", "Talento Humano"),
    ("tecnologia", "Tecnología"),
    ("reuniones_estrategia", "Reuniones y Estrategias"),  # NUEVO
]


@router.get("/ui", name="files_ui")
def files_ui(
    request: Request,
    department: str = "general",  # filtro actual (?department=...)
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(FileModel)
    if department and department != "todos":
        q = q.filter(FileModel.department == department)

    files = q.order_by(FileModel.uploaded_at.desc()).all()

    docs = (
        db.query(DepartmentDocument)
        .filter(DepartmentDocument.department == department)
        .order_by(DepartmentDocument.created_at.desc())
        .all()
    )

    return templates.TemplateResponse(
        "files.html",
        {
            "request": request,
            "user": current_user,
            "files": files,
            "documents": docs,
            "departments": DEPARTMENTS,
            "selected_department": department,
        },
    )


@router.post("/upload", name="files_upload")
async def files_upload(
    request: Request,
    department: str = Form("general"),
    upfile: UploadFile = FastFile(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    dept_dir = UPLOAD_DIR / department
    dept_dir.mkdir(parents=True, exist_ok=True)
    dst = dept_dir / upfile.filename

    with dst.open("wb") as f:
        f.write(await upfile.read())

    rec = FileModel(
        filename=upfile.filename,
        department=department,
        stored_path=str(dst),
        uploaded_by=current_user,
    )
    db.add(rec)
    db.commit()

    return RedirectResponse(
        url=f"/files/ui?department={department}", status_code=303
    )


@router.post("/{file_id}/delete", name="files_delete")
def files_delete(
    file_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    department = request.query_params.get("department", "general")

    f = db.query(FileModel).get(file_id)
    if f:
        try:
            p = Path(f.stored_path)
            if p.exists():
                p.unlink()
        except Exception:
            pass

        db.delete(f)
        db.commit()

    return RedirectResponse(
        url=f"/files/ui?department={department}", status_code=303
    )


# ================== Documentos internos (CareWave Docs) ==================

@router.post("/docs/create", name="files_docs_create")
def files_docs_create(
    request: Request,
    department: str = Form(...),
    title: str = Form(...),
    content: str = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    title = title.strip()
    content = content.strip()
    if not title or not content:
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


@router.get("/docs/{doc_id}", name="files_docs_view")
def files_docs_view(
    doc_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    doc = db.query(DepartmentDocument).get(doc_id)
    if not doc:
        return RedirectResponse(url="/files/ui", status_code=303)

    return templates.TemplateResponse(
        "doc_view.html",
        {"request": request, "user": current_user, "doc": doc},
    )


@router.post("/docs/{doc_id}/delete", name="files_docs_delete")
def files_docs_delete(
    doc_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    department = request.query_params.get("department", "general")

    doc = db.query(DepartmentDocument).get(doc_id)
    if doc:
        db.delete(doc)
        db.commit()

    return RedirectResponse(
        url=f"/files/ui?department={department}", status_code=303
    )