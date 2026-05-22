#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
병원 서빙로봇 웹 대시보드
DB_PATH 환경변수로 SQLite 경로 지정 (미설정 시 개발용 기본 경로 사용)
"""

import io
import os
import math
import sqlite3
import qrcode
from flask import Flask, render_template, request, redirect, url_for, flash, send_file

app = Flask(__name__)
app.secret_key = 'qr-logistics-dev-key'


@app.template_filter('deg')
def to_degrees(rad):
    """라디안 → 도(°) 변환, 소수점 2자리"""
    return round(math.degrees(float(rad)), 2)


@app.template_filter('f2')
def fmt2(val):
    """소수점 2자리 반올림"""
    return round(float(val), 2)

# 기본 경로: web/ 폴더가 qr_logistics_robot/ 아래에 위치할 때 자동으로 ../db/ 를 가리킴
# 예) /home/ubuntu20/catkin_ws/src/qr_logistics_robot/web/app.py
#     → DB: /home/ubuntu20/catkin_ws/src/qr_logistics_robot/db/hospital_rooms.db
DB_PATH = os.environ.get(
    'DB_PATH',
    os.path.abspath(os.path.join(os.path.dirname(__file__),
                                 '../db/hospital_rooms.db'))
)


def get_db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


# ── 대시보드 (전체 현황) ──────────────────────────────────────────────────────
@app.route('/')
def index():
    con = get_db()
    robot  = con.execute("SELECT * FROM robot WHERE id=1").fetchone()
    orders = con.execute(
        "SELECT o.seq, o.room_id, r.name, o.status "
        "FROM orders o JOIN rooms r ON o.room_id=r.id "
        "ORDER BY o.seq"
    ).fetchall()
    rooms  = con.execute("SELECT * FROM rooms ORDER BY id").fetchall()
    con.close()
    return render_template('index.html', robot=robot, orders=orders, rooms=rooms)


# ── rooms 테이블 ──────────────────────────────────────────────────────────────
@app.route('/rooms')
def rooms():
    con   = get_db()
    rooms = con.execute("SELECT * FROM rooms ORDER BY id").fetchall()
    con.close()
    return render_template('rooms.html', rooms=rooms)


@app.route('/rooms/edit/<room_id>', methods=['POST'])
def rooms_edit(room_id):
    name  = request.form['name']
    x     = request.form['x']
    y     = request.form['y']
    theta = request.form['theta']
    con   = get_db()
    con.execute(
        "UPDATE rooms SET name=?, x=?, y=?, theta=? WHERE id=?",
        (name, x, y, theta, room_id)
    )
    con.commit()
    con.close()
    flash(f'{room_id} 병실 정보가 수정되었습니다.')
    return redirect(url_for('rooms'))


# ── robot 테이블 (읽기 전용) ──────────────────────────────────────────────────
@app.route('/robot')
def robot():
    con   = get_db()
    robot = con.execute("SELECT * FROM robot WHERE id=1").fetchone()
    con.close()
    return render_template('robot.html', robot=robot)


# ── orders 테이블 ─────────────────────────────────────────────────────────────
@app.route('/orders')
def orders():
    con    = get_db()
    orders = con.execute(
        "SELECT o.seq, o.room_id, r.name, o.status "
        "FROM orders o JOIN rooms r ON o.room_id=r.id "
        "ORDER BY o.seq"
    ).fetchall()
    rooms  = con.execute("SELECT id, name FROM rooms ORDER BY id").fetchall()
    con.close()
    return render_template('orders.html', orders=orders, rooms=rooms)


@app.route('/orders/add', methods=['POST'])
def orders_add():
    room_id = request.form['room_id']
    con     = get_db()
    con.execute("INSERT INTO orders (room_id, status) VALUES (?, 'pending')", (room_id,))
    con.commit()
    con.close()
    flash(f'{room_id} 병실 배송 주문이 추가되었습니다.')
    return redirect(url_for('orders'))


@app.route('/orders/cancel/<int:seq>', methods=['POST'])
def orders_cancel(seq):
    con    = get_db()
    order  = con.execute("SELECT status FROM orders WHERE seq=?", (seq,)).fetchone()
    if order is None:
        flash(f'주문 #{seq}을 찾을 수 없습니다.')
    elif order['status'] != 'pending':
        flash(f'주문 #{seq}은 {order["status"]} 상태라 취소할 수 없습니다. (pending 상태만 취소 가능)')
    else:
        con.execute("DELETE FROM orders WHERE seq=?", (seq,))
        con.commit()
        flash(f'주문 #{seq}이 취소되었습니다.')
    con.close()
    return redirect(url_for('orders'))


# ── 수령 확인 QR (DB 불필요) ──────────────────────────────────────────────────
ARR_QR_DATA = '{"type":"ARR"}'


@app.route('/arrival-qr/image')
def arrival_qr_image():
    qr = qrcode.QRCode(version=1, box_size=12, border=4)
    qr.add_data(ARR_QR_DATA)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')


@app.route('/arrival-qr')
def arrival_qr():
    return render_template('arrival_qr.html')


if __name__ == '__main__':
    print(f"[DB] {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print("[WARN] DB 파일을 찾을 수 없습니다. Ubuntu 환경에서 실행하거나 DB_PATH를 설정하세요.")
    app.run(debug=True, host='0.0.0.0', port=5000)
