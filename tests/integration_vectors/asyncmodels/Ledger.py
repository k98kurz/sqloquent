from __future__ import annotations
from sqloquent.asyncql import (
    AsyncHashedModel,
    AsyncRelatedCollection,
    AsyncRelatedModel,
)


class Ledger(AsyncHashedModel):
    file_path: str = 'temp.db'
    table: str = 'ledgers'
    id_column: str = 'id'
    columns: tuple[str] = ('id', 'name', 'identity_id')
    id: str
    name: str
    identity_id: str
    accounts: AsyncRelatedCollection
    transactions: AsyncRelatedCollection
    owner: AsyncRelatedModel

    @classmethod
    async def find(cls, id: str) -> Ledger:
        # """For better type hints."""
        return await super().find(id)

    @classmethod
    async def insert(cls, data: dict) -> Ledger | None:
        # """For better type hints."""
        return await super().insert(data)
