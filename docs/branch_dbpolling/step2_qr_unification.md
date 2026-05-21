# Step 2: QR 구조 재편 — 출발 QR 제거 + 도착 QR 단일화

## 설계 근거

### 출발 QR 제거

기존 START QR의 역할은 "다음 배송 작업을 트리거"하는 것이었습니다.  
DB 폴링 방식에서는 `path_planner_node`가 5초마다 `orders` 테이블을 직접 조회하여  
pending 작업을 자동 감지하므로 START QR이 불필요합니다.

```
기존: 사람이 START QR 제시 → 로봇 출발
변경: DB에 pending 작업 존재 → 로봇 자동 출발
```

### 도착 QR 유지 (단일화)

도착 QR은 단순한 "좌표 도달 확인"이 아닌 **환자가 물품을 수령했음을 확인하는 수단**입니다.  
move_base SUCCEEDED만으로는 로봇이 목적지 좌표에 도달했음만 알 수 있고,  
실제로 물품이 전달되었는지는 알 수 없습니다.

도착 QR을 병실 입구에 부착해두고, 환자(또는 보호자)가 로봇에게 QR을 인식시키는 방식으로  
**물품 수령 확인 → 로봇 복귀** 흐름을 구현합니다.

```
기존: 병실마다 별도 QR (qr_arrival_R001, R002, R003) — id로 목적지 검증
변경: 단일 QR (qr_arrival) — 현재 활성 임무가 있으면 수령 확인으로 처리
```

id 검증이 불필요한 이유: 로봇은 한 번에 하나의 임무만 수행하며,  
`current_order_seq`가 활성 상태일 때 수신한 ARR QR은 반드시 해당 임무의 확인입니다.

---

## 변경 내용

### `generate_qr_models.py`

```python
# 변경 전
qr_data_list = [
    {"model_name": "qr_start",        "data": {"type": "START"}},
    {"model_name": "qr_arrival_R001", "data": {"id": "R001", "type": "ARR"}},
    {"model_name": "qr_arrival_R002", "data": {"id": "R002", "type": "ARR"}},
    {"model_name": "qr_arrival_R003", "data": {"id": "R003", "type": "ARR"}},
]

# 변경 후
qr_data_list = [
    {"model_name": "qr_arrival", "data": {"type": "ARR"}},
]
```

### `path_planner_node.py` — ARR 핸들러

```python
# 변경 전: room_id 검증
arr_room_id = logistics_info.get('id')
if self.current_room_id != arr_room_id:
    rospy.logwarn(...)
    return

# 변경 후: 활성 임무 유무만 확인
if self.current_order_seq is None:
    rospy.logwarn("수행 중인 임무가 없는데 도착 QR이 인식되었습니다.")
    return
```

---

## QR 모델 변화 요약

| | 기존 (main 브랜치) | 변경 후 |
|--|-------------------|---------|
| START QR | 1개 (`qr_start`) | **없음** |
| ARR QR | 3개 (`qr_arrival_R001~R003`) | **1개** (`qr_arrival`) |
| **합계** | **4개** | **1개** |

---

## VMware 실행

```bash
cd ~/catkin_ws/src/qr_logistics_robot/scripts
python3 generate_qr_models.py
```

정상 출력:
```
=== 서빙로봇 QR 코드 모델 생성 시작 ===
[완료] qr_arrival 가제보 모델 생성
=== 모든 QR 코드 모델이 생성되었습니다 ===
```

기존 모델 정리 (선택):
```bash
cd ~/catkin_ws/src/qr_logistics_robot/models
rm -rf qr_start qr_arrival_R001 qr_arrival_R002 qr_arrival_R003
```

---

## 다음 단계

Step 3에서 `path_planner_node.py`에 아래 로직을 추가합니다.

- `rospy.Timer(5초)`: `robot.status = '대기'`일 때만 orders 폴링 후 자동 출발
- ARR QR 수신 후 홈 복귀 goal 전송
- `move_base` done 콜백: 홈 도착 시 `robot.status = '대기'` 전환
