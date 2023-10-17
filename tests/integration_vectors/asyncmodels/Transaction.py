from __future__ import annotations
from sqloquent.asyncql import AsyncHashedModel, AsyncModelProtocol
from typing import Callable


class Transaction(AsyncHashedModel):
    file_path: str = 'temp.db'
    table: str = 'transactions'
    id_column: str = 'id'
    columns: tuple[str] = ('id', 'entry_ids', 'ledger_ids')
    id: str
    entry_ids: str
    ledger_ids: str
    entries: Callable[[Transaction, bool], list[AsyncModelProtocol]]
    ledgers: Callable[[Transaction, bool], list[AsyncModelProtocol]]

    @classmethod
    async def insert(cls, data: dict) -> Transaction | None:
        # """For better type hints."""
        return await super().insert(data)
