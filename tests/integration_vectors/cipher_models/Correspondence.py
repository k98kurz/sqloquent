from __future__ import annotations
from sqloquent import RelatedModel
from sqloquent.sqlcipher import HashedSqlcipherModel


class Correspondence(HashedSqlcipherModel):
    table: str = "correspondences"
    id_column: str = "id"
    columns: tuple[str] = ("id", "first_id", "second_id", "details")
    id: str
    first_id: str
    second_id: str
    details: str
    first: RelatedModel
    second: RelatedModel

    @classmethod
    def insert(cls, data: dict) -> Correspondence | None:
        # also insert the inverse
        data2 = {**data, "first_id": data["second_id"], "second_id": data["first_id"]}
        super().insert(data2)
        return super().insert(data)
