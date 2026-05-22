# Web Step 4: 시연 시나리오 (데모 영상)

## 시연 목표

웹 대시보드에서 주문을 입력하면 로봇이 자율 주행으로 병실을 순차 배송하고,  
QR 인식 후 홈 복귀까지 전 과정을 한 화면에서 보여준다.

---

## 사전 준비

### DB 초기화 및 QR 모델 생성

```bash
cd ~/catkin_ws/src/qr_logistics_robot

# DB 초기화 (orders 비어있는 상태로 시작)
rm -f db/hospital_rooms.db
python3 scripts/init_room_db.py

# QR 모델 SDF 파일 생성
python3 scripts/generate_qr_models.py
```

### 터미널 배치 (총 5개)

| 터미널 | 역할 |
|--------|------|
| T1 | Gazebo 월드 |
| T2 | Navigation (AMCL + move_base) |
| T3 | QR 스포너 |
| T4 | 비전 인식 노드 |
| T5 | 경로 플래너 노드 (DB 폴링) |

---

## 실행 순서

### T1 — Gazebo 실행

```bash
source ~/catkin_ws/devel/setup.bash
roslaunch qr_logistics_robot hospital_world.launch
```

> Gazebo가 완전히 기동될 때까지 대기

### T2 — Navigation 실행

```bash
source ~/catkin_ws/devel/setup.bash
roslaunch turtlebot3_navigation turtlebot3_navigation.launch \
  map_file:=$(rospack find qr_logistics_robot)/maps/hospital_map.yaml
```

> RViz에서 로봇 위치 확인 후 2D Pose Estimate로 초기 위치 설정

### T3 — QR 스포너 (로봇 정지 상태에서 실행)

```bash
source ~/catkin_ws/devel/setup.bash
rosrun qr_logistics_robot spawn_qr_models.py
```

> `모든 QR 모델 스폰 완료.` 로그 확인 후 다음 진행

### T4 — 비전 인식 노드

```bash
source ~/catkin_ws/devel/setup.bash
rosrun qr_logistics_robot vision_recognizer_node.py
```

### T5 — 경로 플래너 노드

```bash
source ~/catkin_ws/devel/setup.bash
rosrun qr_logistics_robot path_planner_node.py
```

> `경로 탐색 노드 시작. 5초마다 DB를 폴링합니다...` 확인

### 웹 대시보드 실행

```bash
python3 ~/catkin_ws/src/qr_logistics_robot/web/app.py
```

> 브라우저에서 `http://localhost:5000` 접속

---

## 시연 흐름

### 1단계 — 초기 상태 확인 (카메라: 웹 브라우저)

대시보드(`/`) 접속 → 로봇 상태 **대기**, 주문 없음 확인

### 2단계 — 주문 입력 (카메라: 웹 브라우저)

주문 관리(`/orders`) → **새 주문 추가**
- 1병실(R001) 추가 → `pending` 상태 확인
- 2병실(R002) 추가 → `pending` 상태 확인
- 3병실(R003) 추가 → `pending` 상태 확인

### 3단계 — 자율 배송 시작 (카메라: Gazebo + 웹)

5초 이내 path_planner 폴링 → 로봇 자동 출발

```
[기대 로그 — T5]
[robot.status] → 이동중
>>> [배송 시작] 1병실(으)로 이동합니다! (seq=1)
```

웹 대시보드 새로고침 → 로봇 상태 **이동중**, orders seq=1 **active** 확인

### 4단계 — 병실 도착 및 QR 인식 (카메라: Gazebo 카메라 뷰 or OpenCV 창)

로봇이 R001 앞 정지 → vision 노드 QR 감지

```
[기대 로그 — T4]
=====================================================
[도착 확인 QR 감지!] 수령 확인 처리 중...
=====================================================

[기대 로그 — T5]
*** 배송 완료! (seq=1) 홈으로 복귀합니다. ***
[robot.status] → 복귀
```

### 5단계 — 홈 복귀 및 자동 연속 배송 (카메라: Gazebo)

홈 도착 → 로봇 상태 **대기** 전환 → 다음 폴링에서 R002 자동 출발

```
[기대 로그 — T5]
=== 홈 복귀 완료. 대기 상태로 전환합니다. ===
[robot.status] → 이동중   ← R002 자동 출발
```

R002, R003도 동일하게 반복

### 6단계 — 완료 확인 (카메라: 웹 브라우저)

웹 대시보드 → 로봇 상태 **대기**, 전체 주문 **done** 확인

---

## 촬영 포인트 요약

| 장면 | 촬영 대상 | 핵심 확인 요소 |
|------|-----------|----------------|
| 초기 상태 | 웹 대시보드 | 로봇 대기, 주문 없음 |
| 주문 입력 | 웹 주문 관리 | pending 3건 생성 |
| 로봇 출발 | Gazebo 뷰 | 자동 이동 시작 |
| QR 인식 | OpenCV 창 (`Robot Camera Vision`) | 바운딩 박스 + `ARRIVAL` 텍스트 |
| 상태 전이 | 웹 대시보드 | active → done, 이동중 → 복귀 → 대기 |
| 연속 배송 | T5 터미널 로그 | R001 → R002 → R003 자동 순환 |
| 최종 완료 | 웹 대시보드 | 전체 done 확인 |

---

## DB 실시간 확인 (선택)

터미널에서 주문·로봇 상태를 1초마다 출력:

```bash
watch -n 1 'sqlite3 ~/catkin_ws/src/qr_logistics_robot/db/hospital_rooms.db \
  "SELECT r.status AS robot, o.seq, o.room_id, o.status AS order_status \
   FROM robot r, orders o ORDER BY o.seq;"'
```
