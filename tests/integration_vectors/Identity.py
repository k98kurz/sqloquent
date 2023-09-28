from sqloquent import HashedSqliteModel


class Identity(HashedSqliteModel):
    file_path: str = 'temp.db'
    table: str = 'identities'
    id_field: str = 'id'
    fields: tuple[str] = ('id', 'name', 'seed')
