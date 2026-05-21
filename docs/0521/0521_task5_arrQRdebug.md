# 작업 5: ARRIVAL QR 조기 인식 방지 디버깅

도착 전 이동 중 ARRIVAL QR이 조기 인식되는 문제를 분석하고,  
목적지 theta를 0°로 변경하여 카메라 방향을 조정합니다.

---

## 문제 분석

### 기존 설정 (theta = -90°)

```
로봇 이동 방향 →
                    [ARRIVAL QR]
                         |
                         ↓ (벽면)
            로봇 ──────────→ 목적지
                  카메라가 이동 방향(+x)을 향함
```

theta = -90°(-1.5708 rad)로 설정 시, 로봇이 목적지에 도착하면서  
**-y 방향(측면)**으로 회전하려 합니다.  
회전 중 또는 접근 중 ARRIVAL QR이 카메라 시야에 조기 진입할 수 있습니다.

### 변경 설정 (theta = 0°)

theta = 0°로 변경하면, 로봇은 목적지에서 **+x 방향 정면**을 향해 정지합니다.  
도착 후 로봇이 회전하지 않으므로 이동 중 불필요한 카메라 방향 변화가 없습니다.  
ARRIVAL QR을 **+x 방향 벽면**에 배치하면 도착 직후에만 인식됩니다.

---

## Step 1 — DB 재생성

`init_room_db.py`의 theta가 `0.0`으로 이미 수정되어 있습니다.  
기존 DB를 삭제하고 재생성합니다.

```bash
cd ~/catkin_ws/src/qr_logistics_robot

# 기존 DB 삭제
rm -f db/hospital_rooms.db

# DB 재생성
python3 scripts/init_room_db.py
```

정상 출력 확인:
```
[rooms]
  ('R001', '1병실', 1.6703, -11.0, 0.0)
  ('R002', '2병실', -0.6141, -11.0, 0.0)
  ('R003', '3병실', -3.0615, -11.0, 0.0)

[orders]
  (1, 'R001', 'pending')
  (2, 'R002', 'pending')
  (3, 'R003', 'pending')
```

---

## Step 2 — Gazebo ARRIVAL QR 배치 방향 변경

theta=0° 기준으로 로봇은 목적지에서 **+x 방향**을 향해 정지합니다.  
ARRIVAL QR을 목적지 기준 **+x 방향 벽면**에 배치합니다.

```
          +x →
로봇 정지 위치  →  [ARRIVAL QR 부착 벽면]
(x=1.6703, y=-11.0)
```

기존에 -y 방향 벽면에 배치했던 QR은 +x 방향 벽면으로 이동 필요.

---

## Step 3 — 노드 재시작 및 테스트

```bash
# path_planner_node 재시작 (Ctrl+C 후)
cd ~/catkin_ws && source devel/setup.bash
rosrun qr_logistics_robot path_planner_node.py
```

START QR 인식 시 기대 로그:
```
[INFO] >>> [배송 시작] 1병실(으)로 이동합니다! (seq=1, X=1.6703, Y=-11.0, θ=0.0°)
```

---

## 확인 포인트

| 항목 | 확인 방법 |
|------|-----------|
| theta=0° 적용 여부 | `path_planner_node` 로그에서 `θ=0.0°` 확인 |
| 도착 전 ARR 인식 여부 | 이동 중 `vision_recognizer_node`에서 ARR 로그 미출력 확인 |
| 도착 후 ARR 인식 여부 | 정지 후 `path_planner_node`에서 배송 완료 로그 확인 |

---

## 추가 고려사항

theta=0°로도 조기 인식 문제가 지속되면 아래 방법을 추가 적용합니다.

**방법 A — move_base 도착 이벤트 기반 ARR 인식 활성화**
- `path_planner_node`에서 move_base `SUCCEEDED` 상태 수신 후
- `/arr_detection_enabled` 토픽 발행 → `vision_recognizer_node`가 구독하여 ARR 인식 ON/OFF

**방법 B — 거리 기반 ARR 인식 게이팅**
- `vision_recognizer_node`의 `path_distance`가 임계값(예: 0.3m) 이하일 때만 ARR 발행
- 이미 `path_distance` 계산 로직이 구현되어 있음 (`/move_base/NavfnROS/plan` 구독)
