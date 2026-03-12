# Migrations

Guide to Sqloquent's migration system for managing database schema changes.

## Introduction

The migration system provides a structured way to manage database schema changes
through code using three main classes: `Column`, `Table`, and `Migration`.

It supports both manual migration management and an automatic tracking system
that records applied migrations in a `migrations` table.

## Core Concepts

### Data Types

- `integer`: Integer numbers
- `numeric`: High-precision numeric data
- `real`: Floating-point numbers
- `text`: String data, default values are quoted in SQL
- `blob`: Binary data (bytes), default values are hex-encoded in SQL
- `boolean`: Boolean values

Columns are nullable by default. Use `.not_null()` to enforce non-null values.

Note: The migration system is currently designed for sqlite3. Support for
additional database column types is planned for a future release.

### Column Methods

Chain these methods when defining columns:

- `.not_null()`: Enforce non-null values
- `.nullable()`: Allow null values (default)
- `.default(value)`: Set default value
- `.index()`: Create simple index
- `.unique()`: Create unique index
- `.drop()`: Drop column (alter mode)
- `.rename('new_name')`: Rename column (alter mode)

**Index Naming:**
- Unique indexes: `udx_{table}_{columns}` (e.g., `udx_users_email`)
- Regular indexes: `idx_{table}_{columns}` (e.g., `idx_users_name_email`)

### Table Operations

**Table-level methods:**

- `Table.create(name)` - Create a new table
- `Table.alter(name)` - Alter an existing table
- `Table.drop(name)` - Drop a table
- `Table.alter(name).rename(new_name)` - Rename the table (use only with `alter`)

**Column operations:**

- `t.drop_column(name: str)` - Drop a column
- `t.rename_column(column: Column|list[str])` - Rename a column
    - `t.rename_column(column.rename('new_name'))`
    - `t.rename_column(['old_name', 'new_name'])`
- `t.integer(name)` - Create an integer column
- `t.numeric(name)` - Create a numeric column
- `t.real(name)` - Create a real column
- `t.text(name)` - Create a text column
- `t.blob(name)` - Create a blob column
- `t.boolean(name)` - Create a boolean column

**Index operations:**

- `t.unique([columns])` - Create a unique index (single or composite)
- `t.index([columns])` - Create a simple index (single or composite)
- `t.drop_unique([columns])` - Drop a unique index
- `t.drop_index([columns])` - Drop a simple index

**SQL:**

- `t.custom(callback)` - Add custom SQL via callback that receives and returns `list[str]`
- `t.sql()` - Returns SQL for the table structure changes

## CLI Usage

### Migration Scaffolds

```bash
# Create scaffolding
sqloquent make migration --create Thing      # Create table
sqloquent make migration --alter Thing       # Alter table
sqloquent make migration --drop Thing        # Drop table
sqloquent make migration --model Thing path/to/model.py  # From model

# With custom database context (for custom databases)
sqloquent make migration --create Thing --ctx CustomContext --from mydbpackage
```

The `--ctx` parameter specifies a custom `DBContextProtocol` implementation.
When used with `--from`, it imports the context from the specified package. This
generates migrations using your custom database context instead of the default
`SqliteContext`.

Additionally, there is a command for publishing the migrations associated with
built-in models (HashedRecord, Attachment, and DeletedRecord):

```bash
sqloquent publish path/to/migrations/folder [--ctx name [--from package_name]]
```

### Manual Migration Commands

```bash
sqloquent migrate path/to/migration.py       # Apply single migration
sqloquent rollback path/to/migration.py      # Rollback single migration
sqloquent refresh path/to/migration.py     # Rollback + apply
sqloquent examine path/to/migration.py     # Preview SQL
```

### Automatic Migration System

The automatic system tracks applied migrations in a `migrations` table:

| Column  | Type          | Description                                  |
|---------|---------------|----------------------------------------------|
| `id`    | text (unique) | Migration filename                           |
| `batch` | integer       | Batch number (incremented per `automigrate`) |
| `date`  | text          | Timestamp when applied                       |

**Commands:**
```bash
sqloquent automigrate path/to/migrations/folder      # Apply all pending
sqloquent autorollback path/to/migrations/folder     # Rollback last batch
sqloquent autorefresh path/to/migrations/folder      # Rollback all, reapply
```

Migrations are applied alphabetically. Each `automigrate` creates a new batch;
`autorollback` reverses the most recent batch in reverse order.

### Environment Variables

- `CONNECTION_STRING`: Database connection string (e.g., `path/to/db.db`)
- `MAKE_WITH_CONNSTRING`: When set (not "false" or "0"), embeds connection
string in generated scaffolds

## Generating from Models

The system parses model type annotations to generate migrations.

**Supported Annotations:**
- Basic: `str`, `int`, `bool`, `float`, `bytes`
- Nullable: `str|None`, `int|None`, etc.
- Defaults: `str|Default[value]`, `int|Default[0]`, `bool|Default[True]`
- Combined: `str|None|Default[value]`

**Index Creation:**
- `id` column gets a unique index
- All other columns get simple, per-column indices

**Example:**
```python
from sqloquent import SqlModel, Default

class Product(SqlModel):
    table = 'products'
    columns = ('id', 'name', 'price', 'in_stock', 'description')
    id: str
    name: str|Default['Unnamed Product']
    price: float
    in_stock: bool|Default[True]
    description: str|None
```

```bash
sqloquent make migration --model Product models.py
```

**Publish Built-in Migrations:**
```python
from sqloquent.tools import publish_migrations
publish_migrations('./migrations', connection_string='mydb.db')
# Creates: deleted_model_migration.py, hashed_model_migration.py, attachment_migration.py

# With custom context
publish_migrations(
    './migrations', connection_string='mydb.db',
    ctx=('CustomContext', 'mydbpackage')
)
```

## Examples

### Example 1: Basic Migration File

Every migration file must export a `migration()` function returning a `Migration`
instance. The connection string can be: (1) hardcoded, (2) from `CONNECTION_STRING`
env var, or (3) injected by CLI tools.

```python
from sqloquent import Migration, Table

def up():
    t = Table.create('tasks')
    t.text('id').unique()
    t.text('title').not_null()
    t.text('tags').nullable().index()
    t.boolean('completed').default(False)
    return [t]

def down():
    return [Table.drop('tasks')]

def migration(connection_string: str = 'tasks.db') -> Migration:
    m = Migration(connection_string)
    m.up(up)
    m.down(down)
    return m
```

- Apply: `sqloquent migrate 001_create_tasks.py`
- Rollback: `sqloquent rollback 001_create_tasks.py`

### Example 2: Alter Table + Automatic Migrations

```python
# 002_add_avatar.py
from sqloquent import Migration, Table

def up():
    t = Table.alter('users')
    t.text('avatar_url').nullable().index()
    return [t]

def down():
    t = Table.alter('users')
    t.drop_index(['avatar_url'])
    t.drop_column('avatar_url')
    return [t]

def migration(connection_string: str = 'app.db') -> Migration:
    m = Migration(connection_string)
    m.up(up)
    m.down(down)
    return m
```

```bash
# Apply all pending migrations in folder
sqloquent automigrate ./migrations

# Rollback last batch
sqloquent autorollback ./migrations
```

### Example 3: Custom SQL (Foreign Key)

```python
from sqloquent import Migration, Table

def add_fk(clauses):
    clauses.append(
        'ALTER TABLE comments ADD CONSTRAINT fk_user '
        'FOREIGN KEY (user_id) REFERENCES users(id);'
    )
    return clauses

def up():
    t = Table.create('comments')
    t.text('id').unique()
    t.text('content').not_null()
    t.text('user_id').index()
    t.custom(add_fk)
    return [t]

def down():
    return [Table.drop('comments')]

def migration(connection_string: str = 'blog.db') -> Migration:
    m = Migration(connection_string)
    m.up(up)
    m.down(down)
    return m
```

## Programmatic API

Use `sqloquent.tools` for programmatic access:

```python
from sqloquent import Migration, Table
from sqloquent.tools import (
    make_migration_from_model, make_migration_from_model_path,
    migrate, rollback, refresh, examine,
    automigrate, autorollback, autorefresh
)

# Generate from model
src = make_migration_from_model(MyModel, 'MyModel', 'mydb.db')
with open('migrations/001_create.py', 'w') as f:
    f.write(src)

# Generate from model file path
src = make_migration_from_model_path('MyModel', 'models.py', 'mydb.db')

# Apply migrations
migrate('migrations/001_create.py', 'mydb.db')
automigrate('./migrations', 'mydb.db')

# Rollback
rollback('migrations/001_create.py', 'mydb.db')
autorollback('./migrations', 'mydb.db')           # Last batch
autorollback('./migrations', 'mydb.db', all=True) # All batches

# Refresh (rollback + reapply)
refresh('migrations/001_create.py', 'mydb.db')
autorefresh('./migrations', 'mydb.db')

# Preview SQL without applying
up_sql, down_sql = examine('migrations/001_create.py')

# Direct Migration class usage (with optional custom context)
from mydbpackage import CustomContext
migration = Migration('mydb.db', CustomContext)
migration.up(create_users)
migration.up(create_posts)
migration.down(drop_posts)
migration.down(drop_users)
migration.apply()

# Preview SQL
up_sql = migration.get_apply_sql()
down_sql = migration.get_undo_sql()
```

These are useful for creating packages and for installation or applying updates
in applications.
