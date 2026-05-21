# DB Polling 기반 자율 운행 시스템 개발 계획

## 목표

- START QR 제거 → DB 폴링으로 작업 자동 감지 및 출발
- 로봇 상태(status)를 DB로 관리하여 향후 웹 대시보드와 연동 가능
- 단일 ARR QR로 도착 확인 후 자동 복귀

## 운행 시나리오

```
[대기] 홈(0,0) 위치에서 5초마다 DB 조회
   ↓ pending 작업 발견
[이동중] 목적지로 이동 (orders.status = active, robot.status = 이동중)
   ↓ 목적지 도착 + ARR QR 인식
[복귀] 홈으로 복귀 (orders.status = done, robot.status = 복귀)
   ↓ 홈 도착
[대기] 5초마다 DB 조회 재개
```

---

## DB 구조 변경

### 기존 테이블 (유지)
- `rooms`: 병실 좌표 (변경 없음)
- `orders`: 배송 작업 큐 (변경 없음)

### 신규 테이블 — `robot`

로봇의 현재 상태와 홈 좌표를 저장합니다.

```sql
CREATE TABLE IF NOT EXISTS robot (
    id     INTEGER PRIMARY KEY DEFAULT 1,  -- 단일 로봇 (항상 1행)
    status TEXT NOT NULL DEFAULT '대기',   -- 대기 | 이동중 | 복귀
    home_x REAL NOT NULL DEFAULT 0.0,
    home_y REAL NOT NULL DEFAULT 0.0,
    home_theta REAL NOT NULL DEFAULT 3.1416  -- 180° = π rad
);
```

| status 값 | 의미 |
|-----------|------|
| `대기` | 홈 위치에서 폴링 중 |
| `이동중` | 목적지로 주행 중 |
| `복귀` | 홈으로 복귀 중 |

---

## 작업 계획

### Step 1 — `init_room_db.py` 수정

- `robot` 테이블 생성 및 초기 데이터 삽입 (status=대기, home=0,0,π)
- 기존 `rooms`, `orders` 초기화 로직 유지

### Step 2 — `generate_qr_models.py` 수정

- `qr_start` 제거 (START QR 사용 안 함)
- `qr_arrival_R001~R003` → `qr_arrival` 단일 모델로 통합
- 데이터: `{"type":"ARR"}`
- 결과: QR 모델 4개 → **1개**

### Step 3 — `path_planner_node.py` 핵심 수정

#### 3-1. 폴링 타이머 추가
```python
rospy.Timer(rospy.Duration(5.0), self._poll_orders)
```

#### 3-2. `_poll_orders` 콜백
```
robot.status가 '대기' 또는 '복귀'일 때만 동작
  → orders에서 pending 첫 행 조회
  → 없으면 return
  → 있으면:
      orders.status = 'active'
      robot.status = '이동중'
      send_goal(목적지 좌표)
```

#### 3-3. ARR QR 수신 처리
```
robot.status == '이동중' 확인
  → orders.status = 'done'
  → robot.status = '복귀'
  → send_goal(home_x, home_y, home_theta)
```

#### 3-4. 홈 도착 감지
```
move_base ActionClient의 결과 콜백 추가
  → SUCCEEDED 수신 시
  → robot.status == '복귀' → robot.status = '대기'
```

#### 3-5. START QR 핸들러 제거
- `qr_type == 'START'` 분기 삭제

### Step 4 — `vision_recognizer_node.py` 정리

- START QR 관련 로그 메시지 제거 또는 단순화
- ARR QR: id 필드 없는 `{"type":"ARR"}` 포맷 처리 확인

### Step 5 — 통합 테스트

1. DB 재생성 및 orders 초기 데이터 확인
2. QR 모델 재생성 (`qr_arrival` 1개)
3. 노드 3개 실행 (Gazebo, Navigation, vision, path_planner)
4. orders에 pending 작업 수동 삽입 → 5초 이내 자동 출발 확인
5. 목적지 도착 + ARR QR 인식 → 홈 복귀 확인
6. 홈 도착 → 다음 pending 작업 자동 출발 확인

---

## 파일별 변경 요약

| 파일 | 변경 내용 |
|------|-----------|
| `init_room_db.py` | `robot` 테이블 추가 |
| `generate_qr_models.py` | qr_start 제거, ARR 단일화 |
| `path_planner_node.py` | 폴링 타이머, 상태 전이, 홈 복귀 로직 |
| `vision_recognizer_node.py` | START QR 로그 정리 |

---

## 미결 사항

- [ ] 폴링 중 robot.status가 '이동중'인데 새 작업이 들어오는 경우 → 무시 (현재 설계대로)
- [ ] move_base ABORTED(경로 탐색 실패) 시 robot.status 처리
- [ ] orders가 모두 done인 상태에서 새 작업 추가 방법 (sqlite3 직접 INSERT or 추후 웹 UI)
