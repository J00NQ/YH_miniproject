#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rospy
import actionlib
import json
import math
import sqlite3
import os
from actionlib_msgs.msg import GoalStatus
from std_msgs.msg import String
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal

class PathPlannerNode:
    def __init__(self):
        rospy.init_node('path_planner_node', anonymous=True)

        # move_base 액션 클라이언트
        self.client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
        rospy.loginfo("Navigation(move_base) 서버 연결 대기 중...")
        server_found = self.client.wait_for_server(rospy.Duration(5.0))
        if server_found:
            rospy.loginfo("Navigation 서버 연결 완료! 주행 준비 끝.")
        else:
            rospy.logwarn("Navigation 서버를 찾을 수 없습니다. (통신 뼈대 테스트 모드로 전환합니다.)")

        # SQLite DB 연결
        default_db = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '../db/hospital_rooms.db')
        )
        db_path = rospy.get_param('~db_path', default_db)
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        rospy.loginfo(f"병실 DB 연결 완료: {db_path}")
        rospy.on_shutdown(self._close_db)

        self.current_order_seq = None
        self.current_room_id   = None

        # ARR QR 구독
        rospy.Subscriber('/target_logistics_info', String, self._arr_callback)

        # 5초마다 orders 폴링 (대기 상태일 때만 출발)
        rospy.Timer(rospy.Duration(5.0), self._poll_orders)

        rospy.loginfo("경로 탐색 노드 시작. 5초마다 DB를 폴링합니다...")

    def _close_db(self):
        self.db.close()
        rospy.loginfo("병실 DB 연결 종료.")

    # ── 상태 헬퍼 ────────────────────────────────────────────────────────────

    def _get_robot_status(self):
        row = self.db.execute("SELECT status FROM robot WHERE id=1").fetchone()
        return row[0] if row else None

    def _set_robot_status(self, status):
        self.db.execute("UPDATE robot SET status=? WHERE id=1", (status,))
        self.db.commit()
        rospy.loginfo(f"[robot.status] → {status}")

    # ── goal 전송 ─────────────────────────────────────────────────────────────

    def _send_goal(self, x, y, theta, done_cb=None):
        goal = MoveBaseGoal()
        goal.target_pose.header.frame_id = "map"
        goal.target_pose.header.stamp = rospy.Time.now()
        goal.target_pose.pose.position.x = x
        goal.target_pose.pose.position.y = y
        goal.target_pose.pose.orientation.z = math.sin(theta / 2.0)
        goal.target_pose.pose.orientation.w = math.cos(theta / 2.0)

        if self.client.wait_for_server(rospy.Duration(0.1)):
            self.client.send_goal(goal, done_cb=done_cb)
            rospy.loginfo(f"--- Goal 전송 완료 (X={x:.4f}, Y={y:.4f}, θ={math.degrees(theta):.1f}°) ---")
        else:
            rospy.logwarn("Navigation 서버 미연결 — Goal 전송 실패")

    def _send_home_goal(self):
        row = self.db.execute(
            "SELECT home_x, home_y, home_theta FROM robot WHERE id=1"
        ).fetchone()
        if row is None:
            rospy.logerr("robot 테이블에서 홈 좌표를 읽을 수 없습니다.")
            return
        home_x, home_y, home_theta = row
        rospy.loginfo(">>> [홈 복귀] 출발 지점으로 돌아갑니다.")
        self._send_goal(home_x, home_y, home_theta, done_cb=self._on_home_arrived)

    # ── 홈 도착 콜백 ──────────────────────────────────────────────────────────

    def _on_home_arrived(self, state, result):
        if state == GoalStatus.SUCCEEDED:
            self._set_robot_status('대기')
            rospy.loginfo("=== 홈 복귀 완료. 대기 상태로 전환합니다. ===")
        else:
            rospy.logwarn(f"홈 복귀 실패 (GoalStatus={state}). 수동 확인이 필요합니다.")

    # ── DB 폴링 타이머 ────────────────────────────────────────────────────────

    def _poll_orders(self, event):
        if self._get_robot_status() != '대기':
            return

        row = self.db.execute("""
            SELECT o.seq, o.room_id, r.name, r.x, r.y, r.theta
            FROM orders o JOIN rooms r ON o.room_id = r.id
            WHERE o.status = 'pending'
            ORDER BY o.seq ASC
            LIMIT 1
        """).fetchone()

        if row is None:
            return

        seq, room_id, dest_name, x, y, theta = row

        self.db.execute("UPDATE orders SET status='active' WHERE seq=?", (seq,))
        self._set_robot_status('이동중')

        rospy.loginfo(
            f">>> [배송 시작] {dest_name}(으)로 이동합니다! "
            f"(seq={seq}, X={x}, Y={y}, θ={math.degrees(theta):.1f}°)"
        )

        self.current_order_seq = seq
        self.current_room_id   = room_id
        self._send_goal(x, y, theta)

    # ── ARR QR 수신 콜백 ──────────────────────────────────────────────────────

    def _arr_callback(self, data):
        try:
            logistics_info = json.loads(data.data)
        except json.JSONDecodeError:
            rospy.logerr("수신된 데이터를 JSON으로 파싱할 수 없습니다.")
            return

        if logistics_info.get('type') != 'ARR':
            return

        if self.current_order_seq is None:
            rospy.logwarn("수행 중인 임무가 없는데 도착 QR이 인식되었습니다.")
            return

        # 배송 완료 처리
        self.db.execute("UPDATE orders SET status='done' WHERE seq=?", (self.current_order_seq,))
        self._set_robot_status('복귀')

        rospy.loginfo(
            f"*** 배송 완료! (seq={self.current_order_seq}, 목적지={self.current_room_id}) "
            f"홈으로 복귀합니다. ***"
        )

        self.current_order_seq = None
        self.current_room_id   = None
        self._send_home_goal()

if __name__ == '__main__':
    try:
        node = PathPlannerNode()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
