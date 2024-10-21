from __future__ import annotations
from .errors import tert, vert, tressa
from .interfaces import (
    DBContextProtocol,
    CursorProtocol,
    QueryBuilderProtocol,
    ModelProtocol,
)
from dataclasses import dataclass, field
from hashlib import sha256
from time import time
from types import TracebackType
from typing import Any, Generator, Optional, Type, Union, Callable
from uuid import uuid4
import packify
import sqlite3


class SqliteContext:
    """Context manager for sqlite."""
    connection: sqlite3.Connection
    cursor: sqlite3.Cursor
    connection_info: str

    def __init__(self, connection_info: str = '') -> None:
        """Initialize the instance. Raises TypeError for non-str table.
        """
        if not connection_info and hasattr(self, 'connection_info'):
            connection_info = self.connection_info
        tert(type(connection_info) in (str, bytes),
            'connection_info must be str or bytes')
        tressa(len(connection_info) > 0, 'cannot use with empty connection_info')
        self.connection = sqlite3.connect(connection_info)
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
    table_1: str = field()
    table_1_columns: list[str] = field()
    column_1: str = field()
    comparison: str = field()
    table_2: str = field()
    table_2_columns: list[str] = field()
    column_2: str = field()


@dataclass
class Row:
    """Class for representing a row from a query when no better model exists."""
    data: dict = field()


def dynamic_sqlmodel(connection_string: str|bytes, table_name: str = '',
                     column_names: tuple[str] = ()) -> Type[SqlModel]:
    """Generates a dynamic sqlite model for instantiating context
        managers. Raises TypeError for invalid connection_string or
        table_name.
    """
    tert(type(connection_string) in (str, bytes), 'connection_string must be str|bytes')
    tert(type(table_name) is str, 'table_name must be str')
    class DynamicModel(SqlModel):
        connection_info: str = connection_string
        table: str = table_name
        columns: tuple[str] = column_names
    return DynamicModel


class SqlQueryBuilder:
    """Main query builder class. Extend with child class to bind to a
        specific database by supplying the context_manager param to a
        call to `super().__init__()`. Default binding is to sqlite3.
    """
    model: Type[ModelProtocol]
    context_manager: Type[DBContextProtocol]
    connection_info: str
    clauses: list
    params: list
    order_column: str
    order_dir: str
    limit: int
    offset: int
    joins: list[JoinSpec]
    columns: list[str]
    grouping: str

    def __init__(self, model_or_table: Type[SqlModel]|str = None,
                 context_manager: Type[DBContextProtocol] = SqliteContext,
                 connection_info: str = '', model: Type[SqlModel] = None,
                 table: str = '', columns: list[str] = []
                 ) -> None:
        """Initialize the instance. Must supply model_or_table or model
            or table. Must supply context_manager.
        """
        tressa(model_or_table is not None or model is not None or table is not None,
               'model_or_table, model, or table parameter must be specified')
        if model_or_table is None and model is not None:
            tert(type(model) is type and issubclass(model, SqlModel),
                 'model must be subclass of SqlModel')
            model_or_table = model
        if model_or_table is None and table is not None:
            tert(type(table) is str, 'table must be str name')
            model_or_table = table
        tert(type(model_or_table) is str or
             (type(model_or_table) is type and issubclass(model_or_table, SqlModel)),
             'model_or_table must be Type[SqlModel]|str')
        tert(type(context_manager) is type and issubclass(context_manager, DBContextProtocol),
             'context_manager must be class implementing DBContextProtocol')
        tressa(type(model_or_table) is type or len(columns),
               'must provide class implementing ModelProtocol or columns')
        if not connection_info and hasattr(self.__class__, 'connection_info'):
            connection_info = self.__class__.connection_info
        if type(model_or_table) is type:
            self._model = model_or_table
        else:
            self._model = dynamic_sqlmodel(connection_info, model_or_table, columns)
        self._table = self._model.table if self._model else model_or_table
        self.context_manager = context_manager
        self.connection_info = self._model.connection_info
        self.clauses = []
        self.params = []
        self.order_column = None
        self.order_dir = 'desc'
        self.limit = None
        self.offset = None
        self.joins = []
        self.columns = None
        self.grouping = None

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

    @property
    def table(self) -> str:
        """The table name for the base query. Setting raises TypeError
            if supplied something other than a str.
        """
        return self._table

    @table.setter
    def table(self, name: str) -> None:
        tert(type(name) is str, 'name must be str')
        self._table = name

    def is_null(self, column: str) -> SqlQueryBuilder:
        """Save the 'column is null' clause, then return self. Raises
            TypeError for invalid column.
        """
        tert(type(column) is str, 'column must be str')
        self.clauses.append(f'{column} is null')
        return self

    def not_null(self, column: str) -> SqlQueryBuilder:
        """Save the 'column is not null' clause, then return self.
            Raises TypeError for invalid column.
        """
        tert(type(column) is str, 'column must be str')
        self.clauses.append(f'{column} is not null')
        return self

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

    def like(self, column: str, pattern: str, data: str) -> SqlQueryBuilder:
        """Save the 'column like {pattern.replace(?, data)}' clause and
            param, then return self. Raises TypeError or ValueError for
            invalid column, pattern, or data.
        """
        tert(type(column) is str, 'column must be str')
        tert(type(pattern) is str, 'pattern must be str')
        tert(type(data) is str, 'data must be str')
        vert(len(column), 'column cannot be empty')
        vert(len(pattern), 'pattern cannot be empty')
        vert(len(data), 'data cannot be empty')
        self.clauses.append(f'{column} like ?')
        self.params.append(pattern.replace('?', data))
        return self

    def not_like(self, column: str, pattern: str, data: str) -> SqlQueryBuilder:
        """Save the 'column not like {pattern.replace(?, data)}' clause
            and param, then return self. Raises TypeError or ValueError
            for invalid column, pattern, or data.
        """
        tert(type(column) is str, 'column must be str')
        tert(type(pattern) is str, 'pattern must be str')
        tert(type(data) is str, 'data must be str')
        vert(len(column), 'column cannot be empty')
        vert(len(pattern), 'pattern cannot be empty')
        vert(len(data), 'data cannot be empty')
        self.clauses.append(f'{column} not like ?')
        self.params.append(pattern.replace('?', data))
        return self

    def starts_with(self, column: str, data: str) -> SqlQueryBuilder:
        """Save the 'column like data%' clause and param, then return
            self. Raises TypeError or ValueError for invalid column or
            data.
        """
        return self.like(column, '?%', data)

    def does_not_start_with(self, column: str, data: str) -> SqlQueryBuilder:
        """Save the 'column not like data%' clause and param, then return
            self. Raises TypeError or ValueError for invalid column or
            data.
        """
        return self.not_like(column, '?%', data)

    def contains(self, column: str, data: str) -> SqlQueryBuilder:
        """Save the 'column like %data%' clause and param, then return
            self. Raises TypeError or ValueError for invalid column or
            data.
        """
        return self.like(column, '%?%', data)

    def excludes(self, column: str, data: str) -> SqlQueryBuilder:
        """Save the 'column not like %data%' clause and param, then
            return self. Raises TypeError or ValueError for invalid
            column or data.
        """
        return self.not_like(column, '%?%', data)

    def ends_with(self, column: str, data: str) -> SqlQueryBuilder:
        """Save the 'column like %data' clause and param, then return
            self. Raises TypeError or ValueError for invalid column or
            data.
        """
        return self.like(column, '%?', data)

    def does_not_end_with(self, column: str, data: str) -> SqlQueryBuilder:
        """Save the 'column like %data' clause and param, then return
            self. Raises TypeError or ValueError for invalid column or
            data.
        """
        return self.not_like(column, '%?', data)

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
        vert(column in self.model.columns or column in [j.table_2_columns for j in self.joins],
             f'unrecognized column {column}')
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
        return self.__class__(
            model=self.model, context_manager=self.context_manager,
            connection_info=self.connection_info
        )

    def insert(self, data: dict) -> Optional[SqlModel|Row]:
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

        with self.context_manager(self.connection_info) as cursor:
            cursor.execute(sql, params)
            return self.model(data=data) if self.model else Row(data=data)

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

        with self.context_manager(self.connection_info) as cursor:
            return cursor.executemany(sql, rows).rowcount

    def find(self, id: Any) -> Optional[SqlModel|Row]:
        """Find a record by its id and return it."""
        with self.context_manager(self.connection_info) as cursor:
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

        return self.model(data=data) if self.model else Row(data=data)

    def join(self, model_or_table: Type[SqlModel]|str, on: list[str],
             kind: str = "inner", joined_table_columns: tuple[str] = (),
             ) -> SqlQueryBuilder:
        """Prepares the query for a join over multiple tables/models.
            Raises TypeError or ValueError for invalid model, on, or
            kind.
        """
        tert(type(model_or_table) in (type, str),
             "model_or_table must be Type[SqlModel] or str")
        if type(model_or_table) is str:
            tressa(type(joined_table_columns) in (tuple, list) and len(joined_table_columns),
                   'cannot join on table without columns')
        model = model_or_table
        if type(model) is not type:
            model = dynamic_sqlmodel(self.connection_info, model, joined_table_columns)
        tert(type(on) is list, "on must be list[str]")
        tert(all([type(o) is str for o in on]), "on must be list[str]")
        tert(type(kind) is str, "kind must be str")
        vert(len(on) in (2, 3),
             "on must be of form [column, column] or [column, comparison, column]")
        vert(kind in ("inner", "outer", "left", "right", "full"))

        join = [kind]

        def get_join(model: Type[SqlModel], column: str) -> str:
            if "." in column:
                return [model.table, model.columns, column]
            else:
                tert(column in model.columns,
                     f"column name must be valid for {model.table}")
                return [model.table, model.columns, f"{model.table}.{column}"]

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
            if join.table_2 not in [c.table for c in classes]:
                classes.append(dynamic_sqlmodel(
                    self.connection_info, join.table_2, join.table_2_columns))

        if self.columns:
            columns = self.columns
        else:
            for modelclass in classes:
                columns.extend([
                    f"{modelclass.table}.{f}"
                    for f in modelclass.columns
                ])

        sql = f'select {",".join(columns)} from {self.table}'

        sql += ' ' + ''.join([
            f'{j.kind} join {j.table_2} on {j.column_1} {j.comparison} {j.column_2}'
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

        with self.context_manager(self.connection_info) as cursor:
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

        with self.context_manager(self.connection_info) as cursor:
            cursor.execute(sql, self.params)
            rows = cursor.fetchall()
            if self.grouping or not self.model:
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

        with self.context_manager(self.connection_info) as cursor:
            cursor.execute(sql, self.params)
            return cursor.fetchone()[0]

    def take(self, limit: int) -> list[SqlModel]|list[JoinedModel]|list[Row]:
        """Takes the specified number of rows. Raises TypeError or
            ValueError for invalid limit.
        """
        tert(type(limit) is int, 'limit must be positive int')
        vert(limit > 0, 'limit must be positive int')
        self.limit = limit
        return self.get()

    def chunk(self, number: int) -> Generator[list[SqlModel]|list[JoinedModel]|list[Row], None, None]:
        """Chunk all matching rows the specified number of rows at a
            time. Raises TypeError or ValueError for invalid number.
        """
        tert(type(number) is int, 'number must be int > 0')
        vert(number > 0, 'number must be int > 0')
        return self._chunk(number)

    def _chunk(self, number: int) -> Generator[list[SqlModel]|list[JoinedModel]|list[Row], None, None]:
        """Create the generator for chunking."""
        original_offset = self.offset
        self.offset = self.offset or 0
        result = self.take(number)

        while len(result) > 0:
            yield result
            self.offset += number
            result = self.take(number)

        self.offset = original_offset

    def first(self) -> Optional[SqlModel|Row]:
        """Run the query on the datastore and return the first result."""
        sql = f'select {",".join(self.model.columns)} from {self.table}'

        if len(self.clauses) > 0:
            sql += ' where ' + ' and '.join(self.clauses)

        if self.order_column is not None:
            sql += f' order by {self.order_column} {self.order_dir}'

        with self.context_manager(self.connection_info) as cursor:
            cursor.execute(sql, self.params)
            row = cursor.fetchone()

            if row is None:
                return None

            if self.model:
                return self.model(data={
                    key: value
                    for key, value in zip(self.model.columns, row)
                })
            else:
                return Row(data={
                    key: value
                    for key, value in zip()
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
        with self.context_manager(self.connection_info) as cursor:
            return cursor.execute(sql, [*params, *condition_params]).rowcount

    def delete(self) -> int:
        """Delete the records that match the query and return the number
            of deleted records.
        """
        sql = f'delete from {self.model.table}'

        if len(self.clauses) > 0:
            sql += ' where ' + ' and '.join(self.clauses)

        with self.context_manager(self.connection_info) as cursor:
            return cursor.execute(sql, self.params).rowcount

    def to_sql(self, interpolate_params: bool = True) -> str|tuple[str, list]:
        """Return the sql where clause from the clauses and params. If
            interpolate_params is True, the parameters will be
            interpolated into the SQL str and a single str result will
            be returned. If interpolate_params is False, the parameters
            will not be interpolated into the SQL str, instead including
            question marks, and an additional list of params will be
            returned along with the SQL str.
        """
        sql = f' where {" and ".join(self.clauses)}'

        if interpolate_params:
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

        return sql if interpolate_params else (sql, self.params)

    def execute_raw(self, sql: str) -> tuple[int, list[tuple[Any]]]:
        """Execute raw SQL against the database. Return rowcount and
            fetchall results.
        """
        tert(type(sql) is str, 'sql must be str')
        with self.context_manager(self.connection_info) as cursor:
            cursor.execute(sql)
            return (cursor.rowcount, cursor.fetchall())


class SqlModel:
    """General model for mapping a SQL row to an in-memory object."""
    table: str = 'example'
    id_column: str = 'id'
    columns: tuple = ('id', 'name')
    id: str
    name: str
    query_builder_class: Type[QueryBuilderProtocol] = SqlQueryBuilder
    connection_info: str = ''
    data: dict
    _event_hooks: dict[str, list[Callable]] = {}

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

    @classmethod
    def add_hook(cls, event: str, hook: Callable):
        """Add the hook for the event."""
        if cls is not SqlModel and cls._event_hooks is SqlModel._event_hooks:
            cls._event_hooks = {} # give each class its own event hooks dict
        if event not in cls._event_hooks:
            cls._event_hooks[event] = []
        if hook not in cls._event_hooks[event]:
            cls._event_hooks[event].append(hook)

    @classmethod
    def remove_hook(cls, event: str, hook: Callable):
        """Remove the hook for the event."""
        if cls is not SqlModel and cls._event_hooks is SqlModel._event_hooks:
            cls._event_hooks = {} # give each class its own event hooks dict
        if event not in cls._event_hooks:
            return
        if hook in cls._event_hooks[event]:
            cls._event_hooks[event].remove(hook)

    @classmethod
    def clear_hooks(cls, event: str = None):
        """Remove all hooks for an event. If no event is specified,
            clear all hooks for all events.
        """
        if cls is not SqlModel and cls._event_hooks is SqlModel._event_hooks:
            cls._event_hooks = {} # give each class its own event hooks dict
        if event is None:
            return cls._event_hooks.clear()
        if event not in cls._event_hooks:
            return
        del cls._event_hooks[event]

    @classmethod
    def invoke_hooks(cls, event: str, *args, **kwargs):
        """Invoke the hooks for the event, passing cls, *args, and
            **kwargs.
        """
        for hook in cls._event_hooks.get(event, []):
            hook(cls, *args, **kwargs)

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
            f"columns={self.columns}, data={self.data}, " + \
            f"connection_info='{self.connection_info}')"

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
    def insert(cls, data: dict, /, *, suppress_events: bool = False) -> Optional[SqlModel]:
        """Insert a new record to the datastore. Return instance. Raises
            TypeError if data is not a dict.
        """
        if not suppress_events:
            cls.invoke_hooks('before_insert', data)
        tert(isinstance(data, dict), 'data must be dict')
        if cls.id_column not in data:
            data[cls.id_column] = cls.generate_id()

        val = cls().query_builder_class(model=cls).insert(data)
        if not suppress_events:
            cls.invoke_hooks('after_insert', data, val)
        return val

    @classmethod
    def insert_many(cls, items: list[dict], /, *, suppress_events: bool = False) -> int:
        """Insert a batch of records and return the number of items
            inserted. Raises TypeError if items is not list[dict].
        """
        if not suppress_events:
            cls.invoke_hooks('before_insert_many', items)
        tert(isinstance(items, list), 'items must be type list[dict]')
        for item in items:
            tert(isinstance(item, dict), 'items must be type list[dict]')
            if cls.id_column not in item:
                item[cls.id_column] = cls.generate_id()

        val = cls().query_builder_class(model=cls).insert_many(items)
        if not suppress_events:
            cls.invoke_hooks('after_insert_many', items, val)
        return val

    def update(self, updates: dict, conditions: dict = None, /, *,
               suppress_events: bool = False) -> SqlModel:
        """Persist the specified changes to the datastore. Return self
            in monad pattern. Raises TypeError or ValueError for invalid
            updates or conditions (self.data must include the id to
            update or conditions must be specified).
        """
        if not suppress_events:
            self.invoke_hooks('before_update', self, updates, conditions)
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

        if not suppress_events:
            self.invoke_hooks('after_update', self, updates, conditions)

        return self

    def save(self, /, *, suppress_events: bool = False) -> SqlModel:
        """Persist to the datastore. Return self in monad pattern.
            Calls insert or update and raises appropriate errors.
        """
        if not suppress_events:
            self.invoke_hooks('before_save', self)
        if self.id_column in self.data:
            if self.find(self.data[self.id_column]) is not None:
                val = self.update({})
                if not suppress_events:
                    self.invoke_hooks('after_save', self, val)
                return val
        val = self.insert(self.data)
        if not suppress_events:
            self.invoke_hooks('after_save', self, val)
        return val

    def delete(self, /, *, suppress_events: bool = False) -> None:
        """Delete the record."""
        if not suppress_events:
            self.invoke_hooks('before_delete', self)
        if self.id_column in self.data:
            self.query().equal(self.id_column, self.data[self.id_column]).delete()
        if not suppress_events:
            self.invoke_hooks('after_delete', self)

    def reload(self, /, *, suppress_events: bool = False) -> SqlModel:
        """Reload values from datastore. Return self in monad pattern.
            Raises UsageError if id is not set in self.data.
        """
        if not suppress_events:
            self.invoke_hooks('before_reload', self)
        tressa(self.id_column in self.data,
               'id_column must be set in self.data to reload from db')
        reloaded = self.find(self.data[self.id_column])
        if reloaded:
            self.data = reloaded.data
        if not suppress_events:
            self.invoke_hooks('after_reload', self)
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
        sqb = cls.query_builder_class(model=cls, connection_info=connection_info)

        if conditions is not None:
            for key in conditions:
                sqb.equal(key, conditions[key])

        return sqb


class DeletedModel(SqlModel):
    """Model for preserving and restoring deleted HashedModel records."""
    table: str = 'deleted_records'
    columns: tuple = ('id', 'model_class', 'record_id', 'record', 'timestamp')
    id: str
    model_class: str
    record_id: str
    record: bytes
    timestamp: str

    def __init__(self, data: dict = {}) -> None:
        if 'timestamp' not in data:
            data['timestamp'] = str(int(time()))
        super().__init__(data)

    @classmethod
    def insert(cls, data: dict, /, *, suppress_events: bool = False) -> SqlModel | None:
        if not suppress_events:
            cls.invoke_hooks('before_insert', data)
        if 'timestamp' not in data:
            data['timestamp'] = str(int(time()))
        val = super().insert(data, suppress_events=True) # no duplicate events
        if not suppress_events:
            cls.invoke_hooks('after_insert', data, val)
        return val

    def restore(self, inject: dict = {}, /, *, suppress_events: bool = False) -> SqlModel:
        """Restore a deleted record, remove from deleted_records, and
            return the restored model. Raises ValueError if model_class
            cannot be found. Raises TypeError if model_class is not a
            subclass of SqlModel. Uses packify.unpack to unpack the
            record. Raises TypeError if packed record is not a dict.
        """
        if not suppress_events:
            self.invoke_hooks('before_restore', self, inject)
        dependencies = {**globals(), **inject}
        vert(self.data['model_class'] in dependencies,
            'model_class must be accessible')
        model_class: type[SqlModel] = dependencies[self.data['model_class']]
        tert(issubclass(model_class, SqlModel),
            'related_model must inherit from SqlModel')

        decoded = packify.unpack(self.data['record'])
        tert(type(decoded) is dict, 'encoded record is not a dict')

        if model_class.id_column not in decoded:
            decoded[model_class.id_column] = self.data['record_id']

        model = model_class.insert(decoded)
        self.delete()

        if not suppress_events:
            self.invoke_hooks('after_restore', self, inject, model)

        return model


class HashedModel(SqlModel):
    """Model for interacting with sql database using sha256 for id."""
    table: str = 'hashed_records'
    columns: tuple[str] = ('id', 'details')
    columns_excluded_from_hash: tuple[str] = tuple()
    id: str
    details: bytes

    @classmethod
    def generate_id(cls, data: dict) -> str:
        """Generate an id by hashing the non-id contents. Raises
            TypeError for unencodable type (calls packify.pack). Any
            columns not present in the data dict will be set to None.
            Any columns in the columns_excluded_from_hash tuple will be
            excluded from the sha256 hash.
        """
        for name in cls.columns:
            if name not in data and name != cls.id_column:
                data[name] = None
        data = {
            k: data[k] for k in data
            if k in cls.columns and k != cls.id_column and k not in cls.columns_excluded_from_hash
        }
        preimage = packify.pack(data)
        return sha256(preimage).digest().hex()

    @classmethod
    def insert(cls, data: dict, /, *, suppress_events: bool = False) -> Optional[HashedModel]:
        """Insert a new record to the datastore. Return instance. Raises
            TypeError for non-dict data or unencodable type (calls
            cls.generate_id, which calls packify.pack).
        """
        if not suppress_events:
            cls.invoke_hooks('before_insert', data)
        tert(isinstance(data, dict), 'data must be dict')
        data[cls.id_column] = cls.generate_id(data)

        val = cls.query().insert(data)
        if not suppress_events:
            cls.invoke_hooks('after_insert', data, val)
        return val

    @classmethod
    def insert_many(cls, items: list[dict], /, *, suppress_events: bool = False) -> int:
        """Insert a batch of records and return the number of items
            inserted. Raises TypeError for invalid items or unencodable
            value (calls cls.generate_id, which calls packify.pack).
        """
        if not suppress_events:
            cls.invoke_hooks('before_insert_many', items)
        tert(isinstance(items, list), 'items must be type list[dict]')
        for item in items:
            tert(isinstance(item, dict), 'items must be type list[dict]')
            item[cls.id_column] = cls.generate_id(item)

        vals = cls.query().insert_many(items)
        if not suppress_events:
            cls.invoke_hooks('before_insert_many', items, vals)
        return vals

    def update(self, updates: dict, /, *, suppress_events: bool = False) -> HashedModel:
        """Persist the specified changes to the datastore, creating a
            new record in the process unless the changes were to the
            hash-excluded columns. Update and return self in monad
            pattern. Raises TypeError or ValueError for invalid updates.
            Did not need to overwrite the save method because save calls
            update or insert.
        """
        if not suppress_events:
            self.invoke_hooks('before_update', self, updates)
        tert(type(updates) is dict, 'updates must be dict')

        # merge data into updates
        for key in self.data:
            if key in self.columns and not key in updates:
                updates[key] = self.data[key]

        for key in updates:
            vert(key in self.columns, f'unrecognized column: {key}')

        # insert new record and return
        if not self.data[self.id_column]:
            instance = self.insert(updates)
            if not suppress_events:
                self.invoke_hooks('after_update', self, updates)
            self.data = instance.data
            return self

        # if a committed value is changed, delete old, insert new, and return
        new_id = self.generate_id({**self.data, **updates})
        if new_id != self.data[self.id_column]:
            instance = self.insert(updates)
            self.delete()
            self.data = instance.data
            if not suppress_events:
                self.invoke_hooks('after_update', self, updates)
            return self

        # update uncommitted value and return
        self.query({self.id_column: self.id}).update(updates)
        if not suppress_events:
            self.invoke_hooks('after_update', self, updates)
        return self

    def delete(self, /, *, suppress_events: bool = False) -> DeletedModel:
        """Delete the model, putting it in the deleted_records table,
            then return the DeletedModel. Raises packify.UsageError for
            unserializable data.
        """
        if not suppress_events:
            self.invoke_hooks('before_delete', self)
        model_class = self.__class__.__name__
        record_id = self.data[self.id_column]
        record = packify.pack(self.data)
        deleted = DeletedModel.insert({
            'model_class': model_class,
            'record_id': record_id,
            'record': record
        }, suppress_events=suppress_events)
        super().delete(suppress_events=True) # no duplicate events
        if not suppress_events:
            self.invoke_hooks('after_delete', self, deleted)
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
            model_class: type[SqlModel] = globals()[self.data['related_model']]
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
    def insert(cls, data: dict, /, *, suppress_events: bool = False) -> Optional[Attachment]:
        # """Redefined for better LSP support."""
        if not suppress_events:
            cls.invoke_hooks('before_insert', data)
        val = super().insert(data, suppress_events=True) # no duplicate events
        if not suppress_events:
            cls.invoke_hooks('after_insert', data, val)
        return val
