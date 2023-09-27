from __future__ import annotations
from types import TracebackType
from typing import (
    Any,
    Callable,
    Generator,
    Optional,
    Protocol,
    Type,
    Union,
    runtime_checkable,
)


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
    @property
    def table(self) -> str:
        """Str with the name of the table."""
        ...

    @property
    def id_field(self) -> str:
        """Str with the name of the id field."""
        ...

    @property
    def fields(self) -> tuple[str]:
        """Tuple of str field names."""
        ...

    @property
    def data(self) -> dict:
        """Dict for storing model data."""
        ...

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

    def update(self, updates: dict, conditions: dict = None) -> ModelProtocol:
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

    def reload(self) -> ModelProtocol:
        """Reload values from datastore. Return self in monad pattern."""
        ...

    @classmethod
    def query(cls, conditions: dict = None) -> QueryBuilderProtocol:
        """Return a QueryBuilderProtocol for the model."""
        ...


@runtime_checkable
class JoinedModelProtocol(Protocol):
    def __init__(self, models: list[Type[ModelProtocol]], data: dict) -> None:
        ...

    @property
    def data(self) -> dict:
        """Dict for storing models data."""
        ...

    @staticmethod
    def parse_data(models: list[Type[ModelProtocol]], data: dict) -> dict:
        """Parse data of form {table.column:value} to {table:{column:value}}."""
        ...

    def get_models(self) -> list[ModelProtocol]:
        """Returns the underlying models."""
        ...


@runtime_checkable
class RowProtocol(Protocol):
    @property
    def data(self) -> dict:
        """Returns the underlying row data."""
        ...


@runtime_checkable
class QueryBuilderProtocol(Protocol):
    """Duck typed protocol showing how a query builder should function."""
    def __init__(self, model: ModelProtocol, *args, **kwargs) -> None:
        ...

    @property
    def model(self) -> type:
        """The class of the relevant model."""
        ...

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

    def skip(self, offset: int) -> QueryBuilderProtocol:
        """Sets the number of rows to skip."""
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

    def join(self, model: Type[ModelProtocol]|list[Type[ModelProtocol]],
             on: list[str], kind: str = "inner") -> QueryBuilderProtocol:
        """Prepares the query for a join over multiple tables/models."""
        ...

    def select(self, columns: list[str]) -> QueryBuilderProtocol:
        """Sets the columns to select."""
        ...

    def group(self, by: str) -> QueryBuilderProtocol:
        """Adds a group by constraint."""
        ...

    def get(self) -> list[ModelProtocol|JoinedModelProtocol|RowProtocol]:
        """Run the query on the datastore and return a list of results."""
        ...

    def count(self) -> int:
        """Returns the number of records matching the query."""
        ...

    def take(self, number: int) -> Optional[list[ModelProtocol]]:
        """Takes the specified number of rows."""
        ...

    def chunk(self, number: int) -> Generator[list[ModelProtocol], None, None]:
        """Chunk all matching rows the specified number of rows at a time."""
        ...

    def first(self) -> Optional[ModelProtocol]:
        """Run the query on the datastore and return the first result."""
        ...

    def update(self, updates: dict, conditions: dict = {}) -> int:
        """Update the datastore and return number of records updated."""
        ...

    def delete(self) -> int:
        """Delete the records that match the query and return the number
            of deleted records.
        """
        ...

    def to_sql(self) -> str:
        """Return the sql where clause from the clauses and params."""
        ...

    def execute_raw(self, sql: str) -> tuple[int, Any]:
        """Execute raw SQL against the database. Return rowcount and fetchall
            results.
        """
        ...


@runtime_checkable
class RelationProtocol(Protocol):
    """Duck typed protocol showing how a relation should function."""
    def __init__(self, *args, **kwargs) -> None:
        """The exact initialization will depend upon relation subtype."""
        ...

    @property
    def primary(self) -> ModelProtocol:
        """Property that accesses the primary instance."""
        ...

    @property
    def secondary(self) -> ModelProtocol|tuple[ModelProtocol]:
        """Property that accesses the secondary instance(s)."""
        ...

    @staticmethod
    def single_model_precondition(model) -> None:
        """Checks preconditions for a model."""
        ...

    @staticmethod
    def multi_model_precondition(model) -> None:
        """Checks preconditions for list/tuple of models."""
        ...

    def primary_model_precondition(self, primary: ModelProtocol) -> None:
        """Checks that primary is instance of self.primary_class."""
        ...

    def secondary_model_precondition(self, secondary: ModelProtocol) -> None:
        """Checks that secondary is instance of self.secondary_class."""
        ...

    @staticmethod
    def pivot_preconditions(pivot: type[ModelProtocol]) -> None:
        """Checks preconditions for a pivot."""
        ...

    def save(self) -> None:
        """Save the relation by setting/unsetting relevant database values."""
        ...

    def reload(self) -> None:
        """Reload the secondary models from the database."""
        ...

    def get_cache_key(self) -> str:
        """Get the cache key for the relation."""
        ...

    def create_property(self) -> property:
        """Produces a property to be set on a model, allowing it to access
            the related model through the relation.
        """


@runtime_checkable
class ColumnProtocol(Protocol):
    @property
    def name(self) -> str:
        ...

    @property
    def is_nullable(self) -> str:
        ...

    def validate(self) -> None:
        """Should raise an exception if the column specification is invalid."""
        ...

    def not_null(self) -> ColumnProtocol:
        ...

    def nullable(self) -> ColumnProtocol:
        ...

    def index(self) -> ColumnProtocol:
        ...

    def unique(self) -> ColumnProtocol:
        ...

    def drop(self) -> ColumnProtocol:
        ...

    def rename(self) -> ColumnProtocol:
        ...


@runtime_checkable
class TableProtocol(Protocol):
    @property
    def name(self) -> str:
        ...

    @classmethod
    def create(cls, name: str) -> TableProtocol:
        ...

    @classmethod
    def alter(cls, name: str) -> TableProtocol:
        ...

    @classmethod
    def drop(cls, name: str) -> TableProtocol:
        ...

    def rename(self, name: str) -> TableProtocol:
        ...

    def index(self, columns: list[ColumnProtocol|str]) -> TableProtocol:
        ...

    def drop_index(self, columns: list[ColumnProtocol|str]) -> TableProtocol:
        ...

    def unique(self, columns: list[ColumnProtocol|str]) -> TableProtocol:
        ...

    def drop_unique(self, columns: list[ColumnProtocol|str]) -> TableProtocol:
        ...

    def drop_column(self, column: ColumnProtocol|str) -> TableProtocol:
        ...

    def rename_column(self, column: ColumnProtocol|list[str]) -> TableProtocol:
        ...

    def sql(self) -> list[str]:
        ...


@runtime_checkable
class MigrationProtocol(Protocol):
    def up(self, callback: Callable[[], list[TableProtocol]]) -> None:
        """Specify the forward migration."""
        ...

    def down(self, callback: Callable[[], list[TableProtocol]]) -> None:
        """Specify the backward migration."""
        ...

    def get_apply_sql(self) -> None:
        """Get the SQL for the forward migration."""
        ...

    def apply(self) -> None:
        """Apply the forward migration."""
        ...

    def get_undo_sql(self) -> None:
        """Get the SQL for the backward migration."""
        ...

    def undo(self) -> None:
        """Apply the backward migration."""
        ...
