#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import qrcode
import json
import os

def generate_logistics_qr():
    # 1. 물류 배송에 사용할 데이터 정의 (JSON 포맷)
    logistics_data = {
        "item_id": "BOX-2026-001",
        "destination": "A_zone",            # 목적지 명칭
        "target_coordinates": [3.0, 3.0],   # Gazebo 맵 상의 x, y 좌표
        "priority": "high",
        "description": "Fragile Electronics"
    }
    
    # 2. JSON 객체를 문자열로 변환
    data_str = json.dumps(logistics_data, ensure_ascii=False)
    print(f"[*] 인코딩할 데이터: {data_str}")

    # 3. QR 코드 객체 생성 및 설정
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H, # 인식률을 높이기 위한 High 에러 보정
        box_size=10,
        border=4,
    )
    
    # 4. 데이터 삽입 및 이미지화
    qr.add_data(data_str)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # 5. 저장 경로 설정 및 파일 저장 (models 폴더 내)
    # 윈도우/리눅스 호환성을 위해 상대경로 및 절대경로 처리
    workspace_path = os.path.join(os.path.expanduser('~'), 'catkin_ws', 'src', 'qr_logistics_robot', 'models')
    
    # 윈도우 환경 테스트를 대비한 예외 처리 (디렉토리가 없으면 현재 폴더에 저장)
    if not os.path.exists(workspace_path):
        workspace_path = os.getcwd()
        
    save_path = os.path.join(workspace_path, 'logistics_qr_1.png')
    img.save(save_path)
    
    print(f"[+] QR 코드 생성 완료: {save_path}")

if __name__ == "__main__":
    generate_logistics_qr()
