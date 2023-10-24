from __future__ import annotations
from sqloquent.asyncql import (
    AsyncHashedModel,
    AsyncRelatedCollection,
    AsyncRelatedModel,
)


class Identity(AsyncHashedModel):
    table: str = 'identities'
    id_column: str = 'id'
    columns: tuple[str] = ('id', 'name', 'seed')
    id: str
    name: str
    seed: bytes|None
    correspondences: AsyncRelatedCollection
    correspondents: AsyncRelatedCollection
    ledger: AsyncRelatedModel

    @classmethod
    async def insert(cls, data: dict = {}) -> Identity:
        # """For better type hints."""
        return await super().insert(data)
