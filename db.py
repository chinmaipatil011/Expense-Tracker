import os, sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

DEFAULT_DB=os.getenv("DB_PATH","expenses.db")
def db_path():
    return os.getenv("DB_PATH",DEFAULT_DB)

@contextmanager
def connection():
    conn=sqlite3.connect(db_path(), timeout=10)
    conn.row_factory=sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with connection() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL CHECK(amount > 0),
            category TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )""")

def insert_expense(amount,category,note=""):
    now=datetime.now(timezone.utc).isoformat()
    with connection() as conn:
        cur=conn.execute("INSERT INTO expenses(amount,category,note,created_at) VALUES(?,?,?,?)",
                         (amount,category.strip(),note.strip(),now))
        return {"id":cur.lastrowid,"amount":float(amount),"category":category.strip(),"note":note.strip(),"created_at":now}

def summarize(days):
    cutoff=(datetime.now(timezone.utc)-timedelta(days=days)).isoformat()
    with connection() as conn:
        rows=conn.execute("""SELECT category, ROUND(SUM(amount),2) AS total
                             FROM expenses WHERE created_at >= ? GROUP BY category ORDER BY category""",
                          (cutoff,)).fetchall()
    return {row["category"]:float(row["total"]) for row in rows}
