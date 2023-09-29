from sqloquent import HashedSqliteModel


class Transaction(HashedSqliteModel):
    file_path: str = 'temp.db'
    table: str = 'transactions'
    id_column: str = 'id'
    columns: tuple[str] = ('id', 'entry_ids', 'ledger_ids')
    id: str
    entry_ids: str
    ledger_ids: str
