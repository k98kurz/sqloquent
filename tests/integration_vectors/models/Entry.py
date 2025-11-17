from __future__ import annotations
from .EntryType import EntryType
from decimal import Decimal
from sqloquent import (
    HashedModel,
    QueryBuilderProtocol,
    RelatedModel,
    RelatedCollection,
)


class Entry(HashedModel):
    table: str = 'entries'
    id_column: str = 'id'
    columns: tuple[str] = ('id', 'account_id', 'nonce', 'type', 'amount')
    id: str
    account_id: str
    nonce: str
    type: str
    amount: str
    account: RelatedModel
    transactions: RelatedCollection

    def __hash__(self) -> int:
        data = self.encode_value(self._encode(self.data))
        return hash(bytes(data, 'utf-8'))

    @property
    def type(self) -> EntryType:
        return EntryType(self.data['type'])
    @type.setter
    def type(self, val: EntryType):
        self.data['type'] = val.value

    @property
    def amount(self) -> Decimal:
        return Decimal(self.data['amount'])
    @amount.setter
    def amount(self, val: Decimal):
        self.data['amount'] = str(val)

    @staticmethod
    def _encode(data: dict|None) -> dict|None:
        if type(data) is not dict:
            return data
        if 'type' in data and type(data['type']) is EntryType:
            data['type'] = data['type'].value
        if 'amount' in data and type(data['amount']) is Decimal:
            data['amount'] = str(data['amount'])
        return data

    @classmethod
    def insert(cls, data: dict) -> Entry | None:
        result = super().insert(cls._encode(data))
        return result

    @classmethod
    def insert_many(cls, items: list[dict]) -> int:
        items = [cls._encode(data) for data in items]
        return super().insert_many(items)

    @classmethod
    def query(cls, conditions: dict = None) -> QueryBuilderProtocol:
        return super().query(cls._encode(conditions))
