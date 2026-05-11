import os, psycopg2, psycopg2.extras
from decimal import Decimal
from datetime import datetime

DB_URL = os.getenv("DATABASE_URL")

_cache: dict = {}


def get_conn():
    return psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)


def serialize_rows(rows: list) -> list:
    result = []
    for row in rows:
        clean = {}
        for k, v in row.items():
            if isinstance(v, Decimal):  clean[k] = float(v)
            elif isinstance(v, datetime): clean[k] = v.isoformat()
            else:                        clean[k] = v
        result.append(clean)
    return result


def cached_query(key: str, sql: str) -> list:
    if key not in _cache:
        conn = get_conn()
        cur  = conn.cursor()
        cur.execute(sql)
        _cache[key] = serialize_rows(cur.fetchall())
        cur.close(); conn.close()
    return _cache[key]
