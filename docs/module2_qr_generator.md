# 모듈 2: QR 코드 생성기 구현 가이드

이 문서는 모듈 1 환경 구축 완료 후, 배송할 물류의 정보를 담고 있는 **QR 코드 이미지를 생성하는 파이썬 스크립트**를 작성하고 테스트하는 과정을 다룹니다.

---

## 1. 개요 및 데이터 구조 설계

배송 로봇이 QR 코드를 스캔했을 때 파싱할 수 있는 정형화된 데이터가 필요합니다. 본 프로젝트에서는 확장성이 좋은 **JSON 형식**을 사용합니다.

**[데이터 포맷 예시]**
```json
{
    "item_id": "BOX-2026-001",
    "destination": "A_zone",
    "target_coordinates": [3.0, 3.0],
    "priority": "high"
}
```

---

## 2. QR 코드 생성 스크립트 작성

미리 생성해둔 `scripts` 폴더에 파이썬 파일을 작성합니다.

### 2.1 스크립트 파일 생성
가상머신 터미널에서 다음 명령어를 실행하여 파일을 만듭니다.
```bash
# 1. scripts 폴더로 이동하여 파일 열기
cd ~/catkin_ws/src/qr_logistics_robot/scripts
vim qr_generator.py
```

### 2.2 코드 붙여넣기
아래 코드를 복사하여 `qr_generator.py`에 붙여넣고 저장(vim의 경우 `:wq`)합니다. (해당 파일은 윈도우 측의 `src/qr_logistics_robot/scripts/` 에도 동기화되어 있습니다.)

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import qrcode
import json
import os

def generate_logistics_qr():
    # 1. 물류 배송에 사용할 데이터 정의
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
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    
    # 4. 데이터 삽입 및 이미지화
    qr.add_data(data_str)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # 5. 저장 경로 설정 (models 폴더 내 저장)
    workspace_path = os.path.join(os.path.expanduser('~'), 'catkin_ws', 'src', 'qr_logistics_robot', 'models')
    if not os.path.exists(workspace_path):
        os.makedirs(workspace_path)
        
    save_path = os.path.join(workspace_path, 'logistics_qr_1.png')
    img.save(save_path)
    
    print(f"[+] QR 코드 생성 완료: {save_path}")

if __name__ == "__main__":
    generate_logistics_qr()
```

### 2.3 실행 권한 부여
ROS 및 리눅스 환경에서 스크립트를 독립적으로 실행하기 위해 실행 권한을 줍니다.
```bash
chmod +x ~/catkin_ws/src/qr_logistics_robot/scripts/qr_generator.py
```

---

## 3. 실행 및 검증 (테스트)

이제 작성한 스크립트를 실행하여 QR 코드 이미지가 정상적으로 생성되는지 테스트합니다.

```bash
# 스크립트 실행
python3 ~/catkin_ws/src/qr_logistics_robot/scripts/qr_generator.py

# [설치/실행 확인] 파일이 정상적으로 생성되었는지 출력
ls -l ~/catkin_ws/src/qr_logistics_robot/models/logistics_qr_1.png
```

### ✅ 성공 기준
1. 터미널 창에 `[+] QR 코드 생성 완료: /home/.../models/logistics_qr_1.png` 메시지가 출력됩니다.
2. 우분투 파일 탐색기에서 `~/catkin_ws/src/qr_logistics_robot/models` 경로로 들어가면 **`logistics_qr_1.png`** 이미지 파일이 보입니다.
3. 해당 이미지를 스마트폰의 기본 카메라 앱으로 비췄을 때, 코드에 작성된 JSON 텍스트 내용이 화면에 나타나면 완벽하게 성공입니다!
