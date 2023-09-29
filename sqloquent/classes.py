from __future__ import annotations
from .errors import tert, vert, tressa
from .interfaces import (
    DBContextProtocol,
    CursorProtocol,
    QueryBuilderProtocol
)
from dataclasses import dataclass, field
from hashlib import sha256
from types import TracebackType
from typing import Any, Generator, Optional, Type, Union
from uuid import uuid4
import packify
import sqlite3


class SqliteContext:
    """Context manager for sqlite."""
    connection: sqlite3.Connection
    cursor: sqlite3.Cursor

    def __init__(self, model: Type[SqlModel], connection_info: str = '') -> None:
        """Initialize the instance. Raises TypeError for invalid model
            (must be subclass of SqlModel with str|bytes file_path).
        """
        tert(type(model) is type, 'model must be child class of SqlModel')
        tert(issubclass(model, SqlModel),
            'model must be child class of SqlModel')
        if not connection_info and hasattr(self, 'connection_info'):
            connection_info = self.connection_info
        if not connection_info and hasattr(model, 'file_path'):
            connection_info = model.file_path
        tert(type(connection_info) in (str, bytes),
            'connection_info or model.file_path must be str or bytes')
        self.connection = sqlite3.connect(connection_info or model.file_path)
        self.cursor = self.connection.cursor()

    def __enter__(self) -> CursorProtocol:
        """Enter the context block and return the cursor."""
        return self.cursor

    def __exit__(self, __exc_type: Optional[Type[BaseException]],
                __exc_value: Optional[BaseException],
                __traceback: Optional[TracebackType]) -> None:
        """Exit the context block. Commit or rollback as appropriate,
            then close the connection.
        """
        if __exc_type is not None:
            self.connection.rollback()
        else:
            self.connection.commit()

        self.connection.close()


class SqlModel:
    """General model for mapping a SQL row to an in-memory object."""
    table: str = 'example'
    id_column: str = 'id'
    columns: tuple = ('id', 'name')
    query_builder_class: Type[QueryBuilderProtocol]
    data: dict

    def __init__(self, data: dict = {}) -> None:
        """Initialize the instance. Raises TypeError or ValueError if
            _post_init_hooks is not dict[Any, callable].
        """
        self.data = {}

        if not hasattr(self.__class__, 'disable_column_property_mapping'):
            names = dir(self)
            for column in self.columns:
                if column not in names:
                    setattr(self.__class__, column, self.create_property(column))

        for key in data:
            if key in self.columns and type(key) is str:
                self.data[key] = data[key]

        if hasattr(self, '_post_init_hooks'):
            tert(isinstance(self._post_init_hooks, dict),
                '_post_init_hooks must be a dict mapping names to Callables')
            for _, call in self._post_init_hooks.items():
                vert(callable(call),
                    '_post_init_hooks must be a dict mapping names to Callables')
                call(self)

    @staticmethod
    def create_property(name) -> property:
        """Create a dynamic property for the column with the given name."""
        @property
        def prop(self):
            return self.data.get(name)
        @prop.setter
        def prop(self, value):
            self.data[name] = value
        return prop

    @staticmethod
    def encode_value(val: Any) -> str:
        """Encode a value for hashing. Uses the pack function from
            packify.
        """
        return packify.pack(val).hex()

    def __hash__(self) -> int:
        """Allow inclusion in sets. Raises TypeError for unencodable
            type within self.data (calls packify.pack).
        """
        data = self.encode_value(self.data)
        return hash(bytes(data, 'utf-8'))

    def __eq__(self, other) -> bool:
        """Allow comparisons. Raises TypeError on unencodable value in
            self.data or other.data (calls cls.__hash__ which calls
            packify.pack).
        """
        if type(other) != type(self):
            return False

        return hash(self) == hash(other)

    def __repr__(self) -> str:
        """Pretty str representation."""
        return f"{self.__class__.__name__}(table='{self.table}', " + \
            f"id_column='{self.id_column}', " + \
            f"columns={self.columns}, data={self.data})"

    @classmethod
    def generate_id(cls) -> str:
        """Generates and returns a hexadecimal UUID4."""
        return uuid4().bytes.hex()

    @classmethod
    def find(cls, id: Any) -> Optional[SqlModel]:
        """Find a record by its id and return it. Return None if it does
            not exist.
        """
        return cls().query_builder_class(model=cls).find(id)

    @classmethod
    def insert(cls, data: dict) -> Optional[SqlModel]:
        """Insert a new record to the datastore. Return instance. Raises
            TypeError if data is not a dict.
        """
        tert(isinstance(data, dict), 'data must be dict')
        if cls.id_column not in data:
            data[cls.id_column] = cls.generate_id()

        return cls().query_builder_class(model=cls).insert(data)

    @classmethod
    def insert_many(cls, items: list[dict]) -> int:
        """Insert a batch of records and return the number of items
            inserted. Raises TypeError if items is not list[dict].
        """
        tert(isinstance(items, list), 'items must be type list[dict]')
        for item in items:
            tert(isinstance(item, dict), 'items must be type list[dict]')
            if cls.id_column not in item:
                item[cls.id_column] = cls.generate_id()

        return cls().query_builder_class(model=cls).insert_many(items)

    def update(self, updates: dict, conditions: dict = None) -> SqlModel:
        """Persist the specified changes to the datastore. Return self
            in monad pattern. Raises TypeError or ValueError for invalid
            updates or conditions (self.data must include the id to
            update or conditions must be specified).
        """
        tert(type(updates) is dict, 'updates must be dict')
        tert (type(conditions) is dict or conditions is None,
            'conditions must be dict or None')
        vert(self.id_column in self.data or type(conditions) is dict,
            f'instance must have {self.id_column} or conditions defined')

        # first apply any updates to the instance
        for key in updates:
            if key in self.columns:
                self.data[key] = updates[key]

        # merge data into updates
        for key in self.data:
            if key in self.columns:
                updates[key] = self.data[key]

        # parse conditions
        conditions = conditions if conditions is not None else {}
        if self.id_column in self.data and self.id_column not in conditions:
            conditions[self.id_column] = self.data[self.id_column]

        # run update query
        self.query().update(updates, conditions)

        return self

    def save(self) -> SqlModel:
        """Persist to the datastore. Return self in monad pattern.
            Calls insert or update and raises appropriate errors.
        """
        if self.id_column in self.data:
            if self.find(self.data[self.id_column]) is not None:
                return self.update({})
        return self.insert(self.data)

    def delete(self) -> None:
        """Delete the record."""
        if self.id_column in self.data:
            self.query().equal(self.id_column, self.data[self.id_column]).delete()

    def reload(self) -> SqlModel:
        """Reload values from datastore. Return self in monad pattern.
            Raises UsageError if id is not set in self.data.
        """
        tressa(self.id_column in self.data,
               'id_column must be set in self.data to reload from db')
        reloaded = self.find(self.data[self.id_column])
        if reloaded:
            self.data = reloaded.data
        return self

    @classmethod
    def query(cls, conditions: dict = None, connection_info: str = None) -> QueryBuilderProtocol:
        """Returns a query builder with any conditions provided.
            Conditions are parsed as key=value and cannot handle other
            comparison types. If connection_info is not injected and was
            added as a class attribute, that class attribute will be
            passed to the query_builder_class instead.
        """
        if not connection_info and hasattr(cls, 'connection_info'):
            connection_info = cls.connection_info
        sqb = cls().query_builder_class(model=cls, connection_info=connection_info)

        if conditions is not None:
            for key in conditions:
                sqb.equal(key, conditions[key])

        return sqb


class SqliteModel(SqlModel):
    """Model for interacting with sqlite database."""
    file_path: str = 'database.db'

    def __init__(self, data: dict = {}) -> None:
        """Initialize the instance."""
        self.query_builder_class = SqliteQueryBuilder
        super().__init__(data)

    def __repr__(self) -> str:
        """Pretty str representation."""
        return f"{self.__class__.__name__}(file_path='{self.file_path}', " + \
            f"table='{self.table}', " +\
            f"id_column='{self.id_column}', columns={self.columns}, data={self.data})"


@dataclass
class JoinedModel:
    """Class for representing the results of SQL JOIN queries."""
    models: list[Type[SqlModel]]
    data: dict

    def __init__(self, models: list[Type[SqlModel]], data: dict) -> None:
        """Initialize the instance. Raises TypeError for invalid models
            or data.
        """
        self.models = models
        self.data = self.parse_data(models, data)

    def __repr__(self) -> str:
        """Pretty str representation."""
        return f"{self.__class__.__name__}" + \
            f"(models={[m.__name__ for m in self.models]}, data={self.data})"

    @staticmethod
    def parse_data(models: list[Type[SqlModel]], data: dict) -> dict:
        """Parse data of form {table.column:value} to
            {table:{column:value}}. Raises TypeError for invalid models
            or data.
        """
        tert(type(models) is list, 'models must be list[Type[SqlModel]]')
        tert(all([issubclass(m, SqlModel) for m in models]),
             'models must be list[Type[SqlModel]]')
        tert(type(data) is dict, 'data must be dict')
        result = {}
        for model in models:
            result[model.table] = {}
            for column in model.columns:
                key = f"{model.table}.{column}"
                value = data.get(key)
                if value:
                    result[model.table][column] = value
        return result

    def get_models(self) -> list[SqlModel]:
        """Returns the underlying models. Calls the find method for each
            model.
        """
        instances = []
        for model in self.models:
            if model.table in self.data:
                if model.id_column in self.data[model.table]:
                    model_id = self.data[model.table][model.id_column]
                    instances.append(model.find(model_id))
        return instances


@dataclass
class JoinSpec:
    """Class for representing joins to be executed by a query builder."""
    kind: str = field()
    model_1: SqlModel = field()
    column_1: str = field()
    comparison: str = field()
    model_2: SqlModel = field()
    column_2: str = field()


@dataclass
class Row:
    """Class for representing a row from a query when no better model exists."""
    data: dict = field()


def dynamic_sqlite_model(db_file_path: str|bytes, table_name: str = '') -> Type[SqlModel]:
    """Generates a dynamic sqlite model for instantiating context
        managers. Raises TypeError for invalid db_file_path or
        table_name.
    """
    tert(type(db_file_path) in (str, bytes), 'db_file_path must be str|bytes')
    tert(type(table_name) is str, 'table_name must be str')
    class DynamicModel(SqliteModel):
        file_path: str = db_file_path
        table: str = table_name
    return DynamicModel


@dataclass
class SqlQueryBuilder:
    """Main query builder class. Extend with child class to bind to a
        specific database, c.f. SqliteQueryBuilder.
    """
    model: Type[SqlModel]
    context_manager: Type[DBContextProtocol] = field(default=None)
    connection_info: str = field(default='')
    clauses: list = field(default_factory=list)
    params: list = field(default_factory=list)
    order_column: str = field(default=None)
    order_dir: str = field(default='desc')
    limit: int = field(default=None)
    offset: int = field(default=None)
    joins: list[JoinSpec] = field(default_factory=list)
    columns: list[str] = field(default=None)
    grouping: str = field(default=None)

    @property
    def model(self) -> Type[SqlModel]:
        """The model type that non-joined query results will be. Setting
            raises TypeError if supplied something other than a subclass
            of SqlModel.
        """
        return self._model

    @model.setter
    def model(self, model: Type[SqlModel]) -> None:
        tert(type(model) is type, 'model must be SqlModel subclass')
        tert(issubclass(model, SqlModel), 'model must be SqlModel subclass')
        self._model = model

    def equal(self, column: str, data: Any) -> SqlQueryBuilder:
        """Save the 'column = data' clause and param, then return self.
            Raises TypeError for invalid column.
        """
        tert(type(column) is str, 'column must be str')
        self.clauses.append(f'{column} = ?')
        self.params.append(data)
        return self

    def not_equal(self, column: str, data: Any) -> SqlQueryBuilder:
        """Save the 'column != data' clause and param, then return self.
            Raises TypeError for invalid column.
        """
        tert(type(column) is str, 'column must be str')
        self.clauses.append(f'{column} != ?')
        self.params.append(data)
        return self

    def less(self, column: str, data: Any) -> SqlQueryBuilder:
        """Save the 'column < data' clause and param, then return self.
            Raises TypeError for invalid column.
        """
        tert(type(column) is str, 'column must be str')
        self.clauses.append(f'{column} < ?')
        self.params.append(data)
        return self

    def greater(self, column: str, data: Any) -> SqlQueryBuilder:
        """Save the 'column > data' clause and param, then return self.
            Raises TypeError for invalid column.
        """
        tert(type(column) is str, 'column must be str')
        self.clauses.append(f'{column} > ?')
        self.params.append(data)
        return self

    def starts_with(self, column: str, data: str) -> SqlQueryBuilder:
        """Save the 'column like data%' clause and param, then return
            self. Raises TypeError or ValueError for invalid column or
            data.
        """
        tert(type(column) is str, 'column must be str')
        tert(type(data) is str, 'data must be str')
        vert(len(column), 'column cannot be empty')
        vert(len(data), 'data cannot be empty')
        self.clauses.append(f'{column} like ?')
        self.params.append(f'{data}%')
        return self

    def contains(self, column: str, data: str) -> SqlQueryBuilder:
        """Save the 'column like %data%' clause and param, then return
            self. Raises TypeError or ValueError for invalid column or
            data.
        """
        tert(type(column) is str, 'column must be str')
        tert(type(data) is str, 'data must be str')
        vert(len(column), 'column cannot be empty')
        vert(len(data), 'data cannot be empty')
        self.clauses.append(f'{column} like ?')
        self.params.append(f'%{data}%')
        return self

    def excludes(self, column: str, data: str) -> SqlQueryBuilder:
        """Save the 'column not like %data%' clause and param, then
            return self. Raises TypeError or ValueError for invalid
            column or data.
        """
        tert(type(column) is str, 'column must be str')
        tert(type(data) is str, 'data must be str')
        vert(len(column), 'column cannot be empty')
        vert(len(data), 'data cannot be empty')
        self.clauses.append(f'{column} not like ?')
        self.params.append(f'%{data}%')
        return self

    def ends_with(self, column: str, data: str) -> SqlQueryBuilder:
        """Save the 'column like %data' clause and param, then return
            self. Raises TypeError or ValueError for invalid column or
            data.
        """
        tert(type(column) is str, 'column must be str')
        tert(type(data) is str, 'data must be str')
        vert(len(column), 'column cannot be empty')
        vert(len(data), 'data cannot be empty')
        self.clauses.append(f'{column} like ?')
        self.params.append(f'%{data}')
        return self

    def is_in(self, column: str, data: Union[tuple, list]) -> SqlQueryBuilder:
        """Save the 'column in data' clause and param, then return self.
            Raises TypeError or ValueError for invalid column or data.
        """
        tert(type(column) is str, 'column must be str')
        tert(type(data) in (tuple, list), 'data must be tuple or list')
        vert(len(column), 'column cannot be empty')
        vert(len(data), 'data cannot be empty')
        self.clauses.append(f'{column} in ({",".join(["?" for _ in data])})')
        self.params.extend(data)
        return self

    def not_in(self, column: str, data: Union[tuple, list]) -> SqlQueryBuilder:
        """Save the 'column not in data' clause and param, then return
            self. Raises TypeError or ValueError for invalid column or
            data.
        """
        tert(type(column) is str, 'column must be str')
        tert(type(data) in (tuple, list), 'data must be tuple or list')
        vert(len(column), 'column cannot be empty')
        vert(len(data), 'data cannot be empty')
        self.clauses.append(f'{column} not in ({",".join(["?" for _ in data])})')
        self.params.extend(data)
        return self

    def order_by(self, column: str, direction: str = 'desc') -> SqlQueryBuilder:
        """Sets query order. Raises TypeError or ValueError for invalid
            column or direction.
        """
        tert(type(column) is str, 'column must be str')
        tert(type(direction) is str, 'direction must be str')
        vert(column in self.model.columns, 'unrecognized column')
        vert(direction in ('asc', 'desc'), 'direction must be asc or desc')

        self.order_column = column
        self.order_dir = direction

        return self

    def skip(self, offset: int) -> SqlQueryBuilder:
        """Sets the number of rows to skip. Raises TypeError or
            ValueError for invalid offset.
        """
        tert(type(offset) is int, 'offset must be positive int')
        vert(offset >= 0, 'offset must be positive int')
        self.offset = offset
        return self

    def reset(self) -> SqlQueryBuilder:
        """Returns a fresh instance using the configured model."""
        return self.__class__(model=self.model)

    def insert(self, data: dict) -> Optional[SqlModel]:
        """Insert a record and return a model instance. Raises TypeError
            for invalid data or ValueError if a record with the same id
            already exists.
        """
        tert(isinstance(data, dict), 'data must be dict')
        columns, params = [], []

        for key in data:
            if key in data:
                if key in self.model.columns:
                    columns.append(key)
                    params.append(data[key])

        for key in self.model.columns:
            if key not in data and key != self.model.id_column:
                data[key] = None

        if self.model.id_column in columns:
            vert(self.find(data[self.model.id_column]) is None,
                 'record with this id already exists')

        sql = f'insert into {self.model.table} ({",".join(columns)})' + \
            f' values ({",".join(["?" for p in params])})'

        with self.context_manager(self.model, self.connection_info) as cursor:
            cursor.execute(sql, params)
            return self.model(data=data)

    def insert_many(self, items: list[dict]) -> int:
        """Insert a batch of records and return the number inserted.
            Raises TypeError for invalid items.
        """
        tert(isinstance(items, list), 'items must be list[dict]')
        rows = []
        for item in items:
            tert(isinstance(item, dict), 'items must be list[dict]')
            for key in self.model.columns:
                if key not in item:
                    item[key] = None
            rows.append(tuple([item[key] for key in self.model.columns]))

        sql = f"insert into {self.model.table} values "\
            f"({','.join(['?' for f in self.model.columns])})"

        with self.context_manager(self.model, self.connection_info) as cursor:
            return cursor.executemany(sql, rows).rowcount

    def find(self, id: Any) -> Optional[SqlModel]:
        """Find a record by its id and return it."""
        with self.context_manager(self.model, self.connection_info) as cursor:
            cursor.execute(
                f'select {",".join(self.model.columns)} from {self.model.table}' +
                f' where {self.model.id_column} = ?',
                [id]
            )
            result = cursor.fetchone()

        if result is None:
            return None

        data = {
            column: value
            for column, value in zip(self.model.columns, result)
        }

        return self.model(data=data)

    def join(self, model: Type[SqlModel]|list[Type[SqlModel]], on: list[str],
             kind: str = "inner") -> SqlQueryBuilder:
        """Prepares the query for a join over multiple tables/models.
            Raises TypeError or ValueError for invalid model, on, or
            kind.
        """
        tert(type(model) in (type, list),
             "model must be Type[SqlModel] or list[Type[SqlModel]]")
        if type(model) is list:
            tert(all([type(m) is type and issubclass(m, SqlModel) for m in model]),
                 "each model must be Type[SqlModel]")
        tert(type(on) is list, "on must be list[str]")
        tert(all([type(o) is str for o in on]), "on must be list[str]")
        tert(type(kind) is str, "kind must be str")
        vert(len(on) in (2, 3),
             "on must be of form [column, column] or [column, comparison, column]")
        vert(kind in ("inner", "outer", "left", "right", "full"))

        join = [kind]

        def get_join(model: Type[SqlModel], column: str) -> str:
            if "." in column:
                return [model, column]
            else:
                tert(column in model.columns,
                     f"column name must be valid for {model.table}")
                return [model, f"{model.table}.{column}"]

        if len(on) == 2:
            join.extend(get_join(self.model, on[0]))
            join.append('=')
            join.extend(get_join(model, on[1]))
        elif len(on) == 3:
            vert(on[1] in ('=', '>', '>=', '<', '<=', '<>'),
                 "comparison must be in (=, >, >=, <, <=, <>)")
            join.extend(get_join(self.model, on[0]))
            join.append(on[1])
            join.extend(get_join(model, on[2]))

        self.joins.append(JoinSpec(*join))

        return self

    def select(self, columns: list[str]) -> QueryBuilderProtocol:
        """Sets the columns to select. Raises TypeError for invalid
            columns.
        """
        tert(type(columns) in (list, tuple), "select columns must be list[str]")
        tert(all([type(c) is str for c in columns]), "select columns must be list[str]")
        self.columns = [*columns]
        return self

    def group(self, by: str) -> SqlQueryBuilder:
        """Adds a GROUP BY constraint. Raises TypeError for invalid by."""
        tert(type(by) is str, "group by parameter must be str")
        self.grouping = by
        return self

    def get(self) -> list[SqlModel]|list[JoinedModel]|list[Row]:
        """Run the query on the datastore and return a list of results.
            Return SqlModels when running a simple query. Return
            JoinedModels when running a JOIN query. Return Rows when
            running a non-joined GROUP BY query.
        """
        if len(self.joins) > 0:
            return self._get_joined()
        return self._get_normal()

    def _get_joined(self) -> list[JoinedModel]:
        """Run the query on the datastore and return a list of joined
            results. Used by the `get` method when appropriate. Do not
            call this method manually.
        """
        classes: list[SqlModel] = [self.model]
        columns: list[str] = []
        for join in self.joins:
            if join.model_2 not in classes:
                classes.append(join.model_2)

        if self.columns:
            columns = self.columns
        else:
            for modelclass in classes:
                columns.extend([
                    f"{modelclass.table}.{f}"
                    for f in modelclass.columns
                ])

        sql = f'select {",".join(columns)} from {self.model.table}'

        sql += ' ' + ''.join([
            f'{j.kind} join {j.model_2.table} on {j.column_1} {j.comparison} {j.column_2}'
            for j in self.joins
        ])

        if len(self.clauses) > 0:
            sql += ' where ' + ' and '.join(self.clauses)

        if self.grouping:
            sql += f' group by {self.grouping}'

        if self.order_column is not None:
            sql += f' order by {self.order_column} {self.order_dir}'

        if type(self.limit) is int and self.limit > 0:
            sql += f' limit {self.limit}'

            if type(self.offset) is int and self.offset > 0:
                sql += f' offset {self.offset}'

        with self.context_manager(self.model, self.connection_info) as cursor:
            cursor.execute(sql, self.params)
            rows = cursor.fetchall()
            models = [
                JoinedModel(classes, data={
                    key: value
                    for key, value in zip(columns, row)
                })
                for row in rows
            ]
            return models

    def _get_normal(self) -> list[SqlModel|Row]:
        """Run the query on the datastore and return a list of results
            without joins. Used by the `get` method when appropriate. Do
            not call this method manually.
        """
        columns: list[str] = self.columns or self.model.columns
        sql = f'select {",".join(columns)} from {self.model.table}'

        if len(self.clauses) > 0:
            sql += ' where ' + ' and '.join(self.clauses)

        if self.grouping:
            sql += f' group by {self.grouping}'

        if self.order_column is not None:
            sql += f' order by {self.order_column} {self.order_dir}'

        if type(self.limit) is int and self.limit > 0:
            sql += f' limit {self.limit}'

            if type(self.offset) is int and self.offset > 0:
                sql += f' offset {self.offset}'

        with self.context_manager(self.model, self.connection_info) as cursor:
            cursor.execute(sql, self.params)
            rows = cursor.fetchall()
            if self.grouping:
                models = [
                    Row(data={
                        key: value
                        for key, value in zip(columns, row)
                    })
                    for row in rows
                ]
            else:
                models = [
                    self.model(data={
                        key: value
                        for key, value in zip(columns, row)
                    })
                    for row in rows
                ]
            return models

    def count(self) -> int:
        """Returns the number of records matching the query."""
        sql = f'select count(*) from {self.model.table}'

        if len(self.clauses) > 0:
            sql += ' where ' + ' and '.join(self.clauses)

        with self.context_manager(self.model, self.connection_info) as cursor:
            cursor.execute(sql, self.params)
            return cursor.fetchone()[0]

    def take(self, limit: int) -> Optional[list[SqlModel]]:
        """Takes the specified number of rows. Raises TypeError or
            ValueError for invalid limit.
        """
        tert(type(limit) is int, 'limit must be positive int')
        vert(limit > 0, 'limit must be positive int')
        self.limit = limit
        return self.get()

    def chunk(self, number: int) -> Generator[list[SqlModel], None, None]:
        """Chunk all matching rows the specified number of rows at a
            time. Raises TypeError or ValueError for invalid number.
        """
        tert(type(number) is int, 'number must be int > 0')
        vert(number > 0, 'number must be int > 0')
        return self._chunk(number)

    def _chunk(self, number: int) -> Generator[list[SqlModel], None, None]:
        """Create the generator for chunking."""
        original_offset = self.offset
        self.offset = self.offset or 0
        result = self.take(number)

        while len(result) > 0:
            yield result
            self.offset += number
            result = self.take(number)

        self.offset = original_offset

    def first(self) -> Optional[SqlModel]:
        """Run the query on the datastore and return the first result."""
        sql = f'select {",".join(self.model.columns)} from {self.model.table}'

        if len(self.clauses) > 0:
            sql += ' where ' + ' and '.join(self.clauses)

        if self.order_column is not None:
            sql += f' order by {self.order_column} {self.order_dir}'

        with self.context_manager(self.model, self.connection_info) as cursor:
            cursor.execute(sql, self.params)
            row = cursor.fetchone()

            if row is None:
                return None

            return self.model(data={
                key: value
                for key, value in zip(self.model.columns, row)
            })

    def update(self, updates: dict, conditions: dict = {}) -> int:
        """Update the datastore and return number of records updated.
            Raises TypeError for invalid updates or conditions.
        """
        tert(type(updates) is dict, 'updates must be dict')
        tert(type(conditions) is dict, 'conditions must be dict')

        # parse conditions
        condition_columns, condition_params = self.clauses[:], self.params[:]

        for key in conditions:
            if key in self.model.columns:
                condition_columns.append(f'{key} = ?')
                condition_params.append(conditions[key])

        # parse updates
        columns, params = [], []

        for key in updates:
            if key in self.model.columns:
                columns.append(f'{key} = ?')
                params.append(updates[key])

        if len(columns) == 0:
            return 0

        sql = f'update {self.model.table} set {",".join(columns)}'
        if len(condition_columns) > 0:
            sql += f' where {" and ".join(condition_columns)}'

        # update database
        with self.context_manager(self.model, self.connection_info) as cursor:
            return cursor.execute(sql, [*params, *condition_params]).rowcount

    def delete(self) -> int:
        """Delete the records that match the query and return the number
            of deleted records.
        """
        sql = f'delete from {self.model.table}'

        if len(self.clauses) > 0:
            sql += ' where ' + ' and '.join(self.clauses)

        with self.context_manager(self.model, self.connection_info) as cursor:
            return cursor.execute(sql, self.params).rowcount

    def to_sql(self) -> str:
        """Return the sql where clause from the clauses and params."""
        bindings = []

        for clause, param in zip(self.clauses, self.params):
            if type(param) in (tuple, list):
                bindings.append(clause.replace('?', f'[{",".join(param)}]'))
            else:
                bindings.append(clause.replace('?', param))

        sql = f' where {" and ".join(bindings)}'

        if self.order_column is not None:
            sql += f' order by {self.order_column} {self.order_dir}'

        if type(self.limit) is int and self.limit > 0:
            sql += f' limit {self.limit}'

            if type(self.offset) is int and self.offset > 0:
                sql += f' offset {self.offset}'

        return sql

    def execute_raw(self, sql: str) -> tuple[int, Any]:
        """Execute raw SQL against the database. Return rowcount and fetchall
            results.
        """
        tert(type(sql) is str, 'sql must be str')
        with self.context_manager(self.model, self.connection_info) as cursor:
            cursor.execute(sql)
            return (cursor.rowcount, cursor.fetchall())


class SqliteQueryBuilder(SqlQueryBuilder):
    """SqlQueryBuilder using a SqliteContext."""
    def __init__(self, model: type, *args, **kwargs) -> None:
        """Initialize the instance."""
        super().__init__(model, SqliteContext, *args, **kwargs)


class DeletedModel(SqlModel):
    """Model for preserving and restoring deleted HashedModel records."""
    table: str = 'deleted_records'
    columns: tuple = ('id', 'model_class', 'record_id', 'record')
    id: str
    model_class: str
    record_id: str
    record: bytes

    def restore(self, inject: dict = {}) -> SqlModel:
        """Restore a deleted record, remove from deleted_records, and
            return the restored model. Raises ValueError if model_class
            cannot be found. Raises TypeError if model_class is not a
            subclass of SqlModel. Uses packify.unpack to unpack the
            record. Raises TypeError if packed record is not a dict.
        """
        dependencies = {**globals(), **inject}
        vert(self.data['model_class'] in dependencies,
            'model_class must be accessible')
        model_class = dependencies[self.data['model_class']]
        tert(issubclass(model_class, SqlModel),
            'related_model must inherit from SqlModel')

        decoded = packify.unpack(self.data['record'])
        tert(type(decoded) is dict, 'encoded record is not a dict')

        if model_class.id_column not in decoded:
            decoded[model_class.id_column] = self.data['record_id']

        model = model_class.insert(decoded)
        self.delete()

        return model


class DeletedSqliteModel(DeletedModel, SqliteModel):
    """Model for preserving and restoring deleted HashedSqliteModel records."""


class HashedModel(SqlModel):
    """Model for interacting with sql database using hash for id."""
    table: str = 'hashed_records'
    columns: tuple = ('id', 'details')
    id: str
    details: bytes

    @classmethod
    def generate_id(cls, data: dict) -> str:
        """Generate an id by hashing the non-id contents. Raises
            TypeError for unencodable type (calls packify.pack).
        """
        data = { k: data[k] for k in data if k in cls.columns and k != cls.id_column }
        preimage = packify.pack(data)
        return sha256(preimage).digest().hex()

    @classmethod
    def insert(cls, data: dict) -> Optional[HashedModel]:
        """Insert a new record to the datastore. Return instance. Raises
            TypeError for non-dict data or unencodable type (calls
            cls.generate_id, which calls packify.pack).
        """
        tert(isinstance(data, dict), 'data must be dict')
        data[cls.id_column] = cls.generate_id(data)

        return cls.query().insert(data)

    @classmethod
    def insert_many(cls, items: list[dict]) -> int:
        """Insert a batch of records and return the number of items
            inserted. Raises TypeError for invalid items or unencodable
            value (calls cls.generate_id, which calls packify.pack).
        """
        tert(isinstance(items, list), 'items must be type list[dict]')
        for item in items:
            tert(isinstance(item, dict), 'items must be type list[dict]')
            item[cls.id_column] = cls.generate_id(item)

        return cls.query().insert_many(items)

    def update(self, updates: dict) -> HashedModel:
        """Persist the specified changes to the datastore, creating a new
            record in the process. Return new record in monad pattern.
            Raises TypeError or ValueError for invalid updates.
        """
        tert(type(updates) is dict, 'updates must be dict')

        # merge data into updates
        for key in self.data:
            if key in self.columns and not key in updates:
                updates[key] = self.data[key]

        for key in updates:
            vert(key in self.columns, f'unrecognized column: {key}')

        # insert new record or update and return
        if self.data[self.id_column]:
            instance = self.insert(updates)
            self.delete()
        else:
            instance = self.insert(updates)
        return instance

    def delete(self) -> DeletedModel:
        """Delete the model, putting it in the deleted_records table,
            then return the DeletedModel. Raises packify.UsageError for
            unserializable data.
        """
        model_class = self.__class__.__name__
        record_id = self.data[self.id_column]
        record = packify.pack(self.data)
        deleted = DeletedModel.insert({
            'model_class': model_class,
            'record_id': record_id,
            'record': record
        })
        super().delete()
        return deleted


class HashedSqliteModel(SqliteModel):
    """Model for interacting with sqlite database using hash for id."""

    def delete(self) -> DeletedSqliteModel:
        """Delete the model, putting it in the deleted_records table,
            then return the DeletedSqliteModel. Raises packify.UsageError for
            unserializable data.
        """
        model_class = self.__class__.__name__
        record_id = self.data[self.id_column]
        record = packify.pack(self.data)
        deleted = DeletedSqliteModel.insert({
            'model_class': model_class,
            'record_id': record_id,
            'record': record
        })
        super().delete()
        return deleted


class Attachment(HashedModel):
    """Class for attaching immutable details to a record."""
    table: str = 'attachments'
    columns: tuple = ('id', 'related_model', 'related_id', 'details')
    id: str
    related_model: str
    related_id: str
    details: bytes|None
    _related: SqlModel = None
    _details: packify.SerializableType = None

    def related(self, reload: bool = False) -> SqlModel:
        """Return the related record."""
        if self._related is None or reload:
            vert(self.data['related_model'] in globals(), 'model_class must be accessible')
            model_class = globals()[self.data['related_model']]
            tert(issubclass(model_class, SqlModel),
                'related_model must inherit from SqlModel')
            self._related = model_class.find(self.data['related_id'])
        return self._related

    def attach_to(self, related: SqlModel) -> Attachment:
        """Attach to related model then return self."""
        tert(issubclass(related.__class__, SqlModel),
            'related must inherit from SqlModel')
        self.data['related_model'] = related.__class__.__name__
        self.data['related_id'] = related.data[related.id_column]
        return self

    def get_details(self, reload: bool = False) -> packify.SerializableType:
        """Decode packed bytes to dict."""
        if self._details is None or reload:
            self._details = packify.unpack(self.data['details'])
        return self._details

    def set_details(self, details: packify.SerializableType = {}) -> Attachment:
        """Set the details column using either supplied data or by
            packifying self._details. Return self in monad pattern.
            Raises packify.UsageError or TypeError if details contains
            unseriazliable type.
        """
        if details:
            self._details = details
        self.data['details'] = packify.pack(self._details)
        return self

    @classmethod
    def insert(cls, data: dict) -> Optional[Attachment]:
        """Redefined for better LSP support."""
        return super().insert(data)


class AttachmentSqlite(Attachment, SqliteModel):
    """Class for attaching immutable details to a sqlite record."""
    ...
