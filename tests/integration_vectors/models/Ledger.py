from __future__ import annotations
from sqloquent import HashedModel, RelatedCollection, RelatedModel


class Ledger(HashedModel):
    table: str = 'ledgers'
    id_column: str = 'id'
    columns: tuple[str] = ('id', 'name', 'identity_id')
    id: str
    name: str
    identity_id: str
    accounts: RelatedCollection
    transactions: RelatedCollection
    owner: RelatedModel

    @classmethod
    def find(cls, id: str) -> Ledger:
        """For better type hints."""
        return super().find(id)

    @classmethod
    def insert(cls, data: dict) -> Ledger | None:
        """For better type hints."""
        return super().insert(data)
