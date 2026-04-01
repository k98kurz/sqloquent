from asyncio import run
from context import tools
from integration_vectors import models, asyncmodels
import os
import sqlite3
import unittest


DB_FILEPATH = 'test.db'
MIGRATIONS_PATH = 'tests/integration_vectors/migrations'
MODELS_PATH = 'tests/integration_vectors/models'
isdir = lambda x: os.path.isdir(x)
isfile = lambda x: os.path.isfile(x)


class TestRegressions(unittest.TestCase):
    db: sqlite3.Connection = None
    cursor: sqlite3.Cursor = None

    @classmethod
    def setUpClass(cls) -> None:
        """Monkey-patch the file path."""
        models.Account.connection_info = DB_FILEPATH
        models.Identity.connection_info = DB_FILEPATH
        models.Ledger.connection_info = DB_FILEPATH
        models.Entry.connection_info = DB_FILEPATH
        asyncmodels.Account.connection_info = DB_FILEPATH
        asyncmodels.Identity.connection_info = DB_FILEPATH
        asyncmodels.Ledger.connection_info = DB_FILEPATH
        asyncmodels.Entry.connection_info = DB_FILEPATH
        return super().setUpClass()

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

        # generate migrations
        names = [
            'Account', 'Entry', 'Identity', 'Ledger',
        ]
        for name in names:
            src = tools.make_migration_from_model_path(
                name, f"{MODELS_PATH}/{name}.py"
            )
            if name == 'Account':
                assert "t.boolean('is_active').default(True)" in src, src
            with open(f"{MIGRATIONS_PATH}/{name}_migration.py", 'w') as f:
                f.write(src)

        # run migrations
        tools.automigrate(MIGRATIONS_PATH, DB_FILEPATH)
        return super().setUp()

    def tearDown(self):
        """Close cursor and delete test database."""
        self.cursor.close()
        self.db.close()
        try:
            os.remove(DB_FILEPATH)
        except:
            ...
        for file in os.listdir(MIGRATIONS_PATH):
            if 'migration' in file and file[-3:] == '.py':
                os.remove(f"{MIGRATIONS_PATH}/{file}")
        return super().tearDown()

    def test_BelongsToWrapped_HashedModel_save(self):
        acct = models.Account.insert({'name': 'test'})
        acct_id = acct.id
        entry = models.Entry.insert({
            'account_id': acct.id,
            'nonce': '123',
            'type': 'c',
            'amount': 123,
        })
        passes, msg = True, ''
        try:
            entry.account.is_active = False
            entry.account.save() # should not throw TypeError
        except TypeError as e:
            passes = False
            msg = f"should not have thrown TypeError: {e}"
        assert passes, msg
        assert models.Account.find(acct_id) is not None
        assert models.Account.find(acct_id).is_active is False

    def test_BelongsToWrapped_AsyncHashedModel_save(self):
        async def test():
            acct = await asyncmodels.Account.insert({'name': 'test'})
            acct_id = acct.id
            entry = await asyncmodels.Entry.insert({
                'account_id': acct.id,
                'nonce': '123',
                'type': 'c',
                'amount': 123,
            })
            passes, msg = True, ''
            try:
                entry.account.is_active = False
                await entry.account.save() # should not throw TypeError
            except TypeError as e:
                passes = False
                msg = f"should not have thrown TypeError: {e}"
            assert passes, msg
            assert (await asyncmodels.Account.find(acct_id)) is not None
            assert (await asyncmodels.Account.find(acct_id)).is_active is False

        run(test())

    def test_HasOneWrapped_HashedModel_save(self):
        identity = models.Identity.insert({'name':'Mr. Testington Schlongvanovich'})
        ledger = models.Ledger.insert({
            'name': 'Ledger for Tracking Things',
            'identity_id': identity.id,
        })
        ledger_id = ledger.id
        passes, msg = True, ''
        try:
            identity.ledger.note = 'test'
            identity.ledger.save()
        except TypeError as e:
            passes = False
            msg = f"Should not have thrown TypeError: {e}"
        assert passes, msg
        assert models.Ledger.find(ledger_id) is not None
        assert models.Ledger.find(ledger_id).note == 'test'

    def test_HasOneWrapped_AsyncHashedModel_save(self):
        async def test():
            identity = await asyncmodels.Identity.insert({
                'name':'Mr. Testington Schlongvanovich'
            })
            ledger = await asyncmodels.Ledger.insert({
                'name': 'Ledger for Tracking Things',
                'identity_id': identity.id,
            })
            ledger_id = ledger.id
            passes, msg = True, ''
            try:
                identity.ledger.note = 'test'
                await identity.ledger.save()
            except TypeError as e:
                passes = False
                msg = f"Should not have thrown TypeError: {e}"
            assert passes, msg
            assert (await asyncmodels.Ledger.find(ledger_id)) is not None
            assert (await asyncmodels.Ledger.find(ledger_id)).note == 'test'

        run(test())


if __name__ == '__main__':
    unittest.main()
