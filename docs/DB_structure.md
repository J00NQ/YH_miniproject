# DB 구조 문서

파일 위치: `src/qr_logistics_robot/db/hospital_rooms.db`  
초기화 스크립트: `src/qr_logistics_robot/scripts/init_room_db.py`

---

## 테이블 목록

### 1. `rooms` — 병실 좌표 정보

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| `id` | TEXT | PRIMARY KEY | QR 코드에 인코딩되는 병실 ID |
| `name` | TEXT | NOT NULL | 표시용 이름 |
| `x` | REAL | NOT NULL | Navigation 목표 x 좌표 (map frame) |
| `y` | REAL | NOT NULL | Navigation 목표 y 좌표 (map frame) |
| `theta` | REAL | NOT NULL, DEFAULT 0.0 | 도착 시 바라볼 방향 (라디안) |

```sql
CREATE TABLE IF NOT EXISTS rooms (
    id    TEXT PRIMARY KEY,
    name  TEXT NOT NULL,
    x     REAL NOT NULL,
    y     REAL NOT NULL,
    theta REAL NOT NULL DEFAULT 0.0
);
```

**샘플 데이터**

| id | name | x | y | theta |
|----|------|---|---|-------|
| R001 | 1병실 | 1.6703 | -11.0 | -1.5708 |
| R002 | 2병실 | -0.6141 | -11.0 | -1.5708 |
| R003 | 3병실 | -3.0615 | -11.0 | -1.5708 |

---

### 2. `orders` — 배송 작업 큐 (추가 예정)

START QR을 단일 QR로 통합하기 위해 도입.  
로봇은 START QR 인식 시 `status='pending'`인 행 중 `seq`가 가장 작은 항목을 조회하여 목적지를 결정한다.

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| `seq` | INTEGER | PRIMARY KEY AUTOINCREMENT | 작업 순번 (큐 순서 기준) |
| `room_id` | TEXT | NOT NULL, FK → rooms.id | 목적지 병실 ID |
| `status` | TEXT | NOT NULL, DEFAULT 'pending' | 작업 상태 |

```sql
CREATE TABLE IF NOT EXISTS orders (
    seq     INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id TEXT NOT NULL REFERENCES rooms(id),
    status  TEXT NOT NULL DEFAULT 'pending'
    -- status 값: 'pending' | 'active' | 'done'
);
```

**status 상태 전이**

```
pending → active  : START QR 인식 후 해당 작업 선택 시
active  → done    : ARRIVAL QR 인식 후 배송 완료 시
```

**동작 방식 (큐)**

```sql
-- 로봇이 START QR 인식 시: 가장 오래된 pending 작업 조회
SELECT o.seq, r.name, r.x, r.y, r.theta
FROM orders o JOIN rooms r ON o.room_id = r.id
WHERE o.status = 'pending'
ORDER BY o.seq ASC
LIMIT 1;

-- 조회 후 즉시 active로 전환
UPDATE orders SET status = 'active' WHERE seq = ?;

-- ARRIVAL QR 인식 시 완료 처리
UPDATE orders SET status = 'done' WHERE seq = ?;
```

---

## 변경 이력

| 날짜 | 변경 내용 |
|------|-----------|
| 2026-05-21 | `rooms` 테이블 최초 설계 및 R001~R003 데이터 삽입 |
| 2026-05-21 | `orders` 테이블 설계 (단일 START QR 대응, 미구현) |
