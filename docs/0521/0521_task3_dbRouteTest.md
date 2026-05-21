# 작업 5: DB 기반 경로 탐색 통합 테스트 가이드

QR 인식 → DB 조회 → Navigation 목표 전송 → 도착 QR 인식까지의  
전체 시나리오를 단계별 확인 포인트와 함께 검증합니다.

---

## 0단계 — QR 모델 6개 생성 (최초 1회)

기존 모델(`qr_arrival`, `qr_box`)은 구버전입니다.  
경량화된 신규 포맷(R001~R003 × START/ARR)으로 모델을 생성합니다.

```bash
cd ~/catkin_ws/src/qr_logistics_robot/scripts
python3 generate_qr_models.py
```

정상 출력 (6줄):
```
=== 서빙로봇 QR 코드 모델 생성 시작 ===
[완료] qr_start_R001 가제보 모델 생성 (경로: .../models/qr_start_R001)
[완료] qr_start_R002 가제보 모델 생성 (경로: .../models/qr_start_R002)
[완료] qr_start_R003 가제보 모델 생성 (경로: .../models/qr_start_R003)
[완료] qr_arrival_R001 가제보 모델 생성 (경로: .../models/qr_arrival_R001)
[완료] qr_arrival_R002 가제보 모델 생성 (경로: .../models/qr_arrival_R002)
[완료] qr_arrival_R003 가제보 모델 생성 (경로: .../models/qr_arrival_R003)
=== 모든 QR 코드 모델이 생성되었습니다 ===
```

생성 확인:
```bash
ls ~/catkin_ws/src/qr_logistics_robot/models/ | grep qr
```

기대 출력 (6개):
```
qr_arrival_R001
qr_arrival_R002
qr_arrival_R003
qr_start_R001
qr_start_R002
qr_start_R003
```

> `qrcode` 모듈 없음 오류 시 → `pip3 install qrcode[pil]` 설치 후 재실행

---

## 사전 확인 (실행 전)

### ✅ CP0-1 — DB 데이터 확인

```bash
cd ~/catkin_ws/src/qr_logistics_robot/db
sqlite3 hospital_rooms.db "SELECT * FROM rooms;"
```

기대 출력:
```
R001|1병실|1.6703|-11.0|-1.5708
R002|2병실|-0.6141|-11.0|-1.5708
R003|3병실|-3.0615|-11.0|-1.5708
```

> 출력이 없거나 오류 발생 시 → `cd ../scripts && python3 init_room_db.py` 재실행

---

### ✅ CP0-2 — QR 모델 파일 확인

```bash
ls ~/catkin_ws/src/qr_logistics_robot/models/ | grep qr
```

기대 출력 (6개):
```
qr_arrival_R001
qr_arrival_R002
qr_arrival_R003
qr_start_R001
qr_start_R002
qr_start_R003
```

> 없을 경우 → 위 **0단계** 를 먼저 실행하세요.

---

### ✅ CP0-3 — QR 인코딩 데이터 육안 확인

```bash
python3 -c "
import json
data = {'id': 'R001', 'type': 'START'}
print(json.dumps(data, separators=(',',':')))
"
```

기대 출력: `{"id":"R001","type":"START"}` (좌표·이름 없음)

---

## 터미널 구성 (총 5개)

> 각 터미널은 새 탭에서 열고, **이전 단계가 완전히 뜬 것을 확인한 후** 다음을 실행합니다.

---

### [터미널 1] Gazebo 실행

```bash
cd ~/catkin_ws && source devel/setup.bash
roslaunch qr_logistics_robot hospital_world.launch
```

#### 🔍 CP1 — Gazebo 정상 구동 확인

```bash
# 새 터미널에서
rostopic list | grep camera
```

기대 출력:
```
/camera/rgb/camera_info
/camera/rgb/image_raw
```

> `/camera` 토픽이 없으면 Gazebo 또는 로봇 스폰 실패 → Gazebo 재시작

---

### [터미널 2] Navigation 스택 실행

```bash
cd ~/catkin_ws && source devel/setup.bash
roslaunch turtlebot3_navigation turtlebot3_navigation.launch \
  map_file:=$(rospack find qr_logistics_robot)/maps/hospital_map.yaml
```

#### 🔍 CP2 — Navigation 스택 준비 확인

```bash
rostopic echo /move_base/status -n 1
```

기대 출력: `status_list` 항목이 출력되면 정상

> `ERROR: Cannot communicate with master` → roscore가 없거나 Gazebo가 아직 안 뜸

**RViz에서 초기 위치 설정 필수**:
1. `2D Pose Estimate` 클릭 → 맵의 `(0, 0)` 위치 클릭 + 정면 방향으로 드래그
2. 파티클이 한 곳으로 모이면 완료

---

### [터미널 3] vision_recognizer_node 실행

```bash
cd ~/catkin_ws && source devel/setup.bash
rosrun qr_logistics_robot vision_recognizer_node.py
```

#### 🔍 CP3 — 카메라 영상 수신 확인

노드 실행 직후 OpenCV 창이 열리고 카메라 화면이 보여야 합니다.

```bash
# 별도 터미널에서 토픽 발행 여부 확인
rostopic hz /camera/rgb/image_raw
```

기대 출력: `average rate: XX Hz` (보통 10~30Hz)

> OpenCV 창이 안 열리면 → `export DISPLAY=:0` 설정 후 재실행

---

### [터미널 4] path_planner_node 실행

```bash
cd ~/catkin_ws && source devel/setup.bash
rosrun qr_logistics_robot path_planner_node.py
```

#### 🔍 CP4 — DB 연결 및 노드 대기 확인

터미널 4에서 아래 두 줄이 출력되어야 합니다:

```
[INFO] 병실 DB 연결 완료: .../db/hospital_rooms.db
[INFO] 경로 탐색 노드가 시작되었습니다. 비전 인식기의 좌표 하달을 기다립니다...
```

> `병실 DB 연결 완료`가 없고 오류 발생 시 → DB 파일 경로 확인:
> ```bash
> ls ~/catkin_ws/src/qr_logistics_robot/db/hospital_rooms.db
> ```

---

## QR 인식 → 주행 시나리오 테스트 (R001 기준)

### Step 1 — Gazebo에 START QR 배치

Gazebo GUI에서:
1. 상단 메뉴 `Insert` → 좌측 모델 목록에서 `qr_start_R001` 선택
2. 로봇 정면 약 **0.3~0.5m** 앞에 배치 (카메라 ROI 중앙에 들어오도록)
3. QR 판이 로봇 카메라를 **정면으로 바라보는 방향**으로 회전

#### 🔍 CP5 — vision_recognizer_node QR 인식 확인

**터미널 3** (vision_recognizer_node)에서:
```
[INFO] =====================================================
[INFO] [배송 시작 QR 감지!] 임무 ID: R001 / 임무: 목적지(으)로 이동
[INFO] =====================================================
```

> `임무: 목적지`로 표시되는 것은 정상 (QR에 name 필드 없음 — 이름은 DB에서 관리)

**토픽 직접 확인**:
```bash
# 터미널 5에서
rostopic echo /target_logistics_info
```

기대 출력:
```
data: '{"id":"R001","type":"START"}'
```

> 토픽이 발행되지 않으면 → QR이 카메라 ROI(주황색 박스) 안에 들어오도록 위치 조정

---

### Step 2 — DB 조회 및 주행 목표 전송 확인

#### 🔍 CP6 — path_planner_node DB 조회 확인

**터미널 4** (path_planner_node)에서:
```
[INFO] >>> [1병실(으)로 이동] 임무를 시작합니다! (목표 좌표: X=1.6703, Y=-11.0, θ=-90.0°)
[INFO] --- 주행 목표(Goal) 실제 전송 완료! ---
```

| 로그 내용 | 의미 |
|-----------|------|
| `1병실(으)로 이동` | DB 조회 성공, name 컬럼 정상 반환 |
| `X=1.6703, Y=-11.0, θ=-90.0°` | DB 좌표 정상 적용 |
| `실제 전송 완료` | move_base 서버 연결 성공 |
| `가상 전송 완료` | move_base 미연결 (Navigation 스택 재확인) |

> **`DB에 ID 'R001'에 해당하는 병실 정보가 없습니다`** 경고 시
> → DB가 비어 있거나 ID 불일치 → CP0-1 재확인 후 `python3 init_room_db.py` 재실행

---

### Step 3 — 로봇 실제 주행 확인

#### 🔍 CP7 — 로봇 이동 확인

```bash
rostopic echo /move_base/status -n 3
```

`status: 1` (ACTIVE) → 주행 중  
`status: 3` (SUCCEEDED) → 목적지 도착

RViz에서 녹색 경로선이 표시되고 로봇이 움직이면 정상입니다.

> 로봇이 움직이지 않으면:
> - `status: 4` (ABORTED) → 경로를 못 찾음 (초기 위치 재설정 후 재시도)
> - `status: 0` → goal 미수신 (CP6 재확인)

---

### Step 4 — ARRIVAL QR 배치 및 배송 완료 확인

로봇이 R001 목적지 근처에 도착하면:

1. Gazebo에서 `qr_arrival_R001` 모델을 **로봇 정면 벽면**에 배치
2. 로봇이 QR을 인식하면 **터미널 3**에서:
   ```
   [INFO] [도착 확인 QR 감지!] 임무 완료 대기 중...
   ```
3. **터미널 4**에서:
   ```
   [INFO] *** 배송 완료! (Task ID: R001) 목적지 QR 인식을 성공했습니다. 대기 상태로 전환합니다. ***
   ```

#### 🔍 CP8 — 배송 완료 상태 확인

```bash
rostopic echo /target_logistics_info
```

`{"id":"R001","type":"ARR"}` 가 발행되면 전체 시나리오 완료

> **`현재 수행 중인 임무(None)와 일치하지 않습니다`** 경고 시
> → START QR 인식 전에 ARR QR이 먼저 인식된 것. START → ARR 순서로 진행 확인

---

## 체크리스트 요약

| 단계 | 확인 포인트 | 확인 방법 |
|------|-------------|-----------|
| CP0-1 | DB 데이터 3개 존재 | `sqlite3 ... SELECT *` |
| CP0-2 | QR 모델 6개 존재 | `ls models/ \| grep qr` |
| CP1 | 카메라 토픽 수신 | `rostopic list \| grep camera` |
| CP2 | Navigation 스택 준비 | `rostopic echo /move_base/status` |
| CP3 | 카메라 영상 OpenCV 창 | 육안 확인 |
| CP4 | DB 연결 로그 출력 | 터미널 4 로그 |
| CP5 | `/target_logistics_info` 발행 | `rostopic echo` |
| CP6 | DB 조회 성공 + Goal 전송 | 터미널 4 로그 |
| CP7 | 로봇 실제 이동 | `move_base/status` + RViz |
| CP8 | 배송 완료 로그 | 터미널 4 로그 |

---

## 자주 발생하는 오류

| 증상 | 원인 | 해결 |
|------|------|------|
| QR 인식이 안 됨 | QR이 ROI 밖에 있음 | 로봇 정면 0.3~0.5m, 카메라 중앙에 배치 |
| `DB에 ID 없습니다` | DB 미생성 또는 ID 오타 | `init_room_db.py` 재실행 |
| `가상 전송 완료` | move_base 미연결 | Navigation 스택(터미널 2) 재확인 |
| 로봇이 안 움직임 | 초기 위치 미설정 | RViz `2D Pose Estimate` 재설정 |
| ARR QR 미인식 | 로봇 방향 불일치 | theta=-90° 기준, 로봇이 -y방향 바라봐야 함 |
