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
        self.db = sqlite3.connect(db_path)
        rospy.loginfo(f"병실 DB 연결 완료: {db_path}")
        rospy.on_shutdown(self._close_db)

        # 비전 인식 노드 구독
        rospy.Subscriber('/target_logistics_info', String, self.target_callback)
        rospy.loginfo("경로 탐색 노드가 시작되었습니다. 비전 인식기의 좌표 하달을 기다립니다...")

        self.current_goal_id = None

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
            task_id = logistics_info.get('id')

            if self.current_goal_id == task_id:
                return

            row = self.db.execute(
                "SELECT name, x, y, theta FROM rooms WHERE id=?", (task_id,)
            ).fetchone()

            if row is None:
                rospy.logwarn(f"DB에 ID '{task_id}'에 해당하는 병실 정보가 없습니다.")
                return

            dest_name, x, y, theta = row
            rospy.loginfo(
                f">>> [{dest_name}(으)로 이동] 임무를 시작합니다! "
                f"(목표 좌표: X={x}, Y={y}, θ={math.degrees(theta):.1f}°)"
            )

            self._send_goal(x, y, theta)
            self.current_goal_id = task_id

        elif qr_type == 'ARR':
            task_id = logistics_info.get('id')
            if self.current_goal_id == task_id:
                rospy.loginfo(
                    f"*** 배송 완료! (Task ID: {task_id}) "
                    f"목적지 QR 인식을 성공했습니다. 대기 상태로 전환합니다. ***"
                )
                self.current_goal_id = None
            else:
                rospy.logwarn(
                    f"도착 QR을 인식했지만, 현재 수행 중인 임무({self.current_goal_id})와 일치하지 않습니다."
                )

        else:
            # 구버전 호환 로직 (destination, target_coordinates)
            destination = logistics_info.get('destination')
            coords = logistics_info.get('target_coordinates')

            if coords and len(coords) == 2:
                if self.current_goal_id == destination:
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

                self.current_goal_id = destination
            else:
                rospy.logwarn("수신된 물류 데이터에 유효한 좌표 값이 없습니다.")

if __name__ == '__main__':
    try:
        node = PathPlannerNode()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
