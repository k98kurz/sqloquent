from sqloquent import HashedSqliteModel


class Ledger(HashedSqliteModel):
    file_path: str = 'temp.db'
    table: str = 'ledgers'
    id_column: str = 'id'
    columns: tuple[str] = ('id', 'name', 'identity_id')
    id: str
    name: str
    identity_id: str
