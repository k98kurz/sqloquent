"""
    The interfaces used by the package async features.
    `AsyncRelatedCollection` and `AsyncRelatedModel` describe the
    properties created by the ORM. Any custom relations should implement
    the `AsyncRelationProtocol` and return either `AsyncRelatedModel` or
    `AsyncRelatedCollection` from the `create_property` method.
    `AsyncCursorProtocol` and `AsyncDBContextProtocol` must be
    implemented to bind the library to a new SQL driver.
"""


from __future__ import annotations
from sqloquent.interfaces import RowProtocol
from types import TracebackType, MappingProxyType
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Iterable,
    Optional,
    Protocol,
    Type,
    Union,
    runtime_checkable,
)


@runtime_checkable
class AsyncCursorProtocol(Protocol):
    """Interface showing how a DB cursor should function."""
    async def execute(self, sql: str, parameters: list[str] = []) -> AsyncCursorProtocol:
        """Execute a single query with the given parameters."""
        ...

    async def executemany(self, sql: str,
                    seq_of_parameters: Iterable[list[str]] = []) -> AsyncCursorProtocol:
        """Execute a query once for each list of parameters."""
        ...

    async def executescript(self, sql: str) -> AsyncCursorProtocol:
        """Execute a SQL script without parameters. No implicit
            transaciton handling.
        """
        ...

    async def fetchone(self) -> Any:
        """Get one record returned by the previous query."""
        ...

    async def fetchall(self) -> Any:
        """Get all records returned by the previous query."""
        ...


@runtime_checkable
class AsyncDBContextProtocol(Protocol):
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

    async def __aenter__(self) -> AsyncCursorProtocol:
        """Enter the `async with` block. Should return a cursor useful
            for making db calls.
        """
        ...

    async def __aexit__(self, exc_type: Optional[Type[BaseException]],
                exc_value: Optional[BaseException],
                traceback: Optional[TracebackType]) -> None:
        """Exit the `async with` block. Should commit any pending
            transactions and close the cursor and connection upon
            exiting the context.
        """
        ...


@runtime_checkable
class AsyncModelProtocol(Protocol):
    """Interface showing how an async model should function."""
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

    # Tests randomly started failing due to this.
    # @property
    # def data_original(self) -> MappingProxyType:
    #     """Read-only MappingProxyType for storing original data values
    #         for change tracking.
    #     """
    #     ...

    @classmethod
    def add_hook(cls, event: str, hook: Callable):
        """Add the hook for the event."""
        ...

    @classmethod
    def remove_hook(cls, event: str, hook: Callable):
        """Remove the hook for the event."""
        ...

    @classmethod
    def clear_hooks(cls, event: str = None):
        """Remove all hooks for an event. If no event is specified,
            clear all hooks for all events.
        """
        ...

    @classmethod
    def invoke_hooks(cls, event: str, *args, **kwargs):
        """Invoke the hooks for the event, passing cls, *args, and
            **kwargs. if parallel_hooks=True is passed in the kwargs,
            all coroutines returned from hooks will be awaited
            concurrently (with `asyncio.gather`) after non-async hooks
            have executed; otherwise, each will be waited individually.
        """
        ...

    def __hash__(self) -> int:
        """Allow inclusion in sets."""
        ...

    def __eq__(self, other) -> bool:
        """Return True if types and hashes are equal, else False."""
        ...

    @classmethod
    async def find(cls, id: Any) -> Optional[AsyncModelProtocol]:
        """Find a record by its id and return it. Return None if it does
            not exist.
        """
        ...

    @classmethod
    async def insert(cls, data: dict, /, *,
                     suppress_events: bool = False) -> Optional[AsyncModelProtocol]:
        """Insert a new record to the datastore. Return instance."""
        ...

    @classmethod
    async def insert_many(cls, items: list[dict], /, *,
                          suppress_events: bool = False) -> int:
        """Insert a batch of records and return the number of items inserted."""
        ...

    async def update(self, updates: dict, conditions: dict = None, /, *,
                     suppress_events: bool = False) -> AsyncModelProtocol:
        """Persist the specified changes to the datastore. Return self
            in monad pattern.
        """
        ...

    async def save(self, /, *, suppress_events: bool = False) -> AsyncModelProtocol:
        """Persist to the datastore. Return self in monad pattern."""
        ...

    async def delete(self, /, *, suppress_events: bool = False) -> None:
        """Delete the record."""
        ...

    async def reload(self, /, *, suppress_events: bool = False) -> AsyncModelProtocol:
        """Reload values from datastore. Return self in monad pattern."""
        ...

    @classmethod
    def query(cls, conditions: dict = None) -> AsyncQueryBuilderProtocol:
        """Return a AsyncQueryBuilderProtocol for the model."""
        ...


@runtime_checkable
class AsyncJoinedModelProtocol(Protocol):
    """Interface for representations of JOIN query results."""
    def __init__(self, models: list[Type[AsyncModelProtocol]], data: dict) -> None:
        """Initialize the instance."""
        ...

    @property
    def data(self) -> dict:
        """Dict for storing models data."""
        ...

    @staticmethod
    def parse_data(models: list[Type[AsyncModelProtocol]], data: dict) -> dict:
        """Parse data of form {table.column:value} to {table:{column:value}}."""
        ...

    async def get_models(self) -> list[AsyncModelProtocol]:
        """Returns the underlying models."""
        ...


@runtime_checkable
class AsyncQueryBuilderProtocol(Protocol):
    """Interface showing how a query builder should function."""
    def __init__(self, model_or_table: Type[AsyncModelProtocol]|str,
                 context_manager: Type[AsyncDBContextProtocol],
                 connection_info: str = '', model: Type[AsyncModelProtocol] = None,
                 table: str = None) -> None:
        """Initialize the instance. A class implementing AsyncModelProtocol
            or the str name of a table must be provided.
        """
        ...

    @property
    def table(self) -> str:
        """The name of the table."""
        ...

    @property
    def model(self) -> Type[AsyncModelProtocol]:
        """The class of the relevant model."""
        ...

    def is_null(self, column: str|list[str,]|tuple[str,]) -> AsyncQueryBuilderProtocol:
        """Save the 'column is null' clause, then return self. Raises
            TypeError for invalid column. If a list or tuple is supplied,
            each element is treated as a separate clause.
        """
        ...

    def not_null(self, column: str|list[str,]|tuple[str,]) -> AsyncQueryBuilderProtocol:
        """Save the 'column is not null' clause, then return self.
            Raises TypeError for invalid column. If a list or tuple is
            supplied, each element is treated as a separate clause.
        """
        ...

    def equal(self, column: str = None, data: str = None,
              **conditions: dict[str, Any]) -> AsyncQueryBuilderProtocol:
        """Save the 'column = data' clause and param, then return self.
            Raises TypeError for invalid column. This method can be
            called with `equal(column, data)` or
            `equal(column1=data1, column2=data2, etc=data3)`.
        """
        ...

    def not_equal(self, column: str = None, data: Any = None,
                  **conditions: dict[str, Any]) -> AsyncQueryBuilderProtocol:
        """Save the 'column != data' clause and param, then return self.
            Raises TypeError for invalid column. This method can be
            called with `not_equal(column, data)` or
            `not_equal(column1=data1, column2=data2, etc=data3)`.
        """
        ...

    def less(self, column: str = None, data: str = None,
             **conditions: dict[str, Any]) -> AsyncQueryBuilderProtocol:
        """Save the 'column < data' clause and param, then return self.
            Raises TypeError for invalid column. This method can be
            called with `less(column, data)` or
            `less(column1=data1, column2=data2, etc=data3)`.
        """
        ...

    def greater(self, column: str = None, data: str = None,
                **conditions: dict[str, Any]) -> AsyncQueryBuilderProtocol:
        """Save the 'column > data' clause and param, then return self.
            Raises TypeError for invalid column. This method can be
            called with `greater(column, data)` or
            `greater(column1=data1, column2=data2, etc=data3)`.
        """
        ...

    def like(self, column: str = None, pattern: str = None, data: str = None,
             **conditions: dict[str, Any]) -> AsyncQueryBuilderProtocol:
        """Save the 'column like {pattern.replace(?, data)}' clause and
            param, then return self. Raises TypeError or ValueError for
            invalid column, pattern, or data. This method can be
            called with `like(column, pattern, data)` or
            `like(column1=(pattern1,str1), column2=(pattern2,str2), etc=(pattern3,str3))`.
        """
        ...

    def not_like(self, column: str = None, pattern: str = None, data: str = None,
                 **conditions: dict[str, Any]) -> AsyncQueryBuilderProtocol:
        """Save the 'column not like {pattern.replace(?, data)}' clause
            and param, then return self. Raises TypeError or ValueError
            for invalid column, pattern, or data. This method can be
            called with `not_like(column, pattern, data)` or
            `not_like(column1=(pattern1,str1), column2=(pattern2,str2), etc=(pattern3,str3))`.
        """
        ...

    def starts_with(self, column: str = None, data: str = None,
                    **conditions: dict[str, Any]) -> AsyncQueryBuilderProtocol:
        """Save the 'column like data%' clause and param, then return
            self. Raises TypeError or ValueError for invalid column or
            data. This method can be called with `starts_with(column, data)`
            or `starts_with(column1=str1, column2=str2, etc=str3)`.
        """
        ...

    def does_not_start_with(self, column: str = None, data: str = None,
                             **conditions: dict[str, Any]) -> AsyncQueryBuilderProtocol:
        """Save the 'column not like data%' clause and param, then return
            self. Raises TypeError or ValueError for invalid column or
            data. This method can be called with
            `does_not_start_with(column, data)` or
            `does_not_start_with(column1=str1, column2=str2, etc=str3)`.
        """
        ...

    def contains(self, column: str = None, data: str = None,
                 **conditions: dict[str, Any]) -> AsyncQueryBuilderProtocol:
        """Save the 'column like %data%' clause and param, then return
            self. Raises TypeError or ValueError for invalid column or
            data. This method can be called with `contains(column, data)`
            or `contains(column1=str1, column2=str2, etc=str3)`.
        """
        ...

    def excludes(self, column: str = None, data: str = None,
                 **conditions: dict[str, Any]) -> AsyncQueryBuilderProtocol:
        """Save the 'column not like %data%' clause and param, then
            return self. Raises TypeError or ValueError for invalid
            column or data. This method can be called with
            `excludes(column, data)` or
            `excludes(column1=str1, column2=str2, etc=str3)`.
        """
        ...

    def ends_with(self, column: str = None, data: str = None,
                  **conditions: dict[str, Any]) -> AsyncQueryBuilderProtocol:
        """Save the 'column like %data' clause and param, then return
            self. Raises TypeError or ValueError for invalid column or
            data. This method can be called with `ends_with(column, data)`
            or `ends_with(column1=str1, column2=str2, etc=str3)`.
        """
        ...

    def does_not_end_with(self, column: str = None, data: str = None,
                           **conditions: dict[str, Any]) -> AsyncQueryBuilderProtocol:
        """Save the 'column like %data' clause and param, then return
            self. Raises TypeError or ValueError for invalid column or
            data. This method can be called with
            `does_not_end_with(column, data)` or
            `does_not_end_with(column1=str1, column2=str2, etc=str3)`.
        """
        ...

    def is_in(self, column: str = None, data: Union[tuple, list] = None,
              **conditions: dict[str, Any]) -> AsyncQueryBuilderProtocol:
        """Save the 'column in data' clause and param, then return self.
            Raises TypeError or ValueError for invalid column or data.
            This method can be called with `is_in(column, data)` or
            `is_in(column1=list1, column2=list2, etc=list3)`.
        """
        ...

    def not_in(self, column: str = None, data: Union[tuple, list] = None,
                **conditions: dict[str, Any]) -> AsyncQueryBuilderProtocol:
        """Save the 'column not in data' clause and param, then return
            self. Raises TypeError or ValueError for invalid column or
            data. This method can be called with `not_in(column, data)`
            or `not_in(column1=list1, column2=list2, etc=list3)`.
        """
        ...

    def where(self, **conditions: dict[str, dict[str, Any]|list[str]]) -> AsyncQueryBuilderProtocol:
        """Parse the conditions as if they are sequential calls to the
            equivalent SqlQueryBuilder methods. Syntax is as follows:
            `where(is_null=[column1,...], not_null=[column2,...],
            equal={'column1':data1, 'column2':data2, 'etc':data3},
            not_equal={'column1':data1, 'column2':data2, 'etc':data3},
            less={'column1':data1, 'column2':data2, 'etc':data3},
            greater={'column1':data1, 'column2':data2, 'etc':data3},
            like={'column1':(pattern1,str1), 'column2':(pattern2,str2),
            'etc':(pattern3,str3)}, not_like={'column1':(pattern1,str1),
            'column2':(pattern2,str2), 'etc':(pattern3,str3)},
            starts_with={'column1':str1, 'column2':str2, 'etc':str3},
            does_not_start_with={'column1':str1, 'column2':str2, 'etc':str3},
            contains={'column1':str1, 'column2':str2, 'etc':str3},
            excludes={'column1':str1, 'column2':str2, 'etc':str3},
            ends_with={'column1':str1, 'column2':str2, 'etc':str3},
            does_not_end_with={'column1':str1, 'column2':str2, 'etc':str3},
            is_in={'column1':list1, 'column2':list2, 'etc':list3},
            not_in={'column1':list1, 'column2':list2, 'etc':list3})`. All
            kwargs are optional.
        """
        ...

    def order_by(self, column: str = None, direction: str = 'desc',
                 **conditions: dict[str, str]) -> AsyncQueryBuilderProtocol:
        """Sets query order."""
        ...

    def skip(self, offset: int) -> AsyncQueryBuilderProtocol:
        """Sets the number of rows to skip."""
        ...

    def reset(self) -> AsyncQueryBuilderProtocol:
        """Returns a fresh instance using the configured model."""
        ...

    async def insert(self, data: dict) -> Optional[AsyncModelProtocol|RowProtocol]:
        """Insert a record and return a model instance."""
        ...

    async def insert_many(self, items: list[dict]) -> int:
        """Insert a batch of records and return the number inserted."""
        ...

    async def find(self, id: str) -> Optional[AsyncModelProtocol|RowProtocol]:
        """Find a record by its id and return it."""
        ...

    def join(self, model_or_table: Type[AsyncModelProtocol]|str, on: list[str],
             kind: str = "inner", joined_table_columns: tuple[str] = (),
             ) -> AsyncQueryBuilderProtocol:
        """Prepares the query for a join over multiple tables/models.
            Raises TypeError or ValueError for invalid model, on, or
            kind.
        """
        ...

    def select(self, columns: list[str]) -> AsyncQueryBuilderProtocol:
        """Sets the columns to select."""
        ...

    def group(self, by: str) -> AsyncQueryBuilderProtocol:
        """Adds a group by constraint."""
        ...

    async def get(self) -> list[AsyncModelProtocol]|list[AsyncJoinedModelProtocol]|list[RowProtocol]:
        """Run the query on the datastore and return a list of results.
            Return SqlModels when running a simple query. Return
            JoinedModels when running a JOIN query. Return Rows when
            running a non-joined GROUP BY query.
        """
        ...

    async def count(self) -> int:
        """Returns the number of records matching the query."""
        ...

    async def take(self, number: int) -> list[AsyncModelProtocol]|list[AsyncJoinedModelProtocol]|list[RowProtocol]:
        """Takes the specified number of rows."""
        ...

    def chunk(self, number: int) -> AsyncGenerator[list[AsyncModelProtocol]|list[AsyncJoinedModelProtocol]|list[RowProtocol], None, None]:
        """Chunk all matching rows the specified number of rows at a time."""
        ...

    async def first(self) -> Optional[AsyncModelProtocol|RowProtocol]:
        """Run the query on the datastore and return the first result."""
        ...

    async def update(self, updates: dict, conditions: dict = {}) -> int:
        """Update the datastore and return number of records updated."""
        ...

    async def delete(self) -> int:
        """Delete the records that match the query and return the number
            of deleted records.
        """
        ...

    def to_sql(self, interpolate_params: bool = True) -> str|tuple[str, list]:
        """Return the sql where clause from the clauses and params. If
            interpolate_params is True, the parameters will be
            interpolated into the SQL str and a single str result will
            be returned. If interpolate_params is False, the parameters
            will not be interpolated into the SQL str, instead including
            question marks, and an additional list of params will be
            returned along with the SQL str.
        """
        ...

    async def execute_raw(self, sql: str) -> tuple[int, list[tuple[Any]]]:
        """Execute raw SQL against the database. Return rowcount and fetchall
            results.
        """
        ...


@runtime_checkable
class AsyncRelationProtocol(Protocol):
    """Interface showing how a relation should function."""
    def __init__(self, *args, **kwargs) -> None:
        """The exact initialization will depend upon relation subtype."""
        ...

    @property
    def primary(self) -> AsyncModelProtocol:
        """Property that accesses the primary instance."""
        ...

    @property
    def secondary(self) -> AsyncModelProtocol|tuple[AsyncModelProtocol]:
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

    def primary_model_precondition(self, primary: AsyncModelProtocol) -> None:
        """Checks that primary is instance of self.primary_class."""
        ...

    def secondary_model_precondition(self, secondary: AsyncModelProtocol) -> None:
        """Checks that secondary is instance of self.secondary_class."""
        ...

    @staticmethod
    def pivot_preconditions(pivot: Type[AsyncModelProtocol]) -> None:
        """Checks preconditions for a pivot."""
        ...

    async def save(self) -> None:
        """Save the relation by setting/unsetting relevant database values."""
        ...

    async def reload(self) -> None:
        """Reload the secondary models from the database."""
        ...

    def query(self) -> AsyncQueryBuilderProtocol|None:
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
class AsyncRelatedModel(AsyncModelProtocol, Protocol):
    """Interface showing what a related model returned from an ORM
        helper function or AsyncRelationProtocol.create_property will behave.
        This is used for relations where the primary model is associated
        with a single secondary model.
    """
    def __call__(self) -> AsyncRelationProtocol:
        """Return the underlying relation when the property is called as
            a method, e.g. `phone.owner()` will return the relation
            while `phone.owner` will access the related model.
        """
        ...


@runtime_checkable
class AsyncRelatedCollection(Protocol):
    """Interface showing what a related model returned from an ORM
        helper function or AsyncRelationProtocol.create_property will behave.
        This is used for relations where the primary model is associated
        with multiple secondary models.
    """
    def __call__(self) -> AsyncRelationProtocol:
        """Return the underlying relation when the property is called as
            a method, e.g. `fish.scales()` will return the relation
            while `fish.scales` will access the related models.
        """
        ...

    def __iter__(self) -> AsyncModelProtocol:
        """Allow the collection to be iterated over, returning a model
            on each iteration.
        """

    def __getitem__(self, key) -> AsyncModelProtocol:
        """Return the related model at the given index."""
        ...
