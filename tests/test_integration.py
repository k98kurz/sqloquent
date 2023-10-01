from context import tools
from decimal import Decimal
from genericpath import isdir, isfile
from integration_vectors import models, models2
from secrets import token_hex
import os
import sqlite3
import unittest


DB_FILEPATH = 'test.db'
MIGRATIONS_PATH = 'tests/integration_vectors/migrations'
MODELS_PATH = 'tests/integration_vectors/models'


class TestIntegration(unittest.TestCase):
    db: sqlite3.Connection = None
    cursor: sqlite3.Cursor = None

    @classmethod
    def setUpClass(cls) -> None:
        """Monkey-patch the file path."""
        models.Account.connection_info = DB_FILEPATH
        models.Correspondence.connection_info = DB_FILEPATH
        models.Entry.connection_info = DB_FILEPATH
        models.Identity.connection_info = DB_FILEPATH
        models.Ledger.connection_info = DB_FILEPATH
        models.Transaction.connection_info = DB_FILEPATH
        models2.User.connection_info = DB_FILEPATH
        models2.Avatar.connection_info = DB_FILEPATH
        models2.Post.connection_info = DB_FILEPATH
        models2.Friendship.connection_info = DB_FILEPATH
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

    def test_integration_e2e(self):
        # generate migrations
        names = ['Account', 'Correspondence', 'Entry', 'Identity', 'Ledger', 'Transaction']
        for name in names:
            src = tools.make_migration_from_model(name, f"{MODELS_PATH}/{name}.py")
            with open(f"{MIGRATIONS_PATH}/{name}_migration.py", 'w') as f:
                f.write(src)

        # run migrations
        tables = ['accounts', 'correspondences', 'identities', 'ledgers', 'entries', 'transactions']
        assert not self.table_exists('migrations')
        assert self.tables_do_not_exist(tables)
        tools.automigrate(MIGRATIONS_PATH, DB_FILEPATH)
        assert self.table_exists('migrations')
        assert self.tables_exist(tables)

        # create Alice
        alice = models.Identity({'name':'Alice', 'seed': token_hex(32)})
        alice.save()
        assert models.Identity.query({'id': alice.data['id']}).count() == 1

        # create Bob
        bob = models.Identity.insert({'name':'Bob', 'seed': token_hex(32)})
        assert models.Identity.query({'id': bob.data['id']}).count() == 1

        # create Alice and Bob Correspondence
        correspondence = models.Correspondence.insert({
            'first_id': bob.data['id'],
            'second_id': alice.data['id'],
            'details': 'the bidirectional limit is $9001',
        })
        alice.correspondences().reload()
        assert len(alice.correspondences) == 1
        alice.correspondents().reload()
        assert len(alice.correspondents) == 1
        assert alice.correspondents[0].data['id'] == bob.data['id']
        assert alice.correspondents[0].id == bob.id
        bob.correspondences().reload()
        assert len(bob.correspondences) == 1
        bob.correspondents().reload()
        assert len(bob.correspondents) == 1
        assert bob.correspondents[0].data['id'] == alice.data['id']
        assert alice.correspondences().query().count() == 1

        assert correspondence.data['id'] in (
            alice.correspondences[0].data['id'],
            bob.correspondences[0].data['id'],
        )

        # create Alice ledger
        aledger = models.Ledger({'name': 'Alice main'})
        aledger.save()
        alice.ledger().secondary = aledger
        alice.ledger().save()
        assert aledger.data['identity_id'] == alice.data['id']
        aledger.owner().reload()
        assert aledger.owner.data['id'] == alice.data['id']
        assert aledger.owner.id == alice.id
        assert alice.ledger.data['id'] == aledger.data['id']
        assert alice.ledger.id == aledger.id
        # reload from db
        aledger = models.Ledger.find(aledger.data['id'])
        assert aledger.data['identity_id'] == alice.data['id']
        aledger.owner().reload()
        aledger.owner.data['id'] == alice.id

        # create Bob ledger
        bledger = models.Ledger.insert({
            'name': 'Bob main',
            'identity_id': bob.data['id'],
        })
        bob.ledger().reload()
        assert bledger.data['identity_id'] == bob.data['id']
        bledger.owner().reload()
        bledger.owner.data['id'] == bob.data['id']
        # reload from db
        bledger = models.Ledger.find(bledger.data['id'])
        assert bledger.data['identity_id'] == bob.data['id']
        bledger.owner().reload()
        bledger.owner.data['id'] == bob.data['id']

        # create Alice accounts
        anostro = models.Account.insert({
            'name': 'Nostro with Bob',
            'ledger_id': aledger.data['id'],
            'type': models.AccountType.ASSET,
        })
        avostro = models.Account.insert({
            'name': 'Vostro for Bob',
            'ledger_id': aledger.data['id'],
            'type': models.AccountType.LIABILITY,
        })
        astartingcapital = models.Account.insert({
            'name': 'Alice Starting Capital',
            'ledger_id': aledger.data['id'],
            'type': models.AccountType.ASSET,
        })
        aequity = models.Account.insert({
            'name': 'Alice Equity',
            'ledger_id': aledger.data['id'],
            'type': models.AccountType.EQUITY,
        })
        assert len(aledger.accounts) == 0
        aledger.accounts().reload()
        assert len(aledger.accounts) == 4
        assert hasattr(aledger.accounts[0], 'data') and type(aledger.accounts[0].data) is dict
        assert hasattr(aledger.accounts[0], 'id') and type(aledger.accounts[0].id) is str
        assert len(aledger.accounts().query().get()) == 4
        assert anostro.ledger_id == aledger.id
        anostro.ledger().reload()
        assert anostro.ledger.id == aledger.id
        assert len(models.Account.find(anostro.id).ledger().query().get()) == 1
        assert models.Account.find(anostro.id).ledger().query().first().id == aledger.id

        # create Bob accounts
        bnostro = models.Account.insert({
            'name': 'Nostro with Alice',
            'ledger_id': bledger.data['id'],
            'type': models.AccountType.ASSET,
        })
        bvostro = models.Account.insert({
            'name': 'Vostro for Alice',
            'ledger_id': bledger.data['id'],
            'type': models.AccountType.LIABILITY,
        })
        bequity = models.Account.insert({
            'name': 'Bob Equity',
            'ledger_id': bledger.data['id'],
            'type': models.AccountType.EQUITY,
        })
        bstartingcapital = models.Account.insert({
            'name': 'Bob Starting Capital',
            'ledger_id': bledger.data['id'],
            'type': models.AccountType.ASSET,
        })
        assert len(bledger.accounts) == 0
        bledger.accounts().reload()
        assert len(bledger.accounts) == 4

        # create starting capital asset for Alice
        nonce = token_hex(4)
        entries = [
            models.Entry.insert({
                'account_id': astartingcapital.data['id'],
                'nonce': nonce,
                'type': models.EntryType.DEBIT,
                'amount': Decimal('420.69'),
            }),
            models.Entry.insert({
                'account_id': aequity.data['id'],
                'nonce': nonce,
                'type': models.EntryType.CREDIT,
                'amount': Decimal('420.69'),
            }),
        ]
        assert len(aledger.transactions()) == 0
        txn = models.Transaction.insert({
            'ledger_ids': aledger.data['id'],
            'entry_ids': ','.join([e.data['id'] for e in entries]),
        })
        assert len(aledger.transactions()) == 1
        assert set([e.data['id'] for e in txn.entries()]) == set([e.data['id'] for e in entries])
        assert entries[0].transaction().data['id'] == txn.data['id']

        # create starting capital asset for Bob
        nonce = token_hex(4)
        entries = [
            models.Entry.insert({
                'account_id': bstartingcapital.data['id'],
                'nonce': nonce,
                'type': models.EntryType.DEBIT,
                'amount': Decimal('420.69'),
            }),
            models.Entry.insert({
                'account_id': bequity.data['id'],
                'nonce': nonce,
                'type': models.EntryType.CREDIT,
                'amount': Decimal('420.69'),
            }),
        ]
        assert len(bledger.transactions()) == 0
        models.Transaction.insert({
            'ledger_ids': bledger.data['id'],
            'entry_ids': ','.join([e.data['id'] for e in entries]),
        })
        assert len(bledger.transactions()) == 1

        # create Transaction sending 69 from Alice to Bob
        nonce = token_hex(4)
        entries = [
            models.Entry.insert({
                'account_id': avostro.data['id'],
                'nonce': nonce,
                'type': models.EntryType.CREDIT,
                'amount': Decimal(69),
            }),
            models.Entry.insert({
                'account_id': aequity.data['id'],
                'nonce': nonce,
                'type': models.EntryType.DEBIT,
                'amount': Decimal(69),
            }),
            models.Entry.insert({
                'account_id': bnostro.data['id'],
                'nonce': nonce,
                'type': models.EntryType.DEBIT,
                'amount': Decimal(69),
            }),
            models.Entry.insert({
                'account_id': bequity.data['id'],
                'nonce': nonce,
                'type': models.EntryType.CREDIT,
                'amount': Decimal(69),
            }),
        ]
        assert len(aledger.transactions(True)) == 1
        assert len(bledger.transactions(True)) == 1
        txn = models.Transaction.insert({
            'ledger_ids': f"{aledger.data['id']},{bledger.data['id']}",
            'entry_ids': ','.join([e.data['id'] for e in entries]),
        })
        assert len(aledger.transactions(True)) == 2
        assert len(bledger.transactions(True)) == 2
        assert len(txn.ledgers(True)) == 2
        assert len(txn.entries(True)) == 4

    def test_integration_e2e_models2(self):
        # generate migrations
        names = ['User', 'Avatar', 'Post', 'Friendship']
        for name in names:
            src = tools.make_migration_from_model(name, f"{MODELS_PATH}2.py")
            with open(f"{MIGRATIONS_PATH}/{name}_migration.py", 'w') as f:
                f.write(src)

        # run migrations
        tables = ['users', 'avatars', 'posts', 'friendships']
        assert not self.table_exists('migrations')
        assert self.tables_do_not_exist(tables)
        tools.automigrate(MIGRATIONS_PATH, DB_FILEPATH)
        assert self.table_exists('migrations')
        assert self.tables_exist(tables)

        # add users
        alice: models2.User = models2.User.insert({"name": "Alice"})
        bob: models2.User = models2.User.insert({"name": "Bob"})

        # add avatars
        alice.avatar().secondary = models2.Avatar.insert({
            "url": "http://www.perseus.tufts.edu/img/newbanner.png",
        })
        alice.avatar().save()
        bob.avatar = models2.Avatar.insert({
            "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/90" +
            "/Walrus_(Odobenus_rosmarus)_on_Svalbard.jpg/1200px-Walrus_(Odobe" +
            "nus_rosmarus)_on_Svalbard.jpg",
        })
        bob.avatar().save()

        # add a friendship
        bob.friends = [alice]
        bob.friends().save()
        bob.friendships().reload()
        alice.friendships().reload()
        alice.friends().reload()
        assert len(bob.friendships) == 1
        assert len(alice.friendships) == 1
        assert alice.friends[0].id == bob.id

        # add posts
        assert alice.posts().query().count() == 0
        alice.posts = [
            models2.Post.insert({"content": "hello world"}),
            models2.Post.insert({"content": "satan is a lawyer"}),
        ]
        alice.posts().save()
        assert alice.posts().query().count() == 2
        assert bob.posts().query().count() == 0
        bob.posts = [models2.Post.insert({"content": "yellow submarine"})]
        bob.posts().save()
        assert bob.posts().query().count() == 1

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
