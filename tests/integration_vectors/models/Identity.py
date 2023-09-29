from sqloquent import HashedSqliteModel


class Identity(HashedSqliteModel):
    file_path: str = 'temp.db'
    table: str = 'identities'
    id_column: str = 'id'
    columns: tuple[str] = ('id', 'name', 'seed')
    id: str
    name: str
    seed: bytes|None
