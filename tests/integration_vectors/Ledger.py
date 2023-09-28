from sqloquent import HashedSqliteModel


class Ledger(HashedSqliteModel):
    file_path: str = 'temp.db'
    table: str = 'ledgers'
    id_field: str = 'id'
    fields: tuple[str] = ('id', 'name', 'identity_id')
