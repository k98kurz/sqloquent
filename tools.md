# sqloquent.tools

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

#### Methods

##### `@staticmethod create_property() -> property:`

Create a dynamic property for the column with the given name.

##### `@staticmethod encode_value(val: Any) -> str:`

Encode a value for hashing. Uses the pack function from packify.

##### `@classmethod generate_id() -> str:`

Generates and returns a hexadecimal UUID4.

##### `@classmethod find(id: Any) -> Optional[SqlModel]:`

Find a record by its id and return it. Return None if it does not exist.

##### `@classmethod insert(data: dict) -> Optional[SqlModel]:`

Insert a new record to the datastore. Return instance. Raises TypeError if data
is not a dict.

##### `@classmethod insert_many(items: list[dict]) -> int:`

Insert a batch of records and return the number of items inserted. Raises
TypeError if items is not list[dict].

##### `update(updates: dict, conditions: dict = None) -> SqlModel:`

Persist the specified changes to the datastore. Return self in monad pattern.
Raises TypeError or ValueError for invalid updates or conditions (self.data must
include the id to update or conditions must be specified).

##### `save() -> SqlModel:`

Persist to the datastore. Return self in monad pattern. Calls insert or update
and raises appropriate errors.

##### `delete() -> None:`

Delete the record.

##### `reload() -> SqlModel:`

Reload values from datastore. Return self in monad pattern. Raises UsageError if
id is not set in self.data.

##### `@classmethod query(conditions: dict = None, connection_info: str = None) -> QueryBuilderProtocol:`

Returns a query builder with any conditions provided. Conditions are parsed as
key=value and cannot handle other comparison types. If connection_info is not
injected and was added as a class attribute, that class attribute will be passed
to the query_builder_class instead.

### `HashedModel(SqlModel)`

Model for interacting with sql database using hash for id.

#### Annotations

- table: str
- columns: tuple
- id: str
- details: bytes

#### Methods

##### `@classmethod generate_id(data: dict) -> str:`

Generate an id by hashing the non-id contents. Raises TypeError for unencodable
type (calls packify.pack).

##### `@classmethod insert(data: dict) -> Optional[HashedModel]:`

Insert a new record to the datastore. Return instance. Raises TypeError for
non-dict data or unencodable type (calls cls.generate_id, which calls
packify.pack).

##### `@classmethod insert_many(items: list[dict]) -> int:`

Insert a batch of records and return the number of items inserted. Raises
TypeError for invalid items or unencodable value (calls cls.generate_id, which
calls packify.pack).

##### `update(updates: dict) -> HashedModel:`

Persist the specified changes to the datastore, creating a new record in the
process. Return new record in monad pattern. Raises TypeError or ValueError for
invalid updates.

##### `delete() -> DeletedModel:`

Delete the model, putting it in the deleted_records table, then return the
DeletedModel. Raises packify.UsageError for unserializable data.

## Functions

### `make_migration_create(name: str, connection_string: str = '') -> str:`

Generate a migration scaffold from a table name to create a table.

### `make_migration_alter(name: str, connection_string: str = '') -> str:`

Generate a migration scaffold from a table name to alter a table.

### `make_migration_drop(name: str, connection_string: str = '') -> str:`

Generate a migration scaffold from a table name to drop a table.

### `make_migration_from_model(model_name: str, model_path: str, connection_string: str = '') -> str:`

Generate a migration scaffold from a model.

### `publish_migrations(path: str, connection_string: str = ''):`

Publish the migrations for the DeletedModel and Attachment.

### `make_model(name: str, base: str = 'SqlModel', columns: list = None, connection_string: str = '') -> str:`

Generate a model scaffold with the given name.

### `migrate(path: str, connection_string: str = ''):`

Load and apply the specified migration.

### `rollback(path: str, connection_string: str = ''):`

Load and rollback the specified migration.

### `refresh(path: str, connection_string: str = ''):`

Rollback and apply the specified migration.

### `examine(path: str) -> list[str]:`

Examine the generated SQL from a migration.

### `automigrate(path: str, connection_string: str = ''):`

Enumerate the python files at the path, then connect to the db to read out the
migrations table (creating it if it does not exist), then apply the migrations
that have not been applied and add a record to the migrations table for each.

### `autorollback(path: str, connection_string: str = '', all: bool = False):`

Enumerate the python files at the path, then connect to the db to read out the
migrations table (creating it if it does not exist), then rollback the previous
batch of migrations that were applied and remove the records from the migrations
table for each.

### `autorefresh(path: str, connection_string: str = ''):`

Rollback all migrations then apply all migrations in the folder at path.

### `help_cli(name: str) -> str:`

Return the help string for the CLI tool.

### `run_cli():`

Run the CLI tool.


