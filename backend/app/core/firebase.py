"""
Firebase Admin SDK initialisation.
Call `get_firebase_app()` to get the initialised app (singleton).
"""
import logging
import firebase_admin
from firebase_admin import credentials

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_firebase_app: firebase_admin.App | None = None


def get_firebase_app() -> firebase_admin.App:
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    settings = get_settings()
    cred = credentials.Certificate({
        "type": "service_account",
        "project_id": settings.firebase_project_id,
        "private_key_id": settings.firebase_private_key_id,
        "private_key": settings.firebase_private_key.replace("\\\\n", "\n").replace("\\n", "\n").strip(),
        "client_email": settings.firebase_client_email,
        "token_uri": "https://oauth2.googleapis.com/token",
    })
    _firebase_app = firebase_admin.initialize_app(cred)
    logger.info("Firebase Admin initialised | project=%s", settings.firebase_project_id)
    return _firebase_app
