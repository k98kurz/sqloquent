from asyncio import run
from context import async_classes, errors
import aiosqlite
import asyncio
import unittest
import os


DB_FILEPATH = 'test_transactions.db'
DB_FILEPATH2 = 'test_transactions2.db'


class TestModel(async_classes.AsyncSqlModel):
    table: str = 'test'
    id_column: str = 'id'
    columns: tuple[str, ...] = ('id', 'name')
    id: str
    name: str
    connection_info: str = DB_FILEPATH


class TestModel2(async_classes.AsyncSqlModel):
    table: str = 'test2'
    id_column: str = 'id'
    columns: tuple[str, ...] = ('id', 'name')
    id: str
    name: str
    connection_info: str = DB_FILEPATH2


class TestAsyncSqlTransaction(unittest.TestCase):
    """Test AsyncSqlTransaction class functionality."""
    db1: aiosqlite.Connection = None
    db2: aiosqlite.Connection = None
    cursor1: aiosqlite.Cursor = None
    cursor2: aiosqlite.Cursor = None

    def setUp(self) -> None:
        """Set up the test databases."""
        # Delete old databases to ensure clean slate
        for db in [DB_FILEPATH, DB_FILEPATH2]:
            try:
                if os.path.isfile(db):
                    os.remove(db)
            except:
                ...

        # Setup connections
        async def setup():
            c1 = await aiosqlite.connect(DB_FILEPATH)
            cursor1 = await c1.cursor()
            await cursor1.execute('create table test (id text, name text)')
            self.db1 = c1
            self.cursor1 = cursor1

            c2 = await aiosqlite.connect(DB_FILEPATH2)
            cursor2 = await c2.cursor()
            await cursor2.execute('create table test2 (id text, name text)')
            self.db2 = c2
            self.cursor2 = cursor2

        run(setup())

        return super().setUp()

    def tearDown(self) -> None:
        """Close cursor and delete test databases."""
        for cursor, db in [
                (self.cursor1, self.db1),
                (self.cursor2, self.db2),
            ]:
            if cursor:
                run(cursor.close())
            if db:
                run(db.close())

        for db_file in [DB_FILEPATH, DB_FILEPATH2]:
            try:
                os.remove(db_file)
            except:
                ...

    # Basic AsyncSqlTransaction tests
    def test_basic_asynctransaction_success(self):
        """Test basic AsyncSqlTransaction success with multiple inserts."""
        async def test():
            async with async_classes.AsyncSqlTransaction(DB_FILEPATH):
                await TestModel.insert({'name': 'Alice'})
                await TestModel.insert({'name': 'Bob'})

            results = await TestModel.query().get()
            assert len(results) == 2, len(results)
            assert results[0].name == 'Alice', results[0].name
            assert results[1].name == 'Bob', results[1].name

        run(test())

    def test_transaction_rollback_on_exception(self):
        """Test that transaction rolls back on exception."""
        async def test():
            with self.assertRaises(ValueError):
                async with async_classes.AsyncSqlTransaction(DB_FILEPATH):
                    await TestModel.insert({'name': 'Alice'})
                    raise ValueError('test error')

            results = await TestModel.query().get()
            assert len(results) == 0, len(results)

        run(test())

    # Manual commit/rollback tests
    def test_manual_commit(self):
        """Test manual commit within transaction."""
        async def test():
            with self.assertRaises(ValueError):
                async with async_classes.AsyncSqlTransaction(DB_FILEPATH) as tx:
                    await TestModel.insert({'name': 'Alice'})
                    assert not tx.is_committed, tx.is_committed
                    await tx.commit()
                    assert tx.is_committed, tx.is_committed
                    await TestModel.insert({'name': 'Bob'})
                    raise ValueError('test exception')

            results = await TestModel.query().get()
            assert len(results) == 1, len(results)
            assert results[0].name == 'Alice', results[0].name

        run(test())

    def test_manual_rollback(self):
        """Test manual rollback within transaction."""
        async def test():
            async with async_classes.AsyncSqlTransaction(DB_FILEPATH) as tx:
                await TestModel.insert({'name': 'Alice'})
                assert not tx.is_rolled_back
                await tx.rollback()
                assert tx.is_rolled_back
                await TestModel.insert({'name': 'Bob'})

            results = await TestModel.query().get()
            assert len(results) == 1, len(results)
            assert results[0].name == 'Bob', results[0].name

        run(test())

    def test_manual_commit_then_rollback(self):
        """Test manual commit followed by manual rollback."""
        async def test():
            async with async_classes.AsyncSqlTransaction(DB_FILEPATH) as tx:
                await TestModel.insert({'name': 'Alice'})
                await tx.commit()
                await TestModel.insert({'name': 'Bob'})
                await tx.rollback()

            results = await TestModel.query().get()
            assert len(results) == 1, len(results)
            assert results[0].name == 'Alice', results[0].name

        run(test())

    # Nested transaction tests
    def test_nested_transaction_error(self):
        """Test that nested transactions on same connection raise error."""
        async def test():
            with self.assertRaises(RuntimeError) as cm:
                async with async_classes.AsyncSqlTransaction(DB_FILEPATH):
                    async with async_classes.AsyncSqlTransaction(DB_FILEPATH):
                        pass
            assert 'Nested transactions' in str(cm.exception), str(cm.exception)

        run(test())

    def test_different_connections(self):
        """Test transaction on one connection while other auto-commits."""
        async def test():
            async with async_classes.AsyncSqlTransaction(DB_FILEPATH):
                await TestModel.insert({'name': 'Alice'})
                await TestModel2.insert({'name': 'Bob'})

            results1 = await TestModel.query().get()
            results2 = await TestModel2.query().get()
            assert len(results1) == 1, len(results1)
            assert len(results2) == 1, len(results2)

        run(test())

    # AsyncMultiDBTransaction tests
    def test_asyncmultidbtransaction(self):
        """Test AsyncMultiDBTransaction with two connections."""
        async def test():
            async with async_classes.AsyncMultiDBTransaction(DB_FILEPATH, DB_FILEPATH2):
                await TestModel.insert({'name': 'Alice'})
                await TestModel2.insert({'name': 'Bob'})

            results1 = await TestModel.query().get()
            results2 = await TestModel2.query().get()
            assert len(results1) == 1, len(results1)
            assert len(results2) == 1, len(results2)

        run(test())

    def test_asyncmultidbtransaction_rollback(self):
        """Test AsyncMultiDBTransaction rollback on exception."""
        async def test():
            # test preconditions
            results1 = await TestModel.query().get()
            results2 = await TestModel2.query().get()
            assert len(results1) == 0, ('precondition', results1)
            assert len(results2) == 0, ('precondition', results2)

            with self.assertRaises(ValueError):
                async with async_classes.AsyncMultiDBTransaction(
                        DB_FILEPATH, DB_FILEPATH2
                    ):
                    await TestModel.insert({'name': 'Alice'})
                    await TestModel2.insert({'name': 'Bob'})
                    raise ValueError('test error')

            results1 = await TestModel.query().get()
            results2 = await TestModel2.query().get()
            assert len(results1) == 0, results1
            assert len(results2) == 0, results2

        run(test())

    # atransactional decorator tests
    def test_atransactional_decorator(self):
        """Test @atransactional decorator."""
        async def insert_records():
            async def inner():
                @async_classes.atransactional(DB_FILEPATH)
                async def do_insert():
                    await TestModel.insert({'name': 'Alice'})
                    await TestModel.insert({'name': 'Bob'})
                await do_insert()

            await inner()

            results = await TestModel.query().get()
            assert len(results) == 2, len(results)

        run(insert_records())

    # Async task isolation tests
    def test_async_task_isolation(self):
        """Transactions in separate async tasks don't interfere."""
        async def test():
            async def task1():
                async with async_classes.AsyncSqlTransaction(DB_FILEPATH):
                    await TestModel.insert({'name': 'Alice'})

            async def task2():
                async with async_classes.AsyncSqlTransaction(DB_FILEPATH):
                    await TestModel.insert({'name': 'Bob'})

            await asyncio.gather(task1(), task2())

            results = await TestModel.query().get()
            assert len(results) == 2, len(results)

        run(test())

    # Concurrent multi-DB operations tests
    def test_concurrent_multidb(self):
        """Parallel operations across multiple databases."""
        async def test():
            async with async_classes.AsyncMultiDBTransaction(DB_FILEPATH, DB_FILEPATH2):
                await asyncio.gather(
                    TestModel.insert({'name': 'Alice'}),
                    TestModel2.insert({'name': 'Bob'})
                )

            results1 = await TestModel.query().get()
            results2 = await TestModel2.query().get()
            assert len(results1) == 1, len(results1)
            assert len(results2) == 1, len(results2)

        run(test())

    # All model operations tests
    def test_all_model_operations(self):
        """Test insert, update, delete, save in transaction."""
        async def test():
            async with async_classes.AsyncSqlTransaction(DB_FILEPATH):
                m1 = await TestModel.insert({'name': 'Alice'})
                await m1.update({'name': 'Alice Updated'})
                m2 = TestModel({'name': 'Bob'})
                await m2.save()
                await m2.delete()

            results = await TestModel.query().get()
            assert len(results) == 1, len(results)
            assert results[0].name == 'Alice Updated', results[0].name

        run(test())

    # Event hooks tests
    def test_event_hooks(self):
        """Test that event hooks still fire within transactions."""
        async def test():
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

            async with async_classes.AsyncSqlTransaction(DB_FILEPATH):
                await TestModel.insert({'name': 'Alice'})

            assert before_insert_called, 'before_insert should be called'
            assert after_insert_called, 'after_insert should be called'

        run(test())


if __name__ == '__main__':
    unittest.main()
