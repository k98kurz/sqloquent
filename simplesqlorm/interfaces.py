from __future__ import annotations
from types import TracebackType
from typing import Any, Optional, Protocol, Type, Union, runtime_checkable


@runtime_checkable
class CursorProtocol(Protocol):
    def execute(sql: str) -> CursorProtocol:
        ...

    def executemany(sql: str) -> CursorProtocol:
        ...

    def fetchone() -> Any:
        ...

    def fetchall() -> Any:
        ...


@runtime_checkable
class DBContextProtocol(Protocol):
    def __init__(self, model: ModelProtocol) -> None:
        ...

    def __enter__(self) -> CursorProtocol:
        ...

    def __exit__(self, __exc_type: Optional[Type[BaseException]],
                __exc_value: Optional[BaseException],
                __traceback: Optional[TracebackType]) -> None:
        ...


@runtime_checkable
class ModelProtocol(Protocol):
    """Duck typed protocol showing how a model should function."""
    def __hash__(self) -> int:
        """Allow inclusion in sets."""
        ...

    def __eq__(self, other) -> bool:
        """Return True if types and hashes are equal, else False."""
        ...

    @classmethod
    def find(cls, id: Any) -> Optional[ModelProtocol]:
        """Find a record by its id and return it. Return None if it does
            not exist.
        """
        ...

    @classmethod
    def insert(cls, data: dict) -> Optional[ModelProtocol]:
        """Insert a new record to the datastore. Return instance."""
        ...

    @classmethod
    def insert_many(cls, items: list[dict]) -> int:
        """Insert a batch of records and return the number of items inserted."""
        ...

    def update(self, updates: dict) -> ModelProtocol:
        """Persist the specified changes to the datastore. Return self
            in monad pattern.
        """
        ...

    def save(self) -> ModelProtocol:
        """Persist to the datastore. Return self in monad pattern."""
        ...

    def delete(self) -> None:
        """Delete the record."""
        ...

    @classmethod
    def query(cls, conditions: dict = None) -> QueryBuilderProtocol:
        """Return a QueryBuilderProtocol for the model."""
        ...


@runtime_checkable
class QueryBuilderProtocol(Protocol):
    """Duck typed protocol showing how a query builder should function."""
    def equal(self, field: str, data: str) -> QueryBuilderProtocol:
        """Save the 'field = data' clause and param, then return self."""
        ...

    def not_equal(self, field: str, data: Any) -> QueryBuilderProtocol:
        """Save the 'field != data' clause and param, then return self."""
        ...

    def less(self, field: str, data: str) -> QueryBuilderProtocol:
        """Save the 'field < data' clause and param, then return self."""
        ...

    def greater(self, field: str, data: str) -> QueryBuilderProtocol:
        """Save the 'field > data' clause and param, then return self."""
        ...

    def starts_with(self, field: str, data: str) -> QueryBuilderProtocol:
        """Save the 'field like data%' clause and param, then return self."""
        ...

    def contains(self, field: str, data: str) -> QueryBuilderProtocol:
        """Save the 'field like %data%' clause and param, then return self."""
        ...

    def excludes(self, field: str, data: str) -> QueryBuilderProtocol:
        """Save the 'field not like %data%' clause and param, then return self."""
        ...

    def ends_with(self, field: str, data: str) -> QueryBuilderProtocol:
        """Save the 'field like %data' clause and param, then return self."""
        ...

    def is_in(self, field: str, data: Union[tuple, list]) -> QueryBuilderProtocol:
        """Save the 'field in data' clause and param, then return self."""
        ...

    def order_by(self, field: str, direction: str = 'desc') -> QueryBuilderProtocol:
        """Sets query order."""
        ...

    def reset(self) -> QueryBuilderProtocol:
        """Returns a fresh instance using the configured model."""
        ...

    def insert(self, data: dict) -> Optional[ModelProtocol]:
        """Insert a record and return a model instance."""
        ...

    def insert_many(self, items: list[dict]) -> int:
        """Insert a batch of records and return the number inserted."""
        ...

    def find(self, id: str) -> Optional[ModelProtocol]:
        """Find a record by its id and return it."""
        ...

    def get(self) -> list[ModelProtocol]:
        """Run the query on the datastore and return a list of results."""
        ...

    def count(self) -> int:
        """Returns the number of records matching the query."""
        ...

    def update(self, updates: dict) -> int:
        """Update the datastore and return number of records updated."""
        ...

    def first(self) -> Optional[ModelProtocol]:
        """Run the query on the datastore and return the first result."""
        ...

    def delete(self) -> int:
        """Delete the records that match the query and return the number
            of deleted records.
        """
        ...

    def to_sql(self) -> str:
        """Return the sql where clause from the clauses and params."""
        ...
