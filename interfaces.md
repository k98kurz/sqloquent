# sqloquent.interfaces

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

### `ModelProtocol(Protocol)`

Interface showing how a model should function.

#### Properties

- table: Str with the name of the table.
- id_column: Str with the name of the id column.
- columns: Tuple of str column names.
- data: Dict for storing model data.

#### Methods

##### `@classmethod find(id: Any) -> Optional[ModelProtocol]:`

Find a record by its id and return it. Return None if it does not exist.

##### `@classmethod insert(data: dict) -> Optional[ModelProtocol]:`

Insert a new record to the datastore. Return instance.

##### `@classmethod insert_many(items: list[dict]) -> int:`

Insert a batch of records and return the number of items inserted.

##### `update(updates: dict, conditions: dict = None) -> ModelProtocol:`

Persist the specified changes to the datastore. Return self in monad pattern.

##### `save() -> ModelProtocol:`

Persist to the datastore. Return self in monad pattern.

##### `delete() -> None:`

Delete the record.

##### `reload() -> ModelProtocol:`

Reload values from datastore. Return self in monad pattern.

##### `@classmethod query(conditions: dict = None) -> QueryBuilderProtocol:`

Return a QueryBuilderProtocol for the model.

### `JoinedModelProtocol(Protocol)`

Interface for representations of JOIN query results.

#### Properties

- data: Dict for storing models data.

#### Methods

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

- model: The class of the relevant model.

#### Methods

##### `equal(column: str, data: str) -> QueryBuilderProtocol:`

Save the 'column = data' clause and param, then return self.

##### `not_equal(column: str, data: Any) -> QueryBuilderProtocol:`

Save the 'column != data' clause and param, then return self.

##### `less(column: str, data: str) -> QueryBuilderProtocol:`

Save the 'column < data' clause and param, then return self.

##### `greater(column: str, data: str) -> QueryBuilderProtocol:`

Save the 'column > data' clause and param, then return self.

##### `starts_with(column: str, data: str) -> QueryBuilderProtocol:`

Save the 'column like data%' clause and param, then return self.

##### `contains(column: str, data: str) -> QueryBuilderProtocol:`

Save the 'column like %data%' clause and param, then return self.

##### `excludes(column: str, data: str) -> QueryBuilderProtocol:`

Save the 'column not like %data%' clause and param, then return self.

##### `ends_with(column: str, data: str) -> QueryBuilderProtocol:`

Save the 'column like %data' clause and param, then return self.

##### `is_in(column: str, data: Union[tuple, list]) -> QueryBuilderProtocol:`

Save the 'column in data' clause and param, then return self.

##### `order_by(column: str, direction: str = 'desc') -> QueryBuilderProtocol:`

Sets query order.

##### `skip(offset: int) -> QueryBuilderProtocol:`

Sets the number of rows to skip.

##### `reset() -> QueryBuilderProtocol:`

Returns a fresh instance using the configured model.

##### `insert(data: dict) -> Optional[ModelProtocol]:`

Insert a record and return a model instance.

##### `insert_many(items: list[dict]) -> int:`

Insert a batch of records and return the number inserted.

##### `find(id: str) -> Optional[ModelProtocol]:`

Find a record by its id and return it.

##### `join(model: Type[ModelProtocol] | list[Type[ModelProtocol]], on: list[str], kind: str = 'inner') -> QueryBuilderProtocol:`

Prepares the query for a join over multiple tables/models.

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

##### `take(number: int) -> Optional[list[ModelProtocol]]:`

Takes the specified number of rows.

##### `chunk(number: int) -> Generator[list[ModelProtocol], None, None]:`

Chunk all matching rows the specified number of rows at a time.

##### `first() -> Optional[ModelProtocol]:`

Run the query on the datastore and return the first result.

##### `update(updates: dict, conditions: dict = {}) -> int:`

Update the datastore and return number of records updated.

##### `delete() -> int:`

Delete the records that match the query and return the number of deleted
records.

##### `to_sql() -> str:`

Return the sql where clause from the clauses and params.

##### `execute_raw(sql: str) -> tuple[int, Any]:`

Execute raw SQL against the database. Return rowcount and fetchall results.

### `RelationProtocol(Protocol)`

Interface showing how a relation should function.

#### Properties

- primary: Property that accesses the primary instance.
- secondary: Property that accesses the secondary instance(s).

#### Methods

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

##### `get_cache_key() -> str:`

Get the cache key for the relation.

##### `create_property() -> property:`

Produces a property to be set on a model, allowing it to access the related
model through the relation.

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
For sqlite migrations, this is passed to the model_factory which is in turn
passed to the DBContextManager. For other database bindings, the connection
information should be read from env and injected into the relevant
DBContextManager.

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


