# Mounted at the app root (no extra prefix) — see main.py comment for why:
# nginx strips the /api/auth/ prefix before proxying here, so this file's
# routes must live at the FastAPI root to line up (e.g. POST /login, not
# POST /auth/login).
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.limiter import limiter
from app.repository import get_user_by_username
from app.security import create_token, verify_password

router = APIRouter(tags=["auth"])


class LoginBody(BaseModel):
    username: str
    password: str


@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, body: LoginBody):
    user = await get_user_by_username(body.username)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Invalid username or password")
    token = create_token(user["username"], user["role"])
    return {"token": token, "role": user["role"], "username": user["username"]}
