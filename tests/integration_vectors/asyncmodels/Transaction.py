from __future__ import annotations
from sqloquent.asyncql import AsyncHashedModel, AsyncRelatedCollection


class Transaction(AsyncHashedModel):
    table: str = 'transactions'
    id_column: str = 'id'
    columns: tuple[str] = ('id', 'entry_ids', 'ledger_ids')
    id: str
    entry_ids: str
    ledger_ids: str
    entries: AsyncRelatedCollection
    ledgers: AsyncRelatedCollection

    @classmethod
    async def insert(cls, data: dict) -> Transaction | None:
        # """For better type hints."""
        return await super().insert(data)
