"""Auth router — syncs the Firebase user into PostgreSQL on first login."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.session import get_session
from ...services.user_service import UserService
from ..auth.firebase import verify_firebase_token
from ...schemas.user import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/sync", response_model=UserRead, status_code=status.HTTP_200_OK)
async def sync_user(
    firebase_uid: str = Depends(verify_firebase_token),
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    """Called by the client immediately after Firebase sign-in.

    Creates a PostgreSQL record for new users; returns the existing record for
    returning users.  The JWT is validated by ``verify_firebase_token`` which
    also extracts the email from the token.
    """
    # Email was already verified inside verify_firebase_token; fetch it again
    # from the token data stored by the dependency.  We re-verify here to keep
    # the endpoint self-contained.
    from ...api.auth.firebase import get_firebase_app
    import firebase_admin.auth as fa

    try:
        fb_user = fa.get_user(firebase_uid, app=get_firebase_app())
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    svc = UserService(session)
    user = await svc.get_or_create(firebase_uid, fb_user.email or "")
    return UserRead.model_validate(user)


@router.get("/me", response_model=UserRead)
async def get_me(
    firebase_uid: str = Depends(verify_firebase_token),
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    """Return the current user's profile."""
    svc = UserService(session)
    user = await svc.get_by_firebase_id(firebase_uid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. Call POST /auth/sync first.",
        )
    return UserRead.model_validate(user)
