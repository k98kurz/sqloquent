# Coupling to a SQL Database Client

To couple to a SQL database client, complete the following steps. Note that this does
not currently have advice about connection pooling.

## 0. Implement the `CursorProtocol` or `AsyncCursorProtocol`

If the database client does not include a cursor that implements the
`CursorProtocol` or `AsyncCursorProtocol`, one must be implemented. Besides the
methods `execute`, `executemany`, `executescript`, `fetchone`, and `fetchall`,
an int `rowcount` attribute should be available and updated after calling
`execute`.

If a `rowcount` attribute is not available, then the following methods of the
base `SqlQueryBuilder`/`AsyncSqlQueryBuilder` will need to be overridden in step 2:

- `insert_many`: returns the number of rows inserted
- `update`: returns the number of rows updated
- `delete`: returns the number of rows deleted

Note also that this should handle connection pooling. See the
[`SqliteContext`](https://github.com/k98kurz/sqloquent/blob/v0.7.3/sqloquent/classes.py#L24) and
[`AsyncSqliteContext`](https://github.com/k98kurz/sqloquent/blob/v0.7.3/sqloquent/asyncql/classes.py#L23)
classes for examples of how to implement this.

## 1. Implement the `DBContextProtocol` or `AsyncDBContextProtocol`

See the `SqliteContext` and `AsyncSqliteContext` classes for examples of how to
implement these interfaces. This is a standard context manager that accepts
`connection_info` string and returns a cursor to be used within the context block:

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

## 2. Extend `SqlQueryBuilder` or `AsyncSqlQueryBuilder`

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

## 3. Extend `SqlModel` or `AsyncSqlModel`

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

## 4. Extend Class from Step 3

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

## 5. `SqlQueryBuilder`/`AsyncSqlQueryBuilder` Features

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
