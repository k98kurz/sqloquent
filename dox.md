# sqloquent

The majority of useful features are exposed from the root level of the package,
and the rest from sqloquent.asyncql, sqloquent.tools, or from invoking the tools
through the CLI.

## Classes

### `SqlModel`

General model for mapping a SQL row to an in-memory object.

#### Annotations

- table: str
- id_column: str
- columns: tuple
- id: str
- name: str
- query_builder_class: Type[QueryBuilderProtocol]
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

##### `@classmethod invoke_hooks(event: str):`

Invoke the hooks for the event, passing cls, *args, and **kwargs.

##### `@staticmethod create_property() -> property:`

Create a dynamic property for the column with the given name.

##### `@staticmethod encode_value(val: Any) -> str:`

Encode a value for hashing. Uses the pack function from packify.

##### `@classmethod generate_id() -> str:`

Generates and returns a hexadecimal UUID4.

##### `@classmethod find(id: Any) -> Optional[SqlModel]:`

Find a record by its id and return it. Return None if it does not exist.

##### `@classmethod insert(data: dict, /, *, suppress_events: bool = False) -> Optional[SqlModel]:`

Insert a new record to the datastore. Return instance. Raises TypeError if data
is not a dict.

##### `@classmethod insert_many(items: list[dict], /, *, suppress_events: bool = False) -> int:`

Insert a batch of records and return the number of items inserted. Raises
TypeError if items is not list[dict].

##### `update(updates: dict, conditions: dict = None, /, *, suppress_events: bool = False) -> SqlModel:`

Persist the specified changes to the datastore. Return self in monad pattern.
Raises TypeError or ValueError for invalid updates or conditions (self.data must
include the id to update or conditions must be specified).

##### `save(/, *, suppress_events: bool = False) -> SqlModel:`

Persist to the datastore. Return self in monad pattern. Calls insert or update
and raises appropriate errors.

##### `delete(/, *, suppress_events: bool = False) -> None:`

Delete the record.

##### `reload(/, *, suppress_events: bool = False) -> SqlModel:`

Reload values from datastore. Return self in monad pattern. Raises UsageError if
id is not set in self.data.

##### `@classmethod query(conditions: dict = None, connection_info: str = None) -> QueryBuilderProtocol:`

Returns a query builder with any conditions provided. Conditions are parsed as
key=value and cannot handle other comparison types. If connection_info is not
injected and was added as a class attribute, that class attribute will be passed
to the query_builder_class instead.

### `SqlQueryBuilder`

Main query builder class. Extend with child class to bind to a specific database
by supplying the context_manager param to a call to `super().__init__()`.
Default binding is to sqlite3.

#### Annotations

- model: Type[ModelProtocol]
- context_manager: Type[DBContextProtocol]
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
TypeError if supplied something other than a subclass of SqlModel.
- table: The table name for the base query. Setting raises TypeError if supplied
something other than a str.

#### Methods

##### `__init__(model_or_table: Type[SqlModel] | str = None, context_manager: Type[DBContextProtocol] = SqliteContext, connection_info: str = '', model: Type[SqlModel] = None, table: str = '', columns: list[str] = []) -> None:`

Initialize the instance. Must supply model_or_table or model or table. Must
supply context_manager.

##### `is_null(column: str) -> SqlQueryBuilder:`

Save the 'column is null' clause, then return self. Raises TypeError for invalid
column.

##### `not_null(column: str) -> SqlQueryBuilder:`

Save the 'column is not null' clause, then return self. Raises TypeError for
invalid column.

##### `equal(column: str, data: Any) -> SqlQueryBuilder:`

Save the 'column = data' clause and param, then return self. Raises TypeError
for invalid column.

##### `not_equal(column: str, data: Any) -> SqlQueryBuilder:`

Save the 'column != data' clause and param, then return self. Raises TypeError
for invalid column.

##### `less(column: str, data: Any) -> SqlQueryBuilder:`

Save the 'column < data' clause and param, then return self. Raises TypeError
for invalid column.

##### `greater(column: str, data: Any) -> SqlQueryBuilder:`

Save the 'column > data' clause and param, then return self. Raises TypeError
for invalid column.

##### `like(column: str, pattern: str, data: str) -> SqlQueryBuilder:`

Save the 'column like {pattern.replace(?, data)}' clause and param, then return
self. Raises TypeError or ValueError for invalid column, pattern, or data.

##### `not_like(column: str, pattern: str, data: str) -> SqlQueryBuilder:`

Save the 'column not like {pattern.replace(?, data)}' clause and param, then
return self. Raises TypeError or ValueError for invalid column, pattern, or
data.

##### `starts_with(column: str, data: str) -> SqlQueryBuilder:`

Save the 'column like data%' clause and param, then return self. Raises
TypeError or ValueError for invalid column or data.

##### `does_not_start_with(column: str, data: str) -> SqlQueryBuilder:`

Save the 'column not like data%' clause and param, then return self. Raises
TypeError or ValueError for invalid column or data.

##### `contains(column: str, data: str) -> SqlQueryBuilder:`

Save the 'column like %data%' clause and param, then return self. Raises
TypeError or ValueError for invalid column or data.

##### `excludes(column: str, data: str) -> SqlQueryBuilder:`

Save the 'column not like %data%' clause and param, then return self. Raises
TypeError or ValueError for invalid column or data.

##### `ends_with(column: str, data: str) -> SqlQueryBuilder:`

Save the 'column like %data' clause and param, then return self. Raises
TypeError or ValueError for invalid column or data.

##### `does_not_end_with(column: str, data: str) -> SqlQueryBuilder:`

Save the 'column like %data' clause and param, then return self. Raises
TypeError or ValueError for invalid column or data.

##### `is_in(column: str, data: Union[tuple, list]) -> SqlQueryBuilder:`

Save the 'column in data' clause and param, then return self. Raises TypeError
or ValueError for invalid column or data.

##### `not_in(column: str, data: Union[tuple, list]) -> SqlQueryBuilder:`

Save the 'column not in data' clause and param, then return self. Raises
TypeError or ValueError for invalid column or data.

##### `order_by(column: str, direction: str = 'desc') -> SqlQueryBuilder:`

Sets query order. Raises TypeError or ValueError for invalid column or
direction.

##### `skip(offset: int) -> SqlQueryBuilder:`

Sets the number of rows to skip. Raises TypeError or ValueError for invalid
offset.

##### `reset() -> SqlQueryBuilder:`

Returns a fresh instance using the configured model.

##### `insert(data: dict) -> Optional[SqlModel | Row]:`

Insert a record and return a model instance. Raises TypeError for invalid data
or ValueError if a record with the same id already exists.

##### `insert_many(items: list[dict]) -> int:`

Insert a batch of records and return the number inserted. Raises TypeError for
invalid items.

##### `find(id: Any) -> Optional[SqlModel | Row]:`

Find a record by its id and return it.

##### `join(model_or_table: Type[SqlModel] | str, on: list[str], kind: str = 'inner', joined_table_columns: tuple[str] = ()) -> SqlQueryBuilder:`

Prepares the query for a join over multiple tables/models. Raises TypeError or
ValueError for invalid model, on, or kind.

##### `select(columns: list[str]) -> QueryBuilderProtocol:`

Sets the columns to select. Raises TypeError for invalid columns.

##### `group(by: str) -> SqlQueryBuilder:`

Adds a GROUP BY constraint. Raises TypeError for invalid by.

##### `get() -> list[SqlModel] | list[JoinedModel] | list[Row]:`

Run the query on the datastore and return a list of results. Return SqlModels
when running a simple query. Return JoinedModels when running a JOIN query.
Return Rows when running a non-joined GROUP BY query.

##### `count() -> int:`

Returns the number of records matching the query.

##### `take(limit: int) -> list[SqlModel] | list[JoinedModel] | list[Row]:`

Takes the specified number of rows. Raises TypeError or ValueError for invalid
limit.

##### `chunk(number: int) -> Generator[list[SqlModel] | list[JoinedModel] | list[Row], None, None]:`

Chunk all matching rows the specified number of rows at a time. Raises TypeError
or ValueError for invalid number.

##### `first() -> Optional[SqlModel | Row]:`

Run the query on the datastore and return the first result.

##### `update(updates: dict, conditions: dict = {}) -> int:`

Update the datastore and return number of records updated. Raises TypeError for
invalid updates or conditions.

##### `delete() -> int:`

Delete the records that match the query and return the number of deleted
records.

##### `to_sql(interpolate_params: bool = True) -> str | tuple[str, list]:`

Return the sql where clause from the clauses and params. If interpolate_params
is True, the parameters will be interpolated into the SQL str and a single str
result will be returned. If interpolate_params is False, the parameters will not
be interpolated into the SQL str, instead including question marks, and an
additional list of params will be returned along with the SQL str.

##### `execute_raw(sql: str) -> tuple[int, list[tuple[Any]]]:`

Execute raw SQL against the database. Return rowcount and fetchall results.

### `SqliteContext`

Context manager for sqlite.

#### Annotations

- connection: sqlite3.Connection
- cursor: sqlite3.Cursor
- connection_info: str

#### Methods

##### `__init__(connection_info: str = '') -> None:`

Initialize the instance. Raises TypeError for non-str table.

##### `__enter__() -> CursorProtocol:`

Enter the context block and return the cursor.

##### `__exit__(_SqliteContext__exc_type: Optional[Type[BaseException]], _SqliteContext__exc_value: Optional[BaseException], _SqliteContext__traceback: Optional[TracebackType]) -> None:`

Exit the context block. Commit or rollback as appropriate, then close the
connection.

### `DeletedModel(SqlModel)`

Model for preserving and restoring deleted HashedModel records.

#### Annotations

- table: str
- id_column: str
- columns: tuple
- id: str
- name: str
- query_builder_class: Type[QueryBuilderProtocol]
- connection_info: str
- data: dict
- _event_hooks: dict[str, list[Callable]]
- model_class: str
- record_id: str
- record: bytes
- timestamp: str

#### Methods

##### `__init__(data: dict = {}) -> None:`

##### `@classmethod insert(data: dict, /, *, suppress_events: bool = False) -> SqlModel | None:`

Insert a new record to the datastore. Return instance. Raises TypeError if data
is not a dict. Automatically sets a timestamp if one is not supplied.

##### `restore(inject: dict = {}, /, *, suppress_events: bool = False) -> SqlModel:`

Restore a deleted record, remove from deleted_records, and return the restored
model. Raises ValueError if model_class cannot be found. Raises TypeError if
model_class is not a subclass of SqlModel. Uses packify.unpack to unpack the
record. Raises TypeError if packed record is not a dict.

### `HashedModel(SqlModel)`

Model for interacting with sql database using sha256 for id.

#### Annotations

- table: str
- id_column: str
- columns: tuple[str]
- id: str
- name: str
- query_builder_class: Type[QueryBuilderProtocol]
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

##### `@classmethod insert(data: dict, /, *, suppress_events: bool = False) -> Optional[HashedModel]:`

Insert a new record to the datastore. Return instance. Raises TypeError for
non-dict data or unencodable type (calls cls.generate_id, which calls
packify.pack).

##### `@classmethod insert_many(items: list[dict], /, *, suppress_events: bool = False) -> int:`

Insert a batch of records and return the number of items inserted. Raises
TypeError for invalid items or unencodable value (calls cls.generate_id, which
calls packify.pack).

##### `update(updates: dict, /, *, suppress_events: bool = False) -> HashedModel:`

Persist the specified changes to the datastore, creating a new record in the
process unless the changes were to the hash-excluded columns. Update and return
self in monad pattern. Raises TypeError or ValueError for invalid updates. Did
not need to overwrite the save method because save calls update or insert.

##### `delete(/, *, suppress_events: bool = False) -> DeletedModel:`

Delete the model, putting it in the deleted_records table, then return the
DeletedModel. Raises packify.UsageError for unserializable data.

### `Attachment(HashedModel)`

Class for attaching immutable details to a record.

#### Annotations

- table: str
- id_column: str
- columns: tuple
- id: str
- name: str
- query_builder_class: Type[QueryBuilderProtocol]
- connection_info: str
- data: dict
- _event_hooks: dict[str, list[Callable]]
- columns_excluded_from_hash: tuple[str]
- details: bytes | None
- related_model: str
- related_id: str
- _related: SqlModel
- _details: packify.SerializableType

#### Methods

##### `related(reload: bool = False) -> SqlModel:`

Return the related record.

##### `attach_to(related: SqlModel) -> Attachment:`

Attach to related model then return self.

##### `get_details(reload: bool = False) -> packify.SerializableType:`

Decode packed bytes to dict.

##### `set_details(details: packify.SerializableType = {}) -> Attachment:`

Set the details column using either supplied data or by packifying
self._details. Return self in monad pattern. Raises packify.UsageError or
TypeError if details contains unseriazliable type.

##### `@classmethod insert(data: dict, /, *, suppress_events: bool = False) -> Optional[Attachment]:`

### `Row`

Class for representing a row from a query when no better model exists.

#### Annotations

- data: dict

#### Methods

##### `__init__(data: dict):`

##### `__repr__():`

##### `__eq__():`

### `JoinedModel`

Class for representing the results of SQL JOIN queries.

#### Annotations

- models: list[Type[SqlModel]]
- data: dict

#### Methods

##### `__init__(models: list[Type[SqlModel]], data: dict) -> None:`

Initialize the instance. Raises TypeError for invalid models or data.

##### `__repr__() -> str:`

Pretty str representation.

##### `__eq__():`

##### `@staticmethod parse_data(models: list[Type[SqlModel]], data: dict) -> dict:`

Parse data of form {table.column:value} to {table:{column:value}}. Raises
TypeError for invalid models or data.

##### `get_models() -> list[SqlModel]:`

Returns the underlying models. Calls the find method for each model.

### `JoinSpec`

Class for representing joins to be executed by a query builder.

#### Annotations

- kind: str
- table_1: str
- table_1_columns: list[str]
- column_1: str
- comparison: str
- table_2: str
- table_2_columns: list[str]
- column_2: str

#### Methods

##### `__init__(kind: str, table_1: str, table_1_columns: list[str], column_1: str, comparison: str, table_2: str, table_2_columns: list[str], column_2: str):`

##### `__repr__():`

##### `__eq__():`

### `CursorProtocol(Protocol)`

Interface showing how a DB cursor should function.

#### Methods

##### `execute(sql: str, parameters: list[str] = []) -> CursorProtocol:`

Execute a single query with the given parameters.

##### `executemany(sql: str, seq_of_parameters: Iterable[list[str]] = []) -> CursorProtocol:`

Execute a query once for each list of parameters.

##### `executescript(sql: str) -> CursorProtocol:`

Execute a SQL script without parameters. No implicit transaciton handling.

##### `fetchone() -> Any:`

Get one record returned by the previous query.

##### `fetchall() -> Any:`

Get all records returned by the previous query.

### `DBContextProtocol(Protocol)`

Interface showing how a context manager for connecting to a database should
behave.

#### Methods

##### `__init__(connection_info: str = '') -> None:`

Using the connection_info parameter is optional but should be supported. I
recommend setting a class attribute with the default value taken from an
environment variable, then use that class attribute within this method,
overriding with the parameter only if it is not empty.

##### `__enter__() -> CursorProtocol:`

Enter the `with` block. Should return a cursor useful for making db calls.

##### `__exit__(exc_type: Optional[Type[BaseException]], exc_value: Optional[BaseException], traceback: Optional[TracebackType]) -> None:`

Exit the `with` block. Should commit any pending transactions and close the
cursor and connection upon exiting the context.

### `ModelProtocol(Protocol)`

Interface showing how a model should function.

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

Invoke the hooks for the event, passing cls, *args, and **kwargs.

##### `@classmethod find(id: Any) -> Optional[ModelProtocol]:`

Find a record by its id and return it. Return None if it does not exist.

##### `@classmethod insert(data: dict, /, *, suppress_events: bool = False) -> Optional[ModelProtocol]:`

Insert a new record to the datastore. Return instance.

##### `@classmethod insert_many(items: list[dict], /, *, suppress_events: bool = False) -> int:`

Insert a batch of records and return the number of items inserted.

##### `update(updates: dict, conditions: dict = None, /, *, suppress_events: bool = False) -> ModelProtocol:`

Persist the specified changes to the datastore. Return self in monad pattern.

##### `save(/, *, suppress_events: bool = False) -> ModelProtocol:`

Persist to the datastore. Return self in monad pattern.

##### `delete(/, *, suppress_events: bool = False) -> None:`

Delete the record.

##### `reload(/, *, suppress_events: bool = False) -> ModelProtocol:`

Reload values from datastore. Return self in monad pattern.

##### `@classmethod query(conditions: dict = None) -> QueryBuilderProtocol:`

Return a QueryBuilderProtocol for the model.

### `QueryBuilderProtocol(Protocol)`

Interface showing how a query builder should function.

#### Properties

- table: The name of the table.
- model: The class of the relevant model.

#### Methods

##### `__init__(model_or_table: Type[ModelProtocol] | str, context_manager: Type[DBContextProtocol], connection_info: str = '', model: Type[ModelProtocol] = None, table: str = None) -> None:`

Initialize the instance. A class implementing ModelProtocol or the str name of a
table must be provided.

##### `is_null(column: str) -> QueryBuilderProtocol:`

Save the 'column is null' clause, then return self. Raises TypeError for invalid
column.

##### `not_null(column: str) -> QueryBuilderProtocol:`

Save the 'column is not null' clause, then return self. Raises TypeError for
invalid column.

##### `equal(column: str, data: str) -> QueryBuilderProtocol:`

Save the 'column = data' clause and param, then return self.

##### `not_equal(column: str, data: Any) -> QueryBuilderProtocol:`

Save the 'column != data' clause and param, then return self.

##### `less(column: str, data: str) -> QueryBuilderProtocol:`

Save the 'column < data' clause and param, then return self.

##### `greater(column: str, data: str) -> QueryBuilderProtocol:`

Save the 'column > data' clause and param, then return self.

##### `like(column: str, pattern: str, data: str) -> QueryBuilderProtocol:`

Save the 'column like {pattern.replace(?, data)}' clause and param, then return
self. Raises TypeError or ValueError for invalid column, pattern, or data.

##### `not_like(column: str, pattern: str, data: str) -> QueryBuilderProtocol:`

Save the 'column not like {pattern.replace(?, data)}' clause and param, then
return self. Raises TypeError or ValueError for invalid column, pattern, or
data.

##### `starts_with(column: str, data: str) -> QueryBuilderProtocol:`

Save the 'column like data%' clause and param, then return self.

##### `does_not_start_with(column: str, data: str) -> QueryBuilderProtocol:`

Save the 'column not like data%' clause and param, then return self. Raises
TypeError or ValueError for invalid column or data.

##### `contains(column: str, data: str) -> QueryBuilderProtocol:`

Save the 'column like %data%' clause and param, then return self.

##### `excludes(column: str, data: str) -> QueryBuilderProtocol:`

Save the 'column not like %data%' clause and param, then return self.

##### `ends_with(column: str, data: str) -> QueryBuilderProtocol:`

Save the 'column like %data' clause and param, then return self.

##### `does_not_end_with(column: str, data: str) -> QueryBuilderProtocol:`

Save the 'column like %data' clause and param, then return self. Raises
TypeError or ValueError for invalid column or data.

##### `is_in(column: str, data: Union[tuple, list]) -> QueryBuilderProtocol:`

Save the 'column in data' clause and param, then return self.

##### `not_in(column: str, data: Union[tuple, list]) -> QueryBuilderProtocol:`

Save the 'column not in data' clause and param, then return self. Raises
TypeError or ValueError for invalid column or data.

##### `order_by(column: str, direction: str = 'desc') -> QueryBuilderProtocol:`

Sets query order.

##### `skip(offset: int) -> QueryBuilderProtocol:`

Sets the number of rows to skip.

##### `reset() -> QueryBuilderProtocol:`

Returns a fresh instance using the configured model.

##### `insert(data: dict) -> Optional[ModelProtocol | RowProtocol]:`

Insert a record and return a model instance.

##### `insert_many(items: list[dict]) -> int:`

Insert a batch of records and return the number inserted.

##### `find(id: str) -> Optional[ModelProtocol | RowProtocol]:`

Find a record by its id and return it.

##### `join(model_or_table: Type[ModelProtocol] | str, on: list[str], kind: str = 'inner', joined_table_columns: tuple[str] = ()) -> QueryBuilderProtocol:`

Prepares the query for a join over multiple tables/models. Raises TypeError or
ValueError for invalid model, on, or kind.

##### `select(columns: list[str]) -> QueryBuilderProtocol:`

Sets the columns to select.

##### `group(by: str) -> QueryBuilderProtocol:`

Adds a group by constraint.

##### `get() -> list[ModelProtocol] | list[JoinedModelProtocol] | list[RowProtocol]:`

Run the query on the datastore and return a list of results. Return SqlModels
when running a simple query. Return JoinedModels when running a JOIN query.
Return Rows when running a non-joined GROUP BY query.

##### `count() -> int:`

Returns the number of records matching the query.

##### `take(number: int) -> list[ModelProtocol] | list[JoinedModelProtocol] | list[RowProtocol]:`

Takes the specified number of rows.

##### `chunk(number: int) -> Generator[list[ModelProtocol] | list[JoinedModelProtocol] | list[RowProtocol], None, None]:`

Chunk all matching rows the specified number of rows at a time.

##### `first() -> Optional[ModelProtocol | RowProtocol]:`

Run the query on the datastore and return the first result.

##### `update(updates: dict, conditions: dict = {}) -> int:`

Update the datastore and return number of records updated.

##### `delete() -> int:`

Delete the records that match the query and return the number of deleted
records.

##### `to_sql(interpolate_params: bool = True) -> str | tuple[str, list]:`

Return the sql where clause from the clauses and params. If interpolate_params
is True, the parameters will be interpolated into the SQL str and a single str
result will be returned. If interpolate_params is False, the parameters will not
be interpolated into the SQL str, instead including question marks, and an
additional list of params will be returned along with the SQL str.

##### `execute_raw(sql: str) -> tuple[int, list[tuple[Any]]]:`

Execute raw SQL against the database. Return rowcount and fetchall results.

### `JoinedModelProtocol(Protocol)`

Interface for representations of JOIN query results.

#### Properties

- data: Dict for storing models data.

#### Methods

##### `__init__(models: list[Type[ModelProtocol]], data: dict) -> None:`

Initialize the instance.

##### `@staticmethod parse_data(models: list[Type[ModelProtocol]], data: dict) -> dict:`

Parse data of form {table.column:value} to {table:{column:value}}.

##### `get_models() -> list[ModelProtocol]:`

Returns the underlying models.

### `RowProtocol(Protocol)`

Interface for a generic row representation.

#### Properties

- data: Returns the underlying row data.

### `RelationProtocol(Protocol)`

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

##### `primary_model_precondition(primary: ModelProtocol) -> None:`

Checks that primary is instance of self.primary_class.

##### `secondary_model_precondition(secondary: ModelProtocol) -> None:`

Checks that secondary is instance of self.secondary_class.

##### `@staticmethod pivot_preconditions(pivot: Type[ModelProtocol]) -> None:`

Checks preconditions for a pivot.

##### `save() -> None:`

Save the relation by setting/unsetting relevant database values.

##### `reload() -> None:`

Reload the secondary models from the database.

##### `query() -> QueryBuilderProtocol | None:`

Creates the base query for the underlying relation.

##### `get_cache_key() -> str:`

Get the cache key for the relation.

##### `create_property() -> property:`

Produces a property to be set on a model, allowing it to access the related
model through the relation.

### `RelatedModel(ModelProtocol)`

Interface showing what a related model returned from an ORM helper function or
RelationProtocol.create_property will behave. This is used for relations where
the primary model is associated with a single secondary model.

#### Methods

##### `__call__() -> RelationProtocol:`

Return the underlying relation when the property is called as a method, e.g.
`phone.owner()` will return the relation while `phone.owner` will access the
related model.

### `RelatedCollection(Protocol)`

Interface showing what a related model returned from an ORM helper function or
RelationProtocol.create_property will behave. This is used for relations where
the primary model is associated with multiple secondary models.

#### Methods

##### `__call__() -> RelationProtocol:`

Return the underlying relation when the property is called as a method, e.g.
`fish.scales()` will return the relation while `fish.scales` will access the
related models.

##### `__iter__() -> ModelProtocol:`

Allow the collection to be iterated over, returning a model on each iteration.

##### `__getitem__() -> ModelProtocol:`

Return the related model at the given index.

### `Relation`

Base class for setting up relations.

#### Annotations

- primary_class: Type[ModelProtocol]
- secondary_class: Type[ModelProtocol]
- primary_to_add: ModelProtocol
- primary_to_remove: ModelProtocol
- secondary_to_add: list[ModelProtocol]
- secondary_to_remove: list[ModelProtocol]
- primary: ModelProtocol
- secondary: ModelProtocol | tuple[ModelProtocol]
- _primary: Optional[ModelProtocol]
- _secondary: Optional[ModelProtocol]

#### Properties

- primary: The primary model instance. Setting raises TypeError if a
precondition check fails.
- secondary: The secondary model instance(s).

#### Methods

##### `__init__(primary_class: Type[ModelProtocol], secondary_class: Type[ModelProtocol], primary_to_add: ModelProtocol = None, primary_to_remove: ModelProtocol = None, secondary_to_add: list[ModelProtocol] = [], secondary_to_remove: list[ModelProtocol] = [], primary: ModelProtocol = None, secondary: ModelProtocol | tuple[ModelProtocol] = None) -> None:`

##### `@staticmethod single_model_precondition() -> None:`

Precondition check for a single model. Raises TypeError if the check fails.

##### `@staticmethod multi_model_precondition() -> None:`

Precondition checks for a list of models. Raises TypeError if any check fails.

##### `primary_model_precondition(primary: ModelProtocol) -> None:`

Precondition check for the primary instance. Raises TypeError if the check
fails.

##### `secondary_model_precondition(secondary: ModelProtocol) -> None:`

Precondition check for a secondary instance. Raises TypeError if the check
fails.

##### `@staticmethod pivot_preconditions(pivot: Type[ModelProtocol]) -> None:`

Precondition check for a pivot type. Raises TypeError if the check fails.

##### `save() -> None:`

Save the relation by setting/unsetting the relevant database values and unset
the following attributes: primary_to_add, primary_to_remove, secondary_to_add,
and secondary_to_remove.

##### `reload() -> Relation:`

Reload the relation from the database. Return self in monad pattern.

##### `query() -> QueryBuilderProtocol | None:`

Creates the base query for the underlying relation.

##### `get_cache_key() -> str:`

Returns the cache key for the Relation.

##### `create_property() -> property:`

Creates a property to be used on a model.

### `HasOne(Relation)`

Class for the relation where primary owns a secondary: primary.data[id_column] =
secondary.data[foreign_id_column]. An owner model.

#### Annotations

- primary_class: Type[ModelProtocol]
- secondary_class: Type[ModelProtocol]
- primary_to_add: ModelProtocol
- primary_to_remove: ModelProtocol
- secondary_to_add: list[ModelProtocol]
- secondary_to_remove: list[ModelProtocol]
- primary: ModelProtocol
- secondary: ModelProtocol | tuple[ModelProtocol]
- _primary: Optional[ModelProtocol]
- _secondary: Optional[ModelProtocol]
- foreign_id_column: str

#### Properties

- secondary: The secondary model instance. Setting raises TypeError if the
precondition check fails.

#### Methods

##### `__init__(foreign_id_column: str) -> None:`

Set the foreign_id_column attribute, then let the Relation init handle the rest.
Raises TypeError if foreign_id_column is not a str.

##### `save() -> None:`

Save the relation by setting/unsetting the relevant database values and unset
the following attributes: primary_to_add, primary_to_remove, secondary_to_add,
and secondary_to_remove. Raises UsageError if the relation is missing data.

##### `reload() -> HasOne:`

Reload the relation from the database. Return self in monad pattern.

##### `query() -> QueryBuilderProtocol | None:`

Creates the base query for the underlying relation.

##### `get_cache_key() -> str:`

Returns the cache key for this relation.

##### `create_property() -> property:`

Creates a property that can be used to set relation properties on models. Sets
the relevant post-init hook to set up the relation on newly created models.
Setting the secondary property on the instance will raise a TypeError if the
precondition check fails.

### `HasMany(HasOne)`

Class for the relation where primary owns multiple secondary models:
model.data[foreign_id_column] = primary.data[id_column] instance of this class
is set on the owner model.

#### Annotations

- primary_class: Type[ModelProtocol]
- secondary_class: Type[ModelProtocol]
- primary_to_add: ModelProtocol
- primary_to_remove: ModelProtocol
- secondary_to_add: list[ModelProtocol]
- secondary_to_remove: list[ModelProtocol]
- primary: ModelProtocol
- secondary: ModelProtocol | tuple[ModelProtocol]
- _primary: Optional[ModelProtocol]
- _secondary: Optional[ModelProtocol]
- foreign_id_column: str

#### Properties

- secondary: The secondary model instance. Setting raises TypeError if the
precondition check fails.

#### Methods

##### `save() -> None:`

Save the relation by setting the relevant database value(s). Raises UsageError
if the relation is incomplete.

##### `reload() -> HasMany:`

Reload the relation from the database. Return self in monad pattern.

##### `query() -> QueryBuilderProtocol | None:`

Creates the base query for the underlying relation.

##### `create_property() -> property:`

Creates a property that can be used to set relation properties on models. Sets
the relevant post-init hook to set up the relation on newly created models.
Setting the secondary property on the instance will raise a TypeError if the
precondition check fails.

### `BelongsTo(HasOne)`

Class for the relation where primary belongs to a secondary:
primary.data[foreign_id_column] = secondary.data[id_column]. Inverse of HasOne
and HasMany. An instance of this class is set on the owned model.

#### Annotations

- primary_class: Type[ModelProtocol]
- secondary_class: Type[ModelProtocol]
- primary_to_add: ModelProtocol
- primary_to_remove: ModelProtocol
- secondary_to_add: list[ModelProtocol]
- secondary_to_remove: list[ModelProtocol]
- primary: ModelProtocol
- secondary: ModelProtocol | tuple[ModelProtocol]
- _primary: Optional[ModelProtocol]
- _secondary: Optional[ModelProtocol]
- foreign_id_column: str

#### Methods

##### `save() -> None:`

Persists the relation to the database. Raises UsageError if the relation is
incomplete.

##### `reload() -> BelongsTo:`

Reload the relation from the database. Return self in monad pattern.

##### `query() -> QueryBuilderProtocol | None:`

Creates the base query for the underlying relation.

##### `create_property() -> property:`

Creates a property that can be used to set relation properties on models. Sets
the relevant post-init hook to set up the relation on newly created models.
Setting the secondary property on the instance will raise a TypeError if the
precondition check fails.

### `BelongsToMany(Relation)`

Class for the relation where each primary can have many secondary and each
secondary can have many primary; e.g. users and roles, or roles and permissions.
This requires the use of a pivot.

#### Annotations

- primary_class: Type[ModelProtocol]
- secondary_class: Type[ModelProtocol]
- primary_to_add: ModelProtocol
- primary_to_remove: ModelProtocol
- secondary_to_add: list[ModelProtocol]
- secondary_to_remove: list[ModelProtocol]
- primary: ModelProtocol
- secondary: ModelProtocol | tuple[ModelProtocol]
- _primary: Optional[ModelProtocol]
- _secondary: Optional[ModelProtocol]
- pivot: Type[ModelProtocol]
- primary_id_column: str
- secondary_id_column: str

#### Properties

- secondary: The secondary model instances. Setting raises TypeError if a
precondition check fails.
- pivot

#### Methods

##### `__init__(pivot: Type[ModelProtocol], primary_id_column: str, secondary_id_column: str) -> None:`

Set the pivot and query_builder_pivot attributes, then let the Relation class
handle the rest. Raises TypeError if either primary_id_column or
secondary_id_column is not a str.

##### `save() -> None:`

Save the relation by setting/unsetting the relevant database value(s). Raises
UsageError if the relation is incomplete.

##### `reload() -> BelongsToMany:`

Reload the relation from the database. Return self in monad pattern.

##### `query() -> QueryBuilderProtocol | None:`

Creates the base query for the underlying relation. This will return the query
for a join between the pivot and the related model.

##### `get_cache_key() -> str:`

Returns the cache key for this relation.

##### `create_property() -> property:`

Creates a property that can be used to set relation properties on models. Sets
the relevant post-init hook to set up the relation on newly created models.
Setting the secondary property on the instance will raise a TypeError if the
precondition check fails.

### `Contains(HasMany)`

Class for encoding a relationship in which a model contains the ID(s) for other
models within a column: primary.data[foreign_id_column] = ",".join(sorted([
s.data[id_column] for s in secondary])). Useful for DAGs using HashedModel or
something similar. IDs are sorted for deterministic hashing via HashedModel.

#### Annotations

- primary_class: Type[ModelProtocol]
- secondary_class: Type[ModelProtocol]
- primary_to_add: ModelProtocol
- primary_to_remove: ModelProtocol
- secondary_to_add: list[ModelProtocol]
- secondary_to_remove: list[ModelProtocol]
- primary: ModelProtocol
- secondary: tuple[ModelProtocol]
- _primary: Optional[ModelProtocol]
- _secondary: tuple[ModelProtocol]
- foreign_id_column: str

#### Methods

##### `save() -> None:`

Persists the relation to the database. Raises UsageError if the relation is
incomplete.

##### `reload() -> Contains:`

Reload the relation from the database. Return self in monad pattern.

##### `query() -> QueryBuilderProtocol | None:`

Creates the base query for the underlying relation.

##### `create_property() -> property:`

Creates a property that can be used to set relation properties on models. Sets
the relevant post-init hook to set up the relation on newly created models.
Setting the secondary property on the instance will raise a TypeError if the
precondition check fails.

### `Within(HasMany)`

Class for encoding a relationship in which the model's ID is contained within a
column of another model: all([ primary.data[id_column] in
s.data[foreign_id_column] for s in secondary]). Useful for DAGs using
HashedModel or something similar. IDs are sorted for deterministic hashing via
HashedModel.

#### Annotations

- primary_class: Type[ModelProtocol]
- secondary_class: Type[ModelProtocol]
- primary_to_add: ModelProtocol
- primary_to_remove: ModelProtocol
- secondary_to_add: list[ModelProtocol]
- secondary_to_remove: list[ModelProtocol]
- primary: ModelProtocol
- secondary: tuple[ModelProtocol]
- _primary: Optional[ModelProtocol]
- _secondary: Optional[ModelProtocol]
- foreign_id_column: str

#### Methods

##### `save() -> None:`

Persists the relation to the database. Raises UsageError if the relation is
incomplete.

##### `reload() -> Within:`

Reload the relation from the database. Return self in monad pattern.

##### `query() -> QueryBuilderProtocol | None:`

Creates the base query for the underlying relation (i.e. to query the secondary
class).

##### `create_property() -> property:`

Creates a property that can be used to set relation properties on models. Sets
the relevant post-init hook to set up the relation on newly created models.
Setting the secondary property on the instance will raise a TypeError if the
precondition check fails.

### `Column`

Column class for creating migrations.

#### Annotations

- name: str
- datatype: str
- table: TableProtocol
- is_nullable: bool
- new_name: str

#### Methods

##### `__init__(name: str, datatype: str, table: TableProtocol, is_nullable: bool = True, new_name: str = None):`

##### `__repr__():`

##### `__eq__():`

##### `validate() -> None:`

Validate the Column name. Raises TypeError or ValueError if the column name is
invalid.

##### `not_null() -> Column:`

Marks the column as not nullable.

##### `nullable() -> Column:`

Marks the column as nullable.

##### `index() -> Column:`

Creates an index on the column.

##### `unique() -> Column:`

Creates an unique index on the column.

##### `drop() -> Column:`

Drops the column.

##### `rename(new_name: str) -> Column:`

Marks the column as needing to be renamed.

### `Table`

Table class for creating migrations.

#### Annotations

- name: str
- new_name: str
- columns_to_add: list[Column]
- columns_to_drop: list[Column | str]
- columns_to_rename: list[Column | list[str]]
- indices_to_add: list[list[Column | str]]
- indices_to_drop: list[list[Column | str]]
- uniques_to_add: list[list[Column | str]]
- uniques_to_drop: list[list[Column | str]]
- is_create: bool
- is_drop: bool
- callback: Callable[[list[str]], list[str]]

#### Methods

##### `__init__(name: str, new_name: str = None, columns_to_add: list[Column] = <factory>, columns_to_drop: list[Column | str] = <factory>, columns_to_rename: list[Column | list[str]] = <factory>, indices_to_add: list[list[Column | str]] = <factory>, indices_to_drop: list[list[Column | str]] = <factory>, uniques_to_add: list[list[Column | str]] = <factory>, uniques_to_drop: list[list[Column | str]] = <factory>, is_create: bool = False, is_drop: bool = False, callback: Callable[[list[str]], list[str]] = <factory>):`

##### `__repr__():`

##### `__eq__():`

##### `@classmethod create(name: str) -> Table:`

For creating a table.

##### `@classmethod alter(name: str) -> Table:`

For altering a table.

##### `@classmethod drop(name: str) -> Table:`

For dropping a table.

##### `rename(name: str) -> Table:`

Rename the table.

##### `index(columns: list[Column | str]) -> Table:`

Create a simple index or a composite index.

##### `drop_index(columns: list[Column | str]) -> Table:`

Drop a simple index or a composite index.

##### `unique(columns: list[Column | str]) -> Table:`

Create a simple unique index or a composite unique index.

##### `drop_unique(columns: list[Column | str]) -> Table:`

Drop a simple unique index or a composite unique index.

##### `drop_column(column: Column | str) -> Table:`

Drop the specified column.

##### `rename_column(column: Column | list[str]) -> Table:`

Rename the specified column.

##### `integer(name: str) -> Column:`

Creates an integer column.

##### `numeric(name: str) -> Column:`

Creates a numeric column.

##### `real(name: str) -> Column:`

Creates a real column.

##### `text(name: str) -> Column:`

Creates a text column.

##### `blob(name: str) -> Column:`

Creates a blob column.

##### `custom(callback: Callable[[list[str]], list[str]]) -> Table:`

Add a custom callback that parses the SQL clauses before they are returnedf from
the `sql` method. Must accept and return list[str]. This is a way to add custom
SQL while still using the migration system. Return self in monad pattern.

##### `sql() -> list[str]:`

Return the SQL for the table structure changes. Raises UsageError if the Table
was used incorrectly. Raises TypeError or ValueError if a Column fails
validation.

### `Migration`

Migration class for updating a database schema.

#### Annotations

- connection_info: str
- context_manager: Type[DBContextProtocol]
- up_callbacks: list[Callable[[], list[TableProtocol]]]
- down_callbacks: list[Callable[[], list[TableProtocol]]]

#### Methods

##### `__init__(connection_info: str = '', context_manager: Type[DBContextProtocol] = SqliteContext, up_callbacks: list[Callable[[], list[TableProtocol]]] = <factory>, down_callbacks: list[Callable[[], list[TableProtocol]]] = <factory>):`

##### `__repr__():`

##### `__eq__():`

##### `up(callback: Callable[[], list[TableProtocol]]) -> None:`

Specify the forward migration. May be called multiple times for multi-step
migrations.

##### `down(callback: Callable[[], list[TableProtocol]]) -> None:`

Specify the backward migration. May be called multiple times for multi-step
migrations.

##### `get_apply_sql() -> str:`

Get the SQL for the forward migration. Note that this will call all registered
callbacks and may result in unexpected behavior.

##### `apply() -> None:`

Apply the forward migration.

##### `get_undo_sql() -> str:`

Get the SQL for the backward migration. Note that this will call all registered
callbacks and may result in unexpected behavior.

##### `undo() -> None:`

Apply the backward migration.

## Functions

### `dynamic_sqlmodel(connection_string: str | bytes, table_name: str = '', column_names: tuple[str] = ()) -> Type[SqlModel]:`

Generates a dynamic sqlite model for instantiating context managers. Raises
TypeError for invalid connection_string or table_name.

### `has_one(cls: Type[ModelProtocol], owned_model: Type[ModelProtocol], foreign_id_column: str = None) -> property:`

Creates a HasOne relation and returns the result of create_property. Usage
syntax is like `User.avatar = has_one( User, Avatar)`. If the foreign id column
on the Avatar.table table is not user_id (cls.__name__ PascalCase -> snake_case
+ "_id"), then it can be specified.

### `has_many(cls: Type[ModelProtocol], owned_model: Type[ModelProtocol], foreign_id_column: str = None) -> property:`

Creates a HasMany relation and returns the result of create_property. Usage
syntax is like `User.posts = has_many( User, Post)`. If the foreign id column on
the Post.table table is not user_id (cls.__name__ PascalCase -> snake_case +
"_id"), then it can be specified.

### `belongs_to(cls: Type[ModelProtocol], owner_model: Type[ModelProtocol], foreign_id_column: str = None) -> property:`

Creates a BelongsTo relation and returns the result of create_property. Usage
syntax is like `Post.owner = belongs_to( Post, User)`. If the foreign id column
on the Post.table table is not user_id (cls.__name__ PascalCase -> snake_case +
"_id"), then it can be specified.

### `belongs_to_many(cls: Type[ModelProtocol], other_model: Type[ModelProtocol], pivot: Type[ModelProtocol], primary_id_column: str = None, secondary_id_column: str = None) -> property:`

Creates a BelongsToMany relation and returns the result of create_property.
Usage syntax is like `User.liked_posts = belongs_to_many(User, Post, LikedPost)`.
If the foreign id columns on LikedPost are not user_id and post_id (cls.__name__
or other_model.__name__ PascalCase -> snake_case + "_id"), then they can be
specified.

### `contains(cls: Type[ModelProtocol], other_model: Type[ModelProtocol], foreign_ids_column: str = None) -> property:`

Creates a Contains relation and returns the result of calling create_property.
Usage syntax is like `Item.parents = contains(Item, Item)`. If the column
containing the sorted list of ids is not item_ids (i.e. other_model.__name__ ->
snake_case + '_ids'), it can be specified.

### `within(cls: Type[ModelProtocol], other_model: Type[ModelProtocol], foreign_ids_column: str = None) -> property:`

Creates a Within relation and returns the result of calling create_property.
Usage syntax is like `Item.children = within(Item, Item)`. If the column
containing the sorted list of ids is not item_ids (i.e. cls.__name__ ->
snake_case + '_ids'), it can be specified.

### `get_index_name(table: TableProtocol, columns: list[Column | str], is_unique: bool = False) -> str:`

Generate the name for an index from the table, columns, and type.


