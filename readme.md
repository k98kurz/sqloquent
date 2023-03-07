# Simple SQL ORM

This is a simple and hopefully rather SOLID SQL ORM system.

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
- [x] Cryptographic bonus code
- [x] Add chunk generator to `QueryBuilderProtocol` and `SqlQueryBuilder`
- [x] Decent documentation
- [ ] ORM helper functions
- [ ] Publish to pypi

## Setup and Usage

Requires python 3+.

### Setup

To install, clone/unpack the repo.

### Usage

There are two primary ways to use this package: either with the bundled sqlite3
coupling or with a custom coupling to an arbitrary SQL database client. The
cryptographic audit trail features can be used with any SQL database coupling.

#### Note About Table Construction

The package as it stands relies upon text or varchar type `id` columns. The
`SqlModel` uses a hexadecimal uuid4 as a GUID, while the `HashedModel` uses the
sha256 of the deterministically encoded record content as a GUID. This can be
changed for use with autoincrementing int id columns by extending `SqlModel` or
`SqliteModel` and overriding the `insert` and `insert_many` methods to prevent
setting the id via `cls.generate_id()`. However, this is not recommended unless
the autoincrement id can be discerned from the db cursor in some way, which did
not work with sqlite3 when I tried it.

This does not include a database migration system. That might be an eventual
improvement, but it is not currently planned. Table construction and management
will have to be done manually or with a migration tool. (I am fond of the
migration system used by Laravel, so the temptation to build a python equivalent
is strong.)

#### Using the sqlite3 coupling

To use the supplied sqlite3 coupling without the cryptographic features, extend
the `SqliteModel`, filling these attributes as shown below:

- `table: str`: the name of the table
- `fields: tuple`: the ordered tuple of column names

Additionally, set up any relevant relations with `_{related_name}: RelatedModel`
attributes and `{related_name}(self, reload: bool = False)` methods. Dicts
should be encoded using `json.dumps` and stored in text columns.

```python
class ModelA(SqliteModel):
    table: str = 'model_a'
    fields: tuple = ('id', 'name', 'details')
    _model_b: ModelB = None
    _details: dict = None

    def model_b(self, reload: bool = False) -> Optional[ModelB]:
        if self._model_b is None or reload:
            self._model_b = ModelB.query({'model_a_id': self.data['id']}).first()
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

    def set_details(self, details: dict = {}) -> Attachment:
        if details:
            self._details = details
        self.data['details'] = json.dumps(self._details)
        return self

class ModelB(SqliteModel):
    table: str = 'model_b'
    fields: tuple = ('id', 'name', 'model_a_id', 'number')
    _model_a: ModelA = None

    def model_a(self, reload: bool = False) -> Optional[ModelA]:
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
`executemany`, `fetchone`, and `fetchall`, an int `rowcount` attribute should be
available and updated after calling `execute`.

If a `rowcount` attribute is not available, then the following methods of the
base `SqlQueryBuilder` will need to be overridden in step 2:

- `insert_many`: returns the number of rows inserted
- `update`: returns the number of rows updated
- `delete`: returns the number of rows deleted

##### 1. Implement the `DBContextProtocol`

See the `SqliteContext` class for an example of how to implement this interface.
This is a standard context manager that accepts an instance of a class that
implements `ModelProtocol` and returns an instance of the class made in step 0
when used with the following syntax:

```python
with SomeDBContextImplementation(SomeModel) as cursor:
    cursor.execute('...')
```

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
class SomeDBModel(SqlModel):
    """Model for interacting with SomeDB database."""
    some_config_key: str = 'some_config_value'

    def __init__(self, data: dict = {}) -> None:
        self.query_builder_class = SomeDBQueryBuilder
        super().__init__(data)
```

##### 4. Extend Class from Step 3

To create models, simply extend the class from step 3, filling these attributes:

- `table: str`: the name of the table
- `fields: tuple`: the ordered tuple of column names

Additionally, set up any relevant relations with `_{related_name}: RelatedModel`
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
env_db_file_path = 'some_file.db'

class HashedModel(simplesqlorm.HashedModel, simplesqlorm.SqliteModel):
    file_path: str = env_db_file_path
simplesqlorm.HashedModel_original = simplesqlorm.HashedModel
simplesqlorm.HashedModel = HashedModel

class DeletedModel(simplesqlorm.DeletedModel, simplesqlorm.SqliteModel):
    file_path: str = env_db_file_path
simplesqlorm.DeletedModel_original = simplesqlorm.DeletedModel
simplesqlorm.DeletedModel = DeletedModel

class Attachment(simplesqlorm.Attachment, simplesqlorm.SqliteModel):
    file_path: str = env_db_file_path
simplesqlorm.Attachment_original = simplesqlorm.Attachment
simplesqlorm.Attachment = Attachment
```

This must be done exactly once. The value supplied for `file_path` (or relevant
configuration value for other database couplings) should be set with some
environment configuration system, but here it is only poorly mocked.

## Interfaces and Classes

Below are the interfaces and classes, along with attributes and methods. Note
that any type that includes itself in a return signature indicates a jquery-
style monad pattern.

### Interfaces

- CursorProtocol(Protocol)
    - `execute(sql: str) -> CursorProtocol`
    - `executemany(sql: str) -> CursorProtocol`
    - `fetchone() -> Any`
    - `fetchall() -> Any`
- DBContextProtocol(Protocol)
    - `__init__(self, model: ModelProtocol) -> None`
    - `__enter__(self) -> CursorProtocol`
    - `__exit__(self, __exc_type: Optional[Type[BaseException]],`
                `__exc_value: Optional[BaseException],`
                `__traceback: Optional[TracebackType]) -> None`
- ModelProtocol(Protocol)
    - `__hash__(self) -> int`
    - `__eq__(self, other) -> bool`
    - `@classmethod find(cls, id: Any) -> Optional[ModelProtocol]`
    - `@classmethod insert(cls, data: dict) -> Optional[ModelProtocol]`
    - `@classmethod insert_many(cls, data: dict) -> int`
    - `update(self, updates: dict, conditions: dict = None) -> ModelProtocol`
    - `save(self) -> ModelProtocol`
    - `delete(self) -> None`
    - `@classmethod query(cls, conditions: dict = None) -> QueryBuilderProtocol`
- QueryBuilderProtocol(Protocol)
    - `equal(self, field: str, data: str) -> QueryBuilderProtocol`
    - `not_equal(self, field: str, data: Any) -> QueryBuilderProtocol`
    - `less(self, field: str, data: str) -> QueryBuilderProtocol`
    - `greater(self, field: str, data: str) -> QueryBuilderProtocol`
    - `starts_with(self, field: str, data: str) -> QueryBuilderProtocol`
    - `contains(self, field: str, data: str) -> QueryBuilderProtocol`
    - `excludes(self, field: str, data: str) -> QueryBuilderProtocol`
    - `ends_with(self, field: str, data: str) -> QueryBuilderProtocol`
    - `is_in(self, field: str, data: Union[tuple, list]) -> QueryBuilderProtocol`
    - `order_by(self, field: str, direction: str = 'desc') -> QueryBuilderProtocol`
    - `skip(self, offset: int) -> QueryBuilderProtocol`
    - `reset(self) -> QueryBuilderProtocol`
    - `insert(self, data: dict) -> Optional[ModelProtocol]`
    - `insert_many(self, items: list[dict]) -> int`
    - `find(self, id: str) -> Optional[ModelProtocol]`
    - `get(self) -> list[ModelProtocol]`
    - `count(self) -> int`
    - `take(self, number: int) -> Optional[list[ModelProtocol]]`
    - `chunk(self, number: int) -> Generator[list[ModelProtocol], None, None]`
    - `first(self) -> Optional[ModelProtocol]`
    - `update(self, updates: dict, conditions: dict = {}) -> int`
    - `delete(self) -> int`
    - `to_sql(self) -> str`
    - `execute_raw(self, sql: str) -> tuple[int, Any]`

### Classes

Classes implement the protocols or extend the classes indicated. Only additional
and/or overridden methods/attributes are included in this list.

- SqliteContext(DBContextProtocol)
    - `connection: sqlite3.Connection`
    - `cursor: sqlite3.Cursor`
- SqlModel(ModelProtocol)
    - `table: str = 'example'`
    - `id_field: str = 'id'`
    - `fields: tuple = ('id', 'name')`
    - `query_builder_class: Type[QueryBuilderProtocol]`
    - `data: dict`
    - `__init__(self, data: dict = {}) -> None`
    - `@staticmethod encode_value(val: Any) -> str`
    - `@classmethod generate_id(cls) -> str`
- SqliteModel(SqlModel)
    - `__init__(self, data: dict = {}) -> None`
- SqlQueryBuilder(QueryBuilderProtocol)
    - `model: type`
    - `context_manager: Type[DBContextProtocol] = field(default=None)`
    - `clauses: list = field(default_factory=list)`
    - `params: list = field(default_factory=list)`
    - `order_field: str = field(default=None)`
    - `order_dir: str = field(default='desc')`
    - `@property model(self) -> type`
    - `@model.setter model(self, model: type) -> None`
- SqliteQueryBuilder(SqlQueryBuilder)
    - `__init__(self, model: type, *args, **kwargs) -> None`
- DeletedModel(SqlModel)
    - `table: str = 'deleted_records'`
    - `fields: tuple = ('id', 'model_class', 'record_id', 'record')`
    - `restore(self) -> SqlModel`
- HashedModel(SqlModel)
    - `table: str = 'hashed_records'`
    - `fields: tuple = ('id', 'data')`
    - `@classmethod generate_id(cls, data: dict) -> str`
    - `@classmethod def insert(cls, data: dict) -> Optional[HashedModel]`
    - `@classmethod insert_many(cls, items: list[dict]) -> int`
    - `update(self, updates: dict) -> HashedModel`
    - `delete(self) -> DeletedModel`
- Attachment(HashedModel)
    - `table: str = 'attachments'`
    - `fields: tuple = ('id', 'related_model', 'related_id', 'details')`
    - `_related: SqlModel = None`
    - `_details: dict = None`
    - `related(self, reload: bool = False) -> SqlModel`
    - `attach_to(self, related: SqlModel) -> Attachment`
    - `details(self, reload: bool = False) -> dict`
    - `set_details(self, details: dict = {}) -> Attachment`

## Tests

Open a terminal in the root directory and run the following:

```
python tests/test_classes.py
```

The tests demonstrate the intended (and actual) behavior of the classes, as
well as some contrived examples of how they are used. Perusing the tests will be
informative to anyone seeking to use this package.

## ISC License

Copyleft (c) 2023 k98kurz

Permission to use, copy, modify, and/or distribute this software
for any purpose with or without fee is hereby granted, provided
that the above copyleft notice and this permission notice appear in
all copies.

Exceptions: this permission is not granted to Alphabet/Google, Amazon,
Apple, Microsoft, Netflix, Meta/Facebook, Twitter, or Disney; nor is
permission granted to any company that contracts to supply weapons or
logistics to any national military; nor is permission granted to any
national government or governmental agency; nor is permission granted to
any employees, associates, or affiliates of these designated entities.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL
WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE
AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR
CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS
OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,
NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN
CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
