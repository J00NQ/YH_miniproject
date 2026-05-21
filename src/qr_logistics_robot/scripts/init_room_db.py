#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
병실 좌표 DB 초기화 스크립트
실행: python3 init_room_db.py
생성 위치: ../db/hospital_rooms.db
"""

import sqlite3
import os

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../db/hospital_rooms.db'))

# ── 작업 1 완료 후 실제 측정값으로 교체 ──────────────────────────────────────
ROOMS = [
    # (id,    name,    x,       y,      theta)
    ("R001", "1병실",  1.6703,  -11.0,  -1.5708),
    ("R002", "2병실", -0.6141,  -11.0,  -1.5708),
    ("R003", "3병실", -3.0615,  -11.0,  -1.5708),
]
# ─────────────────────────────────────────────────────────────────────────────

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            id    TEXT PRIMARY KEY,
            name  TEXT NOT NULL,
            x     REAL NOT NULL,
            y     REAL NOT NULL,
            theta REAL NOT NULL DEFAULT 0.0
        )
    """)

    cur.executemany(
        "INSERT OR REPLACE INTO rooms (id, name, x, y, theta) VALUES (?, ?, ?, ?, ?)",
        ROOMS
    )

    con.commit()
    print(f"DB 초기화 완료: {DB_PATH}")
    print(f"삽입된 병실 수: {cur.rowcount if cur.rowcount > 0 else len(ROOMS)}")

    for row in cur.execute("SELECT * FROM rooms"):
        print(f"  {row}")

    con.close()

if __name__ == "__main__":
    init_db()
