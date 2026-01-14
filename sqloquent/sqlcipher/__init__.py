"""
    Classes for use with encrypted SQLite databases via SQLCipher. 
    Requires an additional dependency, which should be installed with 
    `pip install sqloquent[sqlcipher]`.
"""

from .classes import (
    SqlcipherContext,
    SqlcipherQueryBuilder,
    SqlcipherModel,
    HashedSqlcipherModel,
)

__all__ = [
    'SqlcipherContext',
    'SqlcipherQueryBuilder',
    'SqlcipherModel',
    'HashedSqlcipherModel',
]
