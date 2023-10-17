from __future__ import annotations
from .Correspondence import Correspondence
from .Identity import Identity
from .Ledger import Ledger
from .Account import Account
from .AccountType import AccountType
from .Entry import Entry
from .EntryType import EntryType
from .Transaction import Transaction
from sqloquent.asyncql import (
    async_belongs_to, async_has_many, async_has_one, async_belongs_to_many
)


# set up relations
Identity.ledger = async_has_one(Identity, Ledger)
Ledger.owner = async_belongs_to(Ledger, Identity)

Identity.correspondences = async_has_many(Identity, Correspondence, 'first_id')
Identity.correspondents = async_belongs_to_many(
    Identity,
    Identity,
    Correspondence,
    'first_id',
    'second_id',
)

Correspondence.first = async_belongs_to(Correspondence, Identity, 'first_id')
Correspondence.second = async_belongs_to(Correspondence, Identity, 'second_id')

Ledger.accounts = async_has_many(Ledger, Account)
Account.ledger = async_belongs_to(Account, Ledger)

Account.entries = async_has_many(Account, Entry)
Entry.account = async_belongs_to(Entry, Account)


async def entry_transaction(self: Entry, reload: bool = False) -> Transaction|None:
    if reload or not hasattr(self, '_transaction') or not self._transaction:
        self._transaction = await Transaction.query().contains('entry_ids', self.data['id']).first()
    return self._transaction
Entry.transaction = entry_transaction

async def transaction_entries(self: Transaction, reload: bool = False) -> list[Entry]:
    if reload or not hasattr(self, '_entries') or not self._entries:
        entry_ids = self.data['entry_ids'].split(',')
        self._entries = await Entry.query().is_in('id', entry_ids).get()
    return self._entries
Transaction.entries = transaction_entries


async def ledger_transactions(self: Ledger, reload: bool = False) -> list[Transaction]:
    if reload or not hasattr(self, '_transactions') or not self._transactions:
        self._transactions = await Transaction.query().contains('ledger_ids', self.data['id']).get()
    return self._transactions
Ledger.transactions = ledger_transactions

async def transaction_ledgers(self: Transaction, reload: bool = False) -> list[Ledger]:
    if reload or not hasattr(self, '_ledgers') or not self._ledgers:
        ledger_ids = self.data['ledger_ids'].split(',')
        self._ledgers = await Ledger.query().is_in('id', ledger_ids).get()
    return self._ledgers
Transaction.ledgers = transaction_ledgers
