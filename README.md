# QR 코드 기반 병원 물류 배송 로봇 시스템

병원 내 반복 배송 업무를 자동화하는 ROS 기반 시뮬레이션 프로젝트.  
웹 대시보드에서 주문을 입력하면 TurtleBot3가 병실을 순차 배송하고, QR 인식 후 자동 복귀합니다.

## 기술 스택

| 구분 | 내용 |
|------|------|
| 시뮬레이션 | ROS Noetic, Gazebo 11, TurtleBot3 waffle_pi |
| 자율 주행 | AMCL, move_base (TurtleBot3 Navigation Stack) |
| 인식 | OpenCV, pyzbar (2단계 QR 감지) |
| 데이터 | SQLite3 (rooms / orders / robot 테이블) |
| 웹 | Flask, Jinja2, qrcode[pil] |
| 개발 환경 | Ubuntu 20.04 (VMware), Python 3.8 |

## 디렉터리 구조

```
mini_project/
├── src/qr_logistics_robot/
│   ├── scripts/
│   │   ├── init_room_db.py          # DB 초기화
│   │   ├── generate_qr_models.py    # QR 모델 SDF 생성
│   │   ├── spawn_qr_models.py       # Gazebo QR 자동 배치
│   │   ├── vision_recognizer_node.py
│   │   └── path_planner_node.py
│   ├── launch/hospital_world.launch
│   ├── maps/hospital_map.yaml
│   ├── models/qr_arrival/
│   └── worlds/hospital.world
└── web/                             # Flask 대시보드
    ├── app.py
    ├── requirements.txt
    ├── templates/
    └── static/
```

## 실행 방법

### 1. 사전 준비

```bash
cd ~/catkin_ws/src/qr_logistics_robot

# DB 초기화 및 QR 모델 생성
python3 scripts/init_room_db.py
python3 scripts/generate_qr_models.py

# web 의존성 설치
pip3 install --user -r web/requirements.txt
```

### 2. 노드 실행 (터미널 5개)

```bash
# T1 — Gazebo
roslaunch qr_logistics_robot hospital_world.launch

# T2 — Navigation (AMCL + move_base)
roslaunch turtlebot3_navigation turtlebot3_navigation.launch \
  map_file:=$(rospack find qr_logistics_robot)/maps/hospital_map.yaml

# T3 — QR 스포너 (로봇 정지 상태에서 실행)
rosrun qr_logistics_robot spawn_qr_models.py

# T4 — 비전 인식
rosrun qr_logistics_robot vision_recognizer_node.py

# T5 — 경로 플래너 (DB 폴링)
rosrun qr_logistics_robot path_planner_node.py
```

### 3. 웹 대시보드

```bash
python3 ~/catkin_ws/src/qr_logistics_robot/web/app.py
# → http://localhost:5000
```

대시보드에서 주문을 추가하면 로봇이 자동으로 배송을 시작합니다.

## 동작 흐름

```
웹 대시보드에서 주문 추가 (pending)
  → path_planner_node가 5초마다 DB 폴링
  → pending 주문 감지 → 목적지로 이동 (active)
  → 병실 도착 → QR 코드 인식
  → 배송 완료 (done) → 홈 복귀
  → 대기 상태 전환 → 다음 주문 자동 처리
```
