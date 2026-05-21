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
        # latch=True: 늦게 연결된 구독자에게도 마지막 메시지를 즉시 전달 (노드 시작 순서 무관)
        self.pub = rospy.Publisher('/target_logistics_info', String, queue_size=10, latch=True)
        
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
        self.roi_offset = (0, 0)   # ROI 크롭 오프셋 (바운딩 박스 좌표 역변환용)
        self.decode_scale = 1      # 업스케일 배율 (바운딩 박스 좌표 역변환용)
        self.qr_detector = cv2.QRCodeDetector()  # pyzbar 실패 시 fallback

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

    def detect_qr(self, cv_image):
        """중앙 ROI 크롭 + 멀티스케일 업스케일로 소형 QR 인식.
        반환: (decoded_list, roi_offset(x,y), scale)
        """
        h, w = cv_image.shape[:2]

        # 화면 중앙 60% 영역 크롭 (로봇 정면 QR이 항상 중앙에 위치)
        x1, y1 = int(w * 0.2), int(h * 0.2)
        x2, y2 = int(w * 0.8), int(h * 0.8)
        roi = cv_image[y1:y2, x1:x2]

        # 전처리: 그레이스케일 → CLAHE → Otsu 이진화
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        enhanced = self.clahe.apply(gray)
        _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

        # pyzbar: ROI 원본(1x) → 2x → 4x 순으로 업스케일 후 디코딩 시도
        # 업스케일로 QR 모듈당 픽셀 수를 늘려 pyzbar 인식률 향상
        for scale in [1, 2, 4]:
            img = cv2.resize(thresh, None, fx=scale, fy=scale,
                             interpolation=cv2.INTER_CUBIC) if scale > 1 else thresh
            results = decode(img)
            if results:
                return results, (x1, y1), scale

        # cv2.QRCodeDetector fallback: pyzbar 전부 실패 시 시도
        # OpenCV 4.2에서 pts 윤곽 면적이 0이면 내부 decode()가 cv2.error를 던지므로 방어 처리
        try:
            data, pts, _ = self.qr_detector.detectAndDecode(roi)
        except cv2.error:
            return [], (x1, y1), 1
        if data:
            polygon = []
            if pts is not None and len(pts) > 0:
                polygon = [type('P', (), {'x': int(p[0]), 'y': int(p[1])})()
                           for p in pts[0]]
            class _QR:
                pass
            obj = _QR()
            obj.data = data.encode('utf-8')
            obj.polygon = polygon
            return [obj], (x1, y1), 1

        return [], (x1, y1), 1

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

        # 프레임 스킵: 3프레임마다 1회만 디코딩 수행 (FPS 최적화)
        self.frame_count += 1
        if self.frame_count % 3 == 0:
            self.last_decoded, self.roi_offset, self.decode_scale = self.detect_qr(cv_image)

        if self.last_decoded:
            for obj in self.last_decoded:
                # 1. QR 데이터 디코딩
                qr_data = obj.data.decode('utf-8')

                # 2. 바운딩 박스 그리기: ROI+스케일 좌표 → 전체 이미지 좌표 역변환
                points = obj.polygon
                ox, oy = self.roi_offset
                s = self.decode_scale
                if len(points) == 4:
                    full_pts = np.array(
                        [[int(p.x / s) + ox, int(p.y / s) + oy] for p in points],
                        dtype=np.int32
                    )
                    cv2.polylines(cv_image, [full_pts.reshape((-1, 1, 2))], True, (0, 255, 0), 3)
                    cx = int(np.mean(full_pts[:, 0]))
                    cy = int(np.mean(full_pts[:, 1]))
                    cv2.circle(cv_image, (cx, cy), 5, (0, 0, 255), -1)

                # 3. 데이터 파싱 및 퍼블리시
                if qr_data != self.last_published_data:
                    try:
                        logistics_info = json.loads(qr_data)
                        qr_type = logistics_info.get('type')
                        task_id = logistics_info.get('id')

                        if qr_type == 'START':
                            rospy.loginfo(f"=====================================================")
                            rospy.loginfo(f"[배송 시작 QR 감지!] 목적지는 orders DB에서 결정됩니다.")
                            rospy.loginfo(f"=====================================================")
                        elif qr_type == 'ARR':
                            rospy.loginfo(f"=====================================================")
                            rospy.loginfo(f"[도착 확인 QR 감지!] 임무 완료 대기 중...")
                            rospy.loginfo(f"=====================================================")
                        else:
                            rospy.loginfo(f"=====================================================")
                            rospy.loginfo(f"[새로운 QR 감지!] 임무 ID: {task_id} / 주행 시작 대기 중...")
                            rospy.loginfo(f"=====================================================")

                        # 파싱된 데이터 문자열을 ROS Topic으로 발행
                        self.pub.publish(qr_data)

                        # 중복 방지를 위해 최근 데이터 갱신
                        self.last_published_data = qr_data

                    except json.JSONDecodeError:
                        rospy.logwarn("인식된 데이터가 유효한 JSON 포맷이 아닙니다.")

                # QR코드 목적지 텍스트를 Bounding Box 위에 오버레이
                try:
                    info = json.loads(qr_data)
                    qr_type = info.get('type')
                    if qr_type == 'START':
                        display_text = f"START: ID {info.get('id', 'Task')}"
                    elif qr_type == 'ARR':
                        display_text = f"ARRIVAL"
                    else:
                        display_text = f"ID: {info.get('id', 'QR')}"
                except:
                    display_text = "QR Code"

                text_x = int(points[0].x / s) + ox
                text_y = max(int(points[0].y / s) + oy - 10, 10)
                cv2.putText(cv_image, f"Dest: {display_text}", (text_x, text_y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # ROI 영역 표시 (주황색 박스 - QR 탐색 범위 시각화)
        h_img, w_img = cv_image.shape[:2]
        roi_x1, roi_y1 = int(w_img * 0.2), int(h_img * 0.2)
        roi_x2, roi_y2 = int(w_img * 0.8), int(h_img * 0.8)
        cv2.rectangle(cv_image, (roi_x1, roi_y1), (roi_x2, roi_y2), (0, 165, 255), 2)
        cv2.putText(cv_image, "ROI", (roi_x1 + 4, roi_y1 + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)

        # FPS 및 거리 화면 좌측 상단 텍스트 출력
        cv2.putText(cv_image, f"FPS: {fps:.1f}", (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

        dist_text = f"Dist to Dest: {self.path_distance:.2f}m" if self.path_distance > 0 else "Dist to Dest: N/A"
        cv2.putText(cv_image, dist_text, (20, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

        # 실시간 시각화 창 띄우기 (OpenCV)
        cv2.imshow("Robot Camera Vision (Processed)", cv_image)
        cv2.waitKey(1)

if __name__ == '__main__':
    try:
        node = VisionRecognizerNode()
        # 노드가 종료되지 않고 계속해서 카메라 콜백을 대기하도록 유지
        rospy.spin()
    except rospy.ROSInterruptException:
        cv2.destroyAllWindows()
