---
name: sqloquent
description: Guide for using the sqloquent SQL/ORM library - model creation, migrations, relations, and query builder patterns
---

# sqloquent

Sqloquent is a SQL/ORM library with sqlite bindings, inspired by Laravel Eloquent. It provides models, query builders, relations, migrations, and a CLI tool for scaffolding.

## Quick Setup

```bash
# Set environment variables
export CONNECTION_STRING='database.db'
export MAKE_WITH_CONNSTRING=1

# Create directories
mkdir -p migrations models
```

## Using the CLI Tool

### Scaffold a Model

```bash
# Basic model
sqloquent make model User --columns "id=str,name=str,email=str|None" > models/User.py

# HashedModel (for cryptographic audit trail)
sqloquent make model Document --hashed --columns "id=str,content=bytes,version=int" > models/Document.py

# Async model
sqloquent make model Message --columns "id=str,content=str,views=int|Default[0]" --async > models/Message.py
```

### Scaffold Migrations

```bash
# From a model file
sqloquent make migration --model User models/User.py > migrations/001_create_users.py

# Create table scaffold
sqloquent make migration --create Thing > migrations/002_create_thing.py

# Alter table scaffold
sqloquent make migration --alter Thing > migrations/003_alter_thing.py

# Drop table scaffold
sqloquent make migration --drop Thing > migrations/004_drop_thing.py
```

### Manage Migrations

```bash
# Preview SQL
sqloquent examine migrations/001_create_users.py

# Apply single migration
sqloquent migrate migrations/001_create_users.py

# Rollback single migration
sqloquent rollback migrations/001_create_users.py

# Refresh (rollback + apply)
sqloquent refresh migrations/001_create_users.py
```

### Automatic Migration System

```bash
# Apply all pending migrations
sqloquent automigrate migrations/

# Rollback last batch
sqloquent autorollback migrations/

# Rollback all, reapply all
sqloquent autorefresh migrations/
```

## Setting Up Models Module

Create or edit `models/__init__.py` to configure connection info, relations, and run migrations:

```python
from __future__ import annotations
from sqloquent import SqlModel, has_one, has_many, belongs_to, contains, within
from .User import User
from .Avatar import Avatar
from .Post import Post
from .Document import Document
import os

# Set connection info for all models
def set_connection_info(connection_string: str):
    User.connection_info = connection_string
    Avatar.connection_info = connection_string
    Post.connection_info = connection_string
    Document.connection_info = connection_string

# Define relations
User.avatar = has_one(User, Avatar)
Avatar.user = belongs_to(Avatar, User)

User.posts = has_many(User, Post)
Post.author = belongs_to(Post, User)

# For DAG structures with HashedModel
Document.parents = contains(Document, Document, 'parent_ids')
Document.children = within(Document, Document, 'parent_ids')

__all__ = [
    'User', 'Avatar', 'Post', 'Document', 'set_connection_info',
]
```

**Important:** Relations must be defined at the module level, not inside model classes. Use the helper functions (`has_one`, `has_many`, `belongs_to`, `belongs_to_many`, `contains`, `within`) to set up relations. Use `RelatedModel` or `RelatedCollection` for annotating relations within model classes.

## Query Builder Patterns

### Basic Query Builder Usage

The query builder uses a fluent interface. Most query methods can be called in two ways:

```python
from models import User

# Method 1: Two parameters
User.query().equal('name', 'Alice')

# Method 2: Keyword arguments for multiple columns
User.query().equal(name='Alice', email='alice@example.com')
```

Strict equality has an additional syntax:

```python
# dict parameter to `query()` for multiple `equal` clauses
User.query({'name': 'Alice', 'email': 'alice@example.com'})
```

### Comparison Methods

```python
# Equality/inequality
User.query().equal('name', 'Alice')
User.query().not_equal('name', 'Alice')

# Comparisons
User.query().greater('age', 18)
User.query().greater_or_equal('age', 18)
User.query().less('age', 65)
User.query().less_or_equal('age', 65)

# Null checks
User.query().is_null('deleted_at')
User.query().not_null('email')

# Pattern matching
User.query().starts_with('name', 'Al')
User.query().ends_with('email', '@example.com')
User.query().contains('bio', 'developer')
User.query().like('name', 'A%')
User.query().like('email', '%@%.%')

# List membership
User.query().is_in('id', ['id1', 'id2', 'id3'])
User.query().not_in('status', ['deleted', 'suspended'])
```

### Complex Queries

```python
# Using where() for multiple conditions
User.query().where(
    greater={'age': 18},
    is_null=['deleted_at'],
    contains={'name': 'John'}
)

# Ordering and limiting
User.query().order_by('name', 'asc').take(10)

# Skip/offset (for pagination)
User.query().skip(20).take(10)

# Chaining multiple conditions
User.query().greater('age', 18).not_null('email').equal('active', True)
```

### Selecting Specific Columns

```python
# Select only specific columns (returns models with only those columns in data)
users = User.query().select(['id', 'name']).get()

# With joins: use table-qualified column names
from models import Post
User.query().join(Post, ['id', 'user_id']).select(['users.name', 'posts.title'])

# With aggregations: returns Row objects instead of models
from models import Attachment
Attachment.query().group('related_id').select(['count(*)', 'related_id']).get()
```

**Important**: `select()` changes what data is included in results:
- Without joins or GROUP BY: returns models with only selected columns
- With joins: returns JoinedModel with table-qualified columns
- With GROUP BY: returns Row objects (not models)

### Executing Queries

```python
# Get all results
users = User.query().equal('active', True).get()

# Get first result
user = User.query().equal('email', 'alice@example.com').first()

# Count results
count = User.query().equal('active', True).count()

# Take N results
recent_users = User.query().order_by('created_at', 'desc').take(5)

# Chunk through results (for large datasets)
for chunk in User.query().chunk(100):
    for user in chunk:
        print(user.name)
```

## Relations: The Critical Distinction

This is the most common pitfall when using sqloquent. Relations create special properties on models with **two different access patterns**:

### Property Access: `model.related`

Accesses the **related model(s)** rather than the Relation class instance:

```python
user = User.find('user-id-123')

# Property access
avatar = user.avatar  # Returns Avatar or None
posts = user.posts   # Returns RelatedCollection (list-like)
```

### Method Call: `model.related()`

Returns the **Relation object** which can be used to:
- Reload from database
- Query the relation
- Save changes

```python
user = User.find('user-id-123')

# Method call - returns Relation object
user.avatar()           # Returns HasOne relation
user.posts()            # Returns HasMany relation
user.avatar().reload()  # Reload from database
user.posts().save()     # Save relation changes
user.posts().query()    # Returns a query builder with relevant clauses and params
```

### Common Patterns

```python
# Reading related data (use property)
user = User.find('user-id-123')
avatar = user.avatar
if avatar:
    print(avatar.url)

# Reloading from database (use method call)
user.avatar().reload()
avatar = user.avatar  # Now fresh from database

# Setting related data (assign to property, then save)
user.avatar = Avatar.insert({'url': 'https://example.com/avatar.jpg'})
user.avatar().save()  # Persist the relationship

# Querying related data
user.posts().query().where(contains={'content': 'important'}).get()

# Saving multiple related items
user.posts = [post1, post2, post3]
user.posts().save()

# Reload after changes
user.posts().reload()
for post in user.posts:
    print(post.content)
```

### Relation Types Summary

| Relation Type | Property Returns | When to Use |
|---------------|------------------|-------------|
| `has_one` | Single model or None | One-to-one (User has one Avatar) |
| `has_many` | RelatedCollection (iterable) | One-to-many (User has many Posts) |
| `belongs_to` | Single model or None | Many-to-one inverse (Post belongs to User) |
| `belongs_to_many` | RelatedCollection (iterable) | Many-to-many (Users have many Roles) |
| `contains` | RelatedCollection (iterable) | Store IDs in column (DAG parent IDs) |
| `within` | RelatedCollection (iterable) | ID stored in related models (DAG child IDs) |

### Setting Up Relations

```python
from sqloquent import has_one, has_many, belongs_to, belongs_to_many

# HasOne: User has one Avatar (avatars table has user_id)
User.avatar = has_one(User, Avatar)
Avatar.user = belongs_to(Avatar, User)

# HasMany: User has many Posts (posts table has user_id)
User.posts = has_many(User, Post)
Post.author = belongs_to(Post, User)

# BelongsToMany: Users have many Roles via pivot
from .Role import Role
from .UserRole import UserRole  # pivot table
User.roles = belongs_to_many(User, Role, UserRole, 'user_id', 'role_id')
Role.users = belongs_to_many(Role, User, UserRole, 'role_id', 'user_id')

# Contains: Document contains parent IDs in parent_ids column
Document.parents = contains(Document, Document, 'parent_ids')

# Within: Document's ID is in parent_ids of its children
Document.children = within(Document, Document, 'parent_ids')
```

## Connection Management with Context Managers

For proper connection management in background processes or when you need direct cursor access, use `SqliteContext`:

```python
from sqloquent import SqliteContext

# Raw SQL operations with automatic commit/rollback
with SqliteContext('database.db') as cursor:
    cursor.execute('select count(*) from users')
    count = cursor.fetchone()[0]
    # Committed on exit, rolled back if exception

# Connection pooling prevents leaks in multi-threaded apps
with SqliteContext(db_path) as cursor:
    app.run()
```

**Important limitations:**
- SqliteContext returns a cursor for raw SQL operations
- Model operations (`insert()`, `update()`, etc.) create their own internal contexts and commit independently
- Does NOT provide transaction control for model operations - each model operation commits immediately
- Primarily useful for raw SQL and preventing connection leaks in background processes

## Model Operations

### Creating Models

```python
from models import User

# Insert and return model
user = User.insert({'name': 'Alice', 'email': 'alice@example.com'})

# Create instance, then save
user = User({'name': 'Bob'})
user.save()

# Batch insert
User.insert_many([
    {'name': 'Charlie', 'email': 'charlie@example.com'},
    {'name': 'Diana', 'email': 'diana@example.com'},
])
```

### Updating Models

```python
# Update model instance
user = User.find('user-id-123')
user.email = 'newemail@example.com'
user.save()

# Update with query
User.query().equal('id', 'user-id-123').update({'email': 'updated@example.com'})

# Conditional update
User.query().equal('status', 'pending').update({'status': 'active'})
```

### Deleting Models

```python
# Delete model instance
user = User.find('user-id-123')
user.delete()

# Delete with query
User.query().equal('status', 'deleted').delete()
```

### Finding Models

```python
# Find by ID
user = User.find('user-id-123')

# Find with conditions
user = User.query().equal('email', 'alice@example.com').first()

# Find multiple
users = User.query().equal('active', True).get()
```

## Migration System

### Supported Data Types

Only sqlite3 types are currently supported:
- `integer` - Integer numbers
- `numeric` - High-precision numeric
- `real` - Floating-point numbers
- `text` - String data (default values are quoted in SQL)
- `blob` - Binary data (default values are hex-encoded in SQL)
- `boolean` - Boolean values

### Column Methods

```python
# Create table migration
from sqloquent import Migration, Table

def up():
    t = Table.create('users')
    t.text('id').unique()           # unique index: udx_users_id
    t.text('name').not_null()       # NOT NULL, simple index
    t.text('email').unique()        # unique index: udx_users_email
    t.text('password')
    t.integer('age').nullable()     # explicitly nullable (default anyway)
    t.boolean('active').default(True)
    return [t]

def down():
    return [Table.drop('users')]

def migration(connection_string: str = '') -> Migration:
    m = Migration(connection_string)
    m.up(up)
    m.down(down)
    return m
```

### Programmatic Migration API

```python
from sqloquent.tools import (
    make_migration_from_model_path,
    automigrate, autorollback, autorefresh
)

# Generate migration from model
src = make_migration_from_model_path('User', 'models/User.py', 'database.db')
with open('migrations/001_create_users.py', 'w') as f:
    f.write(src)

# Apply all pending migrations
automigrate('migrations/', 'database.db')

# Rollback last batch
autorollback('migrations/', 'database.db')

# Refresh all migrations
autorefresh('migrations/', 'database.db')
```

## Model Annotations

When using the CLI to generate models, you can specify column types with annotations that will be used by the migration system:

```bash
# Type annotations
sqloquent make model Product --columns \
  "id=str,name=str|Default['Unnamed'],price=float,in_stock=bool|Default[True],description=str|None" > models/Product.py
```

Supported annotation patterns:
- Basic types: `str`, `int`, `bool`, `float`, `bytes`
- Nullable: `str|None`, `int|None`, etc.
- Defaults: `str|Default[value]`, `int|Default[0]`, `bool|Default[True]`
- Combined: `str|None|Default[value]`

## Async Support

For async operations, use the asyncql module:

```bash
# Install with async support
pip install sqloquent[asyncql]

# Generate async model
sqloquent make model AsyncUser --columns "id=str,name=str" --async > models/AsyncUser.py
```

```python
from asyncio import run
from sqloquent.asyncql import AsyncSqlModel

class AsyncUser(AsyncSqlModel):
    table = 'users'
    columns = ('id', 'name')
    connection_info = 'database.db'

async def main():
    # methods are async
    user = await AsyncUser.insert({'name': 'Alice'})
    await user.delete()
    # query builder setup is sync
    sqb = AsyncUser.query().starts_with('name', 'B')
    # interactions with db are async
    count = await sqb.count()
    async for users in AsyncUser.query().chunk(100):
        ...

run(main())
```

The asyncql subpackage mirrors the normal sqloquent package but with coroutines and async generators.

**Note:** The async ORM may create `ResourceWarning`s when relation properties are accessed within async functions. This comes from an upstream dependency but has been harmless in testing.

## Common Gotchas

1. **Query builder comparison methods**: Always use the fluent interface, not direct comparisons. Wrong: `User.query(name == 'Alice')`, Correct: `User.query().equal('name', 'Alice')`

2. **Relation access**: Remember `model.related` lazy-loads from database and caches; `model.related()` returns relation object for operations like reload(), save(), query().

3. **SqliteContext and model operations**: SqliteContext does NOT provide transaction control for model operations. Each `insert()`, `update()`, `delete()`, etc. creates its own internal context and commits independently. Use SqliteContext for raw SQL cursor operations or connection cleanup in background processes.

4. **Environment variables**: Set `CONNECTION_STRING` for CLI migration tools. Set `MAKE_WITH_CONNSTRING` to embed connection string in scaffolds.

5. **Relation setup**: Define relations at module level in `__init__.py`, not inside model classes.

6. **Migration types**: Only sqlite types are supported. Use `text` for strings, `blob` for binary data.

7. **Async ResourceWarnings**: The async ORM can produce warnings when accessing relation properties in async contexts.

## Additional Resources

- **Main/Sync Docs**: `docs/dox.md`
- **Async Docs**: `docs/asyncql_dox.md` and `docs/async_interfaces.md` - Async API documentation
- **Interface Docs**: `docs/interfaces.md` - Protocol definitions for custom implementations
- **Migration Guide**: `docs/migrations.md` - Comprehensive migration system documentation
- **Tools Reference**: `docs/tools.md` - CLI and programmatic tools API
- **How to Couple**: `docs/how_to_couple.md` - Guide for binding to other SQL databases

## CLI Help

```bash
# View all CLI commands
sqloquent

# Get help on a specific command
sqloquent make --help
sqloquent make model --help
sqloquent make migration --help
```
