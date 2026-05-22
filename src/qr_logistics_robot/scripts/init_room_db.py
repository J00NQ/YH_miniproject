#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
병실 좌표 DB 초기화 스크립트
실행: python3 init_room_db.py
생성 위치: ../db/hospital_rooms.db
"""

import sqlite3
import os
import math

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../db/hospital_rooms.db'))

ROOMS = [
    # (id,    name,    x,       y,      theta)
    ("R001", "1병실",  1.6703,  -11.0,  0.0),
    ("R002", "2병실", -0.6141,  -11.0,  0.0),
    ("R003", "3병실", -3.0615,  -11.0,  0.0),
]

INITIAL_ORDERS = [
    # (room_id, status)
    ("R001", "pending"),
    ("R002", "pending"),
    ("R003", "pending"),
]

# 홈 좌표: Gazebo 스폰 위치 (0, 0), 180° 방향
HOME = (0.0, 0.0, math.pi)

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
    cur.execute("DELETE FROM orders")
    cur.executemany(
        "INSERT INTO orders (room_id, status) VALUES (?, ?)",
        INITIAL_ORDERS
    )

    # robot 테이블 — 로봇 상태 및 홈 좌표
    cur.execute("""
        CREATE TABLE IF NOT EXISTS robot (
            id         INTEGER PRIMARY KEY DEFAULT 1,
            status     TEXT NOT NULL DEFAULT '대기',
            home_x     REAL NOT NULL DEFAULT 0.0,
            home_y     REAL NOT NULL DEFAULT 0.0,
            home_theta REAL NOT NULL DEFAULT 3.1416
        )
    """)
    # 행이 없을 때만 INSERT — 재실행 시 현재 상태 보존
    cur.execute("""
        INSERT OR IGNORE INTO robot (id, status, home_x, home_y, home_theta)
        VALUES (1, '대기', ?, ?, ?)
    """, HOME)

    con.commit()

    print(f"DB 초기화 완료: {DB_PATH}")
    print("\n[rooms]")
    for row in cur.execute("SELECT * FROM rooms"):
        print(f"  {row}")
    print("\n[orders]")
    for row in cur.execute("SELECT * FROM orders"):
        print(f"  {row}")
    print("\n[robot]")
    for row in cur.execute("SELECT * FROM robot"):
        print(f"  {row}")

    con.close()

if __name__ == "__main__":
    init_db()
