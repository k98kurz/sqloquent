# sqloquent.asyncql

Classes for use with asyncio. Requires an additional dependency, which should be
installed with `pip install sqloquent[asyncql]`.

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

### `AsyncJoinedModelProtocol(Protocol)`

Interface for representations of JOIN query results.

#### Properties

- data: Dict for storing models data.

#### Methods

##### `__init__(models: list[Type[AsyncModelProtocol]], data: dict) -> None:`

Initialize the instance.

##### `@staticmethod parse_data(models: list[Type[AsyncModelProtocol]], data: dict) -> dict:`

Parse data of form {table.column:value} to {table:{column:value}}.

##### `async get_models() -> list[AsyncModelProtocol]:`

Returns the underlying models.

### `AsyncModelProtocol(Protocol)`

Interface showing how an async model should function.

#### Properties

- table: Str with the name of the table.
- id_column: Str with the name of the id column.
- columns: Tuple of str column names.
- data: Dict for storing model data.

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

### `AsyncQueryBuilderProtocol(Protocol)`

Interface showing how a query builder should function.

#### Properties

- table: The name of the table.
- model: The class of the relevant model.

#### Methods

##### `__init__(model_or_table: Type[AsyncModelProtocol] | str, context_manager: Type[AsyncDBContextProtocol], connection_info: str = '', model: Type[AsyncModelProtocol] = None, table: str = None) -> None:`

Initialize the instance. A class implementing AsyncModelProtocol or the str name
of a table must be provided.

##### `is_null(column: str) -> AsyncQueryBuilderProtocol:`

Save the 'column is null' clause, then return self. Raises TypeError for invalid
column.

##### `not_null(column: str) -> AsyncQueryBuilderProtocol:`

Save the 'column is not null' clause, then return self. Raises TypeError for
invalid column.

##### `equal(column: str, data: str) -> AsyncQueryBuilderProtocol:`

Save the 'column = data' clause and param, then return self.

##### `not_equal(column: str, data: Any) -> AsyncQueryBuilderProtocol:`

Save the 'column != data' clause and param, then return self.

##### `less(column: str, data: str) -> AsyncQueryBuilderProtocol:`

Save the 'column < data' clause and param, then return self.

##### `greater(column: str, data: str) -> AsyncQueryBuilderProtocol:`

Save the 'column > data' clause and param, then return self.

##### `like(column: str, pattern: str, data: str) -> AsyncQueryBuilderProtocol:`

Save the 'column like {pattern.replace(?, data)}' clause and param, then return
self. Raises TypeError or ValueError for invalid column, pattern, or data.

##### `not_like(column: str, pattern: str, data: str) -> AsyncQueryBuilderProtocol:`

Save the 'column not like {pattern.replace(?, data)}' clause and param, then
return self. Raises TypeError or ValueError for invalid column, pattern, or
data.

##### `starts_with(column: str, data: str) -> AsyncQueryBuilderProtocol:`

Save the 'column like data%' clause and param, then return self.

##### `does_not_start_with(column: str, data: str) -> AsyncQueryBuilderProtocol:`

Save the 'column like data%' clause and param, then return self. Raises
TypeError or ValueError for invalid column or data.

##### `contains(column: str, data: str) -> AsyncQueryBuilderProtocol:`

Save the 'column like %data%' clause and param, then return self.

##### `excludes(column: str, data: str) -> AsyncQueryBuilderProtocol:`

Save the 'column not like %data%' clause and param, then return self.

##### `ends_with(column: str, data: str) -> AsyncQueryBuilderProtocol:`

Save the 'column like %data' clause and param, then return self.

##### `does_not_end_with(column: str, data: str) -> AsyncQueryBuilderProtocol:`

Save the 'column like %data' clause and param, then return self. Raises
TypeError or ValueError for invalid column or data.

##### `is_in(column: str, data: Union[tuple, list]) -> AsyncQueryBuilderProtocol:`

Save the 'column in data' clause and param, then return self.

##### `not_in(column: str, data: Union[tuple, list]) -> AsyncQueryBuilderProtocol:`

Save the 'column not in data' clause and param, then return self. Raises
TypeError or ValueError for invalid column or data.

##### `order_by(column: str, direction: str = 'desc') -> AsyncQueryBuilderProtocol:`

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

### `AsyncRelatedModel(AsyncModelProtocol)`

Interface showing what a related model returned from an ORM helper function or
AsyncRelationProtocol.create_property will behave. This is used for relations
where the primary model is associated with a single secondary model.

#### Methods

##### `__call__() -> AsyncRelationProtocol:`

Return the underlying relation when the property is called as a method, e.g.
`phone.owner()` will return the relation while `phone.owner` will access the
related model.

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

### `AsyncSqliteContext`

Context manager for sqlite.

#### Annotations

- connection: aiosqlite.Connection
- cursor: aiosqlite.Cursor
- connection_info: str

#### Methods

##### `__init__(connection_info: str = '') -> None:`

Initialize the instance. Raises TypeError for non-str table.

##### `async __aenter__() -> AsyncCursorProtocol:`

Enter the context block and return the cursor.

##### `async __aexit__(exc_type: Optional[Type[BaseException]], exc_value: Optional[BaseException], traceback: Optional[TracebackType]) -> None:`

Exit the context block. Commit or rollback as appropriate, then close the
connection.

### `AsyncSqlModel`

General model for mapping a SQL row to an in-memory object.

#### Annotations

- table: str
- id_column: str
- columns: tuple
- id: str
- name: str
- query_builder_class: Type[AsyncQueryBuilderProtocol]
- connection_info: str
- data: dict
- _event_hooks: dict[str, list[Callable]]

#### Methods

##### `__init__(data: dict = {}) -> None:`

Initialize the instance. Raises TypeError or ValueError if _post_init_hooks is
not dict[Any, callable].

##### `__hash__() -> int:`

Allow inclusion in sets. Raises TypeError for unencodable type within self.data
(calls packify.pack).

##### `__eq__() -> bool:`

Allow comparisons. Raises TypeError on unencodable value in self.data or
other.data (calls cls.__hash__ which calls packify.pack).

##### `__repr__() -> str:`

Pretty str representation.

##### `@classmethod add_hook(event: str, hook: Callable):`

Add the hook for the event.

##### `@classmethod remove_hook(event: str, hook: Callable):`

Remove the hook for the event.

##### `@classmethod clear_hooks(event: str = None):`

Remove all hooks for an event. If no event is specified, clear all hooks for all
events.

##### `@classmethod async invoke_hooks(event: str):`

Invoke the hooks for the event, passing cls, *args, and **kwargs. if
parallel_hooks=True is passed in the kwargs, all coroutines returned from hooks
will be awaited concurrently (with `asyncio.gather`) after non-async hooks have
executed; otherwise, each will be waited individually.

##### `@staticmethod create_property() -> property:`

Create a dynamic property for the column with the given name.

##### `@staticmethod encode_value(val: Any) -> str:`

Encode a value for hashing. Uses the pack function from packify.

##### `@classmethod generate_id() -> str:`

Generates and returns a hexadecimal UUID4.

##### `@classmethod async find(id: Any) -> Optional[AsyncSqlModel]:`

Find a record by its id and return it. Return None if it does not exist.

##### `@classmethod async insert(data: dict, /, *, parallel_events: bool = False, suppress_events: bool = False) -> Optional[AsyncSqlModel]:`

Insert a new record to the datastore. Return instance. Raises TypeError if data
is not a dict.

##### `@classmethod async insert_many(items: list[dict], /, *, parallel_events: bool = False, suppress_events: bool = False) -> int:`

Insert a batch of records and return the number of items inserted. Raises
TypeError if items is not list[dict].

##### `async update(updates: dict, conditions: dict = None, /, *, parallel_events: bool = False, suppress_events: bool = False) -> AsyncSqlModel:`

Persist the specified changes to the datastore. Return self in monad pattern.
Raises TypeError or ValueError for invalid updates or conditions (self.data must
include the id to update or conditions must be specified).

##### `async save(/, *, parallel_events: bool = False, suppress_events: bool = False) -> AsyncSqlModel:`

Persist to the datastore. Return self in monad pattern. Calls insert or update
and raises appropriate errors.

##### `async delete(/, *, parallel_events: bool = False, suppress_events: bool = False) -> None:`

Delete the record.

##### `async reload(/, *, parallel_events: bool = False, suppress_events: bool = False) -> AsyncSqlModel:`

Reload values from datastore. Return self in monad pattern. Raises UsageError if
id is not set in self.data.

##### `@classmethod query(conditions: dict = None, connection_info: str = None) -> AsyncQueryBuilderProtocol:`

Returns a query builder with any conditions provided. Conditions are parsed as
key=value and cannot handle other comparison types. If connection_info is not
injected and was added as a class attribute, that class attribute will be passed
to the query_builder_class instead.

### `AsyncJoinedModel`

Class for representing the results of SQL JOIN queries.

#### Annotations

- models: list[Type[AsyncSqlModel]]
- data: dict

#### Methods

##### `__init__(models: list[Type[AsyncSqlModel]], data: dict) -> None:`

Initialize the instance. Raises TypeError for invalid models or data.

##### `__repr__() -> str:`

Pretty str representation.

##### `__eq__():`

##### `@staticmethod parse_data(models: list[Type[AsyncSqlModel]], data: dict) -> dict:`

Parse data of form {table.column:value} to {table:{column:value}}. Raises
TypeError for invalid models or data.

##### `async get_models() -> list[AsyncSqlModel]:`

Returns the underlying models. Calls the find method for each model.

### `AsyncSqlQueryBuilder`

Main query builder class. Extend with child class to bind to a specific database
by supplying the context_manager param to a call to `super().__init__()`.
Default binding is to aiosqlite.

#### Annotations

- model: Type[AsyncModelProtocol]
- context_manager: Type[AsyncDBContextProtocol]
- connection_info: str
- clauses: list
- params: list
- order_column: str
- order_dir: str
- limit: int
- offset: int
- joins: list[JoinSpec]
- columns: list[str]
- grouping: str

#### Properties

- model: The model type that non-joined query results will be. Setting raises
TypeError if supplied something other than a subclass of AsyncSqlModel.
- table: The table name for the base query. Setting raises TypeError if supplied
something other than a str.

#### Methods

##### `__init__(model_or_table: Type[AsyncSqlModel] | str = None, context_manager: Type[AsyncDBContextProtocol] = AsyncSqliteContext, connection_info: str = '', model: Type[AsyncSqlModel] = None, table: str = '', columns: list[str] = []) -> None:`

Initialize the instance. Must supply model_or_table or model or table. Must
supply context_manager.

##### `is_null(column: str) -> AsyncSqlQueryBuilder:`

Save the 'column is null' clause, then return self. Raises TypeError for invalid
column.

##### `not_null(column: str) -> AsyncSqlQueryBuilder:`

Save the 'column is not null' clause, then return self. Raises TypeError for
invalid column.

##### `equal(column: str, data: Any) -> AsyncSqlQueryBuilder:`

Save the 'column = data' clause and param, then return self. Raises TypeError
for invalid column.

##### `not_equal(column: str, data: Any) -> AsyncSqlQueryBuilder:`

Save the 'column != data' clause and param, then return self. Raises TypeError
for invalid column.

##### `less(column: str, data: Any) -> AsyncSqlQueryBuilder:`

Save the 'column < data' clause and param, then return self. Raises TypeError
for invalid column.

##### `greater(column: str, data: Any) -> AsyncSqlQueryBuilder:`

Save the 'column > data' clause and param, then return self. Raises TypeError
for invalid column.

##### `like(column: str, pattern: str, data: str) -> AsyncSqlQueryBuilder:`

Save the 'column like {pattern.replace(?, data)}' clause and param, then return
self. Raises TypeError or ValueError for invalid column, pattern, or data.

##### `not_like(column: str, pattern: str, data: str) -> AsyncSqlQueryBuilder:`

Save the 'column not like {pattern.replace(?, data)}' clause and param, then
return self. Raises TypeError or ValueError for invalid column, pattern, or
data.

##### `starts_with(column: str, data: str) -> AsyncSqlQueryBuilder:`

Save the 'column like data%' clause and param, then return self. Raises
TypeError or ValueError for invalid column or data.

##### `does_not_start_with(column: str, data: str) -> AsyncSqlQueryBuilder:`

Save the 'column like data%' clause and param, then return self. Raises
TypeError or ValueError for invalid column or data.

##### `contains(column: str, data: str) -> AsyncSqlQueryBuilder:`

Save the 'column like %data%' clause and param, then return self. Raises
TypeError or ValueError for invalid column or data.

##### `excludes(column: str, data: str) -> AsyncSqlQueryBuilder:`

Save the 'column not like %data%' clause and param, then return self. Raises
TypeError or ValueError for invalid column or data.

##### `ends_with(column: str, data: str) -> AsyncSqlQueryBuilder:`

Save the 'column like %data' clause and param, then return self. Raises
TypeError or ValueError for invalid column or data.

##### `does_not_end_with(column: str, data: str) -> AsyncSqlQueryBuilder:`

Save the 'column like %data' clause and param, then return self. Raises
TypeError or ValueError for invalid column or data.

##### `is_in(column: str, data: Union[tuple, list]) -> AsyncSqlQueryBuilder:`

Save the 'column in data' clause and param, then return self. Raises TypeError
or ValueError for invalid column or data.

##### `not_in(column: str, data: Union[tuple, list]) -> AsyncSqlQueryBuilder:`

Save the 'column not in data' clause and param, then return self. Raises
TypeError or ValueError for invalid column or data.

##### `order_by(column: str, direction: str = 'desc') -> AsyncSqlQueryBuilder:`

Sets query order. Raises TypeError or ValueError for invalid column or
direction.

##### `skip(offset: int) -> AsyncSqlQueryBuilder:`

Sets the number of rows to skip. Raises TypeError or ValueError for invalid
offset.

##### `reset() -> AsyncSqlQueryBuilder:`

Returns a fresh instance using the configured model.

##### `async insert(data: dict) -> Optional[AsyncSqlModel | Row]:`

Insert a record and return a model instance. Raises TypeError for invalid data
or ValueError if a record with the same id already exists.

##### `async insert_many(items: list[dict]) -> int:`

Insert a batch of records and return the number inserted. Raises TypeError for
invalid items.

##### `async find(id: Any) -> Optional[AsyncSqlModel | Row]:`

Find a record by its id and return it.

##### `join(model_or_table: Type[AsyncSqlModel] | str, on: list[str], kind: str = 'inner', joined_table_columns: tuple[str] = ()) -> AsyncSqlQueryBuilder:`

Prepares the query for a join over multiple tables/models. Raises TypeError or
ValueError for invalid model, on, or kind.

##### `select(columns: list[str]) -> AsyncQueryBuilderProtocol:`

Sets the columns to select. Raises TypeError for invalid columns.

##### `group(by: str) -> AsyncSqlQueryBuilder:`

Adds a GROUP BY constraint. Raises TypeError for invalid by.

##### `async get() -> list[AsyncSqlModel] | list[AsyncJoinedModel] | list[Row]:`

Run the query on the datastore and return a list of results. Return SqlModels
when running a simple query. Return JoinedModels when running a JOIN query.
Return Rows when running a non-joined GROUP BY query.

##### `async count() -> int:`

Returns the number of records matching the query.

##### `async take(limit: int) -> list[AsyncSqlModel] | list[AsyncJoinedModel] | list[Row]:`

Takes the specified number of rows. Raises TypeError or ValueError for invalid
limit.

##### `chunk(number: int) -> AsyncGenerator[list[AsyncSqlModel] | list[AsyncJoinedModel] | list[Row], None, None]:`

Chunk all matching rows the specified number of rows at a time. Raises TypeError
or ValueError for invalid number.

##### `async first() -> Optional[AsyncSqlModel | Row]:`

Run the query on the datastore and return the first result.

##### `async update(updates: dict, conditions: dict = {}) -> int:`

Update the datastore and return number of records updated. Raises TypeError for
invalid updates or conditions.

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

### `AsyncDeletedModel(AsyncSqlModel)`

Model for preserving and restoring deleted AsyncHashedModel records.

#### Annotations

- table: str
- id_column: str
- columns: tuple
- id: str
- name: str
- query_builder_class: Type[AsyncQueryBuilderProtocol]
- connection_info: str
- data: dict
- _event_hooks: dict[str, list[Callable]]
- model_class: str
- record_id: str
- record: bytes
- timestamp: str

#### Methods

##### `__init__(data: dict = {}) -> None:`

##### `@classmethod async insert(data: dict, /, *, parallel_events: bool = False, suppress_events: bool = False) -> AsyncSqlModel | None:`

Insert a new record to the datastore. Return instance. Raises TypeError if data
is not a dict. Automatically sets a timestamp if one is not supplied.

##### `async restore(inject: dict = {}, /, *, parallel_events: bool = False, suppress_events: bool = False) -> AsyncSqlModel:`

Restore a deleted record, remove from deleted_records, and return the restored
model. Raises ValueError if model_class cannot be found. Raises TypeError if
model_class is not a subclass of AsyncSqlModel. Uses packify.unpack to unpack
the record. Raises TypeError if packed record is not a dict.

### `AsyncHashedModel(AsyncSqlModel)`

Model for interacting with sql database using sha256 for id.

#### Annotations

- table: str
- id_column: str
- columns: tuple[str]
- id: str
- name: str
- query_builder_class: Type[AsyncQueryBuilderProtocol]
- connection_info: str
- data: dict
- _event_hooks: dict[str, list[Callable]]
- columns_excluded_from_hash: tuple[str]
- details: bytes

#### Methods

##### `@classmethod generate_id(data: dict) -> str:`

Generate an id by hashing the non-id contents. Raises TypeError for unencodable
type (calls packify.pack). Any columns not present in the data dict will be set
to None. Any columns in the columns_excluded_from_hash tuple will be excluded
from the sha256 hash.

##### `@classmethod async insert(data: dict, /, *, parallel_events: bool = False, suppress_events: bool = False) -> Optional[AsyncHashedModel]:`

Insert a new record to the datastore. Return instance. Raises TypeError for
non-dict data or unencodable type (calls cls.generate_id, which calls
packify.pack).

##### `@classmethod async insert_many(items: list[dict], /, *, parallel_events: bool = False, suppress_events: bool = False) -> int:`

Insert a batch of records and return the number of items inserted. Raises
TypeError for invalid items or unencodable value (calls cls.generate_id, which
calls packify.pack).

##### `async update(updates: dict, /, *, parallel_events: bool = False, suppress_events: bool = False) -> AsyncHashedModel:`

Persist the specified changes to the datastore, creating a new record in the
process unless the changes were to the hash-excluded columns. Update and return
self in monad pattern. Raises TypeError or ValueError for invalid updates. Did
not need to overwrite the save method because save calls update or insert.

##### `async delete(/, *, parallel_events: bool = False, suppress_events: bool = False) -> AsyncDeletedModel:`

Delete the model, putting it in the deleted_records table, then return the
AsyncDeletedModel. Raises packify.UsageError for unserializable data.

### `AsyncAttachment(AsyncHashedModel)`

Class for attaching immutable details to a record.

#### Annotations

- table: str
- id_column: str
- columns: tuple
- id: str
- name: str
- query_builder_class: Type[AsyncQueryBuilderProtocol]
- connection_info: str
- data: dict
- _event_hooks: dict[str, list[Callable]]
- columns_excluded_from_hash: tuple[str]
- details: bytes | None
- related_model: str
- related_id: str
- _related: AsyncSqlModel
- _details: packify.SerializableType

#### Methods

##### `async related(reload: bool = False) -> AsyncSqlModel:`

Return the related record.

##### `attach_to(related: AsyncSqlModel) -> AsyncAttachment:`

Attach to related model then return self.

##### `get_details(reload: bool = False) -> packify.SerializableType:`

Decode packed bytes to dict.

##### `set_details(details: packify.SerializableType = {}) -> AsyncAttachment:`

Set the details column using either supplied data or by packifying
self._details. Return self in monad pattern. Raises packify.UsageError or
TypeError if details contains unseriazliable type.

##### `@classmethod async insert(data: dict, /, *, parallel_events: bool = False, suppress_events: bool = False) -> Optional[AsyncAttachment]:`

### `AsyncRelation`

Base class for setting up relations.

#### Annotations

- primary_class: Type[AsyncModelProtocol]
- secondary_class: Type[AsyncModelProtocol]
- primary_to_add: AsyncModelProtocol
- primary_to_remove: AsyncModelProtocol
- secondary_to_add: list[AsyncModelProtocol]
- secondary_to_remove: list[AsyncModelProtocol]
- primary: AsyncModelProtocol
- secondary: AsyncModelProtocol | tuple[AsyncModelProtocol]
- _primary: Optional[AsyncModelProtocol]
- _secondary: Optional[AsyncModelProtocol]

#### Properties

- primary: The primary model instance. Setting raises TypeError if a
precondition check fails.
- secondary: The secondary model instance(s).

#### Methods

##### `__init__(primary_class: Type[AsyncModelProtocol], secondary_class: Type[AsyncModelProtocol], primary_to_add: AsyncModelProtocol = None, primary_to_remove: AsyncModelProtocol = None, secondary_to_add: list[AsyncModelProtocol] = [], secondary_to_remove: list[AsyncModelProtocol] = [], primary: AsyncModelProtocol = None, secondary: AsyncModelProtocol | tuple[AsyncModelProtocol] = None) -> None:`

##### `@staticmethod single_model_precondition() -> None:`

Precondition check for a single model. Raises TypeError if the check fails.

##### `@staticmethod multi_model_precondition() -> None:`

Precondition checks for a list of models. Raises TypeError if any check fails.

##### `primary_model_precondition(primary: AsyncModelProtocol) -> None:`

Precondition check for the primary instance. Raises TypeError if the check
fails.

##### `secondary_model_precondition(secondary: AsyncModelProtocol) -> None:`

Precondition check for a secondary instance. Raises TypeError if the check
fails.

##### `@staticmethod pivot_preconditions(pivot: Type[AsyncModelProtocol]) -> None:`

Precondition check for a pivot type. Raises TypeError if the check fails.

##### `async save() -> None:`

Save the relation by setting/unsetting the relevant database values and unset
the following attributes: primary_to_add, primary_to_remove, secondary_to_add,
and secondary_to_remove.

##### `async reload() -> AsyncRelation:`

Reload the relation from the database. Return self in monad pattern.

##### `query() -> AsyncQueryBuilderProtocol | None:`

Creates the base query for the underlying relation.

##### `get_cache_key() -> str:`

Returns the cache key for the AsyncRelation.

##### `create_property() -> property:`

Creates a property to be used on a model.

### `AsyncHasOne(AsyncRelation)`

Class for the relation where primary owns a secondary: primary.data[id_column] =
secondary.data[foreign_id_column]. An owner model.

#### Annotations

- primary_class: Type[AsyncModelProtocol]
- secondary_class: Type[AsyncModelProtocol]
- primary_to_add: AsyncModelProtocol
- primary_to_remove: AsyncModelProtocol
- secondary_to_add: list[AsyncModelProtocol]
- secondary_to_remove: list[AsyncModelProtocol]
- primary: AsyncModelProtocol
- secondary: AsyncModelProtocol | tuple[AsyncModelProtocol]
- _primary: Optional[AsyncModelProtocol]
- _secondary: Optional[AsyncModelProtocol]
- foreign_id_column: str

#### Properties

- secondary: The secondary model instance. Setting raises TypeError if the
precondition check fails.

#### Methods

##### `__init__(foreign_id_column: str) -> None:`

Set the foreign_id_column attribute, then let the AsyncRelation init handle the
rest. Raises TypeError if foreign_id_column is not a str.

##### `async save() -> None:`

Save the relation by setting/unsetting the relevant database values and unset
the following attributes: primary_to_add, primary_to_remove, secondary_to_add,
and secondary_to_remove. Raises UsageError if the relation is missing data.

##### `async reload() -> AsyncHasOne:`

Reload the relation from the database. Return self in monad pattern.

##### `query() -> AsyncQueryBuilderProtocol | None:`

Creates the base query for the underlying relation.

##### `get_cache_key() -> str:`

Returns the cache key for this relation.

##### `create_property() -> property:`

Creates a property that can be used to set relation properties on models. Sets
the relevant post-init hook to set up the relation on newly created models.
Setting the secondary property on the instance will raise a TypeError if the
precondition check fails. Reading the property for the first time will cause an
attempt to read from the database using a synchronized async call, which might
produce a `ResourceWarning` if done within an async function.

### `AsyncHasMany(AsyncHasOne)`

Class for the relation where primary owns multiple secondary models:
model.data[foreign_id_column] = primary.data[id_column] instance of this class
is set on the owner model.

#### Annotations

- primary_class: Type[AsyncModelProtocol]
- secondary_class: Type[AsyncModelProtocol]
- primary_to_add: AsyncModelProtocol
- primary_to_remove: AsyncModelProtocol
- secondary_to_add: list[AsyncModelProtocol]
- secondary_to_remove: list[AsyncModelProtocol]
- primary: AsyncModelProtocol
- secondary: AsyncModelProtocol | tuple[AsyncModelProtocol]
- _primary: Optional[AsyncModelProtocol]
- _secondary: Optional[AsyncModelProtocol]
- foreign_id_column: str

#### Properties

- secondary: The secondary model instance. Setting raises TypeError if the
precondition check fails.

#### Methods

##### `async save() -> None:`

Save the relation by setting the relevant database value(s). Raises UsageError
if the relation is incomplete.

##### `async reload() -> AsyncHasMany:`

Reload the relation from the database. Return self in monad pattern.

##### `query() -> AsyncQueryBuilderProtocol | None:`

Creates the base query for the underlying relation.

##### `create_property() -> property:`

Creates a property that can be used to set relation properties on models. Sets
the relevant post-init hook to set up the relation on newly created models.
Setting the secondary property on the instance will raise a TypeError if the
precondition check fails. Reading the property for the first time will cause an
attempt to read from the database using a synchronized async call, which might
produce a `ResourceWarning` if done within an async function.

### `AsyncBelongsTo(AsyncHasOne)`

Class for the relation where primary belongs to a secondary:
primary.data[foreign_id_column] = secondary.data[id_column]. Inverse of
AsyncHasOne and AsyncHasMany. An instance of this class is set on the owned
model.

#### Annotations

- primary_class: Type[AsyncModelProtocol]
- secondary_class: Type[AsyncModelProtocol]
- primary_to_add: AsyncModelProtocol
- primary_to_remove: AsyncModelProtocol
- secondary_to_add: list[AsyncModelProtocol]
- secondary_to_remove: list[AsyncModelProtocol]
- primary: AsyncModelProtocol
- secondary: AsyncModelProtocol | tuple[AsyncModelProtocol]
- _primary: Optional[AsyncModelProtocol]
- _secondary: Optional[AsyncModelProtocol]
- foreign_id_column: str

#### Methods

##### `async save() -> None:`

Persists the relation to the database. Raises UsageError if the relation is
incomplete.

##### `async reload() -> AsyncBelongsTo:`

Reload the relation from the database. Return self in monad pattern.

##### `query() -> AsyncQueryBuilderProtocol | None:`

Creates the base query for the underlying relation.

##### `create_property() -> property:`

Creates a property that can be used to set relation properties on models. Sets
the relevant post-init hook to set up the relation on newly created models.
Setting the secondary property on the instance will raise a TypeError if the
precondition check fails. Reading the property for the first time will cause an
attempt to read from the database using a synchronized async call, which might
produce a `ResourceWarning` if done within an async function.

### `AsyncBelongsToMany(AsyncRelation)`

Class for the relation where each primary can have many secondary and each
secondary can have many primary; e.g. users and roles, or roles and permissions.
This requires the use of a pivot.

#### Annotations

- primary_class: Type[AsyncModelProtocol]
- secondary_class: Type[AsyncModelProtocol]
- primary_to_add: AsyncModelProtocol
- primary_to_remove: AsyncModelProtocol
- secondary_to_add: list[AsyncModelProtocol]
- secondary_to_remove: list[AsyncModelProtocol]
- primary: AsyncModelProtocol
- secondary: AsyncModelProtocol | tuple[AsyncModelProtocol]
- _primary: Optional[AsyncModelProtocol]
- _secondary: Optional[AsyncModelProtocol]
- pivot: Type[AsyncModelProtocol]
- primary_id_column: str
- secondary_id_column: str

#### Properties

- secondary: The secondary model instances. Setting raises TypeError if a
precondition check fails.
- pivot

#### Methods

##### `__init__(pivot: Type[AsyncModelProtocol], primary_id_column: str, secondary_id_column: str) -> None:`

Set the pivot and query_builder_pivot attributes, then let the AsyncRelation
class handle the rest. Raises TypeError if either primary_id_column or
secondary_id_column is not a str.

##### `async save() -> None:`

Save the relation by setting/unsetting the relevant database value(s). Raises
UsageError if the relation is incomplete.

##### `async reload() -> AsyncBelongsToMany:`

Reload the relation from the database. Return self in monad pattern.

##### `query() -> AsyncQueryBuilderProtocol | None:`

Creates the base query for the underlying relation. This will return the query
for a join between the pivot and the related model.

##### `get_cache_key() -> str:`

Returns the cache key for this relation.

##### `create_property() -> property:`

Creates a property that can be used to set relation properties on models. Sets
the relevant post-init hook to set up the relation on newly created models.
Setting the secondary property on the instance will raise a TypeError if the
precondition check fails. Reading the property for the first time will cause an
attempt to read from the database using a synchronized async call, which might
produce a `ResourceWarning` if done within an async function.

### `AsyncContains(AsyncHasMany)`

Class for encoding a relationship in which a model contains the ID(s) for other
models within a column: primary.data[foreign_id_column] = ",".join(sorted([
s.data[id_column] for s in secondary])). Useful for DAGs using HashedModel or
something similar. IDs are sorted for deterministic hashing via HashedModel.

#### Annotations

- primary_class: Type[AsyncModelProtocol]
- secondary_class: Type[AsyncModelProtocol]
- primary_to_add: AsyncModelProtocol
- primary_to_remove: AsyncModelProtocol
- secondary_to_add: list[AsyncModelProtocol]
- secondary_to_remove: list[AsyncModelProtocol]
- primary: AsyncModelProtocol
- secondary: tuple[AsyncModelProtocol]
- _primary: Optional[AsyncModelProtocol]
- _secondary: tuple[AsyncModelProtocol]
- foreign_id_column: str

#### Methods

##### `async save() -> None:`

Persists the relation to the database. Raises UsageError if the relation is
incomplete.

##### `async reload() -> AsyncContains:`

Reload the relation from the database. Return self in monad pattern.

##### `query() -> AsyncQueryBuilderProtocol | None:`

Creates the base query for the underlying relation.

##### `create_property() -> property:`

Creates a property that can be used to set relation properties on models. Sets
the relevant post-init hook to set up the relation on newly created models.
Setting the secondary property on the instance will raise a TypeError if the
precondition check fails. Reading the property for the first time will cause an
attempt to read from the database using a synchronized async call, which might
produce a `ResourceWarning` if done within an async function.

### `AsyncWithin(AsyncHasMany)`

Class for encoding a relationship in which the model's ID is contained within a
column of another model: all([ primary.data[id_column] in
s.data[foreign_id_column] for s in secondary]). Useful for DAGs using
HashedModel or something similar. IDs are sorted for deterministic hashing via
HashedModel.

#### Annotations

- primary_class: Type[AsyncModelProtocol]
- secondary_class: Type[AsyncModelProtocol]
- primary_to_add: AsyncModelProtocol
- primary_to_remove: AsyncModelProtocol
- secondary_to_add: list[AsyncModelProtocol]
- secondary_to_remove: list[AsyncModelProtocol]
- primary: AsyncModelProtocol
- secondary: tuple[AsyncModelProtocol]
- _primary: Optional[AsyncModelProtocol]
- _secondary: Optional[AsyncModelProtocol]
- foreign_id_column: str

#### Methods

##### `async save() -> None:`

Persists the relation to the database. Raises UsageError if the relation is
incomplete.

##### `async reload() -> AsyncWithin:`

Reload the relation from the database. Return self in monad pattern.

##### `query() -> AsyncQueryBuilderProtocol | None:`

Creates the base query for the underlying relation (i.e. to query the secondary
class).

##### `create_property() -> property:`

Creates a property that can be used to set relation properties on models. Sets
the relevant post-init hook to set up the relation on newly created models.
Setting the secondary property on the instance will raise a TypeError if the
precondition check fails. Reading the property for the first time will cause an
attempt to read from the database using a synchronized async call, which might
produce a `ResourceWarning` if done within an async function.

## Functions

### `async_dynamic_sqlmodel(connection_string: str | bytes, table_name: str = '', column_names: tuple[str] = ()) -> Type[AsyncSqlModel]:`

Generates a dynamic sqlite model for instantiating context managers. Raises
TypeError for invalid connection_string or table_name.

### `async_has_one(cls: Type[AsyncModelProtocol], owned_model: Type[AsyncModelProtocol], foreign_id_column: str = None) -> property:`

Creates a AsyncHasOne relation and returns the result of create_property. Usage
syntax is like `User.avatar = async_has_one( User, Avatar)`. If the foreign id
column on the Avatar.table table is not user_id (cls.__name__ PascalCase ->
snake_case + "_id"), then it can be specified.

### `async_has_many(cls: Type[AsyncModelProtocol], owned_model: Type[AsyncModelProtocol], foreign_id_column: str = None) -> property:`

Creates a AsyncHasMany relation and returns the result of create_property. Usage
syntax is like `User.posts = async_has_many( User, Post)`. If the foreign id
column on the Post.table table is not user_id (cls.__name__ PascalCase ->
snake_case + "_id"), then it can be specified.

### `async_belongs_to(cls: Type[AsyncModelProtocol], owner_model: Type[AsyncModelProtocol], foreign_id_column: str = None) -> property:`

Creates a AsyncBelongsTo relation and returns the result of create_property.
Usage syntax is like `Post.owner = async_belongs_to( Post, User)`. If the
foreign id column on the Post.table table is not user_id (cls.__name__
PascalCase -> snake_case + "_id"), then it can be specified.

### `async_belongs_to_many(cls: Type[AsyncModelProtocol], other_model: Type[AsyncModelProtocol], pivot: Type[AsyncModelProtocol], primary_id_column: str = None, secondary_id_column: str = None) -> property:`

Creates a AsyncBelongsToMany relation and returns the result of create_property.
Usage syntax is like `User.liked_posts = async_belongs_to_many(User, Post, LikedPost)`.
If the foriegn id columns on LikedPost are not user_id and post_id (cls.__name__
or other_model.__name__ PascalCase -> snake_case + "_id"), then they can be
specified.

### `async_contains(cls: Type[AsyncModelProtocol], other_model: Type[AsyncModelProtocol], foreign_ids_column: str = None) -> property:`

Creates a Contains relation and returns the result of calling create_property.
Usage syntax is like `Item.parents = async_contains(Item, Item)`. If the column
containing the sorted list of ids is not item_ids (i.e. other_model.__name__ ->
snake_case + '_ids'), it can be specified.

### `async_within(cls: Type[AsyncModelProtocol], other_model: Type[AsyncModelProtocol], foreign_ids_column: str = None) -> property:`

Creates a Within relation and returns the result of calling create_property.
Usage syntax is like `Item.children = async_within(Item, Item)`. If the column
containing the sorted list of ids is not item_ids (i.e. cls.__name__ ->
snake_case + '_ids'), it can be specified.


