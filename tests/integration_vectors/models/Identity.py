from __future__ import annotations
from sqloquent import HashedSqliteModel, RelatedCollection, RelatedModel


class Identity(HashedSqliteModel):
    file_path: str = 'temp.db'
    table: str = 'identities'
    id_column: str = 'id'
    columns: tuple[str] = ('id', 'name', 'seed')
    id: str
    name: str
    seed: bytes|None
    correspondences: RelatedCollection
    correspondents: RelatedCollection
    ledger: RelatedModel

    @classmethod
    def insert(cls, data: dict = {}) -> Identity:
        return super().insert(data)
