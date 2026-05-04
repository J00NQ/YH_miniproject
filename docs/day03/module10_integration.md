# 모듈 10: QR 연동 기반 자율 이동 로직 통합

이 문서는 여태까지 1~3일차에 걸쳐 개발한 모든 모듈(비전 인식, 경로 탐색, Navigation 스택)을 하나로 묶어, **"카메라에 QR 코드가 포착되면 로봇이 스스로 물류 배송을 출발하는"** 최종 시스템 통합 시나리오를 다룹니다.

---

## 1. 개요
* 파이썬 코드를 추가로 수정할 필요는 없습니다. (2일차 모듈 7에서 만들었던 `path_planner_node.py`가 이미 주행 서버의 가동을 기다리도록 똑똑하게 설계되어 있습니다.)
* **시스템 데이터 흐름**:
  1. Gazebo 가상 카메라 영상 송출
  2. `vision_recognizer_node`: 영상 속 QR 해독 ➡️ 목적지 정보 토픽 발행
  3. `path_planner_node`: 목적지 수신 ➡️ 좌표로 변환 ➡️ 주행 서버에 Goal 하달
  4. `move_base` (Navigation): 자율 주행 시작 및 장애물 회피

---

## 2. 통합 시나리오 테스트 방법

총 4개의 터미널이 필요합니다. 
*(이전 모듈에서 켜두었던 Gazebo와 Navigation 터미널이 있다면 끄지 말고 그대로 재사용하시면 됩니다.)*

### [터미널 1] 시뮬레이션 환경 (유지)
```bash
roslaunch qr_logistics_robot logistics_world.launch
```

### [터미널 2] Navigation 스택 및 초기 위치 설정 (유지)
```bash
roslaunch turtlebot3_navigation turtlebot3_navigation.launch map_file:=$HOME/catkin_ws/src/qr_logistics_robot/maps/logistics_map.yaml
```
* **⚠️ 필수 주의사항**: RViz에서 `2D Pose Estimate`를 사용해 로봇의 초기 위치가 현재 실제 위치와 딱 일치하도록 반드시 맞춰주셔야 합니다!

### [터미널 3] 실시간 비전 인식 노드 가동
이제 로봇의 "눈"을 켭니다.
```bash
cd ~/catkin_ws
source devel/setup.bash
rosrun qr_logistics_robot vision_recognizer_node.py
```

### [터미널 4] 경로 탐색(주행 명령 하달) 노드 가동
눈에서 받은 정보를 주행 서버로 넘겨주는 "두뇌"를 켭니다.
```bash
cd ~/catkin_ws
source devel/setup.bash
rosrun qr_logistics_robot path_planner_node.py
```

---

## 3. 작동 검증 (체크포인트 3)

모든 터미널이 에러 없이 대기 상태라면, **새 터미널을 열어 키보드 조종 노드(`rosrun turtlebot3_teleop turtlebot3_teleop_key`)를 켜거나 Gazebo 화면에서 로봇을 살짝 돌려 로봇 카메라 시야에 QR 박스가 들어오게 만들어 줍니다.**

### ✅ 성공 시나리오 (자동화의 완성!)
1. 카메라 시야에 QR 코드가 포착되는 즉시, [터미널 3]에서 목적지를 파싱했다는 로그가 번개처럼 지나갑니다.
2. 찰나의 순간, [터미널 4]에서 `>>> [A_zone] 구역으로 주행 명령을 하달합니다!` 로그가 출력되며 `move_base`로 Goal 좌표를 쏘아 보냅니다.
3. 마우스 클릭(`2D Nav Goal`)을 전혀 하지 않았음에도 불구하고, **RViz 상에 초록색 경로가 쫙 뻗어나가며 로봇이 스스로 목적지 좌표를 향해 주행을 시작**합니다!

이 모든 과정이 사람의 마우스 개입 없이 QR 인식만으로 물 흐르듯 한 번에 진행된다면 대성공입니다! 이 짜릿한 통합 테스트를 진행해 보시고 결과를 알려주세요!
