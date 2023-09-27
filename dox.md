# sqloquent

## Classes

### `SqlModel`

General model for mapping a SQL row to an in-memory object.

#### Annotations

- table: str
- id_field: str
- fields: tuple
- query_builder_class: Type[QueryBuilderProtocol]
- data: dict

#### Methods

##### `@staticmethod encode_value(val: Any) -> str:`

Encode a value for hashing.

##### `@classmethod generate_id() -> str:`

Generates and returns a hexadecimal UUID4.

##### `@classmethod find(id: Any) -> Optional[SqlModel]:`

Find a record by its id and return it. Return None if it does not exist.

##### `@classmethod insert(data: dict) -> Optional[SqlModel]:`

Insert a new record to the datastore. Return instance.

##### `@classmethod insert_many(items: list[dict]) -> int:`

Insert a batch of records and return the number of items inserted.

##### `update(updates: dict, conditions: dict = None) -> SqlModel:`

Persist the specified changes to the datastore. Return self in monad pattern.

##### `save() -> SqlModel:`

Persist to the datastore. Return self in monad pattern.

##### `delete() -> None:`

Delete the record.

##### `reload() -> SqlModel:`

Reload values from datastore. Return self in monad pattern.

##### `@classmethod query(conditions: dict = None) -> QueryBuilderProtocol:`

Returns a query builder with any conditions provided.

### `SqlQueryBuilder`

Main query builder class. Extend with child class to bind to a specific
database, c.f. SqliteQueryBuilder.

#### Annotations

- model: Type[SqlModel]
- context_manager: Type[DBContextProtocol]
- clauses: list
- params: list
- order_field: str
- order_dir: str
- limit: int
- offset: int
- joins: list[JoinSpec]
- columns: list[str]
- grouping: str

#### Properties

- model: The model type that non-joined query results will be.

#### Methods

##### `equal(field: str, data: Any) -> SqlQueryBuilder:`

Save the 'field = data' clause and param, then return self.

##### `not_equal(field: str, data: Any) -> SqlQueryBuilder:`

Save the 'field != data' clause and param, then return self.

##### `less(field: str, data: Any) -> SqlQueryBuilder:`

Save the 'field < data' clause and param, then return self.

##### `greater(field: str, data: Any) -> SqlQueryBuilder:`

Save the 'field > data' clause and param, then return self.

##### `starts_with(field: str, data: str) -> SqlQueryBuilder:`

Save the 'field like data%' clause and param, then return self.

##### `contains(field: str, data: str) -> SqlQueryBuilder:`

Save the 'field like %data%' clause and param, then return self.

##### `excludes(field: str, data: str) -> SqlQueryBuilder:`

Save the 'field not like %data%' clause and param, then return self.

##### `ends_with(field: str, data: str) -> SqlQueryBuilder:`

Save the 'field like %data' clause and param, then return self.

##### `is_in(field: str, data: Union[tuple, list]) -> SqlQueryBuilder:`

Save the 'field in data' clause and param, then return self.

##### `not_in(field: str, data: Union[tuple, list]) -> SqlQueryBuilder:`

Save the 'field not in data' clause and param, then return self.

##### `order_by(field: str, direction: str = 'desc') -> SqlQueryBuilder:`

Sets query order.

##### `skip(offset: int) -> SqlQueryBuilder:`

Sets the number of rows to skip.

##### `reset() -> SqlQueryBuilder:`

Returns a fresh instance using the configured model.

##### `insert(data: dict) -> Optional[SqlModel]:`

Insert a record and return a model instance.

##### `insert_many(items: list[dict]) -> int:`

Insert a batch of records and return the number inserted.

##### `find(id: Any) -> Optional[SqlModel]:`

Find a record by its id and return it.

##### `join(model: Type[SqlModel] | list[Type[SqlModel]], on: list[str], kind: str = 'inner') -> SqlQueryBuilder:`

Prepares the query for a join over multiple tables/models.

##### `select(columns: list[str]) -> QueryBuilderProtocol:`

Sets the columns to select.

##### `group(by: str) -> SqlQueryBuilder:`

Adds a GROUP BY constraint.

##### `get() -> list[SqlModel | JoinedModel | Row]:`

Run the query on the datastore and return a list of results.

##### `count() -> int:`

Returns the number of records matching the query.

##### `take(limit: int) -> Optional[list[SqlModel]]:`

Takes the specified number of rows.

##### `chunk(number: int) -> Generator[list[SqlModel], None, None]:`

Chunk all matching rows the specified number of rows at a time.

##### `first() -> Optional[SqlModel]:`

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

### `SqliteContext`

Context manager for sqlite.

#### Annotations

- connection: sqlite3.Connection
- cursor: sqlite3.Cursor

### `SqliteModel(SqlModel)`

Model for interacting with sqlite database.

#### Annotations

- file_path: str

### `SqliteQueryBuilder(SqlQueryBuilder)`

SqlQueryBuilder using a SqliteContext.

### `DeletedModel(SqlModel)`

Model for preserving and restoring deleted HashedModel records.

#### Annotations

- table: str
- fields: tuple

#### Methods

##### `restore() -> SqlModel:`

Restore a deleted record, remove from deleted_records, and return the restored
model.

### `HashedModel(SqlModel)`

Model for interacting with sqlite database using hash for id.

#### Annotations

- table: str
- fields: tuple

#### Methods

##### `@classmethod generate_id(data: dict) -> str:`

Generate an ID by hashing the non-ID contents.

##### `@classmethod insert(data: dict) -> Optional[HashedModel]:`

Insert a new record to the datastore. Return instance.

##### `@classmethod insert_many(items: list[dict]) -> int:`

Insert a batch of records and return the number of items inserted.

##### `update(updates: dict) -> HashedModel:`

Persist the specified changes to the datastore, creating a new record in the
process. Return new record in monad pattern.

##### `delete() -> DeletedModel:`

Delete the model, putting it in the deleted_records table, then return the
DeletedModel.

### `Attachment(HashedModel)`

Class for attaching immutable json data to a record.

#### Annotations

- table: str
- fields: tuple
- _related: SqlModel
- _details: dict

#### Methods

##### `related(reload: bool = False) -> SqlModel:`

Return the related record.

##### `attach_to(related: SqlModel) -> Attachment:`

Attach to related model then return self.

##### `details(reload: bool = False) -> dict:`

Decode json str to dict.

##### `set_details(details: dict = {}) -> Attachment:`

Set the details field using either a supplied dict or by encoding the
self._details dict to json. Return self in monad pattern.

##### `@classmethod insert(data: dict) -> Optional[Attachment]:`

Redefined for better LSP support.

### `Row(SqlModel)`

Class for representing a row from a query when no better model exists.

#### Annotations

- table: str
- data: dict

### `JoinedModel`

Class for representing the results of SQL JOIN queries.

#### Annotations

- models: list[Type[SqlModel]]
- data: dict

#### Methods

##### `@staticmethod parse_data(models: list[Type[SqlModel]], data: dict) -> dict:`

Parse data of form {table.column:value} to {table:{column:value}}.

##### `get_models() -> list[SqlModel]:`

Returns the underlying models.

### `JoinSpec`

Class for representing joins to be executed by a query builder.

#### Annotations

- kind: str
- model_1: SqlModel
- column_1: str
- comparison: str
- model_2: SqlModel
- column_2: str

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
- id_field: Str with the name of the id field.
- fields: Tuple of str field names.
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

### `QueryBuilderProtocol(Protocol)`

Interface showing how a query builder should function.

#### Properties

- model: The class of the relevant model.

#### Methods

##### `equal(field: str, data: str) -> QueryBuilderProtocol:`

Save the 'field = data' clause and param, then return self.

##### `not_equal(field: str, data: Any) -> QueryBuilderProtocol:`

Save the 'field != data' clause and param, then return self.

##### `less(field: str, data: str) -> QueryBuilderProtocol:`

Save the 'field < data' clause and param, then return self.

##### `greater(field: str, data: str) -> QueryBuilderProtocol:`

Save the 'field > data' clause and param, then return self.

##### `starts_with(field: str, data: str) -> QueryBuilderProtocol:`

Save the 'field like data%' clause and param, then return self.

##### `contains(field: str, data: str) -> QueryBuilderProtocol:`

Save the 'field like %data%' clause and param, then return self.

##### `excludes(field: str, data: str) -> QueryBuilderProtocol:`

Save the 'field not like %data%' clause and param, then return self.

##### `ends_with(field: str, data: str) -> QueryBuilderProtocol:`

Save the 'field like %data' clause and param, then return self.

##### `is_in(field: str, data: Union[tuple, list]) -> QueryBuilderProtocol:`

Save the 'field in data' clause and param, then return self.

##### `order_by(field: str, direction: str = 'desc') -> QueryBuilderProtocol:`

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

##### `get() -> list[ModelProtocol | JoinedModelProtocol | RowProtocol]:`

Run the query on the datastore and return a list of results.

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

##### `@staticmethod pivot_preconditions(pivot: type[ModelProtocol]) -> None:`

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

### `Relation`

Base class for setting up relations.

#### Annotations

- primary_class: type[ModelProtocol]
- secondary_class: type[ModelProtocol]
- primary_to_add: ModelProtocol
- primary_to_remove: ModelProtocol
- secondary_to_add: list[ModelProtocol]
- secondary_to_remove: list[ModelProtocol]
- primary: ModelProtocol
- secondary: ModelProtocol | tuple[ModelProtocol]
- inverse: Optional[Relation | list[Relation]]
- _primary: Optional[ModelProtocol]
- _secondary: Optional[ModelProtocol]

#### Properties

- primary
- secondary

#### Methods

##### `@staticmethod single_model_precondition() -> None:`

##### `@staticmethod multi_model_precondition() -> None:`

##### `primary_model_precondition(primary: ModelProtocol) -> None:`

##### `secondary_model_precondition(secondary: ModelProtocol) -> None:`

##### `@staticmethod pivot_preconditions(pivot: type[ModelProtocol]) -> None:`

##### `save() -> None:`

Save the relation by setting/unsetting the relevant database values and unset
the following attributes: primary_to_add, primary_to_remove, secondary_to_add,
and secondary_to_remove.

##### `reload() -> Relation:`

Reload the relation from the database. Return self in monad pattern.

##### `get_cache_key() -> str:`

##### `create_property() -> property:`

### `HasOne(Relation)`

Class for the relation where primary owns a secondary: primary.data[id_field] =
secondary.data[foreign_id_field]. An inverse of BelongsTo. An instance of this
class is set on the owner model.

#### Annotations

- foreign_id_field: str

#### Properties

- secondary

#### Methods

##### `save() -> None:`

Save the relation by setting/unsetting the relevant database values and unset
the following attributes: primary_to_add, primary_to_remove, secondary_to_add,
and secondary_to_remove.

##### `reload() -> HasOne:`

Reload the relation from the database. Return self in monad pattern.

##### `get_cache_key() -> str:`

##### `create_property() -> property:`

Creates a property that can be used to set relation properties on models.

### `HasMany(HasOne)`

Class for the relation where primary owns multiple secondary models:
model.data[foreign_id_field] = primary.data[id_field] for model in secondary.
The other inverse of BelongsTo. An instance of this class is set on the owner
model.

#### Properties

- secondary

#### Methods

##### `save() -> None:`

Save the relation by setting the relevant database value(s).

##### `reload() -> HasMany:`

Reload the relation from the database. Return self in monad pattern.

##### `query() -> QueryBuilderProtocol | None:`

Creates the base query for the underlying relation.

##### `create_property() -> property:`

Creates a property that can be used to set relation properties on models.

### `BelongsTo(HasOne)`

Class for the relation where primary belongs to a secondary:
primary.data[foreign_id_field] = secondary.data[id_field]. Inverse of HasOne and
HasMany. An instance of this class is set on the owned model.

#### Methods

##### `save() -> None:`

##### `reload() -> BelongsTo:`

Reload the relation from the database. Return self in monad pattern.

##### `create_property() -> property:`

Creates a property that can be used to set relation properties on models.

### `BelongsToMany(Relation)`

Class for the relation where each primary can have many secondary and each
secondary can have many primary; e.g. users and roles, or roles and permissions.
This requires the use of a pivot.

#### Annotations

- pivot: type[ModelProtocol]
- primary_id_field: str
- secondary_id_field: str

#### Properties

- secondary
- pivot

#### Methods

##### `save() -> None:`

Save the relation by setting/unsetting the relevant database value(s).

##### `reload() -> BelongsToMany:`

Reload the relation from the database. Return self in monad pattern.

##### `get_cache_key() -> str:`

##### `create_property() -> property:`

Creates a property that can be used to set relation properties on models.

### `Column`

Column(name: 'str', datatype: 'str', table: 'TableProtocol', is_nullable: 'bool'
= True, new_name: 'str' = None)

#### Annotations

- name: str
- datatype: str
- table: TableProtocol
- is_nullable: bool
- new_name: str

#### Methods

##### `validate() -> None:`

##### `not_null() -> Column:`

##### `nullable() -> Column:`

##### `index() -> Column:`

##### `unique() -> Column:`

##### `drop() -> Column:`

##### `rename(new_name: str) -> Column:`

### `Table`

Table(name: 'str', new_name: 'str' = None, columns_to_add: 'list[Column]' =
<factory>, columns_to_drop: 'list[Column | str]' = <factory>, columns_to_rename:
'list[Column | list[str]]' = <factory>, indices_to_add: 'list[list[Column |
str]]' = <factory>, indices_to_drop: 'list[list[Column | str]]' = <factory>,
uniques_to_add: 'list[list[Column | str]]' = <factory>, uniques_to_drop:
'list[list[Column | str]]' = <factory>, is_create: 'bool' = False, is_drop:
'bool' = False)

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

#### Methods

##### `@classmethod create(name: str) -> Table:`

##### `@classmethod alter(name: str) -> Table:`

##### `@classmethod drop(name: str) -> Table:`

##### `rename(name: str) -> Table:`

Rename the table.

##### `index(columns: list[Column | str]) -> Table:`

##### `drop_index(columns: list[Column | str]) -> Table:`

##### `unique(columns: list[Column | str]) -> Table:`

##### `drop_unique(columns: list[Column | str]) -> Table:`

##### `drop_column(column: Column | str) -> Table:`

##### `rename_column(column: Column | list[str]) -> Table:`

##### `integer(name: str) -> Column:`

##### `numeric(name: str) -> Column:`

##### `real(name: str) -> Column:`

##### `text(name: str) -> Column:`

##### `blob(name: str) -> Column:`

##### `sql() -> list[str]:`

Return the SQL clauses to be run.

### `Migration`

Migration(connection_info: 'str' = '', model_factory: 'Callable[[Any],
ModelProtocol]' = <function dynamic_sqlite_model at 0x7f8f49181ea0>,
context_manager: 'type[DBContextProtocol]' = <class
'sqloquent.classes.SqliteContext'>, up_callbacks: 'list[Callable[[],
list[TableProtocol]]]' = <factory>, down_callbacks: 'list[Callable[[],
list[TableProtocol]]]' = <factory>)

#### Annotations

- connection_info: str
- model_factory: Callable[[Any], ModelProtocol]
- context_manager: type[DBContextProtocol]
- up_callbacks: list[Callable[[], list[TableProtocol]]]
- down_callbacks: list[Callable[[], list[TableProtocol]]]

#### Methods

##### `dynamic_sqlite_model(db_file_path: str, table_name: str = '') -> type[SqlModel]:`

Generates a dynamic sqlite model for instantiating context managers.

##### `up(callback: Callable[[], list[TableProtocol]]) -> None:`

Specify the forward migration. May be called multiple times for multi-step
migrations.

##### `down(callback: Callable[[], list[TableProtocol]]) -> None:`

Specify the backward migration. May be called multiple times for multi-step
migrations.

##### `get_apply_sql() -> str:`

Get the SQL for the forward migration. Note that this may call all registered
callbacks and result in unexpected behavior.

##### `apply() -> None:`

Apply the forward migration.

##### `get_undo_sql() -> str:`

Get the SQL for the backward migration. Note that this may call all registered
callbacks and result in unexpected behavior.

##### `undo() -> None:`

Apply the backward migration.

## Functions

### `dynamic_sqlite_model(db_file_path: str, table_name: str = '') -> type[SqlModel]:`

Generates a dynamic sqlite model for instantiating context managers.

### `has_one(cls: type[ModelProtocol], owned_model: type[ModelProtocol], foreign_id_field: str = None) -> property:`

### `has_many(cls: type[ModelProtocol], owned_model: type[ModelProtocol], foreign_id_field: str = None) -> property:`

### `belongs_to(cls: type[ModelProtocol], owner_model: type[ModelProtocol], foreign_id_field: str = None, inverse_is_many: bool = False) -> property:`

### `belongs_to_many(cls: type[ModelProtocol], other_model: type[ModelProtocol], pivot: type[ModelProtocol], primary_id_field: str = None, secondary_id_field: str = None) -> property:`

### `get_index_name(table: TableProtocol, columns: list[Column | str], is_unique: bool = False) -> str:`

Generate the name for an index from the table, columns, and type.


