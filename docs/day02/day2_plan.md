# 2일차 (Day 2) 세부 진행 계획: 시뮬레이션 카메라 연동 및 주행 기반 마련

## 1. 개요
* **목표**: 1일차에 구축한 독립적인 QR 인식기를 실제 시뮬레이션 로봇 카메라와 연동하고, 인식된 목적지 좌표를 기반으로 주행(Path Planning)을 위한 뼈대를 완성합니다.
* **핵심 방향**: Gazebo 내부에 가상 로봇과 3D QR코드 모델을 배치하여 실제 로봇의 동작 환경과 동일하게 만들고, 실시간 영상 스트리밍을 처리하는 파이프라인을 구축합니다.

---

## 2. 모듈별 상세 계획

### [모듈 5] 시뮬레이션 로봇 및 QR 모델 배치 (Sim Environment Module)
* **목표**: 시뮬레이션 공간에 카메라가 장착된 주행 로봇과 인식 대상인 QR코드 객체 투입
* **세부 작업**:
  1. **로봇 스폰**: TurtleBot3 모델(Waffle Pi 등 카메라 장착 모델 권장)을 기존 1일차의 `logistics.world` 맵에 띄우도록 런치 파일 수정
  2. **QR 객체 생성**: 1일차에 만든 `logistics_qr_1.png`를 텍스처로 입힌 가상의 3D 박스(또는 포스터) 모델을 만들어 Gazebo 맵 내 특정 구역 벽면에 부착
* **독립성/검증**: `roslaunch` 실행 시 맵 안에 로봇과 QR코드가 모두 보이고, 터미널에서 `rostopic list`를 쳤을 때 카메라 관련 토픽(예: `/camera/rgb/image_raw`)이 활성화되어 있어야 합니다.

### [모듈 6] 실시간 카메라 비전 인식기 (Real-time Vision Node)
* **목표**: 로컬 정적 이미지 파일 대신 로봇 카메라의 실시간 영상을 받아 QR을 인식
* **세부 작업**:
  1. 기존 `qr_recognizer_node.py` 구조를 바탕으로 `vision_recognizer_node.py` 생성
  2. ROS의 영상 데이터를 파이썬에서 처리하기 위해 `cv_bridge` 패키지를 사용하여 카메라 토픽(`/camera/rgb/image_raw`)을 Subscribe
  3. 실시간 프레임 단위로 `pyzbar` 디코딩을 수행하고, QR 데이터가 인식되면 1일차와 동일하게 `/target_logistics_info` 토픽으로 파싱된 정보 Publish
* **독립성/검증**: RViz 프로그램을 켜서 로봇의 시야를 확인하며 키보드 조종 노드(Teleop)로 로봇을 회전시켜 QR코드를 바라보게 했을 때, 터미널에 즉각적으로 JSON 파싱 로그가 출력되어야 합니다.

### [모듈 7] 경로 탐색 네비게이션 설계 (Path Planning Logic)
* **목표**: 비전 인식기에서 쏴주는 목적지 좌표를 받아 로봇의 주행 목표 지점(Goal)으로 변환
* **세부 작업**:
  1. `/target_logistics_info` 토픽을 Subscribe 하는 새로운 제어 노드 `path_planner_node.py` 생성
  2. 수신받은 JSON 문자열에서 `target_coordinates` `[x, y]` 값을 추출
  3. ROS Navigation 스택과 통신할 수 있도록, 해당 좌표를 `move_base_msgs/MoveBaseAction`의 Goal 데이터로 포맷팅하여 전달하는 액션 클라이언트 뼈대 작성
* **독립성/검증**: 모듈 6을 통해 로봇이 QR을 바라보는 순간, 모듈 7 노드에서 "목표 좌표 [3.0, 3.0]으로 주행 명령을 하달합니다"라는 로그가 뜨는지 확인합니다.

---

## 3. 진행 순서 및 체크리스트
- [ ] **Step 1**: TurtleBot3 패키지 설치 및 런치 파일에 로봇 모델 스폰(Spawn) 코드 추가
- [ ] **Step 2**: Gazebo용 커스텀 모델(QR 텍스처 박스) 폴더 구성 및 맵 상에 배치
- [ ] **Step 3**: `cv_bridge`를 활용한 `vision_recognizer_node.py` 작성
- [ ] **Step 4**: RViz 구동 및 수동 조작을 통한 실시간 카메라 QR 파싱 연동 테스트
- [ ] **Step 5**: 인식된 좌표로 주행 액션을 구성하는 `path_planner_node.py` 구조 설계
