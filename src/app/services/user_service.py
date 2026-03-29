"""User business logic."""

from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.postgres_repository import UserRepository
from ..db.models import User


class UserService:
    def __init__(self, session: AsyncSession):
        self.repo = UserRepository(session)

    async def get_or_create(self, firebase_id: str, email: str) -> User:
        """Return the existing PG user or create one on first login."""
        user = await self.repo.get_by_firebase_id(firebase_id)
        if user is None:
            user = await self.repo.create(firebase_id=firebase_id, email=email)
        return user

    async def get_by_firebase_id(self, firebase_id: str) -> User | None:
        return await self.repo.get_by_firebase_id(firebase_id)

    async def deactivate(self, firebase_id: str) -> bool:
        user = await self.repo.get_by_firebase_id(firebase_id)
        if not user:
            return False
        await self.repo.update(user.id, is_active=False)
        return True
