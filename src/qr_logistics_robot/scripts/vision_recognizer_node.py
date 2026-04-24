#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rospy
from std_msgs.msg import String
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError
import cv2
from pyzbar.pyzbar import decode
import json

class VisionRecognizerNode:
    def __init__(self):
        # 1. 노드 초기화
        rospy.init_node('vision_recognizer_node', anonymous=True)
        
        # ROS 이미지 포맷과 OpenCV 이미지 포맷 간의 변환기
        self.bridge = CvBridge()
        
        # 2. 파싱된 목적지 데이터를 발행할 퍼블리셔 (모듈 4와 동일)
        self.pub = rospy.Publisher('/target_logistics_info', String, queue_size=10)
        
        # 3. 로봇 카메라 토픽을 구독하는 서브스크라이버 (프레임이 들어올 때마다 image_callback 실행)
        self.sub = rospy.Subscriber('/camera/rgb/image_raw', Image, self.image_callback)
        
        rospy.loginfo("실시간 카메라 비전 인식 노드가 시작되었습니다. 영상을 기다립니다...")
        
        # 똑같은 QR코드를 계속 쳐다보고 있을 때 중복해서 발행하지 않도록 상태 저장
        self.last_published_data = None

    def image_callback(self, data):
        try:
            # ROS Image(sensor_msgs)를 OpenCV Image(bgr8 포맷)로 변환
            cv_image = self.bridge.imgmsg_to_cv2(data, "bgr8")
        except CvBridgeError as e:
            rospy.logerr(f"cv_bridge 에러: {e}")
            return
            
        # 프레임 이미지에서 QR 코드 디코딩 시도
        decoded_objects = decode(cv_image)
        
        if decoded_objects:
            for obj in decoded_objects:
                qr_data = obj.data.decode('utf-8')
                
                # 이전에 인식했던 데이터와 다를 경우에만 새롭게 파싱 및 Publish 진행
                if qr_data != self.last_published_data:
                    try:
                        logistics_info = json.loads(qr_data)
                        rospy.loginfo(f"=====================================================")
                        rospy.loginfo(f"[새로운 QR 감지!] 목적지: {logistics_info.get('destination')} / 좌표: {logistics_info.get('target_coordinates')}")
                        rospy.loginfo(f"=====================================================")
                        
                        # 파싱된 데이터 문자열을 ROS Topic으로 발행
                        self.pub.publish(qr_data)
                        
                        # 중복 방지를 위해 최근 데이터 갱신
                        self.last_published_data = qr_data
                        
                    except json.JSONDecodeError:
                        rospy.logwarn("인식된 데이터가 유효한 JSON 포맷이 아닙니다.")

if __name__ == '__main__':
    try:
        node = VisionRecognizerNode()
        # 노드가 종료되지 않고 계속해서 카메라 콜백을 대기하도록 유지
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
