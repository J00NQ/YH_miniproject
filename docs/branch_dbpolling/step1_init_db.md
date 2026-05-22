# Step 1: DB 구조 설계 및 초기화

## robot 테이블 도입 근거

### 핵심 질문: orders 테이블만으로 로봇 상태를 표현할 수 있는가?

`orders` 테이블의 status는 **배송 작업의 상태**를 나타냅니다.  
로봇의 상태와 겹치는 구간이 있지만 완전히 일치하지 않습니다.

| 로봇 상태 | orders에서 유추 가능? | 문제 |
|-----------|----------------------|------|
| 이동중 | ✅ active 행 존재 | - |
| 도착 | ❌ | done으로 바뀌는 순간 복귀와 구분 불가 |
| 복귀 | ❌ | done과 대기 모두 "active 없음"으로 보임 |
| 대기 | ❌ | 복귀와 동일하게 보임 |

복귀와 대기를 구분하지 못하면 **복귀 중 폴링 차단이 불가능**합니다.  
이것이 이번 설계에서 별도 상태 저장소가 필요한 근본 이유입니다.

### 왜 in-memory 변수가 아닌 robot 테이블인가?

in-memory(`self.robot_status = '대기'`)로도 폴링 차단은 구현됩니다.  
그러나 아래 이유로 DB 테이블이 더 적합합니다.

**1. 재시작 시 상태 복원**
노드가 복귀 중 크래시되면 재시작 후 상태를 알 수 없습니다.  
DB에 저장되어 있으면 `'복귀'` 상태를 읽어 홈 복귀를 재개할 수 있습니다.

**2. 홈 좌표의 소속**
홈 좌표(0, 0, π)는 로봇 설정 데이터입니다.  
`orders`나 `rooms`에 넣는 것은 의미적으로 어색하고,  
`robot` 테이블에 함께 두면 "로봇의 기준 위치"로 자연스럽게 읽힙니다.

**3. 관심사 분리**
- `rooms`: 병실 좌표 (장소 정보)
- `orders`: 배송 작업 큐 (업무 정보)
- `robot`: 로봇 상태와 설정 (기계 정보)

각 테이블이 하나의 관심사만 담아 의미가 명확해집니다.

**4. 향후 웹 대시보드 연동**
웹에서 로봇 현재 상태를 보여줄 때 `SELECT status FROM robot` 한 줄로 조회 가능합니다.  
orders 테이블 로직을 파싱해서 상태를 역산할 필요가 없습니다.

---

## DB 최종 구조

### `rooms` (기존 유지)

```sql
CREATE TABLE IF NOT EXISTS rooms (
    id    TEXT PRIMARY KEY,
    name  TEXT NOT NULL,
    x     REAL NOT NULL,
    y     REAL NOT NULL,
    theta REAL NOT NULL DEFAULT 0.0
);
```

### `orders` (기존 유지)

```sql
CREATE TABLE IF NOT EXISTS orders (
    seq     INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id TEXT NOT NULL REFERENCES rooms(id),
    status  TEXT NOT NULL DEFAULT 'pending'
    -- pending | active | done
);
```

### `robot` (신규)

```sql
CREATE TABLE IF NOT EXISTS robot (
    id         INTEGER PRIMARY KEY DEFAULT 1,
    status     TEXT NOT NULL DEFAULT '대기',
    home_x     REAL NOT NULL DEFAULT 0.0,
    home_y     REAL NOT NULL DEFAULT 0.0,
    home_theta REAL NOT NULL DEFAULT 3.1416
    -- status: 대기 | 이동중 | 복귀
);
```

초기 데이터: `(1, '대기', 0.0, 0.0, 3.1416)`

---

## 상태 전이와 DB 변경 시점

```
[대기]
  robot.status = '대기'
  5초마다 orders 폴링
        ↓ pending 발견
[이동중]
  orders.status: pending → active
  robot.status: 대기 → 이동중
        ↓ ARR QR 인식
[복귀]
  orders.status: active → done
  robot.status: 이동중 → 복귀
  send_goal(home)
        ↓ move_base SUCCEEDED
[대기]
  robot.status: 복귀 → 대기
```

---

## `init_room_db.py` 수정 내용

- `robot` 테이블 생성 추가
- 초기 데이터: status=`대기`, home=(0.0, 0.0, π)
- 재실행 시 robot 행이 없을 때만 INSERT (상태 덮어쓰기 방지)

---

## 실행 및 검증

```bash
cd ~/catkin_ws/src/qr_logistics_robot
rm -f db/hospital_rooms.db
python3 scripts/init_room_db.py
```

기대 출력:
```
[rooms]   3행
[orders]  3행 (pending)
[robot]   1행 → (1, '대기', 0.0, 0.0, 3.1416)
```

DB 직접 확인:
```bash
sqlite3 db/hospital_rooms.db "SELECT * FROM robot;"
# 1|대기|0.0|0.0|3.1416
```
