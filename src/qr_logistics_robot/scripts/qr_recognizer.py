#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
from pyzbar.pyzbar import decode
import json
import os
import sys

def recognize_qr(image_path):
    print(f"[*] 이미지 로드 중: {image_path}")
    
    # 1. OpenCV를 통해 이미지 읽기
    img = cv2.imread(image_path)
    if img is None:
        print("[!] 에러: 이미지를 찾을 수 없거나 열 수 없습니다. 경로를 확인해주세요.")
        sys.exit(1)
        
    # 2. pyzbar를 이용한 QR 코드 디코딩 (여러 개가 있을 수 있으므로 리스트 반환)
    decoded_objects = decode(img)
    
    if not decoded_objects:
        print("[-] 이미지에서 QR 코드를 인식하지 못했습니다.")
        return

    # 3. 인식된 각 QR 코드에 대해 데이터 처리
    for obj in decoded_objects:
        # 데이터는 바이트(byte) 형태이므로 utf-8 문자열로 디코딩
        qr_data = obj.data.decode('utf-8')
        print("\n========================================")
        print("[+] QR 코드 인식 성공!")
        print(f"[-] 원본 문자열: {qr_data}")
        print("========================================")
        
        # 4. JSON 문자열을 파이썬 딕셔너리로 파싱
        try:
            logistics_info = json.loads(qr_data)
            print("\n[+] 물류 데이터 파싱 결과:")
            print(f"  ▶ 물품 ID   : {logistics_info.get('item_id', 'N/A')}")
            print(f"  ▶ 목적지 구역: {logistics_info.get('destination', 'N/A')}")
            print(f"  ▶ 목표 좌표 : {logistics_info.get('target_coordinates', 'N/A')}")
            print(f"  ▶ 우선 순위 : {logistics_info.get('priority', 'N/A')}")
            print(f"  ▶ 상세 설명 : {logistics_info.get('description', 'N/A')}")
            
            # 추후 이 좌표값을 ROS Topic으로 Publish 하는 코드가 여기에 추가됩니다.
            
        except json.JSONDecodeError:
            print("\n[!] 경고: 인식된 데이터가 유효한 JSON 포맷이 아닙니다.")

if __name__ == "__main__":
    # 기본 경로 설정: 모듈 2에서 생성했던 이미지 경로
    workspace_path = os.path.join(os.path.expanduser('~'), 'catkin_ws', 'src', 'qr_logistics_robot', 'models')
    
    # 윈도우 로컬 환경 테스트를 위한 예외 처리 (models 폴더가 없으면 현재 경로 탐색)
    if not os.path.exists(workspace_path):
        workspace_path = os.getcwd()
        
    target_image_path = os.path.join(workspace_path, 'logistics_qr_1.png')
    
    recognize_qr(target_image_path)
