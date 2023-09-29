from __future__ import annotations
from sqloquent import HashedSqliteModel


class Correspondence(HashedSqliteModel):
    file_path: str = 'temp.db'
    table: str = 'correspondences'
    id_column: str = 'id'
    columns: tuple[str] = ('id', 'first', 'second', 'details')
    id: str
    first: str
    second: str
    details: str

    @classmethod
    def insert(cls, data: dict) -> Correspondence|None:
        # also insert the inverse
        data2 = {**data, 'first': data['second'], 'second': data['first']}
        super().insert(data2)
        return super().insert(data)
