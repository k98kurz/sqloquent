from __future__ import annotations
from sqloquent.asyncql import AsyncHashedModel, AsyncRelatedModel


class Correspondence(AsyncHashedModel):
    file_path: str = 'temp.db'
    table: str = 'correspondences'
    id_column: str = 'id'
    columns: tuple[str] = ('id', 'first_id', 'second_id', 'details')
    id: str
    first_id: str
    second_id: str
    details: str
    first: AsyncRelatedModel
    second: AsyncRelatedModel

    @classmethod
    async def insert(cls, data: dict) -> Correspondence|None:
        # also insert the inverse
        data2 = {**data, 'first_id': data['second_id'], 'second_id': data['first_id']}
        await super().insert(data2)
        return await super().insert(data)
