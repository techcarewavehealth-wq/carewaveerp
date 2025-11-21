# app/main.py
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles   # 👈 IMPORTANTE: StaticFiles (con S mayúscula)

from app.db import Base, engine

# Registrar todos los modelos (files, legal, accounting, etc.)
import app.models  # noqa: F401

# Routers
from app.routers.auth import router as auth_router
from app.routers.files import router as files_router
from app.routers.legal import router as legal_router
from app.routers.accounting import router as accounting_router
from app.routers.technology import router as technology_router


BASE_DIR = Path(__file__).resolve().parent

logging.basicConfig(
    level="INFO",
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("carewave")

app = FastAPI(title="CareWave ERP", version="0.3.0")

# ==================== STATIC: STORAGE ====================
# Aquí servimos TODOS los archivos que se suben:
#   storage/<departamento>/<archivo>
# y se verán en el navegador como:
#   /storage/<departamento>/<archivo>
app.mount("/storage", StaticFiles(directory="storage"), name="storage")

# ==================== STATIC: /static opcional ====================
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
else:
    log.info("Carpeta static no encontrada en %s", static_dir)

# ==================== MIDDLEWARES ====================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sesiones para el login (usuarios JSON)
app.add_middleware(SessionMiddleware, secret_key="cambia-esta-clave-en-produccion")

# ==================== ROUTERS ====================

app.include_router(auth_router)
app.include_router(files_router)
app.include_router(legal_router)
app.include_router(accounting_router)
app.include_router(technology_router)

# ==================== RUTAS BASE ====================

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/ui/login")

# ==================== CICLO DE VIDA ====================

@app.on_event("startup")
async def on_startup():
    log.info("Creando tablas de base de datos (files, legal, accounting, etc.)...")
    Base.metadata.create_all(bind=engine)
    log.info("Aplicación CareWave lista en /ui/login")


@app.on_event("shutdown")
async def on_shutdown():
    log.info("Apagando CareWave ERP...")


# Arranque directo opcional: python -m app.main
if __name__ == "_main":   # 👈 corregido (antes ponía "_main")
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
