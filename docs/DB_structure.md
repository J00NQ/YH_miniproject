# DB 구조 문서

파일 위치: `src/qr_logistics_robot/db/hospital_rooms.db`  
초기화 스크립트: `src/qr_logistics_robot/scripts/init_room_db.py`

---

## 테이블 목록

### 1. `rooms` — 병실 좌표 정보

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| `id` | TEXT | PRIMARY KEY | 병실 ID |
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
| R001 | 1병실 | 1.6703 | -11.0 | 0.0 |
| R002 | 2병실 | -0.6141 | -11.0 | 0.0 |
| R003 | 3병실 | -3.0615 | -11.0 | 0.0 |

---

### 2. `orders` — 배송 작업 큐

DB 폴링 방식에서 로봇이 5초마다 조회하여 pending 작업을 자동 감지한다.

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
pending → active  : 폴링으로 작업 선택 시
active  → done    : ARR QR 인식 후 배송 완료 시
```

---

### 3. `robot` — 로봇 상태 및 홈 좌표

로봇의 현재 운행 상태와 홈 복귀 좌표를 저장한다.  
단일 로봇 운용 기준으로 항상 1행(id=1)만 존재한다.

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| `id` | INTEGER | PRIMARY KEY DEFAULT 1 | 로봇 식별자 (단일 로봇: 항상 1) |
| `status` | TEXT | NOT NULL, DEFAULT '대기' | 로봇 운행 상태 |
| `home_x` | REAL | NOT NULL, DEFAULT 0.0 | 홈 x 좌표 |
| `home_y` | REAL | NOT NULL, DEFAULT 0.0 | 홈 y 좌표 |
| `home_theta` | REAL | NOT NULL, DEFAULT 3.1416 | 홈 도착 방향 (π rad = 180°) |

```sql
CREATE TABLE IF NOT EXISTS robot (
    id         INTEGER PRIMARY KEY DEFAULT 1,
    status     TEXT NOT NULL DEFAULT '대기',
    home_x     REAL NOT NULL DEFAULT 0.0,
    home_y     REAL NOT NULL DEFAULT 0.0,
    home_theta REAL NOT NULL DEFAULT 3.1416
    -- status 값: '대기' | '이동중' | '복귀'
);
```

**status 상태 전이**

```
대기   →(pending 작업 발견)→  이동중
이동중 →(ARR QR 인식)→       복귀
복귀   →(홈 도착)→            대기
```

**폴링 조건**: `robot.status = '대기'`일 때만 orders 테이블 조회

---

## 변경 이력

| 날짜 | 변경 내용 |
|------|-----------|
| 2026-05-21 | `rooms` 테이블 최초 설계 및 R001~R003 데이터 삽입 |
| 2026-05-21 | `orders` 테이블 추가 (단일 START QR 대응) |
| 2026-05-21 | `robot` 테이블 추가 (DB 폴링 자율 운행 브랜치) |
