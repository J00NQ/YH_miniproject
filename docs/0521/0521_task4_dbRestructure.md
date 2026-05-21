# 작업 4: DB 재구성 가이드 — 단일 START QR + orders 큐

START QR을 3개 → 1개로 통합하고, 배송 순서를 `orders` 테이블로 관리하도록  
DB와 관련 스크립트를 재구성합니다.

---

## 변경 요약

| 항목 | 변경 전 | 변경 후 |
|------|---------|---------|
| START QR 수 | 3개 (`qr_start_R001~R003`) | 1개 (`qr_start`) |
| START QR 데이터 | `{"id":"R001","type":"START"}` | `{"type":"START"}` |
| 목적지 결정 방식 | QR의 id → rooms 직접 조회 | orders 큐 → rooms 조인 조회 |
| DB 테이블 | `rooms` 1개 | `rooms` + `orders` 2개 |
| ARR QR | 변경 없음 (R001~R003 × 3개 유지) | 변경 없음 |

---

## Step 1 — DB 재생성

`init_room_db.py`가 `orders` 테이블을 포함하도록 이미 수정되어 있습니다.  
기존 DB를 삭제하고 새로 생성합니다.

```bash
cd ~/catkin_ws/src/qr_logistics_robot

# 기존 DB 삭제
rm -f db/hospital_rooms.db

# DB 재생성
python3 scripts/init_room_db.py
```

정상 출력:
```
DB 초기화 완료: .../db/hospital_rooms.db

[rooms]
  ('R001', '1병실', 1.6703, -11.0, -1.5708)
  ('R002', '2병실', -0.6141, -11.0, -1.5708)
  ('R003', '3병실', -3.0615, -11.0, -1.5708)

[orders]
  (1, 'R001', 'pending')
  (2, 'R002', 'pending')
  (3, 'R003', 'pending')
```

---

## Step 2 — orders 테이블 내용 확인 및 관리

### 현재 큐 상태 확인

```bash
sqlite3 ~/catkin_ws/src/qr_logistics_robot/db/hospital_rooms.db \
  "SELECT seq, room_id, status FROM orders;"
```

### 작업 큐 초기화 (테스트 재시작 시)

모든 작업을 pending으로 되돌립니다:

```bash
sqlite3 ~/catkin_ws/src/qr_logistics_robot/db/hospital_rooms.db \
  "UPDATE orders SET status='pending';"
```

### 작업 추가 (특정 병실 추가 배송)

```bash
sqlite3 ~/catkin_ws/src/qr_logistics_robot/db/hospital_rooms.db \
  "INSERT INTO orders (room_id, status) VALUES ('R001', 'pending');"
```

### 특정 작업만 취소

```bash
sqlite3 ~/catkin_ws/src/qr_logistics_robot/db/hospital_rooms.db \
  "UPDATE orders SET status='done' WHERE seq=2;"
```

---

## Step 3 — QR 모델 재생성 (4개로 축소)

`generate_qr_models.py`가 단일 START QR 포맷으로 수정되어 있습니다.

```bash
cd ~/catkin_ws/src/qr_logistics_robot/scripts
python3 generate_qr_models.py
```

정상 출력 (4줄):
```
=== 서빙로봇 QR 코드 모델 생성 시작 ===
[완료] qr_start 가제보 모델 생성
[완료] qr_arrival_R001 가제보 모델 생성
[완료] qr_arrival_R002 가제보 모델 생성
[완료] qr_arrival_R003 가제보 모델 생성
=== 모든 QR 코드 모델이 생성되었습니다 ===
```

생성 확인:
```bash
ls ~/catkin_ws/src/qr_logistics_robot/models/ | grep qr
```

기대 출력 (4개):
```
qr_arrival_R001
qr_arrival_R002
qr_arrival_R003
qr_start
```

> 구버전 `qr_start_R001~R003` 폴더가 남아 있어도 동작에 무관합니다.  
> 정리하려면: `rm -rf models/qr_start_R001 models/qr_start_R002 models/qr_start_R003`

---

## Step 4 — 노드 실행 및 동작 확인

```bash
# 터미널 1: Gazebo
cd ~/catkin_ws && source devel/setup.bash
roslaunch qr_logistics_robot hospital_world.launch

# 터미널 2: Navigation
cd ~/catkin_ws && source devel/setup.bash
roslaunch turtlebot3_navigation turtlebot3_navigation.launch \
  map_file:=$(rospack find qr_logistics_robot)/maps/hospital_map.yaml

# 터미널 3: vision_recognizer_node
cd ~/catkin_ws && source devel/setup.bash
rosrun qr_logistics_robot vision_recognizer_node.py

# 터미널 4: path_planner_node
cd ~/catkin_ws && source devel/setup.bash
rosrun qr_logistics_robot path_planner_node.py
```

---

## Step 5 — 시나리오 검증

### START QR 인식 시 기대 로그 (path_planner_node)

```
[INFO] >>> [배송 시작] 1병실(으)로 이동합니다! (seq=1, X=1.6703, Y=-11.0, θ=-90.0°)
[INFO] --- 주행 목표(Goal) 실제 전송 완료! ---
```

orders 상태 확인:
```bash
sqlite3 ~/catkin_ws/src/qr_logistics_robot/db/hospital_rooms.db \
  "SELECT * FROM orders;"
# seq=1이 active, seq=2,3은 pending
```

### ARRIVAL QR 인식 시 기대 로그

```
[INFO] *** 배송 완료! (seq=1, 목적지=R001) 대기 상태로 전환합니다. ***
```

orders 상태 확인:
```bash
sqlite3 ~/catkin_ws/src/qr_logistics_robot/db/hospital_rooms.db \
  "SELECT * FROM orders;"
# seq=1이 done, seq=2가 다음 pending
```

### 연속 배송 (START QR 재인식)

`qr_start`를 다시 인식시키면 `seq=2` (R002) 작업이 자동으로 시작됩니다.

---

## 주요 변경점 요약

| 파일 | 변경 내용 |
|------|-----------|
| `init_room_db.py` | `orders` 테이블 추가, 초기 pending 데이터 3건 삽입 |
| `path_planner_node.py` | START: orders 큐 조회 + active 전환 / ARR: done 전환 |
| `generate_qr_models.py` | START QR 3개 → 1개 (`qr_start`) |
