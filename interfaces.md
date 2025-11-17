# sqloquent.interfaces

The interfaces used by the package. `RelatedCollection` and `RelatedModel`
describe the properties created by the ORM. Any custom relations should
implement the `RelationProtocol` and return either `RelatedModel` or
`RelatedCollection` from the `create_property` method. `CursorProtocol` and
`DBContextProtocol` must be implemented to bind the library to a new SQL driver.
`ColumnProtocol`, `TableProtocol`, and `MigrationProtocol` describe the schema
migration system and can be implemented for custom schema migration
functionality, e.g. a new `ColumnProtocol` implementation to handle specific
column types for the database.

## Classes

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
Should also handle connection pooling.

##### `__exit__(exc_type: Optional[Type[BaseException]], exc_value: Optional[BaseException], traceback: Optional[TracebackType]) -> None:`

Exit the `with` block. Should commit or rollback as appropriate, then close the
connection if this is the outermost context.

### `ModelProtocol(Protocol)`

Interface showing how a model should function.

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

### `JoinedModelProtocol(Protocol)`

Interface for representations of JOIN query results.

#### Properties

- data: Dict for storing models data.
- models: List of the underlying model classes.

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

### `QueryBuilderProtocol(Protocol)`

Interface showing how a query builder should function.

#### Properties

- table: The name of the table.
- model: The class of the relevant model.

#### Methods

##### `__init__(model_or_table: Type[ModelProtocol] | str, context_manager: Type[DBContextProtocol], connection_info: str = '', model: Type[ModelProtocol] = None, table: str = None) -> None:`

Initialize the instance. A class implementing ModelProtocol or the str name of a
table must be provided.

##### `is_null(column: str | list[str,] | tuple[str,]) -> QueryBuilderProtocol:`

Save the 'column is null' clause, then return self. Raises TypeError for invalid
column. If a list or tuple is supplied, each element is treated as a separate
clause.

##### `not_null(column: str | list[str,] | tuple[str,]) -> QueryBuilderProtocol:`

Save the 'column is not null' clause, then return self. Raises TypeError for
invalid column. If a list or tuple is supplied, each element is treated as a
separate clause.

##### `equal(column: str, data: str = None, conditions: dict[str, Any] = None) -> QueryBuilderProtocol:`

Save the 'column = data' clause and param, then return self. Raises TypeError
for invalid column. This method can be called with `equal(column, data)` or
`equal(column1=data1, column2=data2, etc=data3)`.

##### `not_equal(column: str, data: Any = None, conditions: dict[str, Any] = None) -> QueryBuilderProtocol:`

Save the 'column != data' clause and param, then return self. Raises TypeError
for invalid column. This method can be called with `not_equal(column, data)` or
`not_equal(column1=data1, column2=data2, etc=data3)`.

##### `less(column: str, data: str = None, conditions: dict[str, Any] = None) -> QueryBuilderProtocol:`

Save the 'column < data' clause and param, then return self. Raises TypeError
for invalid column. This method can be called with `less(column, data)` or
`less(column1=data1, column2=data2, etc=data3)`.

##### `less_or_equal(column: str, data: str = None, conditions: dict[str, Any] = None) -> QueryBuilderProtocol:`

Save the 'column <= data' clause and param, then return self. Raises TypeError
for invalid column. This method can be called with `less_or_equal(column, data)`
or `less_or_equal(column1=data1, column2=data2, etc=data3)`.

##### `greater(column: str, data: str = None, conditions: dict[str, Any] = None) -> QueryBuilderProtocol:`

Save the 'column > data' clause and param, then return self. Raises TypeError
for invalid column. This method can be called with `greater(column, data)` or
`greater(column1=data1, column2=data2, etc=data3)`.

##### `greater_or_equal(column: str, data: str = None, conditions: dict[str, Any] = None) -> QueryBuilderProtocol:`

Save the 'column >= data' clause and param, then return self. Raises TypeError
for invalid column. This method can be called with `greater_or_equal(column, data)`
or `greater_or_equal(column1=data1, column2=data2, etc=data3)`.

##### `like(column: str, pattern: str = None, data: str = None, conditions: dict[str, tuple[str, str]] = None) -> QueryBuilderProtocol:`

Save the 'column like {pattern.replace(?, data)}' clause and param, then return
self. Raises TypeError or ValueError for invalid column, pattern, or data. This
method can be called with `like(column, pattern, data)` or
`like(column1=(pattern1,str1), column2=(pattern2,str2), etc=(pattern3,str3))`.

##### `not_like(column: str, pattern: str = None, data: str = None, conditions: dict[str, tuple[str, str]] = None) -> QueryBuilderProtocol:`

Save the 'column not like {pattern.replace(?, data)}' clause and param, then
return self. Raises TypeError or ValueError for invalid column, pattern, or
data. This method can be called with `not_like(column, pattern, data)` or
`not_like(column1=(pattern1,str1), column2=(pattern2,str2), etc=(pattern3,str3))`.

##### `starts_with(column: str, data: str = None, conditions: dict[str, Any] = None) -> QueryBuilderProtocol:`

Save the 'column like data%' clause and param, then return self. Raises
TypeError or ValueError for invalid column or data. This method can be called
with `starts_with(column, data)` or `starts_with(column1=str1, column2=str2,
etc=str3)`.

##### `does_not_start_with(column: str, data: str = None, conditions: dict[str, Any] = None) -> QueryBuilderProtocol:`

Save the 'column not like data%' clause and param, then return self. Raises
TypeError or ValueError for invalid column or data. This method can be called
with `does_not_start_with(column, data)` or `does_not_start_with(column1=str1,
column2=str2, etc=str3)`.

##### `contains(column: str, data: str = None, conditions: dict[str, Any] = None) -> QueryBuilderProtocol:`

Save the 'column like %data%' clause and param, then return self. Raises
TypeError or ValueError for invalid column or data. This method can be called
with `contains(column, data)` or `contains(column1=str1, column2=str2,
etc=str3)`.

##### `excludes(column: str, data: str = None, conditions: dict[str, Any] = None) -> QueryBuilderProtocol:`

Save the 'column not like %data%' clause and param, then return self. Raises
TypeError or ValueError for invalid column or data. This method can be called
with `excludes(column, data)` or `excludes(column1=str1, column2=str2,
etc=str3)`.

##### `ends_with(column: str, data: str = None, conditions: dict[str, Any] = None) -> QueryBuilderProtocol:`

Save the 'column like %data' clause and param, then return self. Raises
TypeError or ValueError for invalid column or data. This method can be called
with `ends_with(column, data)` or `ends_with(column1=str1, column2=str2,
etc=str3)`.

##### `does_not_end_with(column: str, data: str = None, conditions: dict[str, Any] = None) -> QueryBuilderProtocol:`

Save the 'column like %data' clause and param, then return self. Raises
TypeError or ValueError for invalid column or data. This method can be called
with `does_not_end_with(column, data)` or `does_not_end_with(column1=str1,
column2=str2, etc=str3)`.

##### `is_in(column: str, data: Union[tuple, list] = None, conditions: dict[str, Any] = None) -> QueryBuilderProtocol:`

Save the 'column in data' clause and param, then return self. Raises TypeError
or ValueError for invalid column or data. This method can be called with
`is_in(column, data)` or `is_in(column1=list1, column2=list2, etc=list3)`.

##### `not_in(column: str, data: Union[tuple, list] = None, conditions: dict[str, Any] = None) -> QueryBuilderProtocol:`

Save the 'column not in data' clause and param, then return self. Raises
TypeError or ValueError for invalid column or data. This method can be called
with `not_in(column, data)` or `not_in(column1=list1, column2=list2,
etc=list3)`.

##### `where(conditions: dict[str, dict[str, Any] | list[str]]) -> QueryBuilderProtocol:`

Parse the conditions as if they are sequential calls to the equivalent
SqlQueryBuilder methods. Syntax is as follows: `where(is_null=[column1,...], not_null=[column2,...], equal={'column1':data1, 'column2':data2, 'etc':data3}, not_equal={'column1':data1, 'column2':data2, 'etc':data3}, less={'column1':data1, 'column2':data2, 'etc':data3}, less_or_equal={'column1':data1, 'column2':data2, 'etc':data3}, greater={'column1':data1, 'column2':data2, 'etc':data3}, greater_or_equal={'column1':data1, 'column2':data2, 'etc':data3}, like={'column1':(pattern1,str1), 'column2':(pattern2,str2), 'etc':(pattern3,str3)}, not_like={'column1':(pattern1,str1), 'column2':(pattern2,str2), 'etc':(pattern3,str3)}, starts_with={'column1':str1, 'column2':str2, 'etc':str3}, does_not_start_with={'column1':str1, 'column2':str2, 'etc':str3}, contains={'column1':str1, 'column2':str2, 'etc':str3}, excludes={'column1':str1, 'column2':str2, 'etc':str3}, ends_with={'column1':str1, 'column2':str2, 'etc':str3}, does_not_end_with={'column1':str1, 'column2':str2, 'etc':str3}, is_in={'column1':list1, 'column2':list2, 'etc':list3}, not_in={'column1':list1, 'column2':list2, 'etc':list3})`.
All kwargs are optional.

##### `order_by(column: str, direction: str = None, conditions: dict[str, Any] = 'desc') -> QueryBuilderProtocol:`

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

### `ColumnProtocol(Protocol)`

Interface for a column class (for migrations).

#### Properties

- name: The name of the column.
- is_nullable: Whether or not the column can be null.

#### Methods

##### `validate() -> None:`

Should raise an exception if the column specification is invalid.

##### `not_null() -> ColumnProtocol:`

Disable null values for this column.

##### `nullable() -> ColumnProtocol:`

Enable null values for this column.

##### `index() -> ColumnProtocol:`

Should generate a simple index for this column.

##### `unique() -> ColumnProtocol:`

Should generate a unique index for this column.

##### `drop() -> ColumnProtocol:`

Should drop the column from the table.

##### `rename(new_name: str) -> ColumnProtocol:`

Should rename the column.

### `TableProtocol(Protocol)`

Interface for a table class (for migrations).

#### Properties

- name: The name of the table.

#### Methods

##### `@classmethod create(name: str) -> TableProtocol:`

For creating a table.

##### `@classmethod alter(name: str) -> TableProtocol:`

For altering a table.

##### `@classmethod drop(name: str) -> TableProtocol:`

For dropping a table.

##### `rename(name: str) -> TableProtocol:`

Rename the table.

##### `index(columns: list[ColumnProtocol | str]) -> TableProtocol:`

Create a simple index or a composite index.

##### `drop_index(columns: list[ColumnProtocol | str]) -> TableProtocol:`

Drop a simple index or a composite index.

##### `unique(columns: list[ColumnProtocol | str]) -> TableProtocol:`

Create a simple unique index or a composite unique index.

##### `drop_unique(columns: list[ColumnProtocol | str]) -> TableProtocol:`

Drop a simple unique index or a composite unique index.

##### `drop_column(column: ColumnProtocol | str) -> TableProtocol:`

Drop the specified column.

##### `rename_column(column: ColumnProtocol | list[str]) -> TableProtocol:`

Rename the specified column.

##### `custom(callback: Callable[[list[str]], list[str]]) -> TableProtocol:`

Add a custom callback that parses the SQL clauses before they are returnedf from
the `sql` method. Must accept and return list[str]. This is a way to add custom
SQL while still using the migration system. Return self in monad pattern.

##### `sql() -> list[str]:`

Return the SQL for the table structure changes.

### `MigrationProtocol(Protocol)`

Interface for a migration class.

#### Properties

- connection_info: The connection info used for interacting with the database.
For sqlite migrations, this is passed to the DBContextManager. For other
database bindings, the connection information should be read from env and
injected into the relevant DBContextManager.

#### Methods

##### `up(callback: Callable[[], list[TableProtocol]]) -> None:`

Specify the forward migration. May be called multiple times for multi-step
migrations.

##### `down(callback: Callable[[], list[TableProtocol]]) -> None:`

Specify the backward migration. May be called multiple times for multi-step
migrations.

##### `get_apply_sql() -> None:`

Get the SQL for the forward migration. Note that this may call all registered
callbacks and result in unexpected behavior.

##### `apply() -> None:`

Apply the forward migration.

##### `get_undo_sql() -> None:`

Get the SQL for the backward migration. Note that this may call all registered
callbacks and result in unexpected behavior.

##### `undo() -> None:`

Apply the backward migration.


