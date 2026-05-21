# 작업 1: 병실 좌표 측정 가이드 (VMware Ubuntu 20.04)

RViz의 **2D Nav Goal** 도구로 각 병실 입구 좌표 `(x, y, theta)`를 측정하고,  
`init_room_db.py`에 기록하는 전체 절차입니다.

---

## 사전 준비

- VMware 게스트 OS: Ubuntu 20.04 (ROS Noetic)
- 워크스페이스 경로: `~/catkin_ws`
- `TURTLEBOT3_MODEL` 환경변수가 `.bashrc`에 설정되어 있어야 함

```bash
# ~/.bashrc에 없다면 추가
echo "export TURTLEBOT3_MODEL=waffle_pi" >> ~/.bashrc
source ~/.bashrc
```

---

## 터미널 구성 (총 3개)

> 각 터미널을 순서대로 실행합니다. 이전 단계가 완전히 뜬 것을 확인한 후 다음 단계로 넘어가세요.

---

### [터미널 1] Gazebo — 병원 월드 실행

```bash
cd ~/catkin_ws
source devel/setup.bash
roslaunch qr_logistics_robot hospital_world.launch
```

- Gazebo GUI가 뜨고 로봇(TurtleBot3 waffle_pi)이 `(0, 0)` 위치에 스폰되면 정상입니다.

---

### [터미널 2] Navigation 스택 — 맵 서버 + AMCL + move_base 실행

```bash
cd ~/catkin_ws
source devel/setup.bash
roslaunch turtlebot3_navigation turtlebot3_navigation.launch \
  map_file:=$(rospack find qr_logistics_robot)/maps/hospital_map.yaml
```

- RViz가 자동으로 열리며 `hospital_map`이 표시됩니다.
- 맵 위에 로봇 위치가 흐릿하게 분산된 빨간 화살표(파티클)로 표시되면 정상입니다.

> **RViz가 자동으로 열리지 않는 경우**  
> 별도 터미널에서 `rviz`를 실행한 뒤 `File > Open Config`로  
> `~/.rviz/nav.rviz` 또는 turtlebot3_navigation 기본 설정을 불러오세요.

---

### [터미널 3] 초기 위치 설정 확인용 (선택)

```bash
cd ~/catkin_ws
source devel/setup.bash
rostopic echo /amcl_pose
```

- 2D Pose Estimate를 지정한 후 이 토픽에서 실제 추정 위치를 확인할 수 있습니다.

---

## RViz에서 초기 위치 설정

좌표 측정 전 로봇의 초기 위치를 맵에 맞춰야 AMCL이 정확히 동작합니다.

1. RViz 상단 툴바에서 **"2D Pose Estimate"** 클릭
2. 맵에서 **로봇이 실제로 있는 위치**(Gazebo 기준 origin `(0, 0)`)를 클릭
3. 클릭한 채로 드래그하여 **로봇 정면 방향**으로 화살표를 맞춘 후 놓기
4. 파티클(빨간 화살표)이 한 곳으로 모이면 초기화 완료

---

## 병실 좌표 측정 방법

### 방법 A — 2D Nav Goal 클릭 (권장)

1. RViz 툴바에서 **"2D Nav Goal"** 클릭
2. 맵에서 **측정할 병실 입구 앞**을 클릭 + 드래그로 도착 방향 지정
   - 드래그 방향 = 로봇이 도착했을 때 바라보는 방향 (ARRIVAL QR 벽면 정면)
3. RViz 하단 상태바에 표시되는 좌표를 기록

```
Goal: Frame:map, Position(2.34, -1.05, 0.00), Orientation(0.00, 0.00, 0.71, 0.71) = Angle: 90.00deg
```

| 항목 | 값 읽는 곳 |
|------|-----------|
| x | `Position(x, ...)` |
| y | `Position(..., y, ...)` |
| theta (rad) | `Angle: N.Ndeg` → 라디안 변환: `deg × π / 180` |

> **theta 변환 예시**  
> `90.00 deg` → `1.5708 rad`  
> `180.00 deg` → `3.1416 rad`  
> `-90.00 deg` → `-1.5708 rad`

---

### 방법 B — /move_base_simple/goal 토픽으로 정확한 값 확인

2D Nav Goal 클릭 직후 다른 터미널에서:

```bash
cd ~/catkin_ws && source devel/setup.bash
rostopic echo /move_base_simple/goal -n 1
```

출력 예시:
```yaml
header:
  frame_id: "map"
pose:
  position:
    x: 2.3412
    y: -1.0521
    z: 0.0
  orientation:
    x: 0.0
    y: 0.0
    z: 0.7071
    w: 0.7071
```

**쿼터니언 → theta(yaw) 변환 공식:**

```
theta = 2 × arctan2(orientation.z, orientation.w)
```

Python으로 계산:
```bash
python3 -c "import math; z=0.7071; w=0.7071; print(round(2*math.atan2(z,w), 4), 'rad')"
```

---

## 측정값 기록표

아래 표를 실제 측정값으로 채운 뒤 `init_room_db.py`에 반영합니다.

| ID | 이름 | x | y | theta (rad) | 비고 |
|----|------|---|---|-------------|------|
| R001 | 1병실 | | | | |
| R002 | 2병실 | | | | |
| R003 | 3병실 | | | | |

---

## init_room_db.py에 좌표 반영 및 DB 생성

측정 완료 후 `init_room_db.py`의 `ROOMS` 리스트를 수정합니다.

```bash
# 파일 열기
nano ~/catkin_ws/src/qr_logistics_robot/scripts/init_room_db.py
```

`ROOMS` 부분을 실제 측정값으로 교체:
```python
ROOMS = [
    ("R001", "1병실",  x값,  y값,  theta값),
    ("R002", "2병실",  x값,  y값,  theta값),
    ("R003", "3병실",  x값,  y값,  theta값),
]
```

저장 후 DB 생성:
```bash
cd ~/catkin_ws/src/qr_logistics_robot/scripts
python3 init_room_db.py
```

정상 출력 예시:
```
DB 초기화 완료: .../db/hospital_rooms.db
  ('R001', '1병실', 2.34, -1.05, 1.5708)
  ('R002', '2병실', ...)
  ('R003', '3병실', ...)
```

---

## 주의사항

- **맵 좌표계 origin**: `hospital_map.yaml`의 origin이 `[-32.4, -21.2, 0]`이므로  
  RViz에서 보이는 좌표는 이미 map frame 기준값입니다. 별도 변환 불필요.
- **2D Nav Goal은 실제 주행을 트리거합니다.** Gazebo에서 로봇이 움직이므로 장애물 없는 경로로 지정하세요.
- **Navigation 스택이 실행 중이지 않으면** 2D Nav Goal 좌표가 상태바에 표시되지 않습니다.  
  반드시 터미널 2(Navigation 스택)가 완전히 뜬 후 측정하세요.
