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

#### Methods

##### `__hash__() -> int:`

Allow inclusion in sets.

##### `__eq__() -> bool:`

Return True if types and hashes are equal, else False.

##### `@classmethod async find(id: Any) -> Optional[AsyncModelProtocol]:`

Find a record by its id and return it. Return None if it does not exist.

##### `@classmethod async insert(data: dict) -> Optional[AsyncModelProtocol]:`

Insert a new record to the datastore. Return instance.

##### `@classmethod async insert_many(items: list[dict]) -> int:`

Insert a batch of records and return the number of items inserted.

##### `async update(updates: dict, conditions: dict = None) -> AsyncModelProtocol:`

Persist the specified changes to the datastore. Return self in monad pattern.

##### `async save() -> AsyncModelProtocol:`

Persist to the datastore. Return self in monad pattern.

##### `async delete() -> None:`

Delete the record.

##### `async reload() -> AsyncModelProtocol:`

Reload values from datastore. Return self in monad pattern.

##### `@classmethod query(conditions: dict = None) -> AsyncQueryBuilderProtocol:`

Return a AsyncQueryBuilderProtocol for the model.

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


