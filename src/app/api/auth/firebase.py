"""Firebase authentication integration."""

from typing import Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import auth as firebase_auth
from firebase_admin.exceptions import FirebaseError

from app.config import settings

security = HTTPBearer()

# Initialize Firebase Admin SDK (singleton)
_firebase_app: firebase_admin.App | None = None


def get_firebase_app() -> firebase_admin.App:
    """Get or initialize Firebase app."""
    global _firebase_app
    if _firebase_app is None:
        try:
            cred = firebase_admin.credentials.Certificate(settings.firebase_credentials_path)
            _firebase_app = firebase_admin.initialize_app(cred)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Firebase: {e}")
    return _firebase_app


async def verify_firebase_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """
    Verify Firebase JWT token and extract user ID.

    Returns:
        user_id: The Firebase UID of the authenticated user

    Raises:
        HTTPException: If token is invalid or verification fails
    """
    token = credentials.credentials

    try:
        # Verify the token
        decoded_token = firebase_auth.verify_id_token(token, app=get_firebase_app())
        user_id = decoded_token["uid"]

        # Check email domain (@bsu.by)
        email = decoded_token.get("email", "")
        email_verified = decoded_token.get("email_verified", False)

        if not email_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email not verified. Please verify your email before proceeding.",
            )

        if not email.lower().endswith("@bsu.by"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only @bsu.by email addresses are allowed.",
            )

        return user_id

    except FirebaseError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
        )
