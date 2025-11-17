from __future__ import annotations
from sqloquent.asyncql import (
    AsyncHashedModel,
    AsyncQueryBuilderProtocol,
    AsyncRelatedModel,
    AsyncRelatedCollection,
    Default
)
from .AccountType import AccountType


class Account(AsyncHashedModel):
    table: str = 'accounts'
    id_column: str = 'id'
    columns: tuple[str] = ('id', 'name', 'ledger_id', 'type', 'is_active')
    id: str
    name: str
    ledger_id: str
    type: str
    is_active: bool|Default[True]
    ledger: AsyncRelatedModel
    entries: AsyncRelatedCollection

    @staticmethod
    def _encode(data: dict|None) -> dict|None:
        if type(data) is dict and 'type' in data and type(data['type']) is AccountType:
            data['type'] = data['type'].value
        return data

    @staticmethod
    def _parse(data: dict|None) -> dict|None:
        if type(data) is dict and 'type' in data and type(data['type']) is str:
            data['type'] = AccountType(data['type'])
        return data

    @staticmethod
    def parse(models: Account|list[Account]) -> Account|list[Account]:
        if type(models) is list:
            for model in models:
                model.data = Account._parse(model.data)
        else:
            models.data = Account._parse(models.data)
        return models

    @classmethod
    async def insert(cls, data: dict) -> Account | None:
        result = await super().insert(cls._encode(data))
        if result is not None:
            result.data = cls._parse(result.data)
        return result

    @classmethod
    async def insert_many(cls, items: list[dict]) -> int:
        items = [cls._encode(data) for data in items]
        return await super().insert_many(items)

    @classmethod
    def query(cls, conditions: dict = None) -> AsyncQueryBuilderProtocol:
        return super().query(cls._encode(conditions))

    @classmethod
    async def find(cls, id: str) -> Account | None:
        """For better type hinting."""
        return await super().find(id)
