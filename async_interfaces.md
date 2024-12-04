# sqloquent.asyncql.interfaces

The interfaces used by the package async features. `AsyncRelatedCollection` and
`AsyncRelatedModel` describe the properties created by the ORM. Any custom
relations should implement the `AsyncRelationProtocol` and return either
`AsyncRelatedModel` or `AsyncRelatedCollection` from the `create_property`
method. `AsyncCursorProtocol` and `AsyncDBContextProtocol` must be implemented
to bind the library to a new SQL driver.

## Classes

### `AsyncCursorProtocol(Protocol)`

Interface showing how a DB cursor should function.

#### Methods

##### `async execute(sql: str, parameters: list[str] = []) -> AsyncCursorProtocol:`

Execute a single query with the given parameters.

##### `async executemany(sql: str, seq_of_parameters: Iterable[list[str]] = []) -> AsyncCursorProtocol:`

Execute a query once for each list of parameters.

##### `async executescript(sql: str) -> AsyncCursorProtocol:`

Execute a SQL script without parameters. No implicit transaciton handling.

##### `async fetchone() -> Any:`

Get one record returned by the previous query.

##### `async fetchall() -> Any:`

Get all records returned by the previous query.

### `AsyncDBContextProtocol(Protocol)`

Interface showing how a context manager for connecting to a database should
behave.

#### Methods

##### `__init__(connection_info: str = '') -> None:`

Using the connection_info parameter is optional but should be supported. I
recommend setting a class attribute with the default value taken from an
environment variable, then use that class attribute within this method,
overriding with the parameter only if it is not empty.

##### `async __aenter__() -> AsyncCursorProtocol:`

Enter the `async with` block. Should return a cursor useful for making db calls.

##### `async __aexit__(exc_type: Optional[Type[BaseException]], exc_value: Optional[BaseException], traceback: Optional[TracebackType]) -> None:`

Exit the `async with` block. Should commit any pending transactions and close
the cursor and connection upon exiting the context.

### `AsyncModelProtocol(Protocol)`

Interface showing how an async model should function.

#### Properties

- table: Str with the name of the table.
- id_column: Str with the name of the id column.
- columns: Tuple of str column names.
- data: Dict for storing model data.
- data_original: Read-only MappingProxyType for storing original data values for
change tracking.

#### Methods

##### `__hash__() -> int:`

Allow inclusion in sets.

##### `__eq__() -> bool:`

Return True if types and hashes are equal, else False.

##### `@classmethod add_hook(event: str, hook: Callable):`

Add the hook for the event.

##### `@classmethod remove_hook(event: str, hook: Callable):`

Remove the hook for the event.

##### `@classmethod clear_hooks(event: str = None):`

Remove all hooks for an event. If no event is specified, clear all hooks for all
events.

##### `@classmethod invoke_hooks(event: str):`

Invoke the hooks for the event, passing cls, *args, and **kwargs. if
parallel_hooks=True is passed in the kwargs, all coroutines returned from hooks
will be awaited concurrently (with `asyncio.gather`) after non-async hooks have
executed; otherwise, each will be waited individually.

##### `@classmethod async find(id: Any) -> Optional[AsyncModelProtocol]:`

Find a record by its id and return it. Return None if it does not exist.

##### `@classmethod async insert(data: dict, /, *, suppress_events: bool = False) -> Optional[AsyncModelProtocol]:`

Insert a new record to the datastore. Return instance.

##### `@classmethod async insert_many(items: list[dict], /, *, suppress_events: bool = False) -> int:`

Insert a batch of records and return the number of items inserted.

##### `async update(updates: dict, conditions: dict = None, /, *, suppress_events: bool = False) -> AsyncModelProtocol:`

Persist the specified changes to the datastore. Return self in monad pattern.

##### `async save(/, *, suppress_events: bool = False) -> AsyncModelProtocol:`

Persist to the datastore. Return self in monad pattern.

##### `async delete(/, *, suppress_events: bool = False) -> None:`

Delete the record.

##### `async reload(/, *, suppress_events: bool = False) -> AsyncModelProtocol:`

Reload values from datastore. Return self in monad pattern.

##### `@classmethod query(conditions: dict = None) -> AsyncQueryBuilderProtocol:`

Return a AsyncQueryBuilderProtocol for the model.

### `AsyncJoinedModelProtocol(Protocol)`

Interface for representations of JOIN query results.

#### Properties

- data: Dict for storing models data.
- models: List of the underlying model classes.

#### Methods

##### `__init__(models: list[Type[AsyncModelProtocol]], data: dict) -> None:`

Initialize the instance.

##### `@staticmethod parse_data(models: list[Type[AsyncModelProtocol]], data: dict) -> dict:`

Parse data of form {table.column:value} to {table:{column:value}}.

##### `async get_models() -> list[AsyncModelProtocol]:`

Returns the underlying models.

### `AsyncQueryBuilderProtocol(Protocol)`

Interface showing how a query builder should function.

#### Properties

- table: The name of the table.
- model: The class of the relevant model.

#### Methods

##### `__init__(model_or_table: Type[AsyncModelProtocol] | str, context_manager: Type[AsyncDBContextProtocol], connection_info: str = '', model: Type[AsyncModelProtocol] = None, table: str = None) -> None:`

Initialize the instance. A class implementing AsyncModelProtocol or the str name
of a table must be provided.

##### `is_null(column: str | list[str,] | tuple[str,]) -> AsyncQueryBuilderProtocol:`

Save the 'column is null' clause, then return self. Raises TypeError for invalid
column. If a list or tuple is supplied, each element is treated as a separate
clause.

##### `not_null(column: str | list[str,] | tuple[str,]) -> AsyncQueryBuilderProtocol:`

Save the 'column is not null' clause, then return self. Raises TypeError for
invalid column. If a list or tuple is supplied, each element is treated as a
separate clause.

##### `equal(column: str, data: str = None, conditions: dict[str, Any] = None) -> AsyncQueryBuilderProtocol:`

Save the 'column = data' clause and param, then return self. Raises TypeError
for invalid column. This method can be called with `equal(column, data)` or
`equal(column1=data1, column2=data2, etc=data3)`.

##### `not_equal(column: str, data: Any = None, conditions: dict[str, Any] = None) -> AsyncQueryBuilderProtocol:`

Save the 'column != data' clause and param, then return self. Raises TypeError
for invalid column. This method can be called with `not_equal(column, data)` or
`not_equal(column1=data1, column2=data2, etc=data3)`.

##### `less(column: str, data: str = None, conditions: dict[str, Any] = None) -> AsyncQueryBuilderProtocol:`

Save the 'column < data' clause and param, then return self. Raises TypeError
for invalid column. This method can be called with `less(column, data)` or
`less(column1=data1, column2=data2, etc=data3)`.

##### `greater(column: str, data: str = None, conditions: dict[str, Any] = None) -> AsyncQueryBuilderProtocol:`

Save the 'column > data' clause and param, then return self. Raises TypeError
for invalid column. This method can be called with `greater(column, data)` or
`greater(column1=data1, column2=data2, etc=data3)`.

##### `like(column: str, pattern: str = None, data: str = None, conditions: dict[str, Any] = None) -> AsyncQueryBuilderProtocol:`

Save the 'column like {pattern.replace(?, data)}' clause and param, then return
self. Raises TypeError or ValueError for invalid column, pattern, or data. This
method can be called with `like(column, pattern, data)` or
`like(column1=(pattern1,str1), column2=(pattern2,str2), etc=(pattern3,str3))`.

##### `not_like(column: str, pattern: str = None, data: str = None, conditions: dict[str, Any] = None) -> AsyncQueryBuilderProtocol:`

Save the 'column not like {pattern.replace(?, data)}' clause and param, then
return self. Raises TypeError or ValueError for invalid column, pattern, or
data. This method can be called with `not_like(column, pattern, data)` or
`not_like(column1=(pattern1,str1), column2=(pattern2,str2), etc=(pattern3,str3))`.

##### `starts_with(column: str, data: str = None, conditions: dict[str, Any] = None) -> AsyncQueryBuilderProtocol:`

Save the 'column like data%' clause and param, then return self. Raises
TypeError or ValueError for invalid column or data. This method can be called
with `starts_with(column, data)` or `starts_with(column1=str1, column2=str2,
etc=str3)`.

##### `does_not_start_with(column: str, data: str = None, conditions: dict[str, Any] = None) -> AsyncQueryBuilderProtocol:`

Save the 'column not like data%' clause and param, then return self. Raises
TypeError or ValueError for invalid column or data. This method can be called
with `does_not_start_with(column, data)` or `does_not_start_with(column1=str1,
column2=str2, etc=str3)`.

##### `contains(column: str, data: str = None, conditions: dict[str, Any] = None) -> AsyncQueryBuilderProtocol:`

Save the 'column like %data%' clause and param, then return self. Raises
TypeError or ValueError for invalid column or data. This method can be called
with `contains(column, data)` or `contains(column1=str1, column2=str2,
etc=str3)`.

##### `excludes(column: str, data: str = None, conditions: dict[str, Any] = None) -> AsyncQueryBuilderProtocol:`

Save the 'column not like %data%' clause and param, then return self. Raises
TypeError or ValueError for invalid column or data. This method can be called
with `excludes(column, data)` or `excludes(column1=str1, column2=str2,
etc=str3)`.

##### `ends_with(column: str, data: str = None, conditions: dict[str, Any] = None) -> AsyncQueryBuilderProtocol:`

Save the 'column like %data' clause and param, then return self. Raises
TypeError or ValueError for invalid column or data. This method can be called
with `ends_with(column, data)` or `ends_with(column1=str1, column2=str2,
etc=str3)`.

##### `does_not_end_with(column: str, data: str = None, conditions: dict[str, Any] = None) -> AsyncQueryBuilderProtocol:`

Save the 'column like %data' clause and param, then return self. Raises
TypeError or ValueError for invalid column or data. This method can be called
with `does_not_end_with(column, data)` or `does_not_end_with(column1=str1,
column2=str2, etc=str3)`.

##### `is_in(column: str, data: Union[tuple, list] = None, conditions: dict[str, Any] = None) -> AsyncQueryBuilderProtocol:`

Save the 'column in data' clause and param, then return self. Raises TypeError
or ValueError for invalid column or data. This method can be called with
`is_in(column, data)` or `is_in(column1=list1, column2=list2, etc=list3)`.

##### `not_in(column: str, data: Union[tuple, list] = None, conditions: dict[str, Any] = None) -> AsyncQueryBuilderProtocol:`

Save the 'column not in data' clause and param, then return self. Raises
TypeError or ValueError for invalid column or data. This method can be called
with `not_in(column, data)` or `not_in(column1=list1, column2=list2,
etc=list3)`.

##### `where(conditions: dict[str, dict[str, Any] | list[str]]) -> AsyncQueryBuilderProtocol:`

Parse the conditions as if they are sequential calls to the equivalent
SqlQueryBuilder methods. Syntax is as follows: `where(is_null=[column1,...], not_null=[column2,...], equal={'column1':data1, 'column2':data2, 'etc':data3}, not_equal={'column1':data1, 'column2':data2, 'etc':data3}, less={'column1':data1, 'column2':data2, 'etc':data3}, greater={'column1':data1, 'column2':data2, 'etc':data3}, like={'column1':(pattern1,str1), 'column2':(pattern2,str2), 'etc':(pattern3,str3)}, not_like={'column1':(pattern1,str1), 'column2':(pattern2,str2), 'etc':(pattern3,str3)}, starts_with={'column1':str1, 'column2':str2, 'etc':str3}, does_not_start_with={'column1':str1, 'column2':str2, 'etc':str3}, contains={'column1':str1, 'column2':str2, 'etc':str3}, excludes={'column1':str1, 'column2':str2, 'etc':str3}, ends_with={'column1':str1, 'column2':str2, 'etc':str3}, does_not_end_with={'column1':str1, 'column2':str2, 'etc':str3}, is_in={'column1':list1, 'column2':list2, 'etc':list3}, not_in={'column1':list1, 'column2':list2, 'etc':list3})`.
All kwargs are optional.

##### `order_by(column: str, direction: str = None, conditions: dict[str, str] = 'desc') -> AsyncQueryBuilderProtocol:`

Sets query order.

##### `skip(offset: int) -> AsyncQueryBuilderProtocol:`

Sets the number of rows to skip.

##### `reset() -> AsyncQueryBuilderProtocol:`

Returns a fresh instance using the configured model.

##### `async insert(data: dict) -> Optional[AsyncModelProtocol | RowProtocol]:`

Insert a record and return a model instance.

##### `async insert_many(items: list[dict]) -> int:`

Insert a batch of records and return the number inserted.

##### `async find(id: str) -> Optional[AsyncModelProtocol | RowProtocol]:`

Find a record by its id and return it.

##### `join(model_or_table: Type[AsyncModelProtocol] | str, on: list[str], kind: str = 'inner', joined_table_columns: tuple[str] = ()) -> AsyncQueryBuilderProtocol:`

Prepares the query for a join over multiple tables/models. Raises TypeError or
ValueError for invalid model, on, or kind.

##### `select(columns: list[str]) -> AsyncQueryBuilderProtocol:`

Sets the columns to select.

##### `group(by: str) -> AsyncQueryBuilderProtocol:`

Adds a group by constraint.

##### `async get() -> list[AsyncModelProtocol] | list[AsyncJoinedModelProtocol] | list[RowProtocol]:`

Run the query on the datastore and return a list of results. Return SqlModels
when running a simple query. Return JoinedModels when running a JOIN query.
Return Rows when running a non-joined GROUP BY query.

##### `async count() -> int:`

Returns the number of records matching the query.

##### `async take(number: int) -> list[AsyncModelProtocol] | list[AsyncJoinedModelProtocol] | list[RowProtocol]:`

Takes the specified number of rows.

##### `chunk(number: int) -> AsyncGenerator[list[AsyncModelProtocol] | list[AsyncJoinedModelProtocol] | list[RowProtocol], None, None]:`

Chunk all matching rows the specified number of rows at a time.

##### `async first() -> Optional[AsyncModelProtocol | RowProtocol]:`

Run the query on the datastore and return the first result.

##### `async update(updates: dict, conditions: dict = {}) -> int:`

Update the datastore and return number of records updated.

##### `async delete() -> int:`

Delete the records that match the query and return the number of deleted
records.

##### `to_sql(interpolate_params: bool = True) -> str | tuple[str, list]:`

Return the sql where clause from the clauses and params. If interpolate_params
is True, the parameters will be interpolated into the SQL str and a single str
result will be returned. If interpolate_params is False, the parameters will not
be interpolated into the SQL str, instead including question marks, and an
additional list of params will be returned along with the SQL str.

##### `async execute_raw(sql: str) -> tuple[int, list[tuple[Any]]]:`

Execute raw SQL against the database. Return rowcount and fetchall results.

### `AsyncRelationProtocol(Protocol)`

Interface showing how a relation should function.

#### Properties

- primary: Property that accesses the primary instance.
- secondary: Property that accesses the secondary instance(s).

#### Methods

##### `__init__() -> None:`

The exact initialization will depend upon relation subtype.

##### `@staticmethod single_model_precondition() -> None:`

Checks preconditions for a model.

##### `@staticmethod multi_model_precondition() -> None:`

Checks preconditions for list/tuple of models.

##### `primary_model_precondition(primary: AsyncModelProtocol) -> None:`

Checks that primary is instance of self.primary_class.

##### `secondary_model_precondition(secondary: AsyncModelProtocol) -> None:`

Checks that secondary is instance of self.secondary_class.

##### `@staticmethod pivot_preconditions(pivot: Type[AsyncModelProtocol]) -> None:`

Checks preconditions for a pivot.

##### `async save() -> None:`

Save the relation by setting/unsetting relevant database values.

##### `async reload() -> None:`

Reload the secondary models from the database.

##### `query() -> AsyncQueryBuilderProtocol | None:`

Creates the base query for the underlying relation.

##### `get_cache_key() -> str:`

Get the cache key for the relation.

##### `create_property() -> property:`

Produces a property to be set on a model, allowing it to access the related
model through the relation.

### `AsyncRelatedModel(AsyncModelProtocol)`

Interface showing what a related model returned from an ORM helper function or
AsyncRelationProtocol.create_property will behave. This is used for relations
where the primary model is associated with a single secondary model.

#### Methods

##### `__call__() -> AsyncRelationProtocol:`

Return the underlying relation when the property is called as a method, e.g.
`phone.owner()` will return the relation while `phone.owner` will access the
related model.

### `AsyncRelatedCollection(Protocol)`

Interface showing what a related model returned from an ORM helper function or
AsyncRelationProtocol.create_property will behave. This is used for relations
where the primary model is associated with multiple secondary models.

#### Methods

##### `__call__() -> AsyncRelationProtocol:`

Return the underlying relation when the property is called as a method, e.g.
`fish.scales()` will return the relation while `fish.scales` will access the
related models.

##### `__iter__() -> AsyncModelProtocol:`

Allow the collection to be iterated over, returning a model on each iteration.

##### `__getitem__() -> AsyncModelProtocol:`

Return the related model at the given index.


