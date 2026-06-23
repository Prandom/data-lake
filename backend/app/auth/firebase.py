"""
Firebase Admin SDK initialization and token verification.

Initializes the Firebase Admin SDK for verifying ID tokens sent by
the frontend.

Setup:
  1. Go to Firebase Console → Project Settings → Service Accounts
  2. Click "Generate new private key" → download JSON
  3. Set GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json in .env
     OR set FIREBASE_SERVICE_ACCOUNT_JSON with the JSON content directly

For local development without Firebase:
  Set AUTH_DISABLED=true in .env to skip all auth checks.
"""

import os
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_firebase_app = None
_auth_disabled = False


def _init_firebase():
    """
    Initialize Firebase Admin SDK (called once at module load).

    Tries in order:
      1. GOOGLE_APPLICATION_CREDENTIALS env var (path to service account JSON)
      2. FIREBASE_SERVICE_ACCOUNT_JSON env var (inline JSON string)
      3. Default credentials (e.g. running on GCP)
    """
    global _firebase_app, _auth_disabled

    # Allow disabling auth for local dev
    if os.getenv("AUTH_DISABLED", "").lower() in ("true", "1", "yes"):
        _auth_disabled = True
        logger.info("Auth is DISABLED (AUTH_DISABLED=true)")
        return

    try:
        import firebase_admin
        from firebase_admin import credentials

        # Already initialized
        if firebase_admin._apps:
            _firebase_app = firebase_admin.get_app()
            return

        # Try explicit service account JSON string
        sa_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        if sa_json:
            cred = credentials.Certificate(json.loads(sa_json))
            _firebase_app = firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin initialized from FIREBASE_SERVICE_ACCOUNT_JSON")
            return

        # Try GOOGLE_APPLICATION_CREDENTIALS (file path)
        if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            cred = credentials.Certificate(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
            _firebase_app = firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin initialized from GOOGLE_APPLICATION_CREDENTIALS")
            return

        # Try default credentials (GCP environments)
        _firebase_app = firebase_admin.initialize_app()
        logger.info("Firebase Admin initialized with default credentials")

    except Exception as e:
        logger.warning(
            f"Firebase Admin SDK not initialized: {e}. "
            "Auth will be disabled. Set AUTH_DISABLED=true to suppress this warning, "
            "or configure GOOGLE_APPLICATION_CREDENTIALS."
        )
        _auth_disabled = True


# Initialize on import
_init_firebase()


def verify_token(id_token: str) -> Optional[dict]:
    """
    Verify a Firebase ID token and return the decoded claims.

    Returns:
        dict with at least: uid, email, name (if available)
        None if verification fails or auth is disabled

    The returned dict is shaped like:
        {
            "uid": "firebase-uid-string",
            "email": "user@example.com",
            "name": "Display Name",
            "picture": "https://...",
            "email_verified": True,
        }
    """
    if _auth_disabled:
        return None

    if not id_token:
        return None

    try:
        from firebase_admin import auth
        decoded = auth.verify_id_token(id_token)
        return decoded
    except Exception as e:
        logger.warning(f"Token verification failed: {e}")
        return None


def is_auth_enabled() -> bool:
    """Check if auth is currently active."""
    return not _auth_disabled
