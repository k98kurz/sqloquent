from __future__ import annotations
from .classes import SqliteContext, dynamic_sqlite_model
from .errors import tressa
from .interfaces import DBContextProtocol, TableProtocol, ModelProtocol
from dataclasses import dataclass, field
from typing import Any, Callable
import string


@dataclass
class Column:
    name: str = field()
    datatype: str = field()
    table: TableProtocol = field()
    is_nullable: bool = field(default=True)
    new_name: str = field(default=None)

    def validate(self) -> None:
        allowed = set(string.ascii_letters + string.digits + "_")
        tressa(all([n in allowed for n in self.name]),
               "Column name can contain only letters, numbers, and underscores")
        tressa(self.name[0] in string.ascii_letters,
               "Column name must start with a letter")

    def not_null(self) -> Column:
        self.is_nullable = False
        return self

    def nullable(self) -> Column:
        self.is_nullable = True
        return self

    def index(self) -> Column:
        self.table.index([self])
        return self

    def unique(self) -> Column:
        self.table.unique([self])
        return self

    def drop(self) -> Column:
        self.table.drop_column(self)
        return self

    def rename(self, new_name: str) -> Column:
        self.new_name = new_name
        self.table.rename_column(self)
        return self


def get_index_name(table: TableProtocol, columns: list[Column|str],
                   is_unique: bool = False) -> str:
    """Generate the name for an index from the table, columns, and type."""
    name = 'udx_' if is_unique else 'idx_'
    name += table.name + '_'
    column_names = [
        c if type(c) is str else c.name
        for c in columns
    ]
    name += '_'.join(column_names)
    return name


@dataclass
class SqliteTable:
    name: str = field()
    new_name: str = field(default=None)
    columns_to_add: list[Column] = field(default_factory=list)
    columns_to_drop: list[Column|str] = field(default_factory=list)
    columns_to_rename: list[Column|list[str]] = field(default_factory=list)
    indices_to_add: list[list[Column|str]] = field(default_factory=list)
    indices_to_drop: list[list[Column|str]] = field(default_factory=list)
    uniques_to_add: list[list[Column|str]] = field(default_factory=list)
    uniques_to_drop: list[list[Column|str]] = field(default_factory=list)
    is_create: bool = field(default=False)
    is_drop: bool = field(default=False)

    @classmethod
    def create(cls, name: str) -> SqliteTable:
        return cls(name=name, is_create=True)

    @classmethod
    def alter(cls, name: str) -> SqliteTable:
        return cls(name=name)

    @classmethod
    def drop(cls, name: str) -> SqliteTable:
        return cls(name=name, is_drop=True)

    def rename(self, name: str) -> SqliteTable:
        """Rename the table."""
        self.new_name = name
        return self

    def index(self, columns: list[Column|str]) -> SqliteTable:
        self.indices_to_add.append(columns)
        return self

    def drop_index(self, columns: list[Column|str]) -> SqliteTable:
        self.indices_to_drop.append(columns)
        return self

    def unique(self, columns: list[Column|str]) -> SqliteTable:
        self.uniques_to_add.append(columns)
        return self

    def drop_unique(self, columns: list[Column|str]) -> SqliteTable:
        self.uniques_to_drop.append(columns)
        return self

    def drop_column(self, column: Column|str) -> SqliteTable:
        self.columns_to_drop.append(column)
        return self

    def rename_column(self, column: Column|list[str]) -> SqliteTable:
        self.columns_to_rename.append(column)
        return self

    def integer(self, name: str) -> Column:
        column = Column(name, "integer", table=self)
        column.validate()
        self.columns_to_add.append(column)
        return column

    def numeric(self, name: str) -> Column:
        column = Column(name, "numeric", table=self)
        column.validate()
        self.columns_to_add.append(column)
        return column

    def real(self, name: str) -> Column:
        column = Column(name, "real", table=self)
        column.validate()
        self.columns_to_add.append(column)
        return column

    def text(self, name: str) -> Column:
        column = Column(name, "text", table=self)
        column.validate()
        self.columns_to_add.append(column)
        return column

    def blob(self, name: str) -> Column:
        column = Column(name, "blob", table=self)
        column.validate()
        self.columns_to_add.append(column)
        return column

    def sql(self) -> list[str]:
        """Return the SQL clauses to be run."""
        clauses = []

        if self.is_drop:
            errmsg = "cannot combine drop table with other operations"
            tressa(not self.is_create, errmsg)
            tressa(self.new_name is None, errmsg)
            tressa(len(self.columns_to_add) == 0, errmsg)
            tressa(len(self.columns_to_drop) == 0, errmsg)
            tressa(len(self.columns_to_rename) == 0, errmsg)
            tressa(len(self.indices_to_add) == 0, errmsg)
            tressa(len(self.indices_to_drop) == 0, errmsg)
            tressa(len(self.uniques_to_add) == 0, errmsg)
            tressa(len(self.uniques_to_drop) == 0, errmsg)
            return [f"drop table if exists {self.name}"]

        if self.new_name:
            errmsg = "cannot combine rename table with other operations"
            tressa(not self.is_create, errmsg)
            tressa(len(self.columns_to_add) == 0, errmsg)
            tressa(len(self.columns_to_drop) == 0, errmsg)
            tressa(len(self.columns_to_rename) == 0, errmsg)
            tressa(len(self.indices_to_add) == 0, errmsg)
            tressa(len(self.indices_to_drop) == 0, errmsg)
            tressa(len(self.uniques_to_add) == 0, errmsg)
            tressa(len(self.uniques_to_drop) == 0, errmsg)
            return [f"alter table {self.name} rename to {self.new_name}"]

        for idx in self.uniques_to_drop:
            clauses.append(f"drop index if exists {get_index_name(self, idx, True)}")

        for idx in self.indices_to_drop:
            clauses.append(f"drop index if exists {get_index_name(self, idx)}")

        if self.is_create:
            tressa(self.new_name is None, "cannot combine create table with rename")
            create = []
            for col in self.columns_to_add:
                col.validate()
                clause = f"{col.name} {col.datatype}"
                if not col.is_nullable:
                    clause += " not null"
                create.append(clause)
            clauses.append(f"create table if not exists {self.name} ({', '.join(create)})")
        else:
            for col in self.columns_to_drop:
                if isinstance(col, Column):
                    col.validate()
                colname = col if type(col) is str else col.name
                clauses.append(f"alter table {self.name} drop column {colname}")

            for col in self.columns_to_add:
                col.validate()
                clause = f"alter table {self.name} add column {col.name} {col.datatype}"
                if not col.is_nullable:
                    clause += " not null"
                clauses.append(clause)

            for col in self.columns_to_rename:
                clause = f"alter table {self.name} rename column "
                if type(col) is Column:
                    col.validate()
                    clause += f"{col.name} to {col.new_name}"
                else:
                    clause += f"{col[0]} to {col[1]}"
                clauses.append(clause)

        for idx in self.uniques_to_add:
            colnames = [c if type(c) is str else c.name for c in idx]
            clause =f"create unique index if not exists {get_index_name(self, idx, True)} "
            clause += f"on {self.name} (" + ", ".join(colnames) + ")"
            clauses.append(clause)

        for idx in self.indices_to_add:
            colnames = [c if type(c) is str else c.name for c in idx]
            clause =f"create index if not exists {get_index_name(self, idx)} "
            clause += f"on {self.name} (" + ", ".join(colnames) + ")"
            clauses.append(clause)

        return clauses


@dataclass
class Migration:
    connection_info: str = field(default="")
    model_factory: Callable[[Any], ModelProtocol] = field(default=dynamic_sqlite_model)
    context_manager: type[DBContextProtocol] = field(default=SqliteContext)
    up_callbacks: list[Callable[[], list[TableProtocol]]] = field(default_factory=list)
    down_callbacks: list[Callable[[], list[TableProtocol]]] = field(default_factory=list)

    def up(self, callback: Callable[[], list[TableProtocol]]) -> None:
        """Specify the forward migration."""
        self.up_callbacks.append(callback)

    def down(self, callback: Callable[[], list[TableProtocol]]) -> None:
        """Specify the backward migration."""
        self.down_callbacks.append(callback)

    def get_apply_sql(self) -> str:
        """Get the SQL for the forward migration."""
        clauses: list[str] = []
        for callback in self.up_callbacks:
            tables = callback()
            for table in tables:
                clauses.extend(table.sql())
        return "begin;\n" + ";\n".join(clauses) + ";\ncommit;"

    def apply(self) -> None:
        """Apply the forward migration."""
        for callback in self.up_callbacks:
            clauses: list[str] = []
            tables = callback()
            for table in tables:
                clauses.extend(table.sql())
            sql = "begin;\n" + ";\n".join(clauses) + ";\ncommit;"
            with self.context_manager(self.model_factory(self.connection_info)) as cursor:
                cursor.executescript(sql)

    def get_undo_sql(self) -> str:
        """Get the SQL for the backward migration."""
        clauses: list[str] = []
        for callback in self.down_callbacks:
            tables = callback()
            for table in tables:
                clauses.extend(table.sql())
        return "begin;\n" + ";\n".join(clauses) + ";\ncommit;"

    def undo(self) -> None:
        """Apply the backward migration."""
        for callback in self.down_callbacks:
            clauses: list[str] = []
            tables = callback()
            for table in tables:
                clauses.extend(table.sql())
            sql = "begin;\n" + ";\n".join(clauses) + ";\ncommit;"
            with self.context_manager(self.model_factory(self.connection_info)) as cursor:
                cursor.executescript(sql)
