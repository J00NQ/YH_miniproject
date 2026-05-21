# Step 3: path_planner_node.py — DB 폴링 자율 운행 구현

## 변경 파일

| 파일 | 변경 내용 |
|------|-----------|
| `path_planner_node.py` | START 핸들러 제거, 폴링 타이머 추가, 상태 전이, 홈 복귀 |
| `vision_recognizer_node.py` | START QR 로그 분기 제거 |

---

## 운행 흐름

```
노드 시작
  └─ 5초마다 _poll_orders 실행
       └─ robot.status == '대기' + pending 작업 있음
            → orders: pending → active
            → robot:  대기   → 이동중
            → send_goal(목적지)

ARR QR 인식 (_arr_callback)
  └─ orders: active → done
     robot:  이동중 → 복귀
     send_goal(home, done_cb=_on_home_arrived)

move_base SUCCEEDED (_on_home_arrived)
  └─ robot: 복귀 → 대기
     → 폴링 재개
```

---

## 주요 변경 내용

### 1. START QR 핸들러 제거

기존 `target_callback`의 `qr_type == 'START'` 분기를 완전히 제거했습니다.  
출발 트리거는 `rospy.Timer` 폴링이 담당합니다.

---

### 2. `_poll_orders` — 5초 폴링 타이머

```python
rospy.Timer(rospy.Duration(5.0), self._poll_orders)
```

- `robot.status != '대기'`면 즉시 return (이동중/복귀 중 출발 차단)
- pending 작업 없으면 조용히 return
- pending 발견 시: `orders.status → active`, `robot.status → 이동중`, `send_goal(목적지)`

---

### 3. `_arr_callback` — ARR QR 수신 처리

ARR 타입이 아닌 QR은 무시하도록 `target_callback`에서 `_arr_callback`으로 분리했습니다.

```
ARR QR 수신
  → current_order_seq 없으면 경고 후 return
  → orders.status = 'done'
  → robot.status  = '복귀'
  → _send_home_goal() 호출
```

---

### 4. `_send_home_goal` + `_on_home_arrived`

홈 복귀는 `done_cb`를 등록하여 move_base 결과를 비동기로 수신합니다.

```python
self._send_goal(home_x, home_y, home_theta, done_cb=self._on_home_arrived)

def _on_home_arrived(self, state, result):
    if state == GoalStatus.SUCCEEDED:
        robot.status = '대기'   # 폴링 재개
    else:
        logwarn("홈 복귀 실패 — 수동 확인 필요")
```

홈 좌표는 코드에 하드코딩하지 않고 **DB `robot` 테이블에서 조회**합니다.

---

### 5. `_set_robot_status` / `_get_robot_status` 헬퍼

상태 변경마다 로그를 출력하고 DB를 즉시 커밋합니다.  
노드가 재시작되어도 DB에서 마지막 상태를 복원할 수 있습니다.

---

## DB 상태 전이 요약

| 이벤트 | orders.status | robot.status |
|--------|--------------|--------------|
| 폴링 — pending 발견 | pending → active | 대기 → 이동중 |
| ARR QR 인식 | active → done | 이동중 → 복귀 |
| 홈 도착 (move_base SUCCEEDED) | 변경 없음 | 복귀 → 대기 |

---

## VMware 실행

### 사전 준비

```bash
cd ~/catkin_ws/src/qr_logistics_robot

# DB 재생성 (robot 테이블 포함)
rm -f db/hospital_rooms.db
python3 scripts/init_room_db.py

# QR 모델 재생성 (qr_arrival 1개)
python3 scripts/generate_qr_models.py
```

### 노드 실행 (터미널 4개)

```bash
# 터미널 1
cd ~/catkin_ws && source devel/setup.bash
roslaunch qr_logistics_robot hospital_world.launch

# 터미널 2
cd ~/catkin_ws && source devel/setup.bash
roslaunch turtlebot3_navigation turtlebot3_navigation.launch \
  map_file:=$(rospack find qr_logistics_robot)/maps/hospital_map.yaml

# 터미널 3
cd ~/catkin_ws && source devel/setup.bash
rosrun qr_logistics_robot vision_recognizer_node.py

# 터미널 4
cd ~/catkin_ws && source devel/setup.bash
rosrun qr_logistics_robot path_planner_node.py
```

---

## 확인 포인트

| 단계 | 기대 로그 (path_planner_node) |
|------|-------------------------------|
| 노드 시작 | `경로 탐색 노드 시작. 5초마다 DB를 폴링합니다...` |
| 폴링 — 출발 | `[robot.status] → 이동중` |
| | `>>> [배송 시작] 1병실(으)로 이동합니다! (seq=1, ...)` |
| ARR QR 인식 | `*** 배송 완료! (seq=1, 목적지=R001) 홈으로 복귀합니다. ***` |
| | `[robot.status] → 복귀` |
| 홈 도착 | `=== 홈 복귀 완료. 대기 상태로 전환합니다. ===` |
| | `[robot.status] → 대기` |
| 다음 폴링 | `[robot.status] → 이동중` (R002 자동 출발) |

### robot 테이블 실시간 확인

```bash
watch -n 2 'sqlite3 ~/catkin_ws/src/qr_logistics_robot/db/hospital_rooms.db \
  "SELECT r.status, o.seq, o.room_id, o.status FROM robot r, orders o ORDER BY o.seq;"'
```

---

## 미결 사항

| 항목 | 현황 |
|------|------|
| move_base ABORTED 시 robot.status 처리 | 복귀 상태로 고착 가능 — 추후 재시도 로직 필요 |
| orders 전체 done 후 신규 작업 추가 방법 | sqlite3 직접 INSERT 또는 추후 웹 UI |
