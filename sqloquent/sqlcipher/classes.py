from sqloquent.classes import SqlQueryBuilder, SqlModel, HashedModel, DeletedModel, Attachment
from sqloquent.errors import tert, vert, tressa
from sqloquent.interfaces import (
    QueryBuilderProtocol,
    DBContextProtocol,
    ModelProtocol,
    CursorProtocol,
)
from types import TracebackType
from typing import Optional, Type
import sqlcipher3
import threading


class SqlcipherContext:
    """Context manager for encrypted sqlite via SQLCipher.
       Automatically handles connection pooling and encryption.
    """
    _thread_local = threading.local()

    connection: sqlcipher3.Connection
    cursor: sqlcipher3.Cursor
    connection_info: str
    encryption_key: str

    def __init__(self, connection_info: str = '',
                 encryption_key: str = '') -> None:
        """Initialize the instance. Raises TypeError for non-str connection_info."""
        if not connection_info and hasattr(self, 'connection_info'):
            connection_info = self.connection_info
        tert(type(connection_info) is str,
            'connection_info must be str')
        tressa(len(connection_info) > 0, 'cannot use with empty connection_info')
        self.connection_info = connection_info

        tert(type(encryption_key) is str, 'encryption_key must be str')
        if not encryption_key and hasattr(self.__class__, 'encryption_key'):
            encryption_key = self.__class__.encryption_key
        self.encryption_key = encryption_key

    def __enter__(self) -> CursorProtocol:
        """Enter the context block and return the cursor."""
        if not hasattr(SqlcipherContext._thread_local, 'connections'):
            SqlcipherContext._thread_local.connections = {}
        if not hasattr(SqlcipherContext._thread_local, 'cursors'):
            SqlcipherContext._thread_local.cursors = {}
        if not hasattr(SqlcipherContext._thread_local, 'depths'):
            SqlcipherContext._thread_local.depths = {}

        if self.connection_info not in SqlcipherContext._thread_local.depths:
            SqlcipherContext._thread_local.depths[self.connection_info] = 0

        SqlcipherContext._thread_local.depths[self.connection_info] += 1

        if self.connection_info not in SqlcipherContext._thread_local.connections:
            SqlcipherContext._thread_local.connections[self.connection_info] = sqlcipher3.connect(
                self.connection_info
            )

        self.connection = SqlcipherContext._thread_local.connections[self.connection_info]

        if self.encryption_key:
            self.connection.execute(f"PRAGMA key = '{self.encryption_key}'")

        if self.connection_info not in SqlcipherContext._thread_local.cursors:
            SqlcipherContext._thread_local.cursors[self.connection_info] = self.connection.cursor()

        self.cursor = SqlcipherContext._thread_local.cursors[self.connection_info]

        return self.cursor

    def __exit__(self, exc_type: Optional[Type[BaseException]],
                exc_value: Optional[BaseException],
                traceback: Optional[TracebackType]) -> None:
        """Exit the context block. Commit or rollback as appropriate,
            then close the connection if this is the outermost context.
        """
        SqlcipherContext._thread_local.depths[self.connection_info] -= 1

        if exc_type is not None:
            self.connection.rollback()
        else:
            self.connection.commit()

        if SqlcipherContext._thread_local.depths[self.connection_info] == 0:
            self.cursor.close()
            self.connection.close()
            del SqlcipherContext._thread_local.connections[self.connection_info]
            del SqlcipherContext._thread_local.cursors[self.connection_info]
            del SqlcipherContext._thread_local.depths[self.connection_info]


class SqlcipherQueryBuilder(SqlQueryBuilder):
    """Query builder for encrypted SQLite databases."""

    def __init__(self, model_or_table: Type[SqlModel]|str = None,
                 context_manager: Type[DBContextProtocol] = SqlcipherContext,
                 encryption_key: str = '', **kwargs) -> None:
        """Initialize with SqlcipherContext and optional encryption_key."""
        super().__init__(
            model_or_table,
            context_manager,
            **kwargs
        )
        if encryption_key:
            self.context_manager.encryption_key = encryption_key


class SqlcipherModel(SqlModel):
    """Model for encrypted SQLite databases."""
    query_builder_class: Type[QueryBuilderProtocol] = SqlcipherQueryBuilder

    def __init__(self, data: dict = {}) -> None:
        """Initialize instance."""
        super().__init__(data)


class DeletedSqlcipherModel(DeletedModel):
    """DeletedModel for encrypted SQLite databases."""
    query_builder_class: Type[QueryBuilderProtocol] = SqlcipherQueryBuilder

    def restore(self, /, inject: dict = {}, *, suppress_events: bool = False) -> SqlModel:
        return super().restore({**globals(), **inject}, suppress_events=suppress_events)


class HashedSqlcipherModel(HashedModel):
    """HashedModel for encrypted SQLite databases."""
    query_builder_class: Type[QueryBuilderProtocol] = SqlcipherQueryBuilder
    deleted_model_class = DeletedSqlcipherModel


class SqlcipherAttachment(Attachment):
    """Attachment for encrypted SQLite databases."""
    query_builder_class: Type[QueryBuilderProtocol] = SqlcipherQueryBuilder
    deleted_model_class = DeletedSqlcipherModel

    def related(
            self, reload: bool = False, *, inject: dict = {}
        ) -> SqlcipherModel:
        return super().related(reload, inject={**inject, **globals()})

