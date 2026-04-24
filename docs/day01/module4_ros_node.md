# 모듈 4: QR 인식기의 ROS Node 변환 및 통신 테스트

이 문서는 단순한 파이썬 스크립트였던 QR 인식기를 **ROS Node**로 격상시켜, 인식한 데이터를 다른 로봇 시스템이 받을 수 있도록 **토픽(Topic)으로 발행(Publish)**하는 과정을 다룹니다.

---

## 1. 개요

로봇 주행 시스템은 QR 데이터가 필요할 때마다 파일을 직접 읽지 않고, 통신 규약인 **ROS Topic**을 구독(Subscribe)하여 데이터를 넘겨받습니다. 이를 위해 기존 코드를 ROS 환경에 맞게 `rospy` 라이브러리를 사용하여 변환합니다.

---

## 2. ROS 노드 스크립트 작성 및 권한 부여

새롭게 작성된 `qr_recognizer_node.py` 파일을 리눅스 가상머신에 생성하고 실행 권한을 줍니다.

### 2.1 스크립트 생성
```bash
# 파일 열기
cd ~/catkin_ws/src/qr_logistics_robot/scripts
vim qr_recognizer_node.py
```
*(윈도우 쪽에 동기화된 `qr_recognizer_node.py` 코드를 그대로 복사해서 붙여넣습니다.)*

### 2.2 권한 부여
```bash
chmod +x qr_recognizer_node.py
```

---

## 3. 실행 및 검증 (ROS 통신 테스트)

이번에는 단순 출력이 아니라 실제로 ROS 네트워크를 통해 데이터가 전송되는지 확인해야 합니다. 따라서 **터미널을 3개 띄워서 작업**합니다.

### [터미널 1] 마스터 노드 실행
ROS 통신의 핵심인 코어를 실행합니다.
```bash
roscore
```

### [터미널 2] QR 인식 퍼블리셔 노드 실행
방금 만든 파이썬 ROS 노드를 구동합니다. 이 노드는 1초에 한 번씩 QR 이미지를 읽어 데이터를 뿜어냅니다.
```bash
cd ~/catkin_ws
source devel/setup.bash
rosrun qr_logistics_robot qr_recognizer_node.py
```
*(터미널 창에 `[INFO] ... QR 인식 완료! 목적지: A_zone ...` 라는 로그가 1초마다 찍혀야 합니다.)*

### [터미널 3] 발행된 데이터(Topic) 구독 확인
실제로 데이터 네트워크망에 해당 데이터가 잘 흘러다니는지 훔쳐보는(Echo) 단계입니다.
```bash
# 발행되고 있는 토픽 리스트 확인
rostopic list

# /target_logistics_info 토픽의 데이터 실시간 확인
rostopic echo /target_logistics_info
```

### ✅ 성공 기준
터미널 3에서 아래와 같이 우리가 JSON으로 감쌌던 데이터가 실시간으로 계속 출력되면 ROS 통신 구현이 완벽히 성공한 것입니다!
```text
data: "{\"item_id\": \"BOX-2026-001\", \"destination\": \"A_zone\", \"target_coordinates\": [3.0, 3.0], \"priority\": \"high\", \"description\": \"Fragile Electronics\"}"
---
```
