from __future__ import annotations
from decimal import Decimal
from sqloquent import HashedSqliteModel
from sqloquent.interfaces import QueryBuilderProtocol
from .EntryType import EntryType


class Entry(HashedSqliteModel):
    file_path: str = 'temp.db'
    table: str = 'entries'
    id_column: str = 'id'
    columns: tuple[str] = ('id', 'account_id', 'nonce', 'type', 'amount')
    id: str
    account_id: str
    nonce: str
    type: EntryType
    amount: Decimal

    @staticmethod
    def _encode(data: dict|None) -> dict|None:
        if type(data) is dict and type(data['type']) is EntryType:
            data['type'] = data['type'].value
        if type(data) is dict and type(data['amount']) is Decimal:
            data['amount'] = str(data['amount'])
        return data

    @staticmethod
    def _parse(data: dict|None) -> dict|None:
        if type(data) is dict and type(data['type']) is str:
            data['type'] = EntryType(data['type'])
        if type(data) is dict and type(data['amount']) is str:
            data['amount'] = Decimal(data['amount'])
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
        result = super().insert(cls._encode(data))
        if result is not None:
            result.data = cls._parse(result.data)
        return result

    @classmethod
    def insert_many(cls, items: list[dict]) -> int:
        items = [Entry._encode(data) for data in list]
        return super().insert_many(items)

    @classmethod
    def query(cls, conditions: dict = None) -> QueryBuilderProtocol:
        return super().query(cls._encode(conditions))
