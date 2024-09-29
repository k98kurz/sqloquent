from __future__ import annotations
from sqloquent.errors import tert, vert, tressa
from sqloquent.asyncql.interfaces import (
    AsyncDBContextProtocol,
    AsyncCursorProtocol,
    AsyncQueryBuilderProtocol,
    AsyncModelProtocol,
)
from sqloquent.classes import JoinSpec, Row
from dataclasses import dataclass
from hashlib import sha256
from time import time
from types import TracebackType
from typing import Any, AsyncGenerator, Optional, Type, Union
from uuid import uuid4
import aiosqlite
import packify


class AsyncSqliteContext:
    """Context manager for sqlite."""
    connection: aiosqlite.Connection
    cursor: aiosqlite.Cursor
    connection_info: str

    def __init__(self, connection_info: str = '') -> None:
        """Initialize the instance. Raises TypeError for non-str table.
        """
        if not connection_info and hasattr(self, 'connection_info'):
            connection_info = self.connection_info
        tert(type(connection_info) in (str, bytes),
            'connection_info must be str or bytes')
        tressa(len(connection_info) > 0, 'cannot use with empty connection_info')
        self.connection_info = connection_info

    async def __aenter__(self) -> AsyncCursorProtocol:
        """Enter the context block and return the cursor."""
        self.connection = await aiosqlite.connect(self.connection_info)
        self.cursor = await self.connection.cursor().__aenter__()
        return self.cursor

    async def __aexit__(self, exc_type: Optional[Type[BaseException]],
                exc_value: Optional[BaseException],
                traceback: Optional[TracebackType]) -> None:
        """Exit the context block. Commit or rollback as appropriate,
            then close the connection.
        """
        if exc_type is not None:
            await self.connection.rollback()
        else:
            await self.connection.commit()

        await self.connection.close()


@dataclass
class AsyncJoinedModel:
    """Class for representing the results of SQL JOIN queries."""
    models: list[Type[AsyncSqlModel]]
    data: dict

    def __init__(self, models: list[Type[AsyncSqlModel]], data: dict) -> None:
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
    def parse_data(models: list[Type[AsyncSqlModel]], data: dict) -> dict:
        """Parse data of form {table.column:value} to
            {table:{column:value}}. Raises TypeError for invalid models
            or data.
        """
        tert(type(models) is list, 'models must be list[Type[AsyncSqlModel]]')
        tert(all([issubclass(m, AsyncSqlModel) for m in models]),
             'models must be list[Type[AsyncSqlModel]]')
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

    async def get_models(self) -> list[AsyncSqlModel]:
        """Returns the underlying models. Calls the find method for each
            model.
        """
        instances = []
        for model in self.models:
            if model.table in self.data:
                if model.id_column in self.data[model.table]:
                    model_id = self.data[model.table][model.id_column]
                    instances.append(await model.find(model_id))
        return instances


def async_dynamic_sqlmodel(connection_string: str|bytes, table_name: str = '',
                     column_names: tuple[str] = ()) -> Type[AsyncSqlModel]:
    """Generates a dynamic sqlite model for instantiating context
        managers. Raises TypeError for invalid connection_string or
        table_name.
    """
    tert(type(connection_string) in (str, bytes), 'connection_string must be str|bytes')
    tert(type(table_name) is str, 'table_name must be str')
    class DynamicModel(AsyncSqlModel):
        connection_info: str = connection_string
        table: str = table_name
        columns: tuple[str] = column_names
    return DynamicModel


class AsyncSqlQueryBuilder:
    """Main query builder class. Extend with child class to bind to a
        specific database by supplying the context_manager param to a
        call to `super().__init__()`. Default binding is to aiosqlite.
    """
    model: Type[AsyncModelProtocol]
    context_manager: Type[AsyncDBContextProtocol]
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

    def __init__(self, model_or_table: Type[AsyncSqlModel]|str = None,
                 context_manager: Type[AsyncDBContextProtocol] = AsyncSqliteContext,
                 connection_info: str = '', model: Type[AsyncSqlModel] = None,
                 table: str = '', columns: list[str] = []
                 ) -> None:
        tressa(model_or_table is not None or model is not None or table is not None,
               'model_or_table, model, or table parameter must be specified')
        if model_or_table is None and model is not None:
            tert(type(model) is type and issubclass(model, AsyncSqlModel),
                 'model must be subclass of AsyncSqlModel')
            model_or_table = model
        if model_or_table is None and table is not None:
            tert(type(table) is str, 'table must be str name')
            model_or_table = table
        tert(type(model_or_table) is str or
             (type(model_or_table) is type and issubclass(model_or_table, AsyncSqlModel)),
             'model_or_table must be Type[AsyncSqlModel]|str')
        tert(type(context_manager) is type and issubclass(context_manager, AsyncDBContextProtocol),
             'context_manager must be class implementing AsyncDBContextProtocol')
        tressa(type(model_or_table) is type or len(columns),
               'must provide class implementing AsyncModelProtocol or columns')
        if not connection_info and hasattr(self.__class__, 'connection_info'):
            connection_info = self.__class__.connection_info
        if type(model_or_table) is type:
            self._model = model_or_table
        else:
            self._model = async_dynamic_sqlmodel(connection_info, model_or_table, columns)
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
    def model(self) -> Type[AsyncSqlModel]:
        """The model type that non-joined query results will be. Setting
            raises TypeError if supplied something other than a subclass
            of AsyncSqlModel.
        """
        return self._model

    @model.setter
    def model(self, model: Type[AsyncSqlModel]) -> None:
        tert(type(model) is type, 'model must be AsyncSqlModel subclass')
        tert(issubclass(model, AsyncSqlModel), 'model must be AsyncSqlModel subclass')
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

    def is_null(self, column: str) -> AsyncSqlQueryBuilder:
        """Save the 'column is null' clause, then return self. Raises
            TypeError for invalid column.
        """
        tert(type(column) is str, 'column must be str')
        self.clauses.append(f'{column} is null')
        return self

    def not_null(self, column: str) -> AsyncSqlQueryBuilder:
        """Save the 'column is not null' clause, then return self.
            Raises TypeError for invalid column.
        """
        tert(type(column) is str, 'column must be str')
        self.clauses.append(f'{column} is not null')
        return self

    def equal(self, column: str, data: Any) -> AsyncSqlQueryBuilder:
        """Save the 'column = data' clause and param, then return self.
            Raises TypeError for invalid column.
        """
        tert(type(column) is str, 'column must be str')
        self.clauses.append(f'{column} = ?')
        self.params.append(data)
        return self

    def not_equal(self, column: str, data: Any) -> AsyncSqlQueryBuilder:
        """Save the 'column != data' clause and param, then return self.
            Raises TypeError for invalid column.
        """
        tert(type(column) is str, 'column must be str')
        self.clauses.append(f'{column} != ?')
        self.params.append(data)
        return self

    def less(self, column: str, data: Any) -> AsyncSqlQueryBuilder:
        """Save the 'column < data' clause and param, then return self.
            Raises TypeError for invalid column.
        """
        tert(type(column) is str, 'column must be str')
        self.clauses.append(f'{column} < ?')
        self.params.append(data)
        return self

    def greater(self, column: str, data: Any) -> AsyncSqlQueryBuilder:
        """Save the 'column > data' clause and param, then return self.
            Raises TypeError for invalid column.
        """
        tert(type(column) is str, 'column must be str')
        self.clauses.append(f'{column} > ?')
        self.params.append(data)
        return self

    def like(self, column: str, pattern: str, data: str) -> AsyncSqlQueryBuilder:
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

    def not_like(self, column: str, pattern: str, data: str) -> AsyncSqlQueryBuilder:
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

    def starts_with(self, column: str, data: str) -> AsyncSqlQueryBuilder:
        """Save the 'column like data%' clause and param, then return
            self. Raises TypeError or ValueError for invalid column or
            data.
        """
        return self.like(column, '?%', data)

    def does_not_start_with(self, column: str, data: str) -> AsyncSqlQueryBuilder:
        """Save the 'column like data%' clause and param, then return
            self. Raises TypeError or ValueError for invalid column or
            data.
        """
        return self.not_like(column, '?%', data)

    def contains(self, column: str, data: str) -> AsyncSqlQueryBuilder:
        """Save the 'column like %data%' clause and param, then return
            self. Raises TypeError or ValueError for invalid column or
            data.
        """
        return self.like(column, '%?%', data)

    def excludes(self, column: str, data: str) -> AsyncSqlQueryBuilder:
        """Save the 'column not like %data%' clause and param, then
            return self. Raises TypeError or ValueError for invalid
            column or data.
        """
        return self.not_like(column, '%?%', data)

    def ends_with(self, column: str, data: str) -> AsyncSqlQueryBuilder:
        """Save the 'column like %data' clause and param, then return
            self. Raises TypeError or ValueError for invalid column or
            data.
        """
        return self.like(column, '%?', data)

    def does_not_end_with(self, column: str, data: str) -> AsyncSqlQueryBuilder:
        """Save the 'column like %data' clause and param, then return
            self. Raises TypeError or ValueError for invalid column or
            data.
        """
        return self.not_like(column, '%?', data)

    def is_in(self, column: str, data: Union[tuple, list]) -> AsyncSqlQueryBuilder:
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

    def not_in(self, column: str, data: Union[tuple, list]) -> AsyncSqlQueryBuilder:
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

    def order_by(self, column: str, direction: str = 'desc') -> AsyncSqlQueryBuilder:
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

    def skip(self, offset: int) -> AsyncSqlQueryBuilder:
        """Sets the number of rows to skip. Raises TypeError or
            ValueError for invalid offset.
        """
        tert(type(offset) is int, 'offset must be positive int')
        vert(offset >= 0, 'offset must be positive int')
        self.offset = offset
        return self

    def reset(self) -> AsyncSqlQueryBuilder:
        """Returns a fresh instance using the configured model."""
        return self.__class__(
            model=self.model, context_manager=self.context_manager,
            connection_info=self.connection_info
        )

    async def insert(self, data: dict) -> Optional[AsyncSqlModel|Row]:
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
            vert(await self.find(data[self.model.id_column]) is None,
                 'record with this id already exists')

        sql = f'insert into {self.model.table} ({",".join(columns)})' + \
            f' values ({",".join(["?" for p in params])})'

        async with self.context_manager(self.connection_info) as cursor:
            await cursor.execute(sql, params)
            return self.model(data=data) if self.model else Row(data=data)

    async def insert_many(self, items: list[dict]) -> int:
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

        async with self.context_manager(self.connection_info) as cursor:
            return (await cursor.executemany(sql, rows)).rowcount

    async def find(self, id: Any) -> Optional[AsyncSqlModel|Row]:
        """Find a record by its id and return it."""
        async with self.context_manager(self.connection_info) as cursor:
            await cursor.execute(
                f'select {",".join(self.model.columns)} from {self.model.table}' +
                f' where {self.model.id_column} = ?',
                [id]
            )
            result = await cursor.fetchone()

        if result is None:
            return None

        data = {
            column: value
            for column, value in zip(self.model.columns, result)
        }

        return self.model(data=data) if self.model else Row(data=data)

    def join(self, model_or_table: Type[AsyncSqlModel]|str, on: list[str],
             kind: str = "inner", joined_table_columns: tuple[str] = (),
             ) -> AsyncSqlQueryBuilder:
        """Prepares the query for a join over multiple tables/models.
            Raises TypeError or ValueError for invalid model, on, or
            kind.
        """
        tert(type(model_or_table) in (type, str),
             "model_or_table must be Type[AsyncSqlModel] or str")
        if type(model_or_table) is str:
            tressa(type(joined_table_columns) in (tuple, list) and len(joined_table_columns),
                   'cannot join on table without columns')
        model = model_or_table
        if type(model) is not type:
            model = async_dynamic_sqlmodel(self.connection_info, model, joined_table_columns)
        tert(type(on) is list, "on must be list[str]")
        tert(all([type(o) is str for o in on]), "on must be list[str]")
        tert(type(kind) is str, "kind must be str")
        vert(len(on) in (2, 3),
             "on must be of form [column, column] or [column, comparison, column]")
        vert(kind in ("inner", "outer", "left", "right", "full"))

        join = [kind]

        def get_join(model: Type[AsyncSqlModel], column: str) -> str:
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

    def select(self, columns: list[str]) -> AsyncQueryBuilderProtocol:
        """Sets the columns to select. Raises TypeError for invalid
            columns.
        """
        tert(type(columns) in (list, tuple), "select columns must be list[str]")
        tert(all([type(c) is str for c in columns]), "select columns must be list[str]")
        self.columns = [*columns]
        return self

    def group(self, by: str) -> AsyncSqlQueryBuilder:
        """Adds a GROUP BY constraint. Raises TypeError for invalid by."""
        tert(type(by) is str, "group by parameter must be str")
        self.grouping = by
        return self

    async def get(self) -> list[AsyncSqlModel]|list[AsyncJoinedModel]|list[Row]:
        """Run the query on the datastore and return a list of results.
            Return SqlModels when running a simple query. Return
            JoinedModels when running a JOIN query. Return Rows when
            running a non-joined GROUP BY query.
        """
        if len(self.joins) > 0:
            return await self._get_joined()
        return await self._get_normal()

    async def _get_joined(self) -> list[AsyncJoinedModel]:
        """Run the query on the datastore and return a list of joined
            results. Used by the `get` method when appropriate. Do not
            call this method manually.
        """
        classes: list[AsyncSqlModel] = [self.model]
        columns: list[str] = []
        for join in self.joins:
            if join.table_2 not in [c.table for c in classes]:
                classes.append(async_dynamic_sqlmodel(
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

        async with self.context_manager(self.connection_info) as cursor:
            await cursor.execute(sql, self.params)
            rows = await cursor.fetchall()
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
                    AsyncJoinedModel(classes, data={
                        key: value
                        for key, value in zip(columns, row)
                    })
                    for row in rows
                ]
            return models

    async def _get_normal(self) -> list[AsyncSqlModel|Row]:
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

        async with self.context_manager(self.connection_info) as cursor:
            await cursor.execute(sql, self.params)
            rows = await cursor.fetchall()
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

    async def count(self) -> int:
        """Returns the number of records matching the query."""
        sql = f'select count(*) from {self.model.table}'

        if len(self.clauses) > 0:
            sql += ' where ' + ' and '.join(self.clauses)

        async with self.context_manager(self.connection_info) as cursor:
            await cursor.execute(sql, self.params)
            return (await cursor.fetchone())[0]

    async def take(self, limit: int) -> list[AsyncSqlModel]|list[AsyncJoinedModel]|list[Row]:
        """Takes the specified number of rows. Raises TypeError or
            ValueError for invalid limit.
        """
        tert(type(limit) is int, 'limit must be positive int')
        vert(limit > 0, 'limit must be positive int')
        self.limit = limit
        return await self.get()

    def chunk(self, number: int) -> AsyncGenerator[list[AsyncSqlModel]|list[AsyncJoinedModel]|list[Row], None, None]:
        """Chunk all matching rows the specified number of rows at a
            time. Raises TypeError or ValueError for invalid number.
        """
        tert(type(number) is int, 'number must be int > 0')
        vert(number > 0, 'number must be int > 0')
        return self._chunk(number)

    async def _chunk(self, number: int) -> AsyncGenerator[list[AsyncSqlModel]|list[AsyncJoinedModel]|list[Row], None, None]:
        """Create the generator for chunking."""
        original_offset = self.offset
        self.offset = self.offset or 0
        result = await self.take(number)

        while len(result) > 0:
            yield result
            self.offset += number
            result = await self.take(number)

        self.offset = original_offset

    async def first(self) -> Optional[AsyncSqlModel|Row]:
        """Run the query on the datastore and return the first result."""
        sql = f'select {",".join(self.model.columns)} from {self.table}'

        if len(self.clauses) > 0:
            sql += ' where ' + ' and '.join(self.clauses)

        if self.order_column is not None:
            sql += f' order by {self.order_column} {self.order_dir}'

        async with self.context_manager(self.connection_info) as cursor:
            await cursor.execute(sql, self.params)
            row = await cursor.fetchone()

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

    async def update(self, updates: dict, conditions: dict = {}) -> int:
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
        async with self.context_manager(self.connection_info) as cursor:
            return (await cursor.execute(sql, [*params, *condition_params])).rowcount

    async def delete(self) -> int:
        """Delete the records that match the query and return the number
            of deleted records.
        """
        sql = f'delete from {self.model.table}'

        if len(self.clauses) > 0:
            sql += ' where ' + ' and '.join(self.clauses)

        async with self.context_manager(self.connection_info) as cursor:
            return (await cursor.execute(sql, self.params)).rowcount

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

    async def execute_raw(self, sql: str) -> tuple[int, list[tuple[Any]]]:
        """Execute raw SQL against the database. Return rowcount and
            fetchall results.
        """
        tert(type(sql) is str, 'sql must be str')
        async with self.context_manager(self.connection_info) as cursor:
            await cursor.execute(sql)
            return (cursor.rowcount, await cursor.fetchall())


class AsyncSqlModel:
    """General model for mapping a SQL row to an in-memory object."""
    table: str = 'example'
    id_column: str = 'id'
    columns: tuple = ('id', 'name')
    id: str
    name: str
    query_builder_class: Type[AsyncQueryBuilderProtocol] = AsyncSqlQueryBuilder
    connection_info: str = ''
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
            f"columns={self.columns}, data={self.data}, " + \
            f"connection_info='{self.connection_info}')"

    @classmethod
    def generate_id(cls) -> str:
        """Generates and returns a hexadecimal UUID4."""
        return uuid4().bytes.hex()

    @classmethod
    async def find(cls, id: Any) -> Optional[AsyncSqlModel]:
        """Find a record by its id and return it. Return None if it does
            not exist.
        """
        return await cls().query_builder_class(model=cls).find(id)

    @classmethod
    async def insert(cls, data: dict) -> Optional[AsyncSqlModel]:
        """Insert a new record to the datastore. Return instance. Raises
            TypeError if data is not a dict.
        """
        tert(isinstance(data, dict), 'data must be dict')
        if cls.id_column not in data:
            data[cls.id_column] = cls.generate_id()

        return await cls().query_builder_class(model=cls).insert(data)

    @classmethod
    async def insert_many(cls, items: list[dict]) -> int:
        """Insert a batch of records and return the number of items
            inserted. Raises TypeError if items is not list[dict].
        """
        tert(isinstance(items, list), 'items must be type list[dict]')
        for item in items:
            tert(isinstance(item, dict), 'items must be type list[dict]')
            if cls.id_column not in item:
                item[cls.id_column] = cls.generate_id()

        return await cls().query_builder_class(model=cls).insert_many(items)

    async def update(self, updates: dict, conditions: dict = None) -> AsyncSqlModel:
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
        await self.query().update(updates, conditions)

        return self

    async def save(self) -> AsyncSqlModel:
        """Persist to the datastore. Return self in monad pattern.
            Calls insert or update and raises appropriate errors.
        """
        if self.id_column in self.data:
            if await self.find(self.data[self.id_column]) is not None:
                return await self.update({})
        return await self.insert(self.data)

    async def delete(self) -> None:
        """Delete the record."""
        if self.id_column in self.data:
            await self.query().equal(self.id_column, self.data[self.id_column]).delete()

    async def reload(self) -> AsyncSqlModel:
        """Reload values from datastore. Return self in monad pattern.
            Raises UsageError if id is not set in self.data.
        """
        tressa(self.id_column in self.data,
               'id_column must be set in self.data to reload from db')
        reloaded = await self.find(self.data[self.id_column])
        if reloaded:
            self.data = reloaded.data
        return self

    @classmethod
    def query(cls, conditions: dict = None, connection_info: str = None) -> AsyncQueryBuilderProtocol:
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


class AsyncDeletedModel(AsyncSqlModel):
    """Model for preserving and restoring deleted AsyncHashedModel records."""
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
    async def insert(cls, data: dict) -> AsyncSqlModel | None:
        if 'timestamp' not in data:
            data['timestamp'] = str(int(time()))
        return await super().insert(data)

    async def restore(self, inject: dict = {}) -> AsyncSqlModel:
        """Restore a deleted record, remove from deleted_records, and
            return the restored model. Raises ValueError if model_class
            cannot be found. Raises TypeError if model_class is not a
            subclass of AsyncSqlModel. Uses packify.unpack to unpack the
            record. Raises TypeError if packed record is not a dict.
        """
        dependencies = {**globals(), **inject}
        vert(self.data['model_class'] in dependencies,
            'model_class must be accessible')
        model_class: AsyncSqlModel = dependencies[self.data['model_class']]
        tert(issubclass(model_class, AsyncSqlModel),
            'related_model must inherit from AsyncSqlModel')

        decoded = packify.unpack(self.data['record'])
        tert(type(decoded) is dict, 'encoded record is not a dict')

        if model_class.id_column not in decoded:
            decoded[model_class.id_column] = self.data['record_id']

        model = await model_class.insert(decoded)
        await self.delete()

        return model


class AsyncHashedModel(AsyncSqlModel):
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
    async def insert(cls, data: dict) -> Optional[AsyncHashedModel]:
        """Insert a new record to the datastore. Return instance. Raises
            TypeError for non-dict data or unencodable type (calls
            cls.generate_id, which calls packify.pack).
        """
        tert(isinstance(data, dict), 'data must be dict')
        data[cls.id_column] = cls.generate_id(data)

        return await cls.query().insert(data)

    @classmethod
    async def insert_many(cls, items: list[dict]) -> int:
        """Insert a batch of records and return the number of items
            inserted. Raises TypeError for invalid items or unencodable
            value (calls cls.generate_id, which calls packify.pack).
        """
        tert(isinstance(items, list), 'items must be type list[dict]')
        for item in items:
            tert(isinstance(item, dict), 'items must be type list[dict]')
            item[cls.id_column] = cls.generate_id(item)

        return await cls.query().insert_many(items)

    async def update(self, updates: dict) -> AsyncHashedModel:
        """Persist the specified changes to the datastore, creating a
            new record in the process. Update and return self in monad
            pattern. Raises TypeError or ValueError for invalid updates.
            Did not need to overwrite the save method because save calls
            update or insert.
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
            # if there's nothing to do, do nothing
            new_id = self.generate_id({**self.data, **updates})
            if new_id == self.data[self.id_column]:
                return self

            instance = await self.insert(updates)
            await self.delete()
        else:
            instance = await self.insert(updates)

        self.data = instance.data
        return instance

    async def delete(self) -> AsyncDeletedModel:
        """Delete the model, putting it in the deleted_records table,
            then return the AsyncDeletedModel. Raises packify.UsageError for
            unserializable data.
        """
        model_class = self.__class__.__name__
        record_id = self.data[self.id_column]
        record = packify.pack(self.data)
        deleted = await AsyncDeletedModel.insert({
            'model_class': model_class,
            'record_id': record_id,
            'record': record
        })
        await super().delete()
        return deleted


class AsyncAttachment(AsyncHashedModel):
    """Class for attaching immutable details to a record."""
    table: str = 'attachments'
    columns: tuple = ('id', 'related_model', 'related_id', 'details')
    id: str
    related_model: str
    related_id: str
    details: bytes|None
    _related: AsyncSqlModel = None
    _details: packify.SerializableType = None

    async def related(self, reload: bool = False) -> AsyncSqlModel:
        """Return the related record."""
        if self._related is None or reload:
            vert(self.data['related_model'] in globals(), 'model_class must be accessible')
            model_class: AsyncSqlModel = globals()[self.data['related_model']]
            tert(issubclass(model_class, AsyncSqlModel),
                'related_model must inherit from AsyncSqlModel')
            self._related = await model_class.find(self.data['related_id'])
        return self._related

    def attach_to(self, related: AsyncSqlModel) -> AsyncAttachment:
        """Attach to related model then return self."""
        tert(issubclass(related.__class__, AsyncSqlModel),
            'related must inherit from AsyncSqlModel')
        self.data['related_model'] = related.__class__.__name__
        self.data['related_id'] = related.data[related.id_column]
        return self

    def get_details(self, reload: bool = False) -> packify.SerializableType:
        """Decode packed bytes to dict."""
        if self._details is None or reload:
            self._details = packify.unpack(self.data['details'])
        return self._details

    def set_details(self, details: packify.SerializableType = {}) -> AsyncAttachment:
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
    async def insert(cls, data: dict) -> Optional[AsyncAttachment]:
        # """Redefined for better LSP support."""
        return await super().insert(data)
