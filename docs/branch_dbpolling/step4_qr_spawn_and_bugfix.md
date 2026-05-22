# Step 4: QR 월드 배치 자동화 및 버그 수정

## 변경 파일

| 파일 | 변경 내용 |
|------|-----------|
| `scripts/vision_recognizer_node.py` | `qr_type` UnboundLocalError 수정, ROI 크롭 제거 |
| `scripts/spawn_qr_models.py` | **신규** — map↔world 오프셋 자동 보정 후 QR 스폰 |
| `worlds/hospital.world` | QR `<include>` 하드코딩 제거 (스폰 노드로 이관) |

---

## 배경 및 문제

### 문제 1 — vision_recognizer_node UnboundLocalError

ARR QR 인식 시 아래 에러가 반복 발생.

```
UnboundLocalError: local variable 'qr_type' referenced before assignment
  File "vision_recognizer_node.py", line 163, in image_callback
    if qr_data != self.last_published_data or qr_type == 'ARR':
```

**원인**: `qr_type` 변수가 조건문 안쪽(JSON 파싱 블록)에서 처음 할당되는데,
그 조건문의 판단식 자체에서 이미 `qr_type`을 참조했기 때문.

**영향**: 기능(DB 전이, 이동)은 정상 동작하지만 콜백마다 예외가 발생하여
비전 노드가 불안정해지는 잠재적 위험이 있었음.

---

### 문제 2 — QR 월드 좌표 ≠ 실제 로봇 도착 위치

`hospital.world`에 QR 좌표를 rooms DB와 동일한 숫자로 박아 넣어도,
실제 테스트에서 로봇이 QR 위치가 아닌 더 먼 지점으로 이동함.

**원인**: Gazebo **world 프레임**과 ROS Navigation **map 프레임**의 원점이 다를 수 있음.
SLAM으로 지도를 생성할 때 로봇의 시작 위치가 map 원점이 되는데,
이것이 Gazebo world 원점 (0, 0)과 일치하지 않으면 좌표계 오차가 발생.

```
world 프레임:  Gazebo 시뮬레이터 절대 좌표
map   프레임:  SLAM 지도 기반 AMCL 좌표  (navigation goal, amcl_pose)

두 프레임의 원점이 다를 경우:
  QR world 좌표 = rooms DB 좌표  →  실제 로봇 도착 위치와 어긋남
```

---

## 수정 내용

### 1. vision_recognizer_node.py — UnboundLocalError 수정

JSON 파싱(`qr_type` 추출)을 조건문 **앞으로** 이동.

**Before**:
```python
if qr_data != self.last_published_data or qr_type == 'ARR':   # ← qr_type 미정의
    try:
        logistics_info = json.loads(qr_data)
        qr_type = logistics_info.get('type')          # ← 여기서 처음 할당
        ...
    except json.JSONDecodeError:
        ...
```

**After**:
```python
try:
    logistics_info = json.loads(qr_data)
    qr_type = logistics_info.get('type')              # ← 먼저 파싱
except json.JSONDecodeError:
    rospy.logwarn("인식된 데이터가 유효한 JSON 포맷이 아닙니다.")
    qr_type = None

if qr_type is not None and (qr_data != self.last_published_data or qr_type == 'ARR'):
    ...
```

파싱 실패 시 `qr_type = None` → 조건에 `qr_type is not None` 가드 추가.

---

### 2. vision_recognizer_node.py — ROI 크롭 제거

#### 문제

실제 테스트에서 로봇이 목적지에 도착할 때 yaw가 정확히 0°가 아닌 경우(−4.23° 오차 확인),
QR 코드가 카메라 좌측으로 치우쳐 중앙 60% ROI 경계 밖에 걸림 → pyzbar 절반만 인식해 디코딩 실패.

카메라 이미지 분석 결과: QR 패널이 ROI 왼쪽 경계에 걸쳐 잘린 상태로 보임.

#### 수정

`detect_qr` 메서드에서 중앙 60% 크롭을 제거하고 **전체 프레임**을 대상으로 디코딩.
ROI 시각화(주황색 박스 오버레이)도 함께 제거.

**Before**:
```python
x1, y1 = int(w * 0.2), int(h * 0.2)
x2, y2 = int(w * 0.8), int(h * 0.8)
roi = cv_image[y1:y2, x1:x2]
gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
...
return results, (x1, y1), scale   # roi_offset = (x1, y1)
```

**After**:
```python
gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)   # 전체 프레임 사용
...
return results, (0, 0), scale   # roi_offset = (0, 0) 고정
```

바운딩 박스 역변환(`int(p.x / s) + ox`)은 `ox=0`이므로 기존 코드와 호환.

---

### 3. spawn_qr_models.py — 신규 스폰 노드

#### 동작 흐름

```
노드 시작
  └─ /gazebo/spawn_sdf_model, /gazebo/get_model_state 서비스 대기
       └─ 오프셋 결정
            ├─ ~map_to_world_offset_x/y 파라미터 지정 시 → 수동 오프셋 사용
            └─ 미지정 시 → 자동 계산
                  ├─ /gazebo/get_model_state → 로봇 world 좌표 취득
                  └─ /amcl_pose 수신 (최대 15초) → 로봇 map 좌표 취득
                       offset = world_pos − map_pos
       └─ rooms DB 읽기 (id, x, y, theta)
            └─ 각 병실마다:
                  qr_map  = (room_x + 0.4·cos(theta), room_y + 0.4·sin(theta))
                  qr_world = qr_map + offset
                  /gazebo/spawn_sdf_model(qr_arrival_{room_id}, pose=qr_world)
```

#### 핵심 파라미터

| ROS 파라미터 | 기본값 | 설명 |
|---|---|---|
| `~robot_model_name` | `turtlebot3_waffle_pi` | Gazebo 모델명 |
| `~map_to_world_offset_x` | 미지정(자동) | world−map x 오프셋 (m) |
| `~map_to_world_offset_y` | 미지정(자동) | world−map y 오프셋 (m) |

#### QR 배치 규칙

- 도착 지점(nav goal) 기준 **theta 방향으로 0.7 m 앞**에 배치 (테스트로 확정)
- 수직 배치 (pitch = −π/2): +z 면이 −x 방향을 향함 → 로봇 카메라 정면
- z = 0.1 m (바닥 위 중심)

---

### 3. hospital.world — QR 하드코딩 제거

world 파일에 직접 삽입했던 `<include>` 블록 3개를 제거.
QR 배치는 전적으로 `spawn_qr_models.py`가 담당.

---

## VMware 실행

### 사전 준비

```bash
cd ~/catkin_ws/src/qr_logistics_robot

# DB 재생성
rm -f db/hospital_rooms.db
python3 scripts/init_room_db.py

# QR 모델 재생성
python3 scripts/generate_qr_models.py
```

### 노드 실행 (터미널 5개)

```bash
# 터미널 1 — Gazebo
roslaunch qr_logistics_robot hospital_world.launch

# 터미널 2 — Navigation (AMCL 포함)
roslaunch turtlebot3_navigation turtlebot3_navigation.launch \
  map_file:=$(rospack find qr_logistics_robot)/maps/hospital_map.yaml

# 터미널 3 — QR 스포너  ★ navigation 기동 후, 로봇 정지 상태에서 실행
rosrun qr_logistics_robot spawn_qr_models.py

# 터미널 4 — 비전
rosrun qr_logistics_robot vision_recognizer_node.py

# 터미널 5 — 경로 플래너
rosrun qr_logistics_robot path_planner_node.py
```

> **주의**: 터미널 3은 반드시 로봇이 초기 위치(0, 0)에 **정지해 있을 때** 실행.
> 이동 중에 실행하면 offset 계산이 부정확해진다.

### 오프셋 수동 지정 (AMCL 없이 실행할 때)

navigation 없이 Gazebo만 띄운 상태에서 테스트하거나,
자동 계산 offset이 부정확할 때 직접 값을 넣는다.

```bash
# 오프셋 측정 방법:
# 1. navigation + Gazebo 실행 후 로봇 초기 위치에서
# 2. rostopic echo /amcl_pose          → map 좌표 (x, y) 확인
# 3. rosservice call /gazebo/get_model_state ...  → world 좌표 확인
# 4. offset = world - map

rosrun qr_logistics_robot spawn_qr_models.py \
  _map_to_world_offset_x:=<dx값> \
  _map_to_world_offset_y:=<dy값>
```

---

## 확인 포인트

| 단계 | 기대 로그 (spawn_qr_models) |
|------|---------------------------|
| 서비스 연결 | `Gazebo 서비스 대기 중...` |
| 오프셋 계산 | `world(0.000,0.000) - map(0.012,-0.003) → 오프셋 dx=-0.012, dy=0.003` |
| 스폰 완료 | `스폰: qr_arrival_R001  world(2.058, -11.000)` |
| | `스폰: qr_arrival_R002  world(-0.222, -11.000)` |
| | `스폰: qr_arrival_R003  world(-2.672, -11.000)` |
| | `모든 QR 모델 스폰 완료.` |

Gazebo 화면에서 각 병실 앞 0.4 m 지점에 흰색 QR 패널이 수직으로 서 있어야 한다.

---

## 미결 사항

| 항목 | 현황 |
|------|------|
| 복귀 중 ARR QR 재인식 | 배송 완료 후 복귀 시 QR 앞을 지나며 중복 publish 발생 — path_planner가 경고 후 무시하므로 기능 이상 없음. 추후 vision_recognizer_node에 ARR 쿨다운 추가 검토 |
| spawn_qr_models를 launch 파일에 통합 | 현재는 수동 실행 — navigation 기동 타이밍 의존성 때문에 분리 유지 |
| map-world offset TF 기반 자동화 | 현재는 시작 위치 1회 샘플링 — 추후 `map`→`odom`→`base_link` TF 체인 사용 가능 |
