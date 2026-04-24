#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rospy
from std_msgs.msg import String
import cv2
from pyzbar.pyzbar import decode
import json
import os

def recognize_and_publish():
    # 1. ROS 노드 초기화 ('qr_recognizer_node' 라는 이름으로 등록)
    rospy.init_node('qr_recognizer_node', anonymous=True)
    
    # 2. 퍼블리셔 생성: '/target_logistics_info' 토픽으로 String 메시지를 발행
    pub = rospy.Publisher('/target_logistics_info', String, queue_size=10)
    
    # 1초에 1번씩 실행되도록 루프 주기 설정 (1Hz)
    rate = rospy.Rate(1)
    
    # 대상 이미지 경로 설정 (임시로 생성한 로컬 이미지 사용)
    workspace_path = os.path.join(os.path.expanduser('~'), 'catkin_ws', 'src', 'qr_logistics_robot', 'models')
    if not os.path.exists(workspace_path):
        workspace_path = os.getcwd()
    target_image_path = os.path.join(workspace_path, 'logistics_qr_1.png')

    rospy.loginfo(f"QR 인식기 ROS 노드가 시작되었습니다. 대상 이미지: {target_image_path}")

    # 3. 노드가 종료될 때까지 무한 반복 (실시간 카메라 처리를 위한 뼈대)
    while not rospy.is_shutdown():
        # 이미지 불러오기
        img = cv2.imread(target_image_path)
        if img is None:
            rospy.logerr("이미지를 찾을 수 없거나 열 수 없습니다.")
            rate.sleep()
            continue
            
        # QR 디코딩
        decoded_objects = decode(img)
        
        if decoded_objects:
            for obj in decoded_objects:
                qr_data = obj.data.decode('utf-8')
                
                try:
                    # JSON 검증
                    logistics_info = json.loads(qr_data)
                    rospy.loginfo(f"QR 인식 완료! 목적지: {logistics_info.get('destination')} / 퍼블리시 진행 중...")
                    
                    # 파싱된 데이터 문자열을 ROS Topic으로 발행(Publish)
                    pub.publish(qr_data)
                    
                except json.JSONDecodeError:
                    rospy.logwarn("인식된 데이터가 유효한 JSON 포맷이 아닙니다.")
        else:
            rospy.logwarn("QR 코드를 찾을 수 없습니다.")
            
        # 지정된 주기(1Hz)만큼 대기
        rate.sleep()

if __name__ == '__main__':
    try:
        recognize_and_publish()
    except rospy.ROSInterruptException:
        pass
