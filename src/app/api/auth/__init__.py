"""Authentication package."""

from app.api.auth.firebase import verify_firebase_token

__all__ = ["verify_firebase_token"]
