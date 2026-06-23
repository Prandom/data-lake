"""
FastAPI dependencies for authentication.

Provides get_current_user() — a Depends() injectable that:
  1. Extracts the Bearer token from the Authorization header
  2. Verifies it with Firebase Admin SDK
  3. Returns a dict of user claims (uid, email, name, etc.)
  4. Raises 401 if the token is invalid or missing

When AUTH_DISABLED=true, returns a stub local user so the app
works without Firebase during local development.
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth.firebase import verify_token, is_auth_enabled
from app.db.session import get_db
from app.db.models import User

logger = logging.getLogger(__name__)

# Stub user for local development (when auth is disabled)
_LOCAL_USER = {
    "uid": "local-dev-user",
    "email": "dev@localhost",
    "name": "Local Developer",
    "picture": None,
    "email_verified": True,
}


def _extract_token(request: Request) -> Optional[str]:
    """Extract Bearer token from the Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """
    FastAPI dependency that returns the authenticated user.

    Usage:
        @app.get("/api/protected")
        def protected(user: dict = Depends(get_current_user)):
            return {"uid": user["uid"]}

    When auth is disabled (local dev), returns a stub user.
    When auth is enabled, verifies the Firebase ID token and
    upserts the user record in the database.
    """
    if not is_auth_enabled():
        # Ensure the local dev user exists in the DB
        _upsert_user(db, _LOCAL_USER)
        return _LOCAL_USER

    token = _extract_token(request)
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Missing authentication token. Include 'Authorization: Bearer <token>' header.",
        )

    claims = verify_token(token)
    if not claims:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token.",
        )

    user_data = {
        "uid": claims.get("uid"),
        "email": claims.get("email"),
        "name": claims.get("name") or claims.get("email", "").split("@")[0],
        "picture": claims.get("picture"),
        "email_verified": claims.get("email_verified", False),
    }

    # Upsert user in DB (create or update)
    _upsert_user(db, user_data)

    return user_data


async def get_optional_user(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[dict]:
    """
    Like get_current_user, but returns None instead of raising 401.

    Use for endpoints that work both authenticated and unauthenticated.
    """
    if not is_auth_enabled():
        _upsert_user(db, _LOCAL_USER)
        return _LOCAL_USER

    token = _extract_token(request)
    if not token:
        return None

    claims = verify_token(token)
    if not claims:
        return None

    user_data = {
        "uid": claims.get("uid"),
        "email": claims.get("email"),
        "name": claims.get("name") or claims.get("email", "").split("@")[0],
        "picture": claims.get("picture"),
        "email_verified": claims.get("email_verified", False),
    }

    _upsert_user(db, user_data)
    return user_data


def _upsert_user(db: Session, user_data: dict) -> None:
    """
    Create or update a user record in the database.

    Uses the Firebase UID as the primary key.
    """
    try:
        uid = user_data.get("uid")
        if not uid:
            return

        existing = db.query(User).filter(User.id == uid).first()
        if existing:
            # Update fields that may have changed
            existing.email = user_data.get("email", existing.email)
            existing.display_name = user_data.get("name", existing.display_name)
        else:
            new_user = User(
                id=uid,
                email=user_data.get("email", ""),
                display_name=user_data.get("name", ""),
            )
            db.add(new_user)

        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"Failed to upsert user {user_data.get('uid')}: {e}")
