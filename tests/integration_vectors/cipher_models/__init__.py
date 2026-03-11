from __future__ import annotations
from .Correspondence import Correspondence
from .Identity import Identity
from .Ledger import Ledger
from .Account import Account
from .AccountType import AccountType
from .Entry import Entry
from .EntryType import EntryType
from .Transaction import Transaction
from sqloquent import belongs_to, has_many, has_one, belongs_to_many, contains, within


# set up relations
Identity.ledger = has_one(Identity, Ledger)
Ledger.owner = belongs_to(Ledger, Identity)

Identity.correspondences = has_many(Identity, Correspondence, 'first_id')
Identity.correspondents = belongs_to_many(
    Identity,
    Identity,
    Correspondence,
    'first_id',
    'second_id',
)

Correspondence.first = belongs_to(Correspondence, Identity, 'first_id')
Correspondence.second = belongs_to(Correspondence, Identity, 'second_id')

Ledger.accounts = has_many(Ledger, Account)
Account.ledger = belongs_to(Account, Ledger)

Account.entries = has_many(Account, Entry)
Entry.account = belongs_to(Entry, Account)

Entry.transactions = within(Entry, Transaction, 'entry_ids')
Transaction.entries = contains(Transaction, Entry, 'entry_ids')

Ledger.transactions = within(Ledger, Transaction, 'ledger_ids')
Transaction.ledgers = contains(Transaction, Ledger, 'ledger_ids')
