import os
import sqlite3

from config import BASE_DIR


def _dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def get_conn():
    conn = sqlite3.connect(os.path.join(BASE_DIR, 'demos.db'))
    conn.row_factory = _dict_factory
    return conn
