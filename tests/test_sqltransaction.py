from context import sqloquent, errors
import threading
import time
import unittest
import os


DB_FILEPATH = 'test_transactions.db'
DB_FILEPATH1 = 'test_transactions1.db'
DB_FILEPATH2 = 'test_transactions2.db'


class TestModel(sqloquent.SqlModel):
    table: str = 'test'
    id_column: str = 'id'
    columns: tuple[str, ...] = ('id', 'name')
    id: str
    name: str
    connection_info: str = DB_FILEPATH


class TestModel1(sqloquent.SqlModel):
    table: str = 'test1'
    id_column: str = 'id'
    columns: tuple[str, ...] = ('id', 'name')
    id: str
    name: str
    connection_info: str = DB_FILEPATH1


class TestModel2(sqloquent.SqlModel):
    table: str = 'test2'
    id_column: str = 'id'
    columns: tuple[str, ...] = ('id', 'name')
    id: str
    name: str
    connection_info: str = DB_FILEPATH2


class TestSqlTransaction(unittest.TestCase):
    """Test SqlTransaction class functionality."""
    def setUp(self) -> None:
        """Set up the test database."""
        for db in [DB_FILEPATH, DB_FILEPATH1, DB_FILEPATH2]:
            try:
                if os.path.isfile(db):
                    os.remove(db)
            except:
                ...

        c = sqloquent.SqliteContext(DB_FILEPATH)
        cursor = c.__enter__()
        cursor.execute('create table test (id text, name text)')
        c.__exit__(None, None, None)

        c1 = sqloquent.SqliteContext(DB_FILEPATH1)
        cursor1 = c1.__enter__()
        cursor1.execute('create table test1 (id text, name text)')
        c1.__exit__(None, None, None)

        c2 = sqloquent.SqliteContext(DB_FILEPATH2)
        cursor2 = c2.__enter__()
        cursor2.execute('create table test2 (id text, name text)')
        c2.__exit__(None, None, None)

        sqloquent.SqlModel.clear_hooks()

    def tearDown(self) -> None:
        """Close cursor and delete test database."""
        for db in [DB_FILEPATH, DB_FILEPATH1, DB_FILEPATH2]:
            try:
                os.remove(db)
            except:
                ...

    # Basic SqlTransaction tests
    def test_basic_sqltransaction_success(self):
        """Test basic SqlTransaction success with multiple inserts."""
        with sqloquent.SqlTransaction(DB_FILEPATH):
            TestModel.insert({'name': 'Alice'})
            TestModel.insert({'name': 'Bob'})

        # Verify both records committed
        results = TestModel.query().get()
        assert len(results) == 2, 'should have 2 records'
        assert results[0].name == 'Alice', 'first record should be Alice'
        assert results[1].name == 'Bob', 'second record should be Bob'

    def test_transaction_rollback_on_exception(self):
        """Test that transaction rolls back on exception."""
        with self.assertRaises(ValueError):
            with sqloquent.SqlTransaction(DB_FILEPATH):
                TestModel.insert({'name': 'Alice'})
                raise ValueError('test error')

        # Verify no records committed
        results = TestModel.query().get()
        assert len(results) == 0, 'should have 0 records after rollback'

    # Manual commit/rollback tests
    def test_manual_commit(self):
        """Test manual commit within transaction."""
        with self.assertRaises(ValueError):
            with sqloquent.SqlTransaction(DB_FILEPATH) as tx:
                TestModel.insert({'name': 'Alice'})
                assert not tx.is_committed, 'should not be committed yet'
                tx.commit()
                assert tx.is_committed, 'should be committed'
                TestModel.insert({'name': 'Bob'})
                raise ValueError('test exception')

        # Only first record should exist
        results = TestModel.query().get()
        assert len(results) == 1, 'should have 1 record'
        assert results[0].name == 'Alice', 'record should be Alice'

    def test_manual_rollback(self):
        """Test manual rollback within transaction."""
        with sqloquent.SqlTransaction(DB_FILEPATH) as tx:
            TestModel.insert({'name': 'Alice'})
            assert not tx.is_rolled_back, 'should not be rolled back yet'
            tx.rollback()
            assert tx.is_rolled_back, 'should be rolled back'
            TestModel.insert({'name': 'Bob'})

        # Only second record should exist
        results = TestModel.query().get()
        assert len(results) == 1, 'should have 1 record'
        assert results[0].name == 'Bob', 'record should be Bob'

    def test_manual_commit_then_rollback(self):
        """Test manual commit followed by manual rollback."""
        with sqloquent.SqlTransaction(DB_FILEPATH) as tx:
            TestModel.insert({'name': 'Alice'})
            tx.commit()
            TestModel.insert({'name': 'Bob'})
            tx.rollback()

        # Only first record should exist
        results = TestModel.query().get()
        assert len(results) == 1, 'should have 1 record'
        assert results[0].name == 'Alice', 'record should be Alice'

    # Nested transaction tests
    def test_nested_transaction_error(self):
        """Test that nested transactions on same connection raise error."""
        with self.assertRaises(RuntimeError) as cm:
            with sqloquent.SqlTransaction(DB_FILEPATH):
                with sqloquent.SqlTransaction(DB_FILEPATH):
                    pass
        assert 'Nested transactions' in str(cm.exception), 'should be about nested tx'

    def test_different_connections(self):
        """Test transaction on one connection while other auto-commits."""
        with sqloquent.SqlTransaction(DB_FILEPATH1):
            TestModel1.insert({'name': 'Alice'})
            TestModel2.insert({'name': 'Bob'})

        # Verify both records exist
        results1 = TestModel1.query().get()
        results2 = TestModel2.query().get()
        assert len(results1) == 1, 'should have 1 record in conn1'
        assert len(results2) == 1, 'should have 1 record in conn2'

    # MultiDBTransaction tests
    def test_multidbtransaction(self):
        """Test MultiDBTransaction with two connections."""
        with sqloquent.MultiDBTransaction(DB_FILEPATH1, DB_FILEPATH2):
            TestModel1.insert({'name': 'Alice'})
            TestModel2.insert({'name': 'Bob'})

        # Verify both records exist
        results1 = TestModel1.query().get()
        results2 = TestModel2.query().get()
        assert len(results1) == 1, 'should have 1 record in conn1'
        assert len(results2) == 1, 'should have 1 record in conn2'

    def test_multidbtransaction_rollback(self):
        """Test MultiDBTransaction rollback on exception."""
        with self.assertRaises(ValueError):
            with sqloquent.MultiDBTransaction(DB_FILEPATH1, DB_FILEPATH2):
                TestModel1.insert({'name': 'Alice'})
                TestModel2.insert({'name': 'Bob'})
                raise ValueError('test error')

        # Verify no records committed
        results1 = TestModel1.query().get()
        results2 = TestModel2.query().get()
        assert len(results1) == 0, 'should have 0 records in conn1'
        assert len(results2) == 0, 'should have 0 records in conn2'

    # transactional decorator tests
    def test_transactional_decorator(self):
        """Test @transactional decorator."""
        @sqloquent.transactional(DB_FILEPATH)
        def insert_records():
            TestModel.insert({'name': 'Alice'})
            TestModel.insert({'name': 'Bob'})

        insert_records()

        # Verify both records committed
        results = TestModel.query().get()
        assert len(results) == 2, 'should have 2 records'

    # Thread safety tests
    def test_thread_safety(self):
        """Test thread safety of transactions."""
        DB_FILEPATH_THREAD = 'test_transactions_thread.db'

        # Create table for thread test
        c = sqloquent.SqliteContext(DB_FILEPATH_THREAD)
        cursor = c.__enter__()
        cursor.execute('create table test (id text, name text, thread_id text)')
        c.__exit__(None, None, None)

        class TestModelThread(sqloquent.SqlModel):
            table: str = 'test'
            id_column: str = 'id'
            columns: tuple[str, ...] = ('id', 'name', 'thread_id')
            id: str
            name: str
            thread_id: str
            connection_info: str = DB_FILEPATH_THREAD

        def insert_in_thread(thread_id):
            with sqloquent.SqlTransaction(DB_FILEPATH_THREAD):
                TestModelThread.insert({'name': f'Record{thread_id}', 'thread_id': thread_id})
                time.sleep(0.1)

        threads = []
        for i in range(3):
            t = threading.Thread(target=insert_in_thread, args=(f'thread{i}',))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Verify all records committed
        results = TestModelThread.query().get()
        assert len(results) == 3, 'should have 3 records'

        # Clean up
        try:
            os.remove(DB_FILEPATH_THREAD)
        except:
            ...

    # All model operations tests
    def test_all_model_operations(self):
        """Test insert, update, delete, save in transaction."""
        with sqloquent.SqlTransaction(DB_FILEPATH):
            m1 = TestModel.insert({'name': 'Alice'})
            m1.update({'name': 'Alice Updated'})
            m2 = TestModel({'name': 'Bob'})
            m2.save()
            m2.delete()

        # Verify correct state
        results = TestModel.query().get()
        assert len(results) == 1, 'should have 1 record'
        assert results[0].name == 'Alice Updated', 'record should be updated'

    # Event hooks tests
    def test_event_hooks(self):
        """Test that event hooks still fire within transactions."""
        before_insert_called = False
        after_insert_called = False

        def before_hook(cls, data, event=None, **kwargs):
            nonlocal before_insert_called
            before_insert_called = True

        def after_hook(cls, data, val=None, event=None, **kwargs):
            nonlocal after_insert_called
            after_insert_called = True

        TestModel.add_hook('before_insert', before_hook)
        TestModel.add_hook('after_insert', after_hook)

        with sqloquent.SqlTransaction(DB_FILEPATH):
            TestModel.insert({'name': 'Alice'})

        assert before_insert_called, 'before_insert should be called'
        assert after_insert_called, 'after_insert should be called'


if __name__ == '__main__':
    unittest.main()
