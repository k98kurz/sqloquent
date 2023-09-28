# Sqloquent

This is a SQL library with included bindings for sqlite. Inspired by Laravel and
in particular Eloquent.

## Overview

This package provides a set of interfaces and classes to make using a SQL
database easier and simpler. (See section below for full list.)

The primary features are the `SqlQueryBuilder` and `SqlModel` base classes. The
`SqlQueryBuilder` uses a monad pattern to build a query from various clauses. The
`SqlModel` handles encoding, persisting, reading, and decoding models that
correspond to rows. See below for the methods for each class.

These base classes can be coupled to the supplied sqlite3 coupling or to any SQL
database client. See the "Usage" section below for detailed instructions.

Additionally, three classes, `DeletedModel`, `HashedModel`, and `Attachment`
have been supplied to allow easy implementation of a system that includes a
cryptographic audit trail. `DeletedModel` corresponds to any deleted model from
a class that extends `HashedModel` and includes a `restore` method that can
restore the deleted record.

## Status

- [x] Base interfaces
- [x] Base test suite
- [x] Base classes
- [x] ORM
- [x] Cryptographic bonus code
- [x] Detailed query builder
- [x] Code scaffold tools + CLI
- [x] Schema migration system
- [x] Decent documentation
- [ ] Refactor: replace monkeypatching with injection
- [ ] Publish to pypi

## Setup and Usage

Requires Python 3.10+. Have not tested with older Python versions.

### Setup

```bash
pip install sqloquent
```

### Usage

There are two primary ways to use this package: either with the bundled sqlite3
coupling or with a custom coupling to an arbitrary SQL database client. The
cryptographic audit trail features can be used with any SQL database coupling.

#### CLI Tool

For ease of development, a CLI tool is included which can be used for generating
code scaffolds/boilerplates and for managing migrations. After installing via
pip, run `sqloquent` in the terminal to view the help text.

The CLI tool can generate models and migrations, including the ability to
generate migrations from completed models. Migrations can be handled manually or
using an automatic method that tracks migrations via a `migrations` table. To
use the migration tools, the environment variable `CONNECTION_STRING` must be
set either in the CLI environment or in an .env file, e.g.
`CONNECTION_STRING=path/to/file.db`. To insert this connection string into
generated scaffold code, also define a `MAKE_WITH_CONNSTRING` environment
variable and set it to anythong other than "false" or "0"; this is a convenience
feature for working with sqlite3, since that is the only bundled coupling, but
overwriting the `file_path` attribute on models at the app execution entry point
is probably a better strategy.

#### Note About Table Construction

The package as it stands relies upon text or varchar type `id` columns. The
`SqlModel` uses a hexadecimal uuid4 as a GUID, while the `HashedModel` uses the
sha256 of the deterministically encoded record content as a GUID. This can be
changed for use with autoincrementing int id columns by extending `SqlModel` or
`SqliteModel` and overriding the `insert` and `insert_many` methods to prevent
setting the id via `cls.generate_id()`. However, this is not recommended unless
the autoincrement id can be discerned from the db cursor in some way, which did
not work with sqlite3 when I tried it.

Use one of the variants of the `sqloquent make migration` command to create a
migration scaffold, then edit the result as necessary. If you specify the
`--model name path/to/model/file` variant, the resultant source will include a
unique index on the id column and simple indices on all other columns.

#### Using the sqlite3 coupling

To use the supplied sqlite3 coupling without the cryptographic features, extend
the `SqliteModel`, filling these attributes as shown below:

- `table: str`: the name of the table
- `columns: tuple`: the ordered tuple of column names

Additionally, set up any relevant relations using the ORM helper methods.

```python
from sqloquent import SqliteModel, has_many, belongs_to


class ModelA(SqliteModel):
    table: str = 'model_a'
    columns: tuple = ('id', 'name', 'details')
    _details: dict = None

    def details(self, reload: bool = False) -> dict:
        """Decode json str to dict."""
        if self._details is None or reload:
            self._details = json.loads(self.data['details'])
        return self._details

    def set_details(self, details: dict = {}) -> ModelA:
        """Sets details and encodes to json str."""
        if details:
            self._details = details
        self.data['details'] = json.dumps(self._details)
        return self

class ModelB(SqliteModel):
    table: str = 'model_b'
    columns: tuple = ('id', 'name', 'model_a_id', 'number')


ModelA.model_b = has_many(ModelA, ModelB, 'model_a_id')
ModelB.model_a = belongs_to(ModelB, ModelA, 'model_a_id', True)
```

If you do not want to use the bundled ORM system, set up any relevant relations
with `_{related_name}: RelatedModel` attributes and
`{related_name}(self, reload: bool = False)` methods. Dicts should be encoded
using `json.dumps` and stored in text columns. More flexibility can be gained at
the expense of performance by using the packify package, e.g. to encode sets or
classes that implement the `packify.Packable` interface.

```python
from sqloquent import SqliteModel


class ModelA(SqliteModel):
    table: str = 'model_a'
    columns: tuple = ('id', 'name', 'details')
    _model_b: ModelB = None
    _details: dict = None

    def model_b(self, reload: bool = False) -> list[ModelB]:
        """The related model."""
        if self._model_b is None or reload:
            self._model_b = ModelB.query({'model_a_id': self.data['id']}).get()
        return self._model_b

    def set_model_b(self, model_b: ModelB) -> ModelA:
        """Helper method to save some lines."""
        model_b.data['model_a_id'] = self.data['id']
        model_b._model_a = self
        model_b.save()
        self._model_b = model_b
        return self

    def details(self, reload: bool = False) -> dict:
        """Decode json str to dict."""
        if self._details is None or reload:
            self._details = json.loads(self.data['details'])
        return self._details

    def set_details(self, details: dict = {}) -> ModelA:
        """Sets details and encodes to json str."""
        if details:
            self._details = details
        self.data['details'] = json.dumps(self._details)
        return self

class ModelB(SqliteModel):
    table: str = 'model_b'
    columns: tuple = ('id', 'name', 'model_a_id', 'number')
    _model_a: ModelA = None

    def model_a(self, reload: bool = False) -> Optional[ModelA]:
        """Return the related model."""
        if self._model_a is None or reload:
            self._model_a = ModelA.find(self.data['model_a_id'])
        return self._model_a

    def set_model_a(self, model_a: ModelA) -> ModelB:
        """Helper method to save some lines."""
        self.data['model_a_id'] = model_a.data['id']
        self._model_a = model_a
        model_a._model_b = self
        return self.save()
```

#### Coupling to a SQL Database Client

To couple to a SQL database client, complete the following steps.

##### 0. Implement the `CursorProtocol`

If the database client does not include a cursor that implements the
`CursorProtocol`, one must be implemented. Besides the methods `execute`,
`executemany`, `executescript`, `fetchone`, and `fetchall`, an int `rowcount`
attribute should be available and updated after calling `execute`.

If a `rowcount` attribute is not available, then the following methods of the
base `SqlQueryBuilder` will need to be overridden in step 2:

- `insert_many`: returns the number of rows inserted
- `update`: returns the number of rows updated
- `delete`: returns the number of rows deleted

##### 1. Implement the `DBContextProtocol`

See the `SqliteContext` class for an example of how to implement this interface.
This is a standard context manager that accepts a class that implements
`ModelProtocol` and returns an instance of the class made in step 0 when used
with the following syntax:

```python
with SomeDBContextImplementation(SomeModel) as cursor:
    cursor.execute('...')
```

Note that the connection information should be injected here in the context
manager. The bundled sqlite bindings put the file path to the sqlite db on the
models themselves to avoid having to rewrite and rebind the whole system to
customize the db file path.

##### 2. Extend `SqlQueryBuilder`

Extend `SqlQueryBuilder` and supply the class from step 1 as the
second parameter to `super().__init__()`. Example:

```python
class SomeDBQueryBuilder(SqlQueryBuilder):
    def __init__(self, model: type, *args, **kwargs) -> None:
        super().__init__(model, SomeDBContext, *args, **kwargs)
```

Additionally, since the `SqlQueryBuilder` was modeled on sqlite3, any difference
in the SQL implementation of the database or db client will need to be reflected
by overriding the relevant method(s).

##### 3. Extend `SqlModel`

Extend `SqlModel` to include whatever class or instance information is required
and inject the class from step 2 into `self.query_builder_class` in the
`__init__` method. Example:

```python
from sqloquent import QueryBuilderProtocol, SqlModel


class SomeDBModel(SqlModel):
    """Model for interacting with SomeDB database."""
    some_config_key: str = 'some_config_value'
    query_builder_class: QueryBuilderProtocol = SomeDBQueryBuilder

    def __init__(self, data: dict = {}) -> None:
        super().__init__(data)
```

##### 4. Extend Class from Step 3

To create models, simply extend the class from step 3, filling these attributes:

- `table: str`: the name of the table
- `columns: tuple`: the ordered tuple of column names

Additionally, set up any relevant relations using the ORM functions or,
if you don't want to use the ORM, with `_{related_name}: RelatedModel`
attributes and `{related_name}(self, reload: bool = False)` methods. Dicts
should be encoded to comply with the database client, e.g. by using `json.dumps`
for databases that lack a native JSON data type or for clients that require
encoding before making the query. See the above example for using the sqlite3
coupling.

##### 5. `QueryBuilder` Features

A few quick notes about `QueryBuilder` implementations, including the bundled
`SqlQueryBuilder` and `SqliteQueryBuilder`:

- Pagination is accomplished using the `skip(number)` and `take(number)`
methods, or by directly setting the `limit` and `offset` attributes. The
`offset` will only apply when `limit` is specified because that is how SQL works
generally.
- For iterating over large data sets, the `chunk(number)` method returns a
generator that yields subsets with length equal to the specified number.
- For debugging/learning purposes, the `to_sql` produces human-readable SQL.
- The `execute_raw(sql)` method executes raw SQL and returns a tuple of
`(int rowcount, Any results from fetchall)`.

#### Using the Cryptographic Features

If a cryptographic audit trail is desirable, use the following multiple
inheritance + injection pattern to couple the supplied classes to the desired
`ModelProtocol` implementation. (The below example uses the sqlite3 coupling,
but it should work with others.)

```python
import sqloquent

env_db_file_path = 'some_file.db'
HashedModel_original = sqloquent.HashedModel
DeletedModel_original = sqloquent.DeletedModel
Attachment_original = sqloquent.Attachment


class HashedModel(sqloquent.HashedModel, sqloquent.SqliteModel):
    file_path: str = env_db_file_path
sqloquent.HashedModel = HashedModel

class DeletedModel(sqloquent.DeletedModel, sqloquent.SqliteModel):
    file_path: str = env_db_file_path
sqloquent.DeletedModel = DeletedModel

class Attachment(sqloquent.Attachment, sqloquent.SqliteModel):
    file_path: str = env_db_file_path
sqloquent.Attachment = Attachment
```

This must be done exactly once. The value supplied for `file_path` (or relevant
configuration value for other database couplings) should be set with some
environment configuration system, but here it is only poorly mocked.

#### Using the ORM

The ORM is comprised of 4 classes inheriting from `Relation` and implementing
the `RelationProtocol`: `HasOne`, `HasMany`, `BelongsTo`, and `BelongsToMany`.

Each `Relation` child class instance has a method `create_property` that returns
a property that can be set on a model class:

```python
class User(SqlModel):
    ...

class Avatar(SqlModel):
    columns = ('id', 'url', 'user_id')

User_Avatar = HasOne('user_id', User, Avatar)
User_Avatar.inverse = BelongsTo('user_id', Post, User)
User_Avatar.inverse.inverse = User_Avatar
User.avatar = User_Avatar.create_propert()
Avatar.user = User_Avatar.inverse.create_property()
```

There are also four helper functions for setting up relations between models:
`has_one`, `has_many`, `belongs_to`, and `belongs_to_many`. These simplify and
are the intended way for setting up relation between models. Far friendlier way
to use the ORM.

```python
class User(SqlModel):
    @property
    def friends(self) -> list[User]:
        friends = []
        if hasattr(self.my_friends) and self.my_friends:
            friends += self.my_friends
        if hasattr(self.befriended_by) and self.befriended_by:
            friends += self.befriended_by
        return friends
    @friends.setter
    def friends(self, friends: list[User]) -> None:
        current_friends = []
        if hasattr(self.my_friends) and self.my_friends:
            current_friends += self.my_friends
        if hasattr(self.befriended_by) and self.befriended_by:
            current_friends += self.befriended_by

        new_friends = tuple(f for f in friends if f not in current_friends)
        if hasattr(self.my_friends):
            self.my_friends = self.my_friends + new_friends
        elif hasattr(self.befriended_by):
            self.befriended_by = self.befriended_by + new_friends

class Avatar(SqlModel):
    columns = ('id', 'url', 'user_id')

class Post(SqlModel):
    columns = ('id', 'content', 'user_id')

class Friendships(SqlModel):
    columns = ('id', 'user1_id', 'user2_id')

User.avatar = has_one(User, Avatar)
User.posts = has_many(User, Post)
Post.author = belongs_to(Post, User)
User.my_friends = belongs_to_many(User, User, Friendships, 'user1_id', 'user2_id')
User.befriended_by = belongs_to_many(User, User, Friendships, 'user2_id', 'user1_id')
```

NB: polymorphic relations are not supported. See the `Attachment` class for an
example of how to implement polymorphism if necessary. The above example also
shows a contrived and probably suboptimal way to have a many-to-many relation on
a single model.

## Interfaces and Classes

Below is a list of interfaces, classes, errors, and functions. See the
[dox.md](https://github.com/k98kurz/sqloquent/blob/master/dox.md) file generated
by [autodox](https://pypi.org/project/autodox) for full documentation.

### Interfaces

- CursorProtocol(Protocol)
- DBContextProtocol(Protocol)
- ModelProtocol(Protocol)
- JoinedModelProtocol(Protocol)
- RowProtocol(Protocol)
- QueryBuilderProtocol(Protocol)
- RelationProtocol(Protocol)
- ColumnProtocol(Protocol)
- TableProtocol(Protocol)
- MigrationProtocol(Protocol)

### Classes

Classes implement the protocols or extend the classes indicated.

- SqliteContext(DBContextProtocol)
- SqlModel(ModelProtocol)
- SqliteModel(SqlModel)
- JoinedModel(JoinedModelProtocol)
- JoinSpec
- Row(RowProtocol)
- SqlQueryBuilder(QueryBuilderProtocol)
- SqliteQueryBuilder(SqlQueryBuilder)
- DeletedModel(SqlModel)
- DeletedSqliteModel(DeletedModel, SqliteModel)
- HashedModel(SqlModel)
- HashedSqliteModel(HashedModel, SqliteModel)
- Attachment(HashedModel)
- AttachmentSqlite(HashedSqliteModel)
- Relation(RelationProtocol)
- HasOne(Relation)
- HasMany(HasOne)
- BelongsTo(HasOne)
- BelongsToMany(Relation)

### Functions

The package includes some ORM helper functions for setting up relations and some
other useful functions.

- has_one
- has_many
- belongs_to
- belongs_to_many
- dynamic_sqlite_model
- get_index_name

## Tests

Open a terminal in the root directory and run the following:

```
python tests/test_classes.py
python tests/test_relations.py
python tests/test_migration.py
python tests/test_tools.py
python tests/test_integration.py
```

The tests demonstrate the intended (and actual) behavior of the classes, as
well as some contrived examples of how they are used. Perusing the tests will be
informative to anyone seeking to use/break this package, especially the
integration test which demonstrates the full package. There are currently 188
unit tests + 1 e2e integration test.

## ISC License

Copyleft (c) 2023 k98kurz

Permission to use, copy, modify, and/or distribute this software
for any purpose with or without fee is hereby granted, provided
that the above copyleft notice and this permission notice appear in
all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL
WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE
AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR
CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS
OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,
NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN
CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
