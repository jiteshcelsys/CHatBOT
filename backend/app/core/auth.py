"""
FastAPI dependency for Firebase ID token verification.

Usage in a route:
    from app.core.auth import get_current_user, AuthUser

    @router.post("/")
    async def my_route(user: AuthUser = Depends(get_current_user)):
        ...  # user.uid, user.email available
"""
import logging
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth

from app.core.firebase import get_firebase_app

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=True)


@dataclass
class AuthUser:
    uid: str
    email: str | None
    name: str | None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> AuthUser:
    token = credentials.credentials
    try:
        get_firebase_app()  # ensure initialised
        decoded = auth.verify_id_token(token)
        return AuthUser(
            uid=decoded["uid"],
            email=decoded.get("email"),
            name=decoded.get("name"),
        )
    except auth.ExpiredIdTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired.")
    except auth.InvalidIdTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")
    except Exception as exc:
        logger.warning("Firebase token verification failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed.")
