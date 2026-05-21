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

ROOMS = [
    # (id,    name,    x,       y,      theta)
    ("R001", "1병실",  1.6703,  -11.0,  0.0),
    ("R002", "2병실", -0.6141,  -11.0,  0.0),
    ("R003", "3병실", -3.0615,  -11.0,  0.0),
]

# 초기 배송 작업 큐 (테스트용 — 필요 시 수동으로 INSERT)
INITIAL_ORDERS = [
    # (room_id, status)
    ("R001", "pending"),
    ("R002", "pending"),
    ("R003", "pending"),
]

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # rooms 테이블
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

    # orders 테이블
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            seq     INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id TEXT NOT NULL REFERENCES rooms(id),
            status  TEXT NOT NULL DEFAULT 'pending'
        )
    """)
    # 기존 orders 초기화 후 재삽입
    cur.execute("DELETE FROM orders")
    cur.executemany(
        "INSERT INTO orders (room_id, status) VALUES (?, ?)",
        INITIAL_ORDERS
    )

    con.commit()

    print(f"DB 초기화 완료: {DB_PATH}")
    print("\n[rooms]")
    for row in cur.execute("SELECT * FROM rooms"):
        print(f"  {row}")
    print("\n[orders]")
    for row in cur.execute("SELECT * FROM orders"):
        print(f"  {row}")

    con.close()

if __name__ == "__main__":
    init_db()
