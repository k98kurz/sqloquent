# Sqloquent

This is a SQL library with included bindings for sqlite. Inspired by Laravel and
in particular Eloquent.

## Overview

This package provides a set of interfaces and classes to make using a SQL
database easier and simpler, both through synchronously and using asyncio. (See
section below for full list.)

The primary features are the `SqlQueryBuilder` and `SqlModel` base classes (or
`AsyncSqlQueryBuilder` and `AsyncSqlModel` for use with asyncio). The
`SqlQueryBuilder` uses a monad pattern to build and execute a query from various
clauses. The `SqlModel` handles encoding, persisting, reading, and decoding
models that correspond to rows. The query builder can be used without a model,
in which case a dynamic model will be created. Any grouping will result in `get`
returning `Row`s, and joining will result in `get` returning `JoinedModel`s.

```python
from sqloquent import SqlQueryBuilder

sqb = SqlQueryBuilder(
    'some_table', columns=['id', 'etc'], connection_info='temp.db'
).join('some_other_table', columns=['id', 'some_id', 'data'])

# count the number of matches
count = sqb.count()

# chunk through them 1000 at a time
for chunk in sqb.chunk(1000):
    for joined_model in chunk:
        ...

# or just get them all
results = sqb.get()
```

Or for asyncio:

```python
from asyncio import run
from sqloquent.asyncql import AsyncSqlQueryBuilder

sqb = AsyncSqlQueryBuilder(
    'some_table', columns=['id', 'etc'], connection_info='temp.db'
).join('some_other_table', columns=['id', 'some_id', 'data'])

# count the number of matches
count = run(sqb.count())

# chunk through them 1000 at a time
async def chunk_it(sqb):
    async for chunk in sqb.chunk(1000):
        for joined_model in chunk:
            ...
run(chunk_it(sqb))

# or just get them all
results = run(sqb.get())
```

These base classes have a default binding to sqlite3 via the `SqliteContext`
class, but they can be coupled to any SQL database client. See the "Usage"
section below for detailed instructions for the latter.

Additionally, three classes, `DeletedModel`, `HashedModel`, and `Attachment`
have been supplied to allow easy implementation of a system that includes a
cryptographic audit trail. `DeletedModel` corresponds to any deleted model from
a class that extends `HashedModel` and includes a `restore` method that can
restore the deleted record.

There is an included CLI tool that generates code scaffolding for models and
migrations, as well as track, apply, rollback, and refresh migrations.

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
- [x] Added `--columns name=type,etc` param for model generator
- [x] Add asyncio compatibility
- [x] `Contains` and `Within` relations (+ helper functions and async versions)
- [ ] Option for eager loading relations on `get`, `find`, or `insert`
- [ ] Add automatic timestamps to `DeletedModel`
- [ ] Add support for all SQL types in migration system
- [ ] Make `make migration --model ...` compute alter from diff with existing schema

Currently, only the basic sqlite3 types (affinities) of text, blob, integer,
real, and numeric are supported by the migration system.

## Setup and Usage

Requires Python 3.10+. This has not been tested with older Python versions.

### Setup

```bash
pip install sqloquent
```

To use the async version, instead install with the following:

```bash
pip install sqloquent[asyncql]
```

### Usage

There are two primary ways to use this package: either with a bundled sqlite3
coupling or with a custom coupling to an arbitrary SQL database client. The
cryptographic audit trail features can be used with any SQL database coupling.

Note that if you create a custom async DB coupling, you will also need to create
a non-async coupling to use the migration system.

#### Connection Information

Connection information can be bound or injected in several places:

- Bound to each individual model
- Injected into the query builder
- Bound to the query builder
- Bound to the db context manager

Items higher in the list will override those lower in the list. For example, if
you set the connection_info attribute on a model class or instance, it will be
used for interactions with the db originating from that model class or instance,
respectively. If you set the connection_info attribute on the query builder
class, it will be used, but if you pass it as a parameter to initialize a query
builder, that paramter will be used instead.

#### Example

The most thorough examples are the integration tests. The model files for the
first can be found
[here](https://github.com/k98kurz/sqloquent/tree/master/tests/integration_vectors/models),
and the test itself is
[here](https://github.com/k98kurz/sqloquent/blob/master/tests/test_integration.py#L61).

The async versions can be found here:
- [models](https://github.com/k98kurz/sqloquent/tree/master/tests/integration_vectors/asyncmodels)
- [test](https://github.com/k98kurz/sqloquent/blob/master/tests/test_async_integration.py#L62)

The models were scaffolded using the CLI tool, then the details filled out in
each. The relations were set up in the `__init__.py` file. The integration test
generates migrations from these classes using the CLI tool, automigrates using
the CLI tool, then does inserts/updates/deletes and checks the db for
correctness. (These files provide a basic schema for correspondent banking.)

The second integration test is outlined in the "Using the ORM" section below.

#### CLI Tool

For ease of development, a CLI tool is included which can be used for generating
code scaffolds/boilerplates and for managing migrations. After installing via
pip, run `sqloquent` in the terminal to view the help text.

The CLI tool can generate models and migrations, including the ability to
generate migrations from completed models. Migrations can be handled manually or
using an automatic method that tracks migrations via a `migrations` table. To
use the migration tools, the environment variable `CONNECTION_STRING` must be
set either in the CLI environment or in a .env file, e.g.
`CONNECTION_STRING=path/to/file.db`. To insert this connection string into
generated scaffold code, also define a `MAKE_WITH_CONNSTRING` environment
variable and set it to anything other than "false" or "0"; this is a convenience
feature for working with sqlite3, since that is the only bundled coupling, but
overwriting the `connection_info` attribute on models at the app execution entry
point is probably a better strategy -- if using another SQL binding, the
connection info should be injected into the context manager (see section about
binding to other SQL databases/engines below).

Additionally, the functionality of the CLI tool can be accessed programmatically
through `sqloquent.tools`.

#### Note About Table Construction

The package as it stands relies upon text or varchar type `id` columns. The
`SqlModel` uses a hexadecimal uuid4 as a GUID, while the `HashedModel` uses the
sha256 of the deterministically encoded record content as a GUID. This can be
changed for use with autoincrementing int id columns by extending `SqlModel` and
overriding the `insert` and `insert_many` methods to prevent setting the id via
`cls.generate_id()`. However, this is not recommended unless the autoincrement
id can be reliably discerned from the db cursor and there are no concerns about,
say, synchronizing between instances using a CRDT.

Use one of the variants of the `sqloquent make migration` command to create a
migration scaffold, then edit the result as necessary. If you specify the
`--model name path/to/model/file` variant, the resultant source will include a
unique index on the id column and simple indices on all other columns. This will
also parse any class annotations that map to names of columns. For example,
given the following class,

```python
from sqloquent import SqlModel
class Thing(SqlModel):
    table = 'things'
    columns = ('id', 'name', 'amount')
    id: str
    name: bytes
    amount: int|None
```

the `make migration --model` command will produce the following migration:

```python
from sqloquent import Migration, Table


def create_table_things() -> list[Table]:
    t = Table.create('things')
    t.text('id').unique()
    t.blob('name').index()
    t.integer('amount').nullable().index()
    ...
    return [t]

def drop_table_things() -> list[Table]:
    return [Table.drop('things')]

def migration(connection_string: str = '') -> Migration:
    migration = Migration(connection_string)
    migration.up(create_table_things)
    migration.down(drop_table_things)
    return migration
```

This should provide a decent scaffold for migrations, allowing the user of this
package to model their data first as classes if desired. If some custom SQL is
necessary, it can be added using a callback:

```python
def add_custom_sql(clauses: list[str]) -> list[str]:
    clauses.append("do something sql-y")
    return clauses

def create_table_things() -> list[Table]:
    t = Table.create('things')
    t.text('id').unique()
    t.blob('name').index()
    t.integer('amount').nullable().index()
    t.custom(add_custom_sql)
    ...
    return [t]
```

Examine the generated SQL of any migration using the
`sqloquent examine path/to/migration/file` command. The above example will
generate the following:

```sql
/**** generated up/apply sql ****/
begin;
create table if not exists things (id text, name blob, amount integer);
create unique index if not exists udx_things_id on things (id);
create index if not exists idx_things_name on things (name);
create index if not exists idx_things_amount on things (amount);
commit;

/**** generated down/undo sql ****/
begin;
drop table if exists things;
commit;
```

#### Models

Models should extend `SqlModel` or a model that extends `SqlModel` and couples
to another database client. To use the supplied sqlite3 coupling without the
cryptographic features, extend the `SqlModel`, filling these attributes as shown
below:

- `table: str`: the name of the table
- `columns: tuple[str]`: the ordered tuple of column names
- annotations for columns as desired

Additionally, set up any relevant relations using the ORM helper methods.

The CLI tool will produce a scaffold for a model. For example, running
`sqloquent make model Thing --hashed --columns "id,name,stuff=str|None"` will
produce the following:

```python
from sqloquent import HashedModel


class stuff(HashedModel):
    connection_info: str = ''
    table: str = 'stuffs'
    id_column: str = 'id'
    columns: tuple[str] = ('id', 'name', 'stuff')
    id: str
    name: str
    stuff: str|None
```

Specify `--async` to use an async model. For example, running
`sqloquent make model Person --columns id,name --async` will produce the
following:

```python
from sqloquent.asyncql import AsyncSqlModel


class Person(AsyncSqlModel):
    connection_info: str = ''
    table: str = 'persons'
    id_column: str = 'id'
    columns: tuple[str] = ('id', 'name')
    id: str
    name: str
```

Below is a more complex example with relations.

```python
from __future__ import annotations
from sqloquent import SqlModel, has_many, belongs_to, RelatedModel, RelatedCollection
import json

connection_string = ''

with open('.env', 'r') as f:
    lines = f.readlines()
    for l in lines:
        if l[:18] == 'CONNECTION_STRING=':
            connection_string = l[18:-1]

class ModelA(SqlModel):
    connection_info = connection_string
    table: str = 'model_a'
    columns: tuple = ('id', 'name', 'details')
    id: str
    name: str
    _details: dict = None
    model_b: RelatedCollection

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

class ModelB(SqlModel):
    connection_info = connection_string
    table: str = 'model_b'
    columns: tuple = ('id', 'name', 'model_a_id', 'number')
    id: str
    name: str
    model_a_id: str
    number: int
    model_a: RelatedModel


ModelA.model_b = has_many(ModelA, ModelB, 'model_a_id')
ModelB.model_a = belongs_to(ModelB, ModelA, 'model_a_id')


if __name__ == "__main__":
    model_a = ModelA.insert({'name': 'Some ModelA'})
    model_b = ModelB({'name': 'Some ModelB'})
    model_b.save()
    assert hasattr(model_a, 'data') and type(model_a.data) is dict
    assert hasattr(model_b, 'data') and type(model_b.data) is dict
    model_b.model_a = model_a
    model_b.model_a().save()
    model_a.model_b().reload()
    assert model_a.model_b[0].data['id'] == model_b.id
    assert model_a.model_b[0].id == model_b.id
    ModelA.query().delete()
    ModelB.query().delete()
    print("success")
```

To use this, save the code snippet as "example.py" and run the following to set
up the database and then run the script:

```bash
sqloquent make migration --model ModelA example.py > model_a_migration.py
sqloquent make migration --model ModelB example.py > model_b_migration.py
sqloquent migrate model_a_migration.py
sqloquent migrate model_b_migration.py
python example.py
```

It is noteworthy that every column in the `columns` class attribute will be
made into a property that accesses the underlying data stored in the `data`
dict (the annotation just helps the code editor/LSP pick up on this). This will
not work for any column name that collides with an existing class attribute or
method, and the behavior can be disabled by adding a class attribute called
"disable_column_property_mapping"; all row data will still be accessible via the
`data` attribute on each instance regardless of name collision or feature
disabling.

If you do not want to use the bundled ORM system, set up any relevant relations
with `_{related_name}: RelatedModel` attributes and
`{related_name}(self, reload: bool = False)` methods. Dicts should be encoded
using `json.dumps` and stored in text columns. More flexibility can be gained at
the expense of performance by using the packify package, e.g. to encode sets or
classes that implement the `packify.Packable` interface.

```python
from sqloquent import SqlModel


class ModelA(SqlModel):
    table: str = 'model_a'
    columns: tuple = ('id', 'name', 'details')
    id: str
    name: str
    _model_b: ModelB|None = None
    _details: dict|None = None

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

class ModelB(SqlModel):
    table: str = 'model_b'
    columns: tuple = ('id', 'name', 'model_a_id', 'number')
    id: str
    name: str
    model_a_id: str
    number: int
    _model_a: ModelA|None = None

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

##### 0. Implement the `CursorProtocol` or `AsyncCursorProtocol`

If the database client does not include a cursor that implements the
`CursorProtocol` or `AsyncCursorProtocol`, one must be implemented. Besides the
methods `execute`, `executemany`, `executescript`, `fetchone`, and `fetchall`,
an int `rowcount` attribute should be available and updated after calling
`execute`.

If a `rowcount` attribute is not available, then the following methods of the
base `SqlQueryBuilder`/`AsyncSqlQueryBuilder` will need to be overridden in step
2:

- `insert_many`: returns the number of rows inserted
- `update`: returns the number of rows updated
- `delete`: returns the number of rows deleted

##### 1. Implement the `DBContextProtocol` or `AsyncDBContextProtocol`

See the `SqliteContext` and `AsyncSqliteContext` classes for examples of how to
implement these interfaces. This is a standard context manager that accepts
connection_info string and returns a cursor to be used within the context block:

```python
with SomeDBContextImplementation('some optional connection string') as cursor:
    cursor.execute('...')
# or for async
async def wrap():
    async with SomeAsyncContextImplementation('some connection string') as cursor:
        await cursor.execute('...')
asyncio.run(wrap())
```

Note that the connection information should be bound or injected here in the
context manager. Connection strings can be put on the models themselves or by
setting the `connection_info` attribute on the context manager class (e.g.
`SqliteContext.connection_info = 'temp.db'`) or the `SqlQueryBuilder` class
(e.g. `SqlQueryBuilder.connection_info = 'temp.db'`).

##### 2. Extend `SqlQueryBuilder` or `AsyncSqlQueryBuilder`

Extend `SqlQueryBuilder` or `AsyncSqlQueryBuilder` and supply the class from
step 1 as the second parameter to `super().__init__()`. Example:

```python
class SomeDBQueryBuilder(SqlQueryBuilder):
    def __init__(self, model: type, *args, **kwargs) -> None:
        super().__init__(model, SomeDBContextImplementation, *args, **kwargs)
# or for async
class SomeAsyncQueryBuilder(AsyncSqlQueryBuilder):
    def __init__(self, model: type, *args, **kwargs) -> None:
        super().__init__(model, SomeAsyncContextImplementation, *args, **kwargs)
```

Additionally, since the `SqlQueryBuilder` was modeled on sqlite3, any difference
in the SQL implementation of the database or db client will need to be reflected
by overriding the relevant method(s). Same applies for `AsyncSqlQueryBuilder`,
with the caveat that it uses the `aiosqlite` package.

##### 3. Extend `SqlModel` or `AsyncSqlModel`

Extend `SqlModel` or `AsyncSqlModel` to include whatever class or instance
information is required and inject the class from step 2 into the class
attribute `query_builder_class`. Example:

```python
class SomeDBModel(SqlModel):
    """Model for interacting with SomeDB database."""
    some_config_key: str = 'some_config_value'
    query_builder_class: QueryBuilderProtocol = SomeDBQueryBuilder
# or for async
class SomeAsyncModel(AsyncSqlModel):
    """Model for interacting with SomeDB database."""
    some_config_key: str = 'some_config_value'
    query_builder_class: AsyncQueryBuilderProtocol = SomeAsyncQueryBuilder
```

##### 4. Extend Class from Step 3

To create models, simply extend the class from step 3, setting class annotations
and filling these attributes:

- `table: str`: the name of the table
- `columns: tuple`: the ordered tuple of column names

Model class annotations are helpful because the columns will be mapped to class
properties, i.e. `model.data['id'] == model.id`. However, since the base class
methods are type hinted for the base class, instance variables returned from
class methods should be type hinted, e.g.
`model: SomeDBModel = SomeDBModel.find(some_id)`; alternately, the methods can
be overridden just for the type hints, and the code editor LSP should still read
the doc block of the base class method if the child class method is left without
a doc block.

Additionally, set up any relevant relations using the ORM functions or,
if you don't want to use the ORM, with `_{related_name}: SomeModel` attributes
and `{related_name}(self, reload: bool = False)` methods. Dicts should be
encoded to comply with the database client, e.g. by using `json.dumps` for
databases that lack a native JSON data type or for clients that require encoding
before making the query.

##### 5. `SqlQueryBuilder`/`AsyncSqlQueryBuilder` Features

A few quick notes about `QueryBuilderProtocol` implementations, including the
bundled `SqlQueryBuilder`:

- The query builder can be used either with a model or with a table, e.g.
`SqlQueryBuilder(SomeModel)` or `SqlQueryBuilder('some_table', columns=['id', 'etc'])`.
If used with a table name, then columns must be specified.
- Pagination is accomplished using the `skip(number)` and `take(number)`
methods, or by directly setting the `limit` and `offset` attributes. The
`offset` will only apply when `limit` is specified because that is how SQL works
generally.
- For iterating over large data sets, the `chunk(number)` method returns a
generator that yields subsets with length equal to the specified number.
- For debugging/learning purposes, the `to_sql` produces human-readable SQL.
- The `execute_raw(sql)` method executes raw SQL and returns a tuple of
`(int rowcount, Any results from fetchall)`.
- If only certain columns are desired, they can be selected with `select(names)`;
SQL functions can also be selected in this way, e.g. `select["count(*)"]`.
- Joins can be accomplished using `join(AnotherModel, [table1_col, table2_col])`
or `join('another_table', [table1_col, table2_col], columns=['id', 'etc])`. Note
that if a table name is specified, then columns for the table must be provided.

The `AsyncSqlQueryBuilder` implementation of the `AsyncQueryBuilderProtocol` is
similar, but the following methods are async and must be awaited:

- `insert`
- `insert_many`
- `find`
- `get`
- `count`
- `take`
- `chunk`
- `first`
- `update`
- `delete`
- `execute_raw`

#### Using the Cryptographic Features

If a cryptographic audit trail is desirable, use an inheritance pattern to
couple the supplied classes to the desired `ModelProtocol` implementation, or
simply change the connection_info attribute to use with sqlite3.

```python
from .dbcxm import SomeDBContextImplementation
from sqloquent import HashedModel, DeletedModel, Attachment, SqlQueryBuilder

env_db_file_path = 'some_file.db'
env_connstring = 'host=localhost,port=69,user=admin,password=admin'

# option 1: inheritance
class CustomQueryBuilder(SqlQueryBuilder):
    def __init__(self, model_or_table, **kwargs,):
        return super().__init__(model_or_table, SomeDBContextImplementation, **kwargs)

class NewModel(HashedModel, SomeDBModel):
    connection_info = env_connstring
    query_builder_class = CustomQueryBuilder

# option 2: bind the classes
HashedModel.connection_info = env_db_file_path
HashedModel.query_builder_class = CustomQueryBuilder
DeletedModel.connection_info = env_db_file_path
DeletedModel.query_builder_class = CustomQueryBuilder
Attachment.connection_info = env_db_file_path
Attachment.query_builder_class = CustomQueryBuilder
```

The latter must be done exactly once. The value supplied for `connection_info`
should be set with some environment configuration system, but here it is only
poorly mocked.

#### Using the ORM

The ORM is comprised of 6 classes inheriting from `Relation` and implementing
the `RelationProtocol`: `HasOne`, `HasMany`, `BelongsTo`, `BelongsToMany`,
`Contains`, and `Within`. The async version is equivalent with `Async` prefixes.

Each `Relation` child class instance has a method `create_property` that returns
a property that can be set on a model class:

```python
from sqloquent import SqlModel, HashedModel, HasOne, BelongsTo, Contains, Within

class User(SqlModel):
    ...

class Avatar(SqlModel):
    columns = ('id', 'url', 'user_id')

User.avatar = HasOne('user_id', User, Avatar).create_property()
Avatar.user = BelongsTo('user_id', Avatar, User).create_property()

class DAGItem(HashedModel):
    columns = ('id', 'details', 'parent_ids')

DAGItem.parents = Contains('parent_ids', DAGItem, DAGItem).create_property()
DAGItem.children = Within('parent_ids', DAGItem, DAGItem).create_property()
```

There are also six helper functions for setting up relations between models:
`has_one`, `has_many`, `belongs_to`, `belongs_to_many`, `contains`, and `within`.
These simplify and are the intended way for setting up relation between models.
Far friendlier way to use the ORM. (Same applies for async, but with `async_`
prefixes.)

```python
from __future__ import annotations
from sqloquent import (
    SqlModel, RelatedCollection, RelatedModel,
    has_one, has_many, belongs_to, belongs_to_many,
)

class User(SqlModel):
    table = 'users'
    columns = ('id', 'name')
    friends: RelatedCollection
    friendships: RelatedCollection
    avatar: RelatedModel
    posts: RelatedCollection

class Avatar(SqlModel):
    table = 'avatars'
    columns = ('id', 'url', 'user_id')
    user: RelatedModel

class Post(SqlModel):
    table = 'posts'
    columns = ('id', 'content', 'user_id')
    author: RelatedModel

class Friendship(SqlModel):
    table = 'friendships'
    columns = ('id', 'user1_id', 'user2_id')
    user1: RelatedModel
    user2: RelatedModel

    @classmethod
    def insert(cls, data: dict) -> Friendship | None:
        # also set inverse relationship
        result = super().insert(data)
        if result:
            super().insert({
                **data,
                'user1_id': data['user2_id'],
                'user2_id': data['user1_id'],
            })

    @classmethod
    def insert_many(cls, items: list[dict]) -> int:
        inverse = [
            {
                'user1_id': item['user2_id'],
                'user2_id': item['user1_id']
            }
            for item in items
        ]
        return super().insert_many([*items, *inverse])

    def delete(self):
        # first delete the inverse
        self.query().equal('user1_id', self.data['user2_.id']).equal(
            'user2_id', self.data['user1_id']
        ).delete()
        super().delete()

User.avatar = has_one(User, Avatar)
Avatar.user = belongs_to(Avatar, User)

User.posts = has_many(User, Post)
Post.author = belongs_to(Post, User)

User.friendships = has_many(User, Friendship, 'user1_id')
User.friends = belongs_to_many(User, User, Friendship, 'user1_id', 'user2_id')

Friendship.user1 = belongs_to(Friendship, User, 'user1_id')
Friendship.user2 = belongs_to(Friendship, User, 'user2_id')
```

The relations can then be used as follows:

```python
# add users
alice: models2.User = models2.User.insert({"name": "Alice"})
bob: models2.User = models2.User.insert({"name": "Bob"})

# add avatars
alice.avatar().secondary = models2.Avatar.insert({
    "url": "http://www.perseus.tufts.edu/img/newbanner.png",
})
alice.avatar().save()
bob.avatar = models2.Avatar.insert({
    "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/90" +
    "/Walrus_(Odobenus_rosmarus)_on_Svalbard.jpg/1200px-Walrus_(Odobe" +
    "nus_rosmarus)_on_Svalbard.jpg",
})
bob.avatar().save()

# add a friendship
bob.friends = [alice]
bob.friends().save()
bob.friendships().reload()
alice.friendships().reload()
alice.friends().reload()
```

The above is included in the second integration test:
- [models](https://github.com/k98kurz/sqloquent/blob/master/tests/integration_vectors/models2.py)
- [test](https://github.com/k98kurz/sqloquent/blob/master/tests/test_integration.py#L297)

NB: polymorphic relations are not supported. See the `Attachment` class for an
example of how to implement polymorphism if necessary.

Below is an example of the Contains and Within relations:

```python
from sqloquent import (
    HashedModel, RelatedCollection, RelatedModel, contains, within,
)

class DAGItem(HashedModel):
    table = 'dag'
    columns = ('id', 'details', 'parent_ids')
    parents: RelatedCollection
    children: RelatedCollection

    @classmethod
    def insert(cls, data: dict) -> DAGItem|None:
        # """For better type hinting."""
        return super().insert(data)

    @classmethod
    def insert_many(cls, items: list[dict]) -> int:
        # """For better type hinting."""
        return super().insert_many(items)

DAGItem.parents = contains(DAGItem, DAGItem, 'parent_ids')
DAGItem.children = within(DAGItem, DAGItem, 'parent_ids')
```

Which can be used as follows:

```python
# create parents
parent1 = DAGItem.insert({'details': 'parent 1'})
parent2 = DAGItem.insert({'details': 'parent 2'})

# create children
child1 = DAGItem({'details': 'child 1'})
child1.parents = [parent1, parent2]
child1.parents().save()

child2 = DAGItem({'details': 'child 2'})
child2.parents = [parent1]
child2.parents().save()

# reload relation
parent1.children().reload()
parent2.children().reload()
assert len(parent1.children) == 2
assert len(parent2.children) == 1
```

## Interfaces, Classes, Functions, and Tools

Below is a list of interfaces, classes, errors, and functions. See the
[dox.md](https://github.com/k98kurz/sqloquent/blob/master/dox.md) and
[asyncql_dox.md](https://github.com/k98kurz/sqloquent/blob/master/asyncql_dox.md)
files generated by [autodox](https://pypi.org/project/autodox) for full
documentation, or read
[interfaces.md](https://github.com/k98kurz/sqloquent/blob/master/interfaces.md)
and
[async_interfaces.md](https://github.com/k98kurz/sqloquent/blob/master/async_interfaces.md)
for documentation on just the interfaces or
[tools.md](https://github.com/k98kurz/sqloquent/blob/master/tools.md) for
information about the bundled tools.

### Interfaces

- CursorProtocol(Protocol)
- DBContextProtocol(Protocol)
- ModelProtocol(Protocol)
- JoinedModelProtocol(Protocol)
- RowProtocol(Protocol)
- QueryBuilderProtocol(Protocol)
- RelationProtocol(Protocol)
- RelatedModel(ModelProtocol)
- RelatedCollection(Protocol)
- ColumnProtocol(Protocol)
- TableProtocol(Protocol)
- MigrationProtocol(Protocol)

### Classes

Classes implement the protocols or extend the classes indicated.

- SqlModel(ModelProtocol)
- SqlQueryBuilder(QueryBuilderProtocol)
- SqliteContext(DBContextProtocol)
- DeletedModel(SqlModel)
- HashedModel(SqlModel)
- Attachment(HashedModel)
- Row(RowProtocol)
- JoinedModel(JoinedModelProtocol)
- JoinSpec
- Relation(RelationProtocol)
- HasOne(Relation)
- HasMany(HasOne)
- BelongsTo(HasOne)
- BelongsToMany(Relation)
- Contains(HasMany)
- Within(HasMany)
- Column(ColumnProtocol)
- Table(TableProtocol)
- Migration(MigrationProtocol)
- AsyncSqlModel(AsyncModelProtocol)
- AsyncSqlQueryBuilder(AsyncQueryBuilderProtocol)
- AsyncSqliteContext(AsyncDBContextProtocol)
- AsyncDeletedModel(AsyncSqlModel)
- AsyncHashedModel(AsyncSqlModel)
- AsyncAttachment(AsyncHashedModel)
- AsyncJoinedModel(AsyncJoinedModelProtocol)
- AsyncRelation(AsyncRelationProtocol)
- AsyncHasOne(AsyncRelation)
- AsyncHasMany(AsyncHasOne)
- AsyncBelongsTo(AsyncHasOne)
- AsyncBelongsToMany(AsyncRelation)
- AsyncContains(AsyncHasMany)
- AsyncWithin(AsyncHasMany)

### Functions

The package includes some ORM helper functions for setting up relations and some
other useful functions.

- dynamic_sqlmodel
- has_one
- has_many
- belongs_to
- belongs_to_many
- contains
- within
- get_index_name
- async_dynamic_sqlmodel
- async_has_one
- async_has_many
- async_belongs_to
- async_belongs_to_many
- async_contains
- async_within

### Tools

The package includes a set of tools with a CLI invocation script.

- make_migration_create
- make_migration_alter
- make_migration_drop
- make_migration_from_model
- publish_migrations
- make_model
- migrate
- rollback
- refresh
- examine
- automigrate
- autorollback
- autorefresh

## Tests

Open a terminal in the root directory and run the following:

```
mkdir tests/temp
mkdir tests/temp/migrations
python -m venv venv
source venv/bin/activate
pip -r requirements.txt
python tests/test_classes.py
python tests/test_relations.py
python tests/test_migration.py
python tests/test_tools.py
python tests/test_integration.py
python tests/test_async_classes.py
python tests/test_async_relations.py
python tests/test_async_integration.py
```

The tests demonstrate the intended (and actual) behavior of the classes, as
well as some contrived examples of how they are used. Perusing the tests will be
informative to anyone seeking to use/break this package, especially the
integration test which demonstrates the full package. There are currently 402
unit tests + 4 e2e integration tests.

## ISC License

Copyleft (c) 2023 Jonathan Voss (k98kurz)

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
