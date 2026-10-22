"""데이터베이스 연결

- 환경변수 DATABASE_URL이 있으면 Render의 Postgres를 씀
- 없으면 이 폴더의 local.db (SQLite)를 씀. 내 PC에서 시험할 때
"""

import os
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))

# .env 읽기 (내 PC에서만. Render는 환경변수를 직접 넣음)
ENV_FILE = os.path.join(HERE, ".env")
if os.path.isfile(ENV_FILE):
    for line in open(ENV_FILE, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

DATABASE_URL = os.environ.get("DATABASE_URL", "")
LOCAL_DB = os.path.join(HERE, "local.db")
KST = timezone(timedelta(hours=9))


def connect():
    if DATABASE_URL:
        import psycopg
        return psycopg.connect(DATABASE_URL)
    return sqlite3.connect(LOCAL_DB)


def run(conn, sql, params=()):
    """SQL 한 개를 실행하고, 결과가 있으면 dict 목록으로 돌려줌"""
    # SQLite는 ?, Postgres는 %s로 값을 받음
    if DATABASE_URL:
        sql = sql.replace("?", "%s")

    cur = conn.cursor()
    cur.execute(sql, params)

    if cur.description is None:
        return []

    names = []
    for col in cur.description:
        names.append(col[0])

    rows = []
    for values in cur.fetchall():
        rows.append(dict(zip(names, values)))
    return rows


def create_tables(conn):
    with open(os.path.join(HERE, "schema.sql"), encoding="utf-8") as f:
        text = f.read()

    # 그림 칸의 형식 이름만 DB마다 다름
    if DATABASE_URL:
        text = text.replace("{BLOB}", "BYTEA")
    else:
        text = text.replace("{BLOB}", "BLOB")

    for statement in text.split(";"):
        lines = []
        for line in statement.splitlines():
            if not line.strip().startswith("--"):
                lines.append(line)
        sql = "\n".join(lines).strip()
        if sql:
            run(conn, sql)
    conn.commit()


def now_text():
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")


def new_id():
    return uuid.uuid4().hex[:12]
