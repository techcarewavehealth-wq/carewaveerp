# app/security.py
import json
import hashlib
from pathlib import Path

from fastapi import Request, HTTPException, status

SESSION_USER_KEY = "user_id"

# Archivo de usuarios
USERS_FILE = Path("app/data/users.json")


def load_users():
    if USERS_FILE.exists():
        with USERS_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    return []


def hash_password(raw: str) -> str:
    # Por si algún día quieres guardar hashed en el JSON
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def verify_password(raw: str, stored: str) -> bool:
    """
    Si el JSON tiene la contraseña en texto plano (como ahora) → comparamos directo.
    Si en el futuro está hasheada, también funcionaría.
    """
    raw = raw.strip()
    stored = stored.strip()

    if raw == stored:
        return True

    return hash_password(raw) == stored


def get_user_from_json(username: str):
    username = username.strip().lower()
    users = load_users()
    for user in users:
        if user["username"].strip().lower() == username:
            return user
    return None


def authenticate(username: str, password: str):
    username = username.strip()
    password = password.strip()

    user = get_user_from_json(username)
    if not user:
        return None
    if not user.get("is_active", True):
        return None
    if not verify_password(password, user["password"]):
        return None
    return user


def get_current_user(request: Request):
    user = request.session.get(SESSION_USER_KEY)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
        )
    return user