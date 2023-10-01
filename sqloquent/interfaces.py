from __future__ import annotations
from types import TracebackType
from typing import (
    Any,
    Callable,
    Generator,
    Iterable,
    Optional,
    Protocol,
    Type,
    Union,
    runtime_checkable,
)


@runtime_checkable
class CursorProtocol(Protocol):
    """Interface showing how a DB cursor should function."""
    def execute(self, sql: str, parameters: list[str] = []) -> CursorProtocol:
        """Execute a single query with the given parameters."""
        ...

    def executemany(self, sql: str,
                    seq_of_parameters: Iterable[list[str]] = []) -> CursorProtocol:
        """Execute a query once for each list of parameters."""
        ...

    def executescript(self, sql: str) -> CursorProtocol:
        """Execute a SQL script without parameters. No implicit
            transaciton handling.
        """
        ...

    def fetchone(self) -> Any:
        """Get one record returned by the previous query."""
        ...

    def fetchall(self) -> Any:
        """Get all records returned by the previous query."""
        ...


@runtime_checkable
class DBContextProtocol(Protocol):
    """Interface showing how a context manager for connecting
        to a database should behave.
    """
    def __init__(self, connection_info: str = '') -> None:
        """Using the connection_info parameter is optional but should be
            supported. I recommend setting a class attribute with the
            default value taken from an environment variable, then use
            that class attribute within this method, overriding with the
            parameter only if it is not empty.
        """
        ...

    def __enter__(self) -> CursorProtocol:
        """Enter the `with` block. Should return a cursor useful for
            making db calls.
        """
        ...

    def __exit__(self, __exc_type: Optional[Type[BaseException]],
                __exc_value: Optional[BaseException],
                __traceback: Optional[TracebackType]) -> None:
        """Exit the `with` block. Should commit any pending transactions
            and close the cursor and connection upon exiting the context.
        """
        ...


@runtime_checkable
class ModelProtocol(Protocol):
    """Interface showing how a model should function."""
    @property
    def table(self) -> str:
        """Str with the name of the table."""
        ...

    @property
    def id_column(self) -> str:
        """Str with the name of the id column."""
        ...

    @property
    def columns(self) -> tuple[str]:
        """Tuple of str column names."""
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
    """Interface for representations of JOIN query results."""
    def __init__(self, models: list[Type[ModelProtocol]], data: dict) -> None:
        """Initialize the instance."""
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
    """Interface for a generic row representation."""
    @property
    def data(self) -> dict:
        """Returns the underlying row data."""
        ...


@runtime_checkable
class QueryBuilderProtocol(Protocol):
    """Interface showing how a query builder should function."""
    def __init__(self, model_or_table: Type[ModelProtocol]|str,
                 context_manager: Type[DBContextProtocol],
                 connection_info: str = '', model: Type[ModelProtocol] = None,
                 table: str = None) -> None:
        """Initialize the instance. A class implementing ModelProtocol
            or the str name of a table must be provided.
        """
        ...

    @property
    def table(self) -> str:
        """The name of the table."""
        ...

    @property
    def model(self) -> Type[ModelProtocol]:
        """The class of the relevant model."""
        ...

    def equal(self, column: str, data: str) -> QueryBuilderProtocol:
        """Save the 'column = data' clause and param, then return self."""
        ...

    def not_equal(self, column: str, data: Any) -> QueryBuilderProtocol:
        """Save the 'column != data' clause and param, then return self."""
        ...

    def less(self, column: str, data: str) -> QueryBuilderProtocol:
        """Save the 'column < data' clause and param, then return self."""
        ...

    def greater(self, column: str, data: str) -> QueryBuilderProtocol:
        """Save the 'column > data' clause and param, then return self."""
        ...

    def starts_with(self, column: str, data: str) -> QueryBuilderProtocol:
        """Save the 'column like data%' clause and param, then return self."""
        ...

    def contains(self, column: str, data: str) -> QueryBuilderProtocol:
        """Save the 'column like %data%' clause and param, then return self."""
        ...

    def excludes(self, column: str, data: str) -> QueryBuilderProtocol:
        """Save the 'column not like %data%' clause and param, then return self."""
        ...

    def ends_with(self, column: str, data: str) -> QueryBuilderProtocol:
        """Save the 'column like %data' clause and param, then return self."""
        ...

    def is_in(self, column: str, data: Union[tuple, list]) -> QueryBuilderProtocol:
        """Save the 'column in data' clause and param, then return self."""
        ...

    def order_by(self, column: str, direction: str = 'desc') -> QueryBuilderProtocol:
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

    def get(self) -> list[ModelProtocol]|list[JoinedModelProtocol]|list[RowProtocol]:
        """Run the query on the datastore and return a list of results.
            Return SqlModels when running a simple query. Return
            JoinedModels when running a JOIN query. Return Rows when
            running a non-joined GROUP BY query.
        """
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
    """Interface showing how a relation should function."""
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
    def pivot_preconditions(pivot: Type[ModelProtocol]) -> None:
        """Checks preconditions for a pivot."""
        ...

    def save(self) -> None:
        """Save the relation by setting/unsetting relevant database values."""
        ...

    def reload(self) -> None:
        """Reload the secondary models from the database."""
        ...

    def query(self) -> QueryBuilderProtocol|None:
        """Creates the base query for the underlying relation."""
        ...

    def get_cache_key(self) -> str:
        """Get the cache key for the relation."""
        ...

    def create_property(self) -> property:
        """Produces a property to be set on a model, allowing it to access
            the related model through the relation.
        """


@runtime_checkable
class RelatedModel(ModelProtocol, Protocol):
    """Interface showing what a related model returned from an ORM
        helper function or RelationProtocol.create_property will behave.
        This is used for relations where the primary model is associated
        with a single secondary model.
    """
    def __call__(self) -> RelationProtocol:
        """Return the underlying relation when the property is called as
            a method, e.g. `phone.owner()` will return the relation
            while `phone.owner` will access the related model.
        """
        ...


@runtime_checkable
class RelatedCollection(Protocol):
    """Interface showing what a related model returned from an ORM
        helper function or RelationProtocol.create_property will behave.
        This is used for relations where the primary model is associated
        with multiple secondary models.
    """
    def __call__(self) -> RelationProtocol:
        """Return the underlying relation when the property is called as
            a method, e.g. `fish.scales()` will return the relation
            while `fish.scales` will access the related models.
        """
        ...

    def __iter__(self) -> ModelProtocol:
        """Allow the collection to be iterated over, returning a model
            on each iteration.
        """

    def __getitem__(self, key) -> ModelProtocol:
        """Return the related model at the given index."""
        ...


@runtime_checkable
class ColumnProtocol(Protocol):
    """Interface for a column class (for migrations).
    """
    @property
    def name(self) -> str:
        """The name of the column."""
        ...

    @property
    def is_nullable(self) -> str:
        """Whether or not the column can be null."""
        ...

    def validate(self) -> None:
        """Should raise an exception if the column specification is invalid."""
        ...

    def not_null(self) -> ColumnProtocol:
        """Disable null values for this column."""
        ...

    def nullable(self) -> ColumnProtocol:
        """Enable null values for this column."""
        ...

    def index(self) -> ColumnProtocol:
        """Should generate a simple index for this column."""
        ...

    def unique(self) -> ColumnProtocol:
        """Should generate a unique index for this column."""
        ...

    def drop(self) -> ColumnProtocol:
        """Should drop the column from the table."""
        ...

    def rename(self, new_name: str) -> ColumnProtocol:
        """Should rename the column."""
        ...


@runtime_checkable
class TableProtocol(Protocol):
    """Interface for a table class (for migrations)."""
    @property
    def name(self) -> str:
        """The name of the table."""
        ...

    @classmethod
    def create(cls, name: str) -> TableProtocol:
        """For creating a table."""
        ...

    @classmethod
    def alter(cls, name: str) -> TableProtocol:
        """For altering a table."""
        ...

    @classmethod
    def drop(cls, name: str) -> TableProtocol:
        """For dropping a table."""
        ...

    def rename(self, name: str) -> TableProtocol:
        """Rename the table."""
        ...

    def index(self, columns: list[ColumnProtocol|str]) -> TableProtocol:
        """Create a simple index or a composite index."""
        ...

    def drop_index(self, columns: list[ColumnProtocol|str]) -> TableProtocol:
        """Drop a simple index or a composite index."""
        ...

    def unique(self, columns: list[ColumnProtocol|str]) -> TableProtocol:
        """Create a simple unique index or a composite unique index."""
        ...

    def drop_unique(self, columns: list[ColumnProtocol|str]) -> TableProtocol:
        """Drop a simple unique index or a composite unique index."""
        ...

    def drop_column(self, column: ColumnProtocol|str) -> TableProtocol:
        """Drop the specified column."""
        ...

    def rename_column(self, column: ColumnProtocol|list[str]) -> TableProtocol:
        """Rename the specified column."""
        ...

    def custom(self, callback: Callable[[list[str]], list[str]]) -> TableProtocol:
        """Add a custom callback that parses the SQL clauses before they
            are returnedf from the `sql` method. Must accept and return
            list[str]. This is a way to add custom SQL while still using
            the migration system. Return self in monad pattern.
        """
        ...

    def sql(self) -> list[str]:
        """Return the SQL for the table structure changes."""
        ...


@runtime_checkable
class MigrationProtocol(Protocol):
    """Interface for a migration class."""
    @property
    def connection_info(self) -> str:
        """The connection info used for interacting with the database.
            For sqlite migrations, this is passed to the
            DBContextManager. For other database bindings, the
            connection information should be read from env and injected
            into the relevant DBContextManager.
        """
        ...

    def up(self, callback: Callable[[], list[TableProtocol]]) -> None:
        """Specify the forward migration. May be called multiple times
            for multi-step migrations.
        """
        ...

    def down(self, callback: Callable[[], list[TableProtocol]]) -> None:
        """Specify the backward migration. May be called multiple times
            for multi-step migrations.
        """
        ...

    def get_apply_sql(self) -> None:
        """Get the SQL for the forward migration. Note that this may
            call all registered callbacks and result in unexpected
            behavior.
        """
        ...

    def apply(self) -> None:
        """Apply the forward migration."""
        ...

    def get_undo_sql(self) -> None:
        """Get the SQL for the backward migration. Note that this may
            call all registered callbacks and result in unexpected
            behavior.
        """
        ...

    def undo(self) -> None:
        """Apply the backward migration."""
        ...
