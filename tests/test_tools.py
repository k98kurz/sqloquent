from context import tools
from genericpath import isdir, isfile
from secrets import token_hex
import os
import sqlite3
import unittest


DB_FILEPATH = 'test.db'
MIGRATIONS_PATH = 'tests/temp/migrations'


class TestIntegration(unittest.TestCase):
    db: sqlite3.Connection = None
    cursor: sqlite3.Cursor = None

    def setUp(self):
        """Set up the test database."""
        try:
            if isfile(DB_FILEPATH):
                os.remove(DB_FILEPATH)
        except:
            ...
        self.db = sqlite3.connect(DB_FILEPATH)
        self.cursor = self.db.cursor()
        if not isdir(MIGRATIONS_PATH):
            os.mkdir(MIGRATIONS_PATH)
        for file in os.listdir(MIGRATIONS_PATH):
            if 'migration' in file and file[-3:] == '.py':
                os.remove(f"{MIGRATIONS_PATH}/{file}")
        return super().setUp()

    def tearDown(self):
        """Close cursor and delete test database."""
        self.cursor.close()
        self.db.close()
        os.remove(DB_FILEPATH)
        for file in os.listdir(MIGRATIONS_PATH):
            if 'migration' in file and file[-3:] == '.py':
                os.remove(f"{MIGRATIONS_PATH}/{file}")
        return super().tearDown()

    def test_make_migration_create_returns_str_with_correct_content(self):
        name = token_hex(4)
        result = tools.make_migration_create(name, DB_FILEPATH)
        assert type(result) is str
        assert name in result
        assert 'Table.create' in result
        assert 'Table.drop' in result
        assert 'Migration' in result
        assert 'Table' in result
        assert 'up' in result
        assert 'down' in result
        assert 'def migration' in result
        assert DB_FILEPATH in result

    def test_make_migration_alter_returns_str_with_correct_content(self):
        name = token_hex(4)
        result = tools.make_migration_alter(name, DB_FILEPATH)
        assert type(result) is str
        assert name in result
        assert 'Table.alter' in result
        assert 'Migration' in result
        assert 'Table' in result
        assert 'up' in result
        assert 'down' in result
        assert 'def migration' in result
        assert DB_FILEPATH in result

    def test_make_migration_drop_returns_str_with_correct_content(self):
        name = token_hex(4)
        result = tools.make_migration_drop(name, DB_FILEPATH)
        assert type(result) is str
        assert name in result
        assert 'Table.drop' in result
        assert 'Table.create' in result
        assert 'Migration' in result
        assert 'Table' in result
        assert 'up' in result
        assert 'down' in result
        assert 'def migration' in result
        assert DB_FILEPATH in result

    def test_make_migration_from_model_returns_str_with_correct_content(self):
        name = 'Attachment'
        result = tools.make_migration_from_model(name, 'sqloquent/classes.py', DB_FILEPATH)
        assert type(result) is str
        assert name.lower() in result
        assert 'Table.drop' in result
        assert 'Table.create' in result
        assert 'Migration' in result
        assert 'Table' in result
        assert 'up' in result
        assert 'down' in result
        assert 'def migration' in result
        assert DB_FILEPATH in result

    def test_make_model_returns_str_with_correct_content(self):
        name = f"M{token_hex(4)}"
        columns = ('id', 'thing1', 'thing2')
        bases = ('SqliteModel', 'SqlModel', 'HashedModel', 'HashedSqliteModel')
        for base in bases:
            result = tools.make_model(
                name,
                base=base,
                columns=columns,
                connection_string=DB_FILEPATH
            )
            assert type(result) is str
            assert f"class {name}({base}):" in result
            assert f"columns: tuple[str] = {columns}" in result
            if base in ('SqliteModel', 'HashedSqliteModel'):
                assert f"file_path: str = '{DB_FILEPATH}'" in result

    def test_publish_migrations_creates_attachments_and_deleted_model_migrations(self):
        list_files = lambda: [f for f in os.listdir(MIGRATIONS_PATH) if f[-3:] == '.py']
        assert len(list_files()) == 0
        tools.publish_migrations(MIGRATIONS_PATH)
        assert len(list_files()) == 2
        assert 'attachment_migration.py' in list_files()
        assert 'deleted_model_migration.py' in list_files()

    def test_migrate_rollback_refresh_e2e(self):
        path = f"{MIGRATIONS_PATH}/create_test_table_migration.py"
        src = tools.make_migration_create('test', DB_FILEPATH)
        with open(path, 'w') as f:
            f.write(src)
        assert not self.table_exists("test")
        tools.migrate(path, DB_FILEPATH)
        assert self.table_exists("test")
        tools.refresh(path, DB_FILEPATH)
        assert self.table_exists("test")
        tools.rollback(path, DB_FILEPATH)
        assert not self.table_exists("test")

    def test_automigrate_autorollback_autorefresh_e2e(self):
        names = ['test1', 'test2', 'test3']
        for name in names:
            path = f"{MIGRATIONS_PATH}/create_{name}_table_migration.py"
            src = tools.make_migration_create(name, DB_FILEPATH)
            with open(path, 'w') as f:
                f.write(src)
        assert not self.table_exists("migrations")
        assert self.tables_do_not_exist(names)
        tools.automigrate(MIGRATIONS_PATH, DB_FILEPATH)
        assert self.table_exists("migrations")
        assert self.tables_exist(names)
        tools.autorefresh(MIGRATIONS_PATH, DB_FILEPATH)
        assert self.table_exists("migrations")
        assert self.tables_exist(names)
        tools.autorollback(MIGRATIONS_PATH, DB_FILEPATH)
        assert self.table_exists("migrations")
        assert self.tables_do_not_exist(names)

    def test_automigrate_does_not_replicate_batches(self):
        batch1 = ['test1', 'test2']
        batch2 = ['test3', 'test4']
        def create_batch_files(names: list[str]):
            for name in names:
                path = f"{MIGRATIONS_PATH}/create_{name}_table_migration.py"
                src = tools.make_migration_create(name, DB_FILEPATH)
                with open(path, 'w') as f:
                    f.write(src)
        create_batch_files(batch1)
        tools.automigrate(MIGRATIONS_PATH, DB_FILEPATH)
        assert self.table_exists('test2')
        self.cursor.execute('drop table test2')
        assert not self.table_exists('test2')
        create_batch_files(batch2)
        tools.automigrate(MIGRATIONS_PATH, DB_FILEPATH)
        assert not self.table_exists('test2')
        assert self.table_exists('test3')

    def test_help_cli_returns_str_help_text(self):
        result = tools.help_cli('sqloquent')
        assert type(result) is str
        assert result[:5] == 'usage'

    def table_exists(self, name: str) -> bool:
        q = f"select name from sqlite_master where type='table' and name='{name}'"
        return len(self.cursor.execute(q).fetchall()) > 0

    def tables_exist(self, names: list[str]) -> bool:
        for name in names:
            q = f"select name from sqlite_master where type='table' and name='{name}'"
            if len(self.cursor.execute(q).fetchall()) == 0:
                return False
        return True

    def tables_do_not_exist(self, names: list[str]) -> bool:
        for name in names:
            q = f"select name from sqlite_master where type='table' and name='{name}'"
            if len(self.cursor.execute(q).fetchall()) > 0:
                return False
        return True


if __name__ == '__main__':
    unittest.main()
