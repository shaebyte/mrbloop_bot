from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import repository
from app.auth_deps import require_role
from app.security import PasswordTooLong, hash_password

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(require_role("admin"))],
)


class UserCreate(BaseModel):
    username: str
    password: str
    role: str


class UserRoleUpdate(BaseModel):
    role: str


def _validate_role(role: str) -> None:
    if role not in ("admin", "alliance"):
        raise HTTPException(400, "role must be 'admin' or 'alliance'")


@router.post("", status_code=201)
async def create_user(body: UserCreate):
    _validate_role(body.role)
    if await repository.get_user_by_username(body.username):
        raise HTTPException(409, "Username already exists")
    try:
        password_hash = hash_password(body.password)
    except PasswordTooLong as e:
        raise HTTPException(400, str(e))
    user_id = await repository.create_user(body.username, password_hash, body.role)
    return {"id": user_id, "username": body.username, "role": body.role}


@router.get("")
async def list_users():
    return await repository.list_users()


@router.patch("/{user_id}")
async def update_user_role(user_id: int, body: UserRoleUpdate):
    _validate_role(body.role)
    if not await repository.get_user_by_id(user_id):
        raise HTTPException(404, "User not found")
    await repository.update_user_role(user_id, body.role)
    return {"ok": True}


@router.delete("/{user_id}", status_code=204)
async def delete_user(user_id: int):
    if not await repository.delete_user(user_id):
        raise HTTPException(404, "User not found")
