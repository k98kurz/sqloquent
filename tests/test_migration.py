from context import errors, interfaces, migration
from genericpath import isfile
import os
import sqlite3
import string
import unittest


DB_FILEPATH = 'test.db'


class TestMigration(unittest.TestCase):
    db: sqlite3.Connection = None
    cursor: sqlite3.Cursor = None

    def setUp(self) -> None:
        """Set up the test database."""
        try:
            if isfile(DB_FILEPATH):
                os.remove(DB_FILEPATH)
        except:
            ...
        self.db = sqlite3.connect(DB_FILEPATH)
        self.cursor = self.db.cursor()

    def tearDown(self) -> None:
        """Close cursor and delete test database."""
        self.cursor.close()
        self.db.close()
        os.remove(DB_FILEPATH)
        return super().tearDown()

    def test_migration_has_necessary_classes(self):
        assert hasattr(migration, 'Column')
        assert type(migration.Column) is type
        assert hasattr(migration, 'get_index_name')
        assert callable(migration.get_index_name)
        assert hasattr(migration, 'Table')
        assert type(migration.Table) is type
        assert hasattr(migration, 'Migration')
        assert type(migration.Migration) is type

    def test_Column_class_implements_ColumnProtocol(self):
        c = migration.Column('test', 'integer', migration.Table("test"))
        assert isinstance(c, interfaces.ColumnProtocol)

    def test_Column_validate_rejects_bad_names(self):
        t = migration.Table("test")
        disallowed = set(string.punctuation + string.whitespace)
        disallowed.remove("_")
        valid = "hello_world5"
        migration.Column(valid, "integer", t).validate()
        for char in disallowed:
            with self.assertRaises(ValueError) as e:
                migration.Column(valid + char, "integer", t).validate()
            assert str(e.exception) == "Column name can contain only letters, numbers, and underscores"
        with self.assertRaises(ValueError) as e:
            migration.Column("8" + valid, "integer", t).validate()
        assert str(e.exception) == "Column name must start with a letter"

    def test_Table_implements_TableProtocol(self):
        t = migration.Table("test")
        assert isinstance(t, interfaces.TableProtocol)

    def test_Migration_implements_TableProtocol(self):
        m = migration.Migration("test")
        assert isinstance(m, interfaces.MigrationProtocol)

    def test_get_index_name_works(self):
        t = migration.Table("test")
        idxname = migration.get_index_name(t, ["thing"])
        assert type(idxname) is str
        assert idxname == "idx_test_thing"
        idxname = migration.get_index_name(t, ["thing"], True)
        assert type(idxname) is str
        assert idxname == "udx_test_thing"

    # Table tests
    def test_Table_sql_returns_list_str(self):
        t = migration.Table('test')
        t.columns_to_add.append(migration.Column('test1', 'integer', t))
        sql = t.sql()
        assert type(sql) is list
        assert all([type(s) is str for s in sql])

    def test_Table_custom_sets_callback_that_runs_before_returning_sql(self):
        t = migration.Table('test')
        logs = []
        def thing(l: list[str]) -> list[str]:
            logs.append('hello world')
            return l
        s1 = t.sql()
        t.custom(thing)
        assert len(logs) == 0
        s2 = t.sql()
        assert s1 == s2
        assert len(logs) == 1

    def test_Table_create_returns_instance(self):
        t = migration.Table.create('test')
        assert isinstance(t, migration.Table)

    def test_Table_alter_returns_instance(self):
        t = migration.Table.alter('test')
        assert isinstance(t, migration.Table)

    def test_Table_drop_returns_instance(self):
        t = migration.Table.drop('test')
        assert isinstance(t, migration.Table)

    def test_Table_create(self):
        t = migration.Table.create('things')
        t.integer("id")
        sql = t.sql()
        assert len(sql) == 1
        assert sql[0] == "create table if not exists things (id integer)"

        t = migration.Table.create('things')
        t.integer("id").unique()
        t.text("name").index()
        sql = t.sql()
        assert len(sql) == 3
        assert sql[0] == "create table if not exists things (id integer, name text)"
        assert sql[1] == "create unique index if not exists udx_things_id on things (id)"
        assert sql[2] == "create index if not exists idx_things_name on things (name)"

        t = migration.Table.create('things')
        col1 = t.integer("id")
        col2 = t.text("name")
        t.unique([col1, col2])
        sql = t.sql()
        assert len(sql) == 2
        assert sql[0] == "create table if not exists things (id integer, name text)"
        assert sql[1] == "create unique index if not exists udx_things_id_name on things (id, name)"

        t = migration.Table.create('things')
        t.integer("id")
        t.text("name")
        t.numeric("parts")
        t.real("fraction")
        t.blob("data")
        sql = t.sql()
        assert len(sql) == 1
        assert sql[0] == "create table if not exists things (id integer, " + \
            "name text, parts numeric, fraction real, data blob)", f"\'{sql[0]}\' is wrong"

    def test_Table_alter(self):
        t = migration.Table.alter('things')
        t.rename("things2")
        sql = t.sql()
        assert len(sql) == 1
        assert sql[0] == "alter table things rename to things2"

        with self.assertRaises(errors.UsageError):
            t.integer("should_not_work")
            t.sql()

        t = migration.Table.alter('things')
        t.drop_column("test")
        t.rename_column(["first", "second"])
        migration.Column("p1", "integer", t).rename("p2")
        t.drop_index(["test"])
        t.drop_unique(["test"])
        sql = t.sql()
        assert len(sql) == 5
        assert sql[0] == "drop index if exists udx_things_test"
        assert sql[1] == "drop index if exists idx_things_test"
        assert sql[2] == "alter table things drop column test"
        assert sql[3] == "alter table things rename column first to second"
        assert sql[4] == "alter table things rename column p1 to p2"

    def test_Table_drop(self):
        t = migration.Table.drop("things")
        sql = t.sql()
        assert len(sql) == 1
        assert sql[0] == "drop table if exists things"

        with self.assertRaises(ValueError):
            t.integer("some column")
            t.sql()

    # Migration tests
    def test_Migration_apply_calls_all_up_callbacks(self):
        logs = []
        m = migration.Migration(DB_FILEPATH)
        m.up(lambda: logs.append(1) or [])
        m.up(lambda: logs.append(2) or [])
        m.apply()
        assert logs == [1, 2]

    def test_Migration_undo_calls_all_down_callbacks(self):
        logs = []
        m = migration.Migration(DB_FILEPATH)
        m.down(lambda: logs.append(1) or [])
        m.down(lambda: logs.append(2) or [])
        m.undo()
        assert logs == [1, 2]

    def test_Migration_up_and_down_e2e(self):
        def create_things_table():
            t = migration.Table.create("things")
            t.integer("id").unique()
            t.text("name").index()
            return [t]

        def drop_things_table():
            t = migration.Table.drop("things")
            return [t]

        m = migration.Migration(DB_FILEPATH)
        m.up(create_things_table)
        m.down(drop_things_table)
        expected = "begin;\ncreate table if not exists things (id integer, name text);\n"
        expected += "create unique index if not exists udx_things_id on things (id);\n"
        expected += "create index if not exists idx_things_name on things (name);\ncommit;"
        sql = m.get_apply_sql()
        assert type(sql) is str
        assert sql == expected, f"expected '{expected}'\nencountered '{sql}"

        q = "select name from sqlite_master where type='table' and name='things'"
        assert len(self.cursor.execute(q).fetchall())  == 0

        m.apply()
        assert len(self.cursor.execute(q).fetchall())  == 1

        expected = "begin;\ndrop table if exists things;\ncommit;"
        sql = m.get_undo_sql()
        assert type(sql) is str
        assert sql == expected, f"expected '{expected}'\nencountered '{sql}"

        q = "select name from sqlite_master where type='table' and name='things'"
        assert len(self.cursor.execute(q).fetchall())  == 1

        m.undo()
        assert len(self.cursor.execute(q).fetchall())  == 0


if __name__ == '__main__':
    unittest.main()
