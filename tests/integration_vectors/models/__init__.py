from __future__ import annotations
from .Correspondence import Correspondence
from .Identity import Identity
from .Ledger import Ledger
from .Account import Account
from .AccountType import AccountType
from .Entry import Entry
from .EntryType import EntryType
from .Transaction import Transaction
from sqloquent import belongs_to, has_many, has_one, belongs_to_many


# set up relations
Identity.ledger = has_one(Identity, Ledger)
Ledger.owner = belongs_to(Ledger, Identity)

Identity.correspondences = has_many(Identity, Correspondence, 'first')
Identity.correspondents = belongs_to_many(
    Identity,
    Identity,
    Correspondence,
    'first',
    'second',
)

Ledger.accounts = has_many(Ledger, Account)
Account.ledger = belongs_to(Account, Ledger)

Account.entries = has_many(Account, Entry)
Entry.account = belongs_to(Entry, Account)


def entry_transaction(self, reload: bool = False) -> Transaction|None:
    if reload or not hasattr(self, '_transaction') or not self._transaction:
        self._transaction = Transaction.query().contains('entry_ids', self.data['id']).first()
    return self._transaction
Entry.transaction = entry_transaction

def transaction_entries(self, reload: bool = False) -> list[Entry]:
    if reload or not hasattr(self, '_entries') or not self._entries:
        entry_ids = self.data['entry_ids'].split(',')
        self._entries = Entry.query().is_in('id', entry_ids).get()
    return self._entries
Transaction.entries = transaction_entries


def ledger_transactions(self, reload: bool = False) -> list[Transaction]:
    if reload or not hasattr(self, '_transactions') or not self._transactions:
        self._transactions = Transaction.query().contains('ledger_ids', self.data['id']).get()
    return self._transactions
Ledger.transactions = ledger_transactions

def transaction_ledgers(self, reload: bool = False) -> list[Ledger]:
    if reload or not hasattr(self, '_ledgers') or not self._ledgers:
        ledger_ids = self.data['ledger_ids'].split(',')
        self._ledgers = Ledger.query().is_in('id', ledger_ids).get()
    return self._ledgers
Transaction.ledgers = transaction_ledgers
