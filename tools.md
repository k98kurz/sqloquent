# sqloquent.tools

## Functions

### `make_migration_create(name: str, connection_string: str = 'temp.db') -> str:`

Generate a migration scaffold from a table name to create a table.

### `make_migration_alter(name: str, connection_string: str = 'temp.db') -> str:`

Generate a migration scaffold from a table name to alter a table.

### `make_migration_drop(name: str, connection_string: str = 'temp.db') -> str:`

Generate a migration scaffold from a table name to drop a table.

### `make_migration_from_model(model_name: str, model_path: str, connection_string: str = 'temp.db') -> str:`

Generate a migration scaffold from a model.

### `publish_migrations(path: str, connection_string: str = 'temp.db'):`

Publish the migrations for the DeletedModel and Attachment.

### `make_model(name: str, base: str = 'SqliteModel', columns: list = None, connection_string: str = 'temp.db') -> str:`

Generate a model scaffold with the given name.

### `migrate(path: str, connection_string: str = 'temp.db'):`

Load and apply the specified migration.

### `rollback(path: str, connection_string: str = 'temp.db'):`

Load and rollback the specified migration.

### `refresh(path: str, connection_string: str = 'temp.db'):`

Rollback and apply the specified migration.

### `examine(path: str) -> list[str]:`

Examine the generated SQL from a migration.

### `automigrate(path: str, connection_string: str = 'temp.db'):`

Enumerate the python files at the path, then connect to the db to read out the
migrations table (creating it if it does not exist), then apply the migrations
that have not been applied and add a record to the migrations table for each.

### `autorollback(path: str, connection_string: str = 'temp.db', all: bool = False):`

Enumerate the python files at the path, then connect to the db to read out the
migrations table (creating it if it does not exist), then rollback the previous
batch of migrations that were applied and remove the records from the migrations
table for each.

### `autorefresh(path: str, connection_string: str = 'temp.db'):`

Rollback all migrations then apply all migrations in the folder at path.

### `help_cli(name: str) -> str:`

Return the help string for the CLI tool.

### `run_cli():`

Run the CLI tool.


