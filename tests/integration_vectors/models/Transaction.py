from __future__ import annotations
from sqloquent import HashedModel, RelatedCollection


class Transaction(HashedModel):
    table: str = 'transactions'
    id_column: str = 'id'
    columns: tuple[str] = ('id', 'entry_ids', 'ledger_ids')
    id: str
    entry_ids: str
    ledger_ids: str
    entries: RelatedCollection
    ledgers: RelatedCollection

    @classmethod
    def insert(cls, data: dict) -> Transaction | None:
        return super().insert(data)
