# app/routers/auth.py
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.security import SESSION_USER_KEY, authenticate, get_current_user

router = APIRouter(tags=["Auth"])

templates = Jinja2Templates(directory="app/templates")


# -----------------------------
#   PÁGINA DE LOGIN
# -----------------------------
@router.get("/ui/login", name="login_ui")
def login_ui(request: Request):
    # Si ya está logueado → mandar al dashboard
    if request.session.get(SESSION_USER_KEY):
        return RedirectResponse(url="/ui/dashboard", status_code=303)

    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": None},
    )


# -----------------------------
#   PROCESO DE LOGIN
# -----------------------------
@router.post("/ui/login")
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    user = authenticate(username, password)

    if not user:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Usuario o contraseña incorrectos",
            },
            status_code=400,
        )

    # Guardamos el username en sesión
    request.session[SESSION_USER_KEY] = user["username"]

    return RedirectResponse(url="/ui/dashboard", status_code=303)


# -----------------------------
#   LOGOUT
# -----------------------------
@router.get("/logout", name="logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/ui/login", status_code=303)


# -----------------------------
#   DASHBOARD
# -----------------------------
@router.get("/ui/dashboard", name="dashboard_ui")
def dashboard_ui(
    request: Request,
    current_user=Depends(get_current_user)
):
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": current_user,
        }
    )