from __future__ import annotations
from sqloquent import HashedSqliteModel
from sqloquent.interfaces import QueryBuilderProtocol
from .EntryType import EntryType


class Entry(HashedSqliteModel):
    file_path: str = 'temp.db'
    table: str = 'entries'
    id_field: str = 'id'
    fields: tuple[str] = ('id', 'account_id', 'nonce', 'type', 'amount')

    @staticmethod
    def _encode(data: dict|None) -> dict|None:
        if type(data) is dict and type(data['type']) is EntryType:
            data['type'] = data['type'].value
        return data

    @staticmethod
    def _parse(data: dict|None) -> dict|None:
        if type(data) is dict and type(data['type']) is str:
            data['type'] = EntryType(data['type'])
        return data

    @staticmethod
    def parse(models: Entry|list[Entry]) -> Entry|list[Entry]:
        if type(models) is list:
            for model in models:
                model.data = Entry._parse(model.data)
        else:
            models.data = Entry._parse(models.data)
        return models

    @classmethod
    def insert(cls, data: dict) -> Entry | None:
        return super().insert(cls._encode(data))

    @classmethod
    def insert_many(cls, items: list[dict]) -> int:
        items = [Entry._encode(data) for data in list]
        return super().insert_many(items)

    @classmethod
    def query(cls, conditions: dict = None) -> QueryBuilderProtocol:
        return super().query(cls._encode(conditions))
