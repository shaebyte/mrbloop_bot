from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.security import decode_token
import jwt as pyjwt

_bearer = HTTPBearer()


def require_any_role(roles: list[str]):
    def checker(creds: HTTPAuthorizationCredentials = Depends(_bearer)) -> dict:
        try:
            payload = decode_token(creds.credentials)
        except pyjwt.PyJWTError:
            raise HTTPException(401, "Invalid token")
        if payload.get("role") not in roles:
            raise HTTPException(403, "Forbidden")
        return payload

    return checker


def require_role(role: str):
    return require_any_role([role])
