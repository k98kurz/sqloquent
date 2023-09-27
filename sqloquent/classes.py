from __future__ import annotations
from .errors import (tert, vert)
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
import json
import sqlite3


class SqliteContext:
    """Context manager for sqlite."""
    connection: sqlite3.Connection
    cursor: sqlite3.Cursor

    def __init__(self, model: type[SqliteModel]) -> None:
        tert(type(model) is type, 'model must be child class of SqliteModel')
        tert(issubclass(model, SqliteModel),
            'model must be child class of SqliteModel')
        tert(type(model.file_path) in (str, bytes),
            'model.file_path must be str or bytes')
        self.connection = sqlite3.connect(model.file_path)
        self.cursor = self.connection.cursor()

    def __enter__(self) -> CursorProtocol:
        return self.cursor

    def __exit__(self, __exc_type: Optional[Type[BaseException]],
                __exc_value: Optional[BaseException],
                __traceback: Optional[TracebackType]) -> None:
        if __exc_type is not None:
            self.connection.rollback()
        else:
            self.connection.commit()

        self.connection.close()


class SqlModel:
    """General model for mapping a SQL row to an in-memory object."""
    table: str = 'example'
    id_field: str = 'id'
    fields: tuple = ('id', 'name')
    query_builder_class: Type[QueryBuilderProtocol]
    data: dict

    def __init__(self, data: dict = {}) -> None:
        self.data = {}

        for key in data:
            if key in self.fields and type(key) is str:
                self.data[key] = data[key]

        if hasattr(self, '_post_init_hooks'):
            tert(isinstance(self._post_init_hooks, dict),
                '_post_init_hooks must be a dict mapping names to Callables')
            for _, call in self._post_init_hooks.items():
                vert(callable(call),
                    '_post_init_hooks must be a dict mapping names to Callables')
                call(self)

    @staticmethod
    def encode_value(val: Any) -> str:
        """Encode a value for hashing."""
        encodings = {
            'str': lambda v: v,
            'bytes': lambda v: v.hex(),
            'int': lambda v: v,
            'list': lambda v: [SqlModel.encode_value(i) for i in v],
            'tuple': lambda v: [SqlModel.encode_value(i) for i in v],
            'dict': lambda v: {
                SqlModel.encode_value(k): SqlModel.encode_value(v[k])
                for k in v
            },
            'NoneType': lambda v: v,
        }

        tert(type(val).__name__ in encodings, 'unrecognized type')
        return encodings[type(val).__name__](val)

    def __hash__(self) -> int:
        """Allow inclusion in sets."""
        data = json.dumps(
            self.encode_value(self.data),
            sort_keys=True
        )
        return hash(bytes(data, 'utf-8'))

    def __eq__(self, other) -> bool:
        if type(other) != type(self):
            return False

        return hash(self) == hash(other)

    def __repr__(self) -> str:
        return f"SqlModel(table='{self.table}', id_field='{self.id_field}', " + \
            f"fields={self.fields}, data={self.data})"

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
        """Insert a new record to the datastore. Return instance."""
        tert(isinstance(data, dict), 'data must be dict')
        if cls.id_field not in data:
            data[cls.id_field] = cls.generate_id()

        return cls().query_builder_class(model=cls).insert(data)

    @classmethod
    def insert_many(cls, items: list[dict]) -> int:
        """Insert a batch of records and return the number of items inserted."""
        tert(isinstance(items, list), 'items must be type list[dict]')
        for item in items:
            tert(isinstance(item, dict), 'items must be type list[dict]')
            if cls.id_field not in item:
                item[cls.id_field] = cls.generate_id()

        return cls().query_builder_class(model=cls).insert_many(items)

    def update(self, updates: dict, conditions: dict = None) -> SqlModel:
        """Persist the specified changes to the datastore. Return self
            in monad pattern.
        """
        tert(type(updates) is dict, 'updates must be dict')
        tert (type(conditions) is dict or conditions is None,
            'conditions must be dict or None')
        vert(self.id_field in self.data or type(conditions) is dict,
            f'instance must have {self.id_field} or conditions defined')

        # first apply any updates to the instance
        for key in updates:
            if key in self.fields:
                self.data[key] = updates[key]

        # merge data into updates
        for key in self.data:
            if key in self.fields:
                updates[key] = self.data[key]

        # parse conditions
        conditions = conditions if conditions is not None else {}
        if self.id_field in self.data and self.id_field not in conditions:
            conditions[self.id_field] = self.data[self.id_field]

        # run update query
        self.query().update(updates, conditions)

        return self

    def save(self) -> SqlModel:
        """Persist to the datastore. Return self in monad pattern."""
        if self.id_field in self.data:
            if self.find(self.data[self.id_field]) is not None:
                return self.update({})
        return self.insert(self.data)

    def delete(self) -> None:
        """Delete the record."""
        if self.id_field in self.data:
            self.query().equal(self.id_field, self.data[self.id_field]).delete()

    def reload(self) -> SqlModel:
        """Reload values from datastore. Return self in monad pattern."""
        if self.id_field in self.data:
            reloaded = self.find(self.data[self.id_field])
            if reloaded:
                self.data = reloaded.data
        return self

    @classmethod
    def query(cls, conditions: dict = None) -> QueryBuilderProtocol:
        """Returns a query builder with any conditions provided."""
        sqb = cls().query_builder_class(model=cls)

        if conditions is not None:
            for key in conditions:
                sqb.equal(key, conditions[key])

        return sqb


class SqliteModel(SqlModel):
    """Model for interacting with sqlite database."""
    file_path: str = 'database.db'

    def __init__(self, data: dict = {}) -> None:
        self.query_builder_class = SqliteQueryBuilder
        super().__init__(data)

    def __repr__(self) -> str:
        return f"SqliteModel(file_path='{self.file_path}', table='{self.table}', " +\
            f"id_field='{self.id_field}', fields={self.fields}, data={self.data})"


@dataclass
class JoinedModel:
    """Class for representing the results of SQL JOIN queries."""
    models: list[Type[SqlModel]]
    data: dict

    def __init__(self, models: list[Type[SqlModel]], data: dict) -> None:
        self.models = models
        self.data = self.parse_data(models, data)

    def __repr__(self) -> str:
        return f"JoinedModel(models={[m.__name__ for m in self.models]}, " + \
            f"data={self.data})"

    @staticmethod
    def parse_data(models: list[Type[SqlModel]], data: dict) -> dict:
        """Parse data of form {table.column:value} to {table:{column:value}}."""
        result = {}
        for model in models:
            result[model.table] = {}
            for column in model.fields:
                key = f"{model.table}.{column}"
                value = data.get(key)
                if value:
                    result[model.table][column] = value
        return result

    def get_models(self) -> list[SqlModel]:
        """Returns the underlying models."""
        instances = []
        for model in self.models:
            if model.table in self.data:
                if model.id_field in self.data[model.table]:
                    model_id = self.data[model.table][model.id_field]
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
class Row(SqlModel):
    """Class for representing a row from a query when no better model exists."""
    table: str = field()
    data: dict = field()


def dynamic_sqlite_model(db_file_path: str, table_name: str = '') -> type[SqlModel]:
    """Generates a dynamic sqlite model for instantiating context managers."""
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
    clauses: list = field(default_factory=list)
    params: list = field(default_factory=list)
    order_field: str = field(default=None)
    order_dir: str = field(default='desc')
    limit: int = field(default=None)
    offset: int = field(default=None)
    joins: list[JoinSpec] = field(default_factory=list)
    columns: list[str] = field(default=None)
    grouping: str = field(default=None)

    @property
    def model(self) -> type:
        """The model type that non-joined query results will be."""
        return self._model

    @model.setter
    def model(self, model: type) -> None:
        tert(type(model) is type, 'model must be SqlModel subclass')
        tert(issubclass(model, SqlModel), 'model must be SqlModel subclass')
        self._model = model

    def equal(self, field: str, data: Any) -> SqlQueryBuilder:
        """Save the 'field = data' clause and param, then return self."""
        tert(type(field) is str, 'field must be str')
        self.clauses.append(f'{field} = ?')
        self.params.append(data)
        return self

    def not_equal(self, field: str, data: Any) -> SqlQueryBuilder:
        """Save the 'field != data' clause and param, then return self."""
        tert(type(field) is str, 'field must be str')
        self.clauses.append(f'{field} != ?')
        self.params.append(data)
        return self

    def less(self, field: str, data: Any) -> SqlQueryBuilder:
        """Save the 'field < data' clause and param, then return self."""
        tert(type(field) is str, 'field must be str')
        self.clauses.append(f'{field} < ?')
        self.params.append(data)
        return self

    def greater(self, field: str, data: Any) -> SqlQueryBuilder:
        """Save the 'field > data' clause and param, then return self."""
        tert(type(field) is str, 'field must be str')
        self.clauses.append(f'{field} > ?')
        self.params.append(data)
        return self

    def starts_with(self, field: str, data: str) -> SqlQueryBuilder:
        """Save the 'field like data%' clause and param, then return self."""
        tert(type(field) is str, 'field must be str')
        tert(type(data) is str, 'data must be str')
        vert(len(field), 'field cannot be empty')
        vert(len(data), 'data cannot be empty')
        self.clauses.append(f'{field} like ?')
        self.params.append(f'{data}%')
        return self

    def contains(self, field: str, data: str) -> SqlQueryBuilder:
        """Save the 'field like %data%' clause and param, then return self."""
        tert(type(field) is str, 'field must be str')
        tert(type(data) is str, 'data must be str')
        vert(len(field), 'field cannot be empty')
        vert(len(data), 'data cannot be empty')
        self.clauses.append(f'{field} like ?')
        self.params.append(f'%{data}%')
        return self

    def excludes(self, field: str, data: str) -> SqlQueryBuilder:
        """Save the 'field not like %data%' clause and param, then return self."""
        tert(type(field) is str, 'field must be str')
        tert(type(data) is str, 'data must be str')
        vert(len(field), 'field cannot be empty')
        vert(len(data), 'data cannot be empty')
        self.clauses.append(f'{field} not like ?')
        self.params.append(f'%{data}%')
        return self

    def ends_with(self, field: str, data: str) -> SqlQueryBuilder:
        """Save the 'field like %data' clause and param, then return self."""
        tert(type(field) is str, 'field must be str')
        tert(type(data) is str, 'data must be str')
        vert(len(field), 'field cannot be empty')
        vert(len(data), 'data cannot be empty')
        self.clauses.append(f'{field} like ?')
        self.params.append(f'%{data}')
        return self

    def is_in(self, field: str, data: Union[tuple, list]) -> SqlQueryBuilder:
        """Save the 'field in data' clause and param, then return self."""
        tert(type(field) is str, 'field must be str')
        tert(type(data) in (tuple, list), 'data must be tuple or list')
        vert(len(field), 'field cannot be empty')
        vert(len(data), 'data cannot be empty')
        self.clauses.append(f'{field} in ({",".join(["?" for _ in data])})')
        self.params.extend(data)
        return self

    def not_in(self, field: str, data: Union[tuple, list]) -> SqlQueryBuilder:
        """Save the 'field not in data' clause and param, then return self."""
        tert(type(field) is str, 'field must be str')
        tert(type(data) in (tuple, list), 'data must be tuple or list')
        vert(len(field), 'field cannot be empty')
        vert(len(data), 'data cannot be empty')
        self.clauses.append(f'{field} not in ({",".join(["?" for _ in data])})')
        self.params.extend(data)
        return self

    def order_by(self, field: str, direction: str = 'desc') -> SqlQueryBuilder:
        """Sets query order."""
        tert(type(field) is str, 'field must be str')
        tert(type(direction) is str, 'direction must be str')
        vert(field in self.model.fields, 'unrecognized field')
        vert(direction in ('asc', 'desc'), 'direction must be asc or desc')

        self.order_field = field
        self.order_dir = direction

        return self

    def skip(self, offset: int) -> SqlQueryBuilder:
        """Sets the number of rows to skip."""
        tert(type(offset) is int, 'offset must be positive int')
        vert(offset >= 0, 'offset must be positive int')
        self.offset = offset
        return self

    def reset(self) -> SqlQueryBuilder:
        """Returns a fresh instance using the configured model."""
        return self.__class__(model=self.model)

    def insert(self, data: dict) -> Optional[SqlModel]:
        """Insert a record and return a model instance."""
        tert(isinstance(data, dict), 'data must be dict')
        fields, params = [], []

        for key in data:
            if key in data:
                if key in self.model.fields:
                    fields.append(key)
                    params.append(data[key])

        for key in self.model.fields:
            if key not in data and key != self.model.id_field:
                data[key] = None

        if self.model.id_field in fields:
            vert(self.find(data[self.model.id_field]) is None,
                 'record with this id already exists')

        sql = f'insert into {self.model.table} ({",".join(fields)})' + \
            f' values ({",".join(["?" for p in params])})'

        with self.context_manager(self.model) as cursor:
            cursor.execute(sql, params)
            return self.model(data=data)

    def insert_many(self, items: list[dict]) -> int:
        """Insert a batch of records and return the number inserted."""
        tert(isinstance(items, list), 'items must be list[dict]')
        rows = []
        for item in items:
            tert(isinstance(item, dict), 'items must be list[dict]')
            for key in self.model.fields:
                if key not in item:
                    item[key] = None
            rows.append(tuple([item[key] for key in self.model.fields]))

        sql = f"insert into {self.model.table} values "\
            f"({','.join(['?' for f in self.model.fields])})"

        with self.context_manager(self.model) as cursor:
            return cursor.executemany(sql, rows).rowcount

    def find(self, id: Any) -> Optional[SqlModel]:
        """Find a record by its id and return it."""
        with self.context_manager(self.model) as cursor:
            cursor.execute(
                f'select {",".join(self.model.fields)} from {self.model.table}' +
                f' where {self.model.id_field} = ?',
                [id]
            )
            result = cursor.fetchone()

        if result is None:
            return None

        data = {
            field: value
            for field, value in zip(self.model.fields, result)
        }

        return self.model(data=data)

    def join(self, model: Type[SqlModel]|list[Type[SqlModel]], on: list[str],
             kind: str = "inner") -> SqlQueryBuilder:
        """Prepares the query for a join over multiple tables/models."""
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
                tert(column in model.fields,
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
        """Sets the columns to select."""
        tert(type(columns) in (list, tuple), "select columns must be list[str]")
        tert(all([type(c) is str for c in columns]), "select columns must be list[str]")
        self.columns = [*columns]
        return self

    def group(self, by: str) -> SqlQueryBuilder:
        """Adds a GROUP BY constraint."""
        tert(type(by) is str, "group by parameter must be str")
        self.grouping = by
        return self

    def get(self) -> list[SqlModel|JoinedModel|Row]:
        """Run the query on the datastore and return a list of results."""
        if len(self.joins) > 0:
            return self._get_joined()
        return self._get_normal()

    def _get_joined(self) -> list[JoinedModel]:
        """Run the query on the datastore and return a list of joined
            results.
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
                    for f in modelclass.fields
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

        if self.order_field is not None:
            sql += f' order by {self.order_field} {self.order_dir}'

        if type(self.limit) is int and self.limit > 0:
            sql += f' limit {self.limit}'

            if type(self.offset) is int and self.offset > 0:
                sql += f' offset {self.offset}'

        with self.context_manager(self.model) as cursor:
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
            without joins.
        """
        columns: list[str] = self.columns or self.model.fields
        sql = f'select {",".join(columns)} from {self.model.table}'

        if len(self.clauses) > 0:
            sql += ' where ' + ' and '.join(self.clauses)

        if self.grouping:
            sql += f' group by {self.grouping}'

        if self.order_field is not None:
            sql += f' order by {self.order_field} {self.order_dir}'

        if type(self.limit) is int and self.limit > 0:
            sql += f' limit {self.limit}'

            if type(self.offset) is int and self.offset > 0:
                sql += f' offset {self.offset}'

        with self.context_manager(self.model) as cursor:
            cursor.execute(sql, self.params)
            rows = cursor.fetchall()
            if self.grouping:
                models = [
                    Row(self.model.table, data={
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

        with self.context_manager(self.model) as cursor:
            cursor.execute(sql, self.params)
            return cursor.fetchone()[0]

    def take(self, limit: int) -> Optional[list[SqlModel]]:
        """Takes the specified number of rows."""
        tert(type(limit) is int, 'limit must be positive int')
        vert(limit > 0, 'limit must be positive int')
        self.limit = limit
        return self.get()

    def chunk(self, number: int) -> Generator[list[SqlModel], None, None]:
        """Chunk all matching rows the specified number of rows at a time."""
        tert(type(number) is int, 'number must be int > 0')
        vert(number > 0, 'number must be int > 0')
        return self._chunk(number)

    def _chunk(self, number: int) -> Generator[list[SqlModel], None, None]:
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
        sql = f'select {",".join(self.model.fields)} from {self.model.table}'

        if len(self.clauses) > 0:
            sql += ' where ' + ' and '.join(self.clauses)

        if self.order_field is not None:
            sql += f' order by {self.order_field} {self.order_dir}'

        with self.context_manager(self.model) as cursor:
            cursor.execute(sql, self.params)
            row = cursor.fetchone()

            if row is None:
                return None

            return self.model(data={
                key: value
                for key, value in zip(self.model.fields, row)
            })

    def update(self, updates: dict, conditions: dict = {}) -> int:
        """Update the datastore and return number of records updated."""
        tert(type(updates) is dict, 'updates must be dict')
        tert(type(conditions) is dict, 'conditions must be dict')

        # parse conditions
        condition_fields, condition_params = self.clauses[:], self.params[:]

        for key in conditions:
            if key in self.model.fields:
                condition_fields.append(f'{key} = ?')
                condition_params.append(conditions[key])

        # parse updates
        fields, params = [], []

        for key in updates:
            if key in self.model.fields:
                fields.append(f'{key} = ?')
                params.append(updates[key])

        if len(fields) == 0:
            return 0

        sql = f'update {self.model.table} set {",".join(fields)}'
        if len(condition_fields) > 0:
            sql += f' where {" and ".join(condition_fields)}'

        # update database
        with self.context_manager(self.model) as cursor:
            return cursor.execute(sql, [*params, *condition_params]).rowcount

    def delete(self) -> int:
        """Delete the records that match the query and return the number
            of deleted records.
        """
        sql = f'delete from {self.model.table}'

        if len(self.clauses) > 0:
            sql += ' where ' + ' and '.join(self.clauses)

        with self.context_manager(self.model) as cursor:
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

        if self.order_field is not None:
            sql += f' order by {self.order_field} {self.order_dir}'

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
        with self.context_manager(self.model) as cursor:
            cursor.execute(sql)
            return (cursor.rowcount, cursor.fetchall())


class SqliteQueryBuilder(SqlQueryBuilder):
    """SqlQueryBuilder using a SqliteContext."""
    def __init__(self, model: type, *args, **kwargs) -> None:
        super().__init__(model, SqliteContext, *args, **kwargs)


class DeletedModel(SqlModel):
    """Model for preserving and restoring deleted HashedModel records."""
    table: str = 'deleted_records'
    fields: tuple = ('id', 'model_class', 'record_id', 'record')

    def restore(self) -> SqlModel:
        """Restore a deleted record, remove from deleted_records, and
            return the restored model.
        """
        vert(self.data['model_class'] in globals(),
            'model_class must be accessible')
        model_class = globals()[self.data['model_class']]
        decoded = json.loads(self.data['record'])

        tert(issubclass(model_class, SqlModel),
            'related_model must inherit from SqlModel')

        if model_class.id_field not in decoded:
            decoded[model_class.id_field] = self.data['record_id']

        model = model_class.insert(decoded)
        self.delete()

        return model


class HashedModel(SqlModel):
    """Model for interacting with sqlite database using hash for id."""
    table: str = 'hashed_records'
    fields: tuple = ('id', 'data')

    @classmethod
    def generate_id(cls, data: dict) -> str:
        """Generate an ID by hashing the non-ID contents."""
        data = { k: data[k] for k in data if k in cls.fields and k != cls.id_field }
        preimage = json.dumps(
            cls.encode_value(data),
            sort_keys=True
        )
        return sha256(bytes(preimage, 'utf-8')).digest().hex()

    @classmethod
    def insert(cls, data: dict) -> Optional[HashedModel]:
        """Insert a new record to the datastore. Return instance."""
        tert(isinstance(data, dict), 'data must be dict')
        data[cls.id_field] = cls.generate_id(data)

        return SqliteQueryBuilder(model=cls).insert(data)

    @classmethod
    def insert_many(cls, items: list[dict]) -> int:
        """Insert a batch of records and return the number of items inserted."""
        tert(isinstance(items, list), 'items must be type list[dict]')
        for item in items:
            tert(isinstance(item, dict), 'items must be type list[dict]')
            item[cls.id_field] = cls.generate_id(item)

        return SqliteQueryBuilder(model=cls).insert_many(items)

    def update(self, updates: dict) -> HashedModel:
        """Persist the specified changes to the datastore, creating a new
            record in the process. Return new record in monad pattern.
        """
        tert(type(updates) is dict, 'updates must be dict')

        # merge data into updates
        for key in self.data:
            if key in self.fields and not key in updates:
                updates[key] = self.data[key]

        for key in updates:
            vert(key in self.fields, f'unrecognized field: {key}')

        # insert new record or update and return
        if self.data[self.id_field]:
            instance = self.insert(updates)
            self.delete()
        else:
            instance = self.insert(updates)
        return instance

    def delete(self) -> DeletedModel:
        """Delete the model, putting it in the deleted_records table,
            then return the DeletedModel.
        """
        model_class = self.__class__.__name__
        record_id = self.data[self.id_field]
        record = json.dumps(self.data)
        deleted = DeletedModel.insert({
            'model_class': model_class,
            'record_id': record_id,
            'record': record
        })
        super().delete()
        return deleted


class Attachment(HashedModel):
    """Class for attaching immutable json data to a record."""
    table: str = 'attachments'
    fields: tuple = ('id', 'related_model', 'related_id', 'details')
    _related: SqlModel = None
    _details: dict = None

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
        self.data['related_id'] = related.data[related.id_field]
        return self

    def details(self, reload: bool = False) -> dict:
        """Decode json str to dict."""
        if self._details is None or reload:
            self._details = json.loads(self.data['details'])
        return self._details

    def set_details(self, details: dict = {}) -> Attachment:
        """Set the details field using either a supplied dict or by
            encoding the self._details dict to json. Return self in monad
            pattern.
        """
        if details:
            self._details = details
        self.data['details'] = json.dumps(self._details)
        return self

    @classmethod
    def insert(cls, data: dict) -> Optional[Attachment]:
        """Redefined for better LSP support."""
        return super().insert(data)
