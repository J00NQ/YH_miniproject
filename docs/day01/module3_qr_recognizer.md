# 모듈 3: QR 코드 인식기 구현 가이드

이 문서는 모듈 2에서 생성한 QR 코드 이미지 파일을 읽어들여, 그 안에 담긴 JSON 데이터를 로봇이 활용할 수 있는 형태로 파싱(추출)하는 **인식기 스크립트** 작성 및 테스트 과정을 다룹니다.

---

## 1. 개요 및 사용 라이브러리

- **OpenCV (`cv2`)**: 이미지 파일을 읽어오고 배열(Array) 형태로 다루기 위해 사용합니다. 향후 로봇의 카메라 실시간 영상 프레임을 받아올 때도 동일하게 사용됩니다.
- **`pyzbar`**: OpenCV 기본 QR 리더기보다 인식률이 훨씬 뛰어난 바코드/QR 디코딩 전용 라이브러리입니다.

---

## 2. QR 코드 인식 스크립트 작성

### 2.1 스크립트 파일 생성
가상머신 터미널에서 다음 명령어를 실행하여 인식기 파일을 만듭니다.
```bash
# scripts 폴더로 이동하여 qr_recognizer.py 파일 열기
cd ~/catkin_ws/src/qr_logistics_robot/scripts
vim qr_recognizer.py
```

### 2.2 코드 붙여넣기
아래 코드를 복사하여 `qr_recognizer.py`에 붙여넣고 저장(`:wq`)합니다. (이 파일 역시 윈도우 환경에 동기화해 두었습니다.)

```python
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
        print("[!] 에러: 이미지를 찾을 수 없거나 열 수 없습니다.")
        sys.exit(1)
        
    # 2. pyzbar를 이용한 QR 코드 디코딩
    decoded_objects = decode(img)
    if not decoded_objects:
        print("[-] 이미지에서 QR 코드를 인식하지 못했습니다.")
        return

    # 3. 인식된 QR 코드 데이터 처리
    for obj in decoded_objects:
        qr_data = obj.data.decode('utf-8')
        print("\n========================================")
        print("[+] QR 코드 인식 성공!")
        print(f"[-] 원본 문자열: {qr_data}")
        print("========================================")
        
        # 4. JSON 파싱
        try:
            logistics_info = json.loads(qr_data)
            print("\n[+] 물류 데이터 파싱 결과:")
            print(f"  ▶ 물품 ID   : {logistics_info.get('item_id', 'N/A')}")
            print(f"  ▶ 목적지 구역: {logistics_info.get('destination', 'N/A')}")
            print(f"  ▶ 목표 좌표 : {logistics_info.get('target_coordinates', 'N/A')}")
            print(f"  ▶ 우선 순위 : {logistics_info.get('priority', 'N/A')}")
        except json.JSONDecodeError:
            print("\n[!] 경고: 인식된 데이터가 유효한 JSON 포맷이 아닙니다.")

if __name__ == "__main__":
    # 모듈 2에서 생성했던 이미지 경로 지정
    default_path = os.path.join(os.path.expanduser('~'), 'catkin_ws', 'src', 'qr_logistics_robot', 'models', 'logistics_qr_1.png')
    recognize_qr(default_path)
```

### 2.3 실행 권한 부여
마찬가지로 ROS 환경에서의 원활한 실행을 위해 실행 권한을 부여합니다.
```bash
chmod +x ~/catkin_ws/src/qr_logistics_robot/scripts/qr_recognizer.py
```

---

## 3. 실행 및 검증 (테스트)

생성해둔 QR 이미지를 스크립트가 제대로 읽고 JSON 데이터를 분리해내는지 테스트합니다.

```bash
# 스크립트 실행
python3 ~/catkin_ws/src/qr_logistics_robot/scripts/qr_recognizer.py
```

### ✅ 성공 기준
스크립트를 실행했을 때 터미널 창에 에러 없이 아래와 같은 형태의 텍스트가 출력되면 완벽하게 성공입니다!

```text
[*] 이미지 로드 중: /home/ubuntu20/catkin_ws/src/qr_logistics_robot/models/logistics_qr_1.png

========================================
[+] QR 코드 인식 성공!
[-] 원본 문자열: {"item_id": "BOX-2026-001", "destination": "A_zone", "target_coordinates": [3.0, 3.0], "priority": "high", "description": "Fragile Electronics"}
========================================

[+] 물류 데이터 파싱 결과:
  ▶ 물품 ID   : BOX-2026-001
  ▶ 목적지 구역: A_zone
  ▶ 목표 좌표 : [3.0, 3.0]
  ▶ 우선 순위 : high
```

*이 스크립트가 정상 작동한다면 1일차 목표인 **"독립적인 모듈 분리를 통한 환경 세팅 및 QR 생성/인식 구현"**이 모두 완료된 것입니다. 다음 단계(2일차 이후)에서는 이 인식기를 ROS Node로 만들어 시뮬레이션 카메라와 연결하는 작업을 진행할 수 있습니다.*
