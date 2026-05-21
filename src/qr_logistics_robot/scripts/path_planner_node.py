#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rospy
import actionlib
import json
import math
import sqlite3
import os
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

        # 비전 인식 노드 구독
        rospy.Subscriber('/target_logistics_info', String, self.target_callback)
        rospy.loginfo("경로 탐색 노드가 시작되었습니다. 비전 인식기의 좌표 하달을 기다립니다...")

        self.current_order_seq = None   # 현재 수행 중인 orders.seq
        self.current_room_id   = None   # ARRIVAL QR 매칭용 room_id

    def _close_db(self):
        self.db.close()
        rospy.loginfo("병실 DB 연결 종료.")

    def _send_goal(self, x, y, theta):
        goal = MoveBaseGoal()
        goal.target_pose.header.frame_id = "map"
        goal.target_pose.header.stamp = rospy.Time.now()
        goal.target_pose.pose.position.x = x
        goal.target_pose.pose.position.y = y
        goal.target_pose.pose.orientation.z = math.sin(theta / 2.0)
        goal.target_pose.pose.orientation.w = math.cos(theta / 2.0)

        if self.client.wait_for_server(rospy.Duration(0.1)):
            self.client.send_goal(goal)
            rospy.loginfo("--- 주행 목표(Goal) 실제 전송 완료! ---")
        else:
            rospy.loginfo("--- 주행 목표(Goal) 가상 전송 완료! (Navigation 스택 가동 시 로봇이 즉시 출발합니다) ---")

    def target_callback(self, data):
        try:
            logistics_info = json.loads(data.data)
        except json.JSONDecodeError:
            rospy.logerr("수신된 데이터를 JSON으로 파싱할 수 없습니다.")
            return

        qr_type = logistics_info.get('type')

        if qr_type == 'START':
            if self.current_order_seq is not None:
                rospy.logwarn("이미 수행 중인 임무가 있습니다. 현재 임무 완료 후 다시 시도하세요.")
                return

            # orders 큐에서 가장 오래된 pending 작업 조회
            row = self.db.execute("""
                SELECT o.seq, o.room_id, r.name, r.x, r.y, r.theta
                FROM orders o JOIN rooms r ON o.room_id = r.id
                WHERE o.status = 'pending'
                ORDER BY o.seq ASC
                LIMIT 1
            """).fetchone()

            if row is None:
                rospy.logwarn("대기 중인 배송 작업이 없습니다. orders 테이블을 확인하세요.")
                return

            seq, room_id, dest_name, x, y, theta = row

            # 작업 상태를 active로 전환
            self.db.execute("UPDATE orders SET status='active' WHERE seq=?", (seq,))
            self.db.commit()

            rospy.loginfo(
                f">>> [배송 시작] {dest_name}(으)로 이동합니다! "
                f"(seq={seq}, X={x}, Y={y}, θ={math.degrees(theta):.1f}°)"
            )

            self._send_goal(x, y, theta)
            self.current_order_seq = seq
            self.current_room_id   = room_id

        elif qr_type == 'ARR':
            arr_room_id = logistics_info.get('id')

            if self.current_room_id is None:
                rospy.logwarn("수행 중인 임무가 없는데 도착 QR이 인식되었습니다.")
                return

            if self.current_room_id != arr_room_id:
                rospy.logwarn(
                    f"도착 QR({arr_room_id})이 현재 임무 목적지({self.current_room_id})와 일치하지 않습니다."
                )
                return

            # 작업 완료 처리
            self.db.execute("UPDATE orders SET status='done' WHERE seq=?", (self.current_order_seq,))
            self.db.commit()

            rospy.loginfo(
                f"*** 배송 완료! (seq={self.current_order_seq}, 목적지={self.current_room_id}) "
                f"대기 상태로 전환합니다. ***"
            )
            self.current_order_seq = None
            self.current_room_id   = None

        else:
            # 구버전 호환 로직 (destination, target_coordinates)
            destination = logistics_info.get('destination')
            coords = logistics_info.get('target_coordinates')

            if coords and len(coords) == 2:
                if self.current_room_id == destination:
                    return

                rospy.loginfo(
                    f">>> [{destination}] 구역으로 주행 명령을 하달합니다! "
                    f"(목표 좌표: X={coords[0]}, Y={coords[1]})"
                )

                goal = MoveBaseGoal()
                goal.target_pose.header.frame_id = "map"
                goal.target_pose.header.stamp = rospy.Time.now()
                goal.target_pose.pose.position.x = float(coords[0]) - 1.0
                goal.target_pose.pose.position.y = float(coords[1])
                goal.target_pose.pose.orientation.w = 1.0

                if self.client.wait_for_server(rospy.Duration(0.1)):
                    self.client.send_goal(goal)
                    rospy.loginfo("--- 주행 목표(Goal) 실제 전송 완료! ---")
                else:
                    rospy.loginfo("--- 주행 목표(Goal) 가상 전송 완료! ---")

                self.current_room_id = destination
            else:
                rospy.logwarn("수신된 물류 데이터에 유효한 좌표 값이 없습니다.")

if __name__ == '__main__':
    try:
        node = PathPlannerNode()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
