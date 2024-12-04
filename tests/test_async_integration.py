from asyncio import run
from context import tools
from decimal import Decimal
from genericpath import isdir, isfile
from integration_vectors import asyncmodels, asyncmodels2
from secrets import token_hex
import os
import sqlite3
import unittest


DB_FILEPATH = 'test.db'
MIGRATIONS_PATH = 'tests/integration_vectors/migrations'
MODELS_PATH = 'tests/integration_vectors/asyncmodels'


class TestAsyncIntegration(unittest.TestCase):
    db: sqlite3.Connection = None
    cursor: sqlite3.Cursor = None

    @classmethod
    def setUpClass(cls) -> None:
        """Monkey-patch the file path."""
        asyncmodels.Account.connection_info = DB_FILEPATH
        asyncmodels.Correspondence.connection_info = DB_FILEPATH
        asyncmodels.Entry.connection_info = DB_FILEPATH
        asyncmodels.Identity.connection_info = DB_FILEPATH
        asyncmodels.Ledger.connection_info = DB_FILEPATH
        asyncmodels.Transaction.connection_info = DB_FILEPATH
        asyncmodels2.User.connection_info = DB_FILEPATH
        asyncmodels2.Avatar.connection_info = DB_FILEPATH
        asyncmodels2.Post.connection_info = DB_FILEPATH
        asyncmodels2.Friendship.connection_info = DB_FILEPATH
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
        q = "select name from sqlite_master where type='table'"
        self.cursor.execute(q)
        results = self.cursor.fetchall()
        for result in results:
            q = f"drop table if exists {result[0]};"
            try:
                self.cursor.execute(q)
            except BaseException as e:
                print(e)
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

    def test_integration_e2e(self):
        # generate migrations
        names = ['Account', 'Correspondence', 'Entry', 'Identity', 'Ledger', 'Transaction']
        for name in names:
            src = tools.make_migration_from_model_path(name, f"{MODELS_PATH}/{name}.py")
            if name == 'Account':
                assert "t.boolean('is_active').default(True)" in src, src
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
        alice = asyncmodels.Identity({'name':'Alice', 'seed': token_hex(32)})
        run(alice.save())
        assert run(asyncmodels.Identity.query({'id': alice.data['id']}).count()) == 1

        # create Bob
        bob = run(asyncmodels.Identity.insert({'name':'Bob', 'seed': token_hex(32)}))
        assert run(asyncmodels.Identity.query({'id': bob.data['id']}).count()) == 1

        # create Alice and Bob Correspondence
        correspondence = run(asyncmodels.Correspondence.insert({
            'first_id': bob.data['id'],
            'second_id': alice.data['id'],
            'details': 'the bidirectional limit is $9001',
        }))
        run(alice.correspondences().reload())
        assert len(alice.correspondences) == 1
        run(alice.correspondents().reload())
        assert len(alice.correspondents) == 1
        assert alice.correspondents[0].data['id'] == bob.data['id']
        assert alice.correspondents[0].id == bob.id
        run(bob.correspondences().reload())
        assert len(bob.correspondences) == 1
        run(bob.correspondents().reload())
        assert len(bob.correspondents) == 1
        assert bob.correspondents[0].data['id'] == alice.data['id']
        assert run(alice.correspondences().query().count()) == 1

        assert correspondence.data['id'] in (
            alice.correspondences[0].data['id'],
            bob.correspondences[0].data['id'],
        )

        # create Alice ledger
        aledger = asyncmodels.Ledger({'name': 'Alice main'})
        run(aledger.save())
        alice.ledger().secondary = aledger
        run(alice.ledger().save())
        assert aledger.data['identity_id'] == alice.data['id']
        run(aledger.owner().reload())
        assert aledger.owner.data['id'] == alice.data['id']
        assert aledger.owner.id == alice.id
        assert alice.ledger.data['id'] == aledger.data['id']
        assert alice.ledger.id == aledger.id
        # reload from db
        aledger = run(asyncmodels.Ledger.find(aledger.data['id']))
        assert aledger.data['identity_id'] == alice.data['id']
        run(aledger.owner().reload())
        aledger.owner.data['id'] == alice.id

        # create Bob ledger
        bledger = run(asyncmodels.Ledger.insert({
            'name': 'Bob main',
            'identity_id': bob.data['id'],
        }))
        run(bob.ledger().reload())
        assert bledger.data['identity_id'] == bob.data['id']
        run(bledger.owner().reload())
        bledger.owner.data['id'] == bob.data['id']
        # reload from db
        bledger = run(asyncmodels.Ledger.find(bledger.data['id']))
        assert bledger.data['identity_id'] == bob.data['id']
        run(bledger.owner().reload())
        bledger.owner.data['id'] == bob.data['id']

        # create Alice accounts
        anostro = run(asyncmodels.Account.insert({
            'name': 'Nostro with Bob',
            'ledger_id': aledger.data['id'],
            'type': asyncmodels.AccountType.ASSET,
        }))
        avostro = run(asyncmodels.Account.insert({
            'name': 'Vostro for Bob',
            'ledger_id': aledger.data['id'],
            'type': asyncmodels.AccountType.LIABILITY,
        }))
        astartingcapital = run(asyncmodels.Account.insert({
            'name': 'Alice Starting Capital',
            'ledger_id': aledger.data['id'],
            'type': asyncmodels.AccountType.ASSET,
        }))
        aequity = run(asyncmodels.Account.insert({
            'name': 'Alice Equity',
            'ledger_id': aledger.data['id'],
            'type': asyncmodels.AccountType.EQUITY,
        }))
        assert len(aledger.accounts) == 4
        assert hasattr(aledger.accounts[0], 'data') and type(aledger.accounts[0].data) is dict
        assert hasattr(aledger.accounts[0], 'id') and type(aledger.accounts[0].id) is str
        assert len(run(aledger.accounts().query().get())) == 4
        assert anostro.ledger_id == aledger.id
        run(anostro.ledger().reload())
        assert anostro.ledger.id == aledger.id
        assert len(run(run(asyncmodels.Account.find(anostro.id)).ledger().query().get())) == 1
        assert run(run(asyncmodels.Account.find(anostro.id)).ledger().query().first()).id == aledger.id

        assert anostro.is_active is True, anostro.data
        anostro = run(asyncmodels.Account.find(anostro.id))
        assert anostro.is_active is True, anostro.data

        # test that a join properly casts boolean column
        query = asyncmodels.Account.query().join(asyncmodels.Ledger, ['ledger_id', 'id'])
        val = run(query.get())[0]
        acct = val.data['accounts']
        assert type(acct['is_active']) is bool, acct['is_active']

        # create Bob accounts
        bnostro = run(asyncmodels.Account.insert({
            'name': 'Nostro with Alice',
            'ledger_id': bledger.data['id'],
            'type': asyncmodels.AccountType.ASSET,
        }))
        bvostro = run(asyncmodels.Account.insert({
            'name': 'Vostro for Alice',
            'ledger_id': bledger.data['id'],
            'type': asyncmodels.AccountType.LIABILITY,
        }))
        bequity = run(asyncmodels.Account.insert({
            'name': 'Bob Equity',
            'ledger_id': bledger.data['id'],
            'type': asyncmodels.AccountType.EQUITY,
        }))
        bstartingcapital = run(asyncmodels.Account.insert({
            'name': 'Bob Starting Capital',
            'ledger_id': bledger.data['id'],
            'type': asyncmodels.AccountType.ASSET,
        }))
        assert len(bledger.accounts) == 4

        # create starting capital asset for Alice
        nonce = token_hex(4)
        entries = [
            run(asyncmodels.Entry.insert({
                'account_id': astartingcapital.data['id'],
                'nonce': nonce,
                'type': asyncmodels.EntryType.DEBIT,
                'amount': Decimal('420.69'),
            })),
            run(asyncmodels.Entry.insert({
                'account_id': aequity.data['id'],
                'nonce': nonce,
                'type': asyncmodels.EntryType.CREDIT,
                'amount': Decimal('420.69'),
            })),
        ]
        assert len(aledger.transactions) == 0
        txn = run(asyncmodels.Transaction.insert({
            'ledger_ids': aledger.data['id'],
            'entry_ids': ','.join([e.data['id'] for e in entries]),
        }))
        run(txn.entries().reload())
        run(aledger.transactions().reload())
        assert len(aledger.transactions) == 1
        assert set([e.data['id'] for e in txn.entries]) == set([e.data['id'] for e in entries])
        run(entries[0].transactions().reload())
        assert len(entries[0].transactions) == 1
        assert entries[0].transactions[0].data['id'] == txn.data['id']

        # create starting capital asset for Bob
        nonce = token_hex(4)
        entries = [
            run(asyncmodels.Entry.insert({
                'account_id': bstartingcapital.data['id'],
                'nonce': nonce,
                'type': asyncmodels.EntryType.DEBIT,
                'amount': Decimal('420.69'),
            })),
            run(asyncmodels.Entry.insert({
                'account_id': bequity.data['id'],
                'nonce': nonce,
                'type': asyncmodels.EntryType.CREDIT,
                'amount': Decimal('420.69'),
            })),
        ]
        run(bledger.transactions().reload())
        assert len(bledger.transactions) == 0
        run(asyncmodels.Transaction.insert({
            'ledger_ids': bledger.data['id'],
            'entry_ids': ','.join([e.data['id'] for e in entries]),
        }))
        run(bledger.transactions().reload())
        assert len(bledger.transactions) == 1

        # create Transaction sending 69 from Alice to Bob
        nonce = token_hex(4)
        entries = [
            run(asyncmodels.Entry.insert({
                'account_id': avostro.data['id'],
                'nonce': nonce,
                'type': asyncmodels.EntryType.CREDIT,
                'amount': Decimal(69),
            })),
            run(asyncmodels.Entry.insert({
                'account_id': aequity.data['id'],
                'nonce': nonce,
                'type': asyncmodels.EntryType.DEBIT,
                'amount': Decimal(69),
            })),
            run(asyncmodels.Entry.insert({
                'account_id': bnostro.data['id'],
                'nonce': nonce,
                'type': asyncmodels.EntryType.DEBIT,
                'amount': Decimal(69),
            })),
            run(asyncmodels.Entry.insert({
                'account_id': bequity.data['id'],
                'nonce': nonce,
                'type': asyncmodels.EntryType.CREDIT,
                'amount': Decimal(69),
            })),
        ]
        assert len(aledger.transactions) == 1
        assert len(bledger.transactions) == 1
        txn = run(asyncmodels.Transaction.insert({
            'ledger_ids': f"{aledger.data['id']},{bledger.data['id']}",
            'entry_ids': ','.join([e.data['id'] for e in entries]),
        }))
        run(aledger.transactions().reload())
        run(bledger.transactions().reload())
        assert len(aledger.transactions) == 2
        assert len(bledger.transactions) == 2
        run(txn.ledgers().reload())
        run(txn.entries().reload())
        assert len(txn.ledgers) == 2
        assert len(txn.entries) == 4

        # test accessing BelongsTo through a BelongsTo: case 1
        assert bvostro.ledger.owner.id

        # test accessing BelongsTo through a BelongsTo: case 2
        bvostro = run(asyncmodels.Account.find(bvostro.id))
        run(bvostro.ledger().reload())
        run(bvostro.ledger.owner().reload())
        assert bvostro.ledger.owner.id

        # test accessing HasMany through a HasOne
        alice: asyncmodels.Identity = run(asyncmodels.Identity.find(alice.id))
        assert alice.ledger.id
        assert len(alice.ledger.accounts), alice.ledger.accounts

        # test accessing HasMany through a HasMany
        run(aledger.accounts().reload())
        acct = [a for a in aledger.accounts if a.name == 'Alice Equity'][0]
        assert len(acct.entries)

        # test accessing BelongsTo through a Contains
        txn: asyncmodels.Transaction = run(asyncmodels.Transaction.query().first())
        assert len(txn.entries)
        entry: asyncmodels.Entry = txn.entries[0]
        assert entry.account

        # test accessing Within through a HasMany
        run(bequity.entries().reload())
        entry: asyncmodels.Entry = bequity.entries[0]
        assert len(entry.transactions) == 1

    def test_integration_e2e_models2(self):
        # generate migrations
        names = ['User', 'Avatar', 'Post', 'Friendship']
        for name in names:
            src = tools.make_migration_from_model_path(name, f"{MODELS_PATH}2.py")
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
        alice: asyncmodels2.User = run(asyncmodels2.User.insert({"name": "Alice"}))
        bob: asyncmodels2.User = run(asyncmodels2.User.insert({"name": "Bob"}))

        # add avatars
        alice.avatar().secondary = run(asyncmodels2.Avatar.insert({
            "url": "http://www.perseus.tufts.edu/img/newbanner.png",
        }))
        run(alice.avatar().save())
        bob.avatar = run(asyncmodels2.Avatar.insert({
            "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/90" +
            "/Walrus_(Odobenus_rosmarus)_on_Svalbard.jpg/1200px-Walrus_(Odobe" +
            "nus_rosmarus)_on_Svalbard.jpg",
        }))
        run(bob.avatar().save())

        # add a friendship
        bob.friends = [alice]
        run(bob.friends().save())
        run(bob.friendships().reload())
        run(alice.friendships().reload())
        run(alice.friends().reload())
        assert len(bob.friendships) == 1
        assert len(alice.friendships) == 1
        assert alice.friends[0].id == bob.id

        # add posts
        assert run(alice.posts().query().count()) == 0
        alice.posts = [
            run(asyncmodels2.Post.insert({"content": "hello world"})),
            run(asyncmodels2.Post.insert({"content": "satan is a lawyer"})),
        ]
        run(alice.posts().save())
        assert run(alice.posts().query().count()) == 2
        assert run(bob.posts().query().count()) == 0
        bob.posts = [run(asyncmodels2.Post.insert({"content": "yellow submarine"}))]
        run(bob.posts().save())
        assert run(bob.posts().query().count()) == 1

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
