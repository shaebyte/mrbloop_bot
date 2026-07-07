# Login now lives in authservice (mrbloop_BE/authservice) — this module only
# verifies JWTs signed with the shared JWT_SECRET, it issues no tokens.
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import JWT_SECRET

_bearer = HTTPBearer()


def require_any_role(roles: list[str]):
    def checker(creds: HTTPAuthorizationCredentials = Depends(_bearer)) -> dict:
        try:
            payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=["HS256"])
        except jwt.PyJWTError:
            raise HTTPException(401, "Invalid token")
        if payload.get("role") not in roles:
            raise HTTPException(403, "Forbidden")
        return payload

    return checker


# autoredeemgifts_v5 is admin-only — the 'alliance' role never has access here.
require_admin = require_any_role(["admin"])
