from sqloquent import HashedSqliteModel


class Transaction(HashedSqliteModel):
    file_path: str = 'temp.db'
    table: str = 'transactions'
    id_field: str = 'id'
    fields: tuple[str] = ('id', 'entry_ids', 'ledger_ids')
