#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rospy
import actionlib
import json
from std_msgs.msg import String
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal

class PathPlannerNode:
    def __init__(self):
        rospy.init_node('path_planner_node', anonymous=True)
        
        # 1. move_base 액션 클라이언트 생성 (로봇 주행을 관장하는 서버로 명령을 보냄)
        self.client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
        
        rospy.loginfo("Navigation(move_base) 서버 연결 대기 중...")
        # 2일차 현재는 실제 주행 서버(move_base)가 아직 띄워지지 않았으므로 5초만 대기합니다.
        server_found = self.client.wait_for_server(rospy.Duration(5.0))
        if server_found:
            rospy.loginfo("Navigation 서버 연결 완료! 주행 준비 끝.")
        else:
            rospy.logwarn("Navigation 서버를 찾을 수 없습니다. (통신 뼈대 테스트 모드로 전환합니다.)")
            
        # 2. 비전 인식 노드에서 퍼블리시하는 데이터 구독
        rospy.Subscriber('/target_logistics_info', String, self.target_callback)
        rospy.loginfo("경로 탐색 노드가 시작되었습니다. 비전 인식기의 좌표 하달을 기다립니다...")
        
        # 동일한 목적지로의 중복 주행 명령 전송 방지
        self.current_goal_id = None

    def target_callback(self, data):
        try:
            logistics_info = json.loads(data.data)
            destination = logistics_info.get('destination')
            coords = logistics_info.get('target_coordinates')
            
            # 데이터 구조 방어 로직 (coords가 리스트 형태이고 길이가 2인지 확인)
            if coords and len(coords) == 2:
                # 이미 동일한 목적지 명령을 내린 상태라면 무시
                if self.current_goal_id == destination:
                    return
                    
                rospy.loginfo(f">>> [{destination}] 구역으로 주행 명령을 하달합니다! (목표 좌표: X={coords[0]}, Y={coords[1]})")
                
                # 3. ROS Navigation Action Server로 보낼 Goal 데이터 포맷팅
                goal = MoveBaseGoal()
                goal.target_pose.header.frame_id = "map"
                goal.target_pose.header.stamp = rospy.Time.now()
                
                goal.target_pose.pose.position.x = float(coords[0])
                goal.target_pose.pose.position.y = float(coords[1])
                # 로봇이 도착했을 때 바라볼 방향(정면) 임시 설정
                goal.target_pose.pose.orientation.w = 1.0
                
                # 4. Action Server로 Goal 전송 (서버가 연결된 경우에만)
                if self.client.wait_for_server(rospy.Duration(0.1)):
                    self.client.send_goal(goal)
                    rospy.loginfo("--- 주행 목표(Goal) 실제 전송 완료! ---")
                else:
                    rospy.loginfo("--- 주행 목표(Goal) 가상 전송 완료! (Navigation 스택 가동 시 로봇이 즉시 출발합니다) ---")
                
                # 상태 업데이트
                self.current_goal_id = destination
            else:
                rospy.logwarn("수신된 물류 데이터에 유효한 좌표(target_coordinates) 값이 없습니다.")
                
        except json.JSONDecodeError:
            rospy.logerr("수신된 데이터를 JSON으로 파싱할 수 없습니다.")

if __name__ == '__main__':
    try:
        node = PathPlannerNode()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
