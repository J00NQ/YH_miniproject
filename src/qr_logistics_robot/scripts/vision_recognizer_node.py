#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rospy
from std_msgs.msg import String
from sensor_msgs.msg import Image, CameraInfo
from cv_bridge import CvBridge, CvBridgeError
import cv2
from pyzbar.pyzbar import decode
import json
import time
import math
import numpy as np
from nav_msgs.msg import Path

class VisionRecognizerNode:
    def __init__(self):
        # 1. 노드 초기화
        rospy.init_node('vision_recognizer_node', anonymous=True)
        
        # ROS 이미지 포맷과 OpenCV 이미지 포맷 간의 변환기
        self.bridge = CvBridge()
        
        # 2. 파싱된 목적지 데이터를 발행할 퍼블리셔
        self.pub = rospy.Publisher('/target_logistics_info', String, queue_size=10)
        
        # 3. 로봇 카메라 토픽을 구독하는 서브스크라이버 (프레임이 들어올 때마다 image_callback 실행)
        self.sub = rospy.Subscriber('/camera/rgb/image_raw', Image, self.image_callback)
        
        rospy.loginfo("실시간 카메라 비전 인식 노드가 시작되었습니다. 영상을 기다립니다...")
        
        # 상태 변수
        self.last_published_data = None
        self.last_time = time.time()
        self.path_distance = 0.0
        self.camera_matrix = None
        self.dist_coeffs = None
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        self.frame_count = 0
        self.last_decoded = []

        # 4. 카메라 내부 파라미터 수신 (캘리브레이션)
        rospy.Subscriber('/camera/rgb/camera_info', CameraInfo, self.camera_info_callback)

        # 5. 목적지까지의 경로 토픽 구독
        # TurtleBot3 기본 네비게이션 스택의 Global Planner 토픽 구독
        rospy.Subscriber('/move_base/NavfnROS/plan', Path, self.path_callback)
        rospy.Subscriber('/move_base/GlobalPlanner/plan', Path, self.path_callback)

    def camera_info_callback(self, msg):
        """카메라 내부 파라미터를 토픽에서 동적으로 수신 (최초 1회만 저장)"""
        if self.camera_matrix is None:
            self.camera_matrix = np.array(msg.K).reshape(3, 3)
            self.dist_coeffs = np.array(msg.D)
            rospy.loginfo("카메라 캘리브레이션 파라미터 수신 완료.")

    def path_callback(self, msg):
        """Path 토픽을 기반으로 목적지까지의 남은 거리를 계산"""
        if not msg.poses or len(msg.poses) < 2:
            self.path_distance = 0.0
            return
            
        distance = 0.0
        for i in range(len(msg.poses) - 1):
            p1 = msg.poses[i].pose.position
            p2 = msg.poses[i+1].pose.position
            distance += math.hypot(p2.x - p1.x, p2.y - p1.y)
            
        self.path_distance = distance

    def preprocess_image(self, cv_image):
        """조명 및 잡음 환경에 대비한 전처리 (2회차 중급: 기능 안정화)"""
        # 1. 그레이스케일 변환 (인식 속도 및 정확도 향상)
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        
        # 2. Gaussian Blur (센서 노이즈 제거)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # 3. CLAHE (대비 제한 적응형 히스토그램 평활화) - 역광/그림자 환경 대비
        enhanced = self.clahe.apply(blurred)
        
        return enhanced

    def image_callback(self, data):
        # FPS 측정 (현재 시간)
        current_time = time.time()
        fps = 1.0 / (current_time - self.last_time) if (current_time - self.last_time) > 0 else 0
        self.last_time = current_time

        try:
            # ROS Image(sensor_msgs)를 OpenCV Image(bgr8 포맷)로 변환
            cv_image = self.bridge.imgmsg_to_cv2(data, "bgr8")
        except CvBridgeError as e:
            rospy.logerr(f"cv_bridge 에러: {e}")
            return

        # 캘리브레이션 파라미터 수신 완료 시 렌즈 왜곡 보정 적용
        if self.camera_matrix is not None:
            cv_image = cv2.undistort(cv_image, self.camera_matrix, self.dist_coeffs)

        # 프레임 스킵: 3프레임마다 1회만 전처리·디코딩 수행 (FPS 최적화)
        self.frame_count += 1
        if self.frame_count % 3 == 0:
            preprocessed_img = self.preprocess_image(cv_image)
            self.last_decoded = decode(preprocessed_img)

        if self.last_decoded:
            for obj in self.last_decoded:
                # 1. QR 데이터 디코딩
                qr_data = obj.data.decode('utf-8')

                # 2. 바운딩 박스 그리기 (실시간 시각화)
                points = obj.polygon
                if len(points) == 4:
                    pts = np.array(points, dtype=np.int32)
                    pts = pts.reshape((-1, 1, 2))
                    cv2.polylines(cv_image, [pts], True, (0, 255, 0), 3)

                    # 중심점 계산 및 표시
                    cx = int(np.mean([p.x for p in points]))
                    cy = int(np.mean([p.y for p in points]))
                    cv2.circle(cv_image, (cx, cy), 5, (0, 0, 255), -1)

                # 3. 데이터 파싱 및 퍼블리시
                if qr_data != self.last_published_data:
                    try:
                        logistics_info = json.loads(qr_data)
                        dest = logistics_info.get('destination', 'Unknown')
                        rospy.loginfo(f"=====================================================")
                        rospy.loginfo(f"[새로운 QR 감지!] 목적지: {dest} / 주행 시작 대기 중...")
                        rospy.loginfo(f"=====================================================")

                        # 파싱된 데이터 문자열을 ROS Topic으로 발행
                        self.pub.publish(qr_data)

                        # 중복 방지를 위해 최근 데이터 갱신
                        self.last_published_data = qr_data

                    except json.JSONDecodeError:
                        rospy.logwarn("인식된 데이터가 유효한 JSON 포맷이 아닙니다.")

                # QR코드 목적지 텍스트를 Bounding Box 위에 오버레이
                try:
                    display_text = json.loads(qr_data).get('destination', 'QR')
                except:
                    display_text = "QR Code"

                cv2.putText(cv_image, f"Dest: {display_text}", (points[0].x, points[0].y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # FPS 및 거리 화면 좌측 상단 텍스트 출력
        cv2.putText(cv_image, f"FPS: {fps:.1f}", (20, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
        
        dist_text = f"Dist to Dest: {self.path_distance:.2f}m" if self.path_distance > 0 else "Dist to Dest: N/A"
        cv2.putText(cv_image, dist_text, (20, 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

        # 실시간 시각화 창 띄우기 (OpenCV)
        cv2.imshow("Robot Camera Vision (Processed)", cv_image)
        # cv2.imshow("Preprocessed (CLAHE)", preprocessed_img) # 디버깅 시 주석 해제하여 흑백 영상 확인
        cv2.waitKey(1)

if __name__ == '__main__':
    try:
        node = VisionRecognizerNode()
        # 노드가 종료되지 않고 계속해서 카메라 콜백을 대기하도록 유지
        rospy.spin()
    except rospy.ROSInterruptException:
        cv2.destroyAllWindows()
