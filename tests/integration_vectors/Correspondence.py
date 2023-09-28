from __future__ import annotations
from sqloquent import HashedSqliteModel


class Correspondence(HashedSqliteModel):
    file_path: str = 'temp.db'
    table: str = 'correspondences'
    id_field: str = 'id'
    fields: tuple[str] = ('id', 'first', 'second', 'data')

    @classmethod
    def insert(cls, data: dict) -> Correspondence|None:
        # also insert the inverse
        data2 = {**data, 'first': data['second'], 'second': data['first']}
        super().insert(data2)
        return super().insert(data)
