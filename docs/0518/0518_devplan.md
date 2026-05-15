# 5월 18일 세부 진행 계획: SQLite DB 기반 병실 좌표 관리 및 QR 경량화

## 1. 개요

* **목표**: QR 코드에 직접 내장되어 있던 목적지 좌표(tgt, theta)를 SQLite DB로 분리하고, QR은 병실 ID만 인코딩하도록 경량화하여 인식률을 높이고 좌표 관리를 중앙화합니다.
* **핵심 방향**: `path_planner_node`가 QR에서 읽은 ID로 DB를 조인 조회하여 좌표를 획득하는 구조로 전환합니다. 이를 통해 좌표 변경 시 QR 재생성 없이 DB만 수정하면 되는 유지보수 편의성을 확보합니다.

```
[현재]  QR → {"id":"A1","type":"START","name":"책상3","tgt":[2.5,-1.0],"theta":0.0}
[변경]  QR → {"id":"R001","type":"START"}  +  DB 조회 → (name, x, y, theta)
```

---

## 2. 작업별 상세 계획

### [작업 1] 병실 좌표 라벨링

* **목표**: 완성된 `hospital_map`에서 배달 목적지로 사용할 병실 3곳의 좌표와 도착 방향을 확정합니다.
* **세부 작업**:
  1. Navigation 스택 실행 후 RViz에서 `2D Nav Goal` 도구로 각 병실 입구 앞 좌표 클릭
  2. RViz 하단 상태바에 표시되는 `(x, y, theta)` 값을 기록
  3. 아래 표를 실제 측정값으로 채울 것 (현재는 예시 값)

  | ID | 이름 | x | y | theta (rad) | 비고 |
  |----|------|---|---|-------------|------|
  | R001 | 1병실 | - | - | - | 측정 필요 |
  | R002 | 2병실 | - | - | - | 측정 필요 |
  | R003 | 3병실 | - | - | - | 측정 필요 |

  > **도착 방향(theta) 결정 기준**: 해당 병실 입구에서 ARRIVAL QR이 붙어있는 벽면을 정면으로 바라보는 방향으로 설정합니다.

---

### [작업 2] SQLite DB 설계 및 초기화 스크립트 작성

* **목표**: 병실 좌표를 저장하는 SQLite DB와 초기 데이터를 입력하는 스크립트를 작성합니다.
* **DB 파일 위치**: `src/qr_logistics_robot/db/hospital_rooms.db`
* **스키마**:

  ```sql
  CREATE TABLE IF NOT EXISTS rooms (
      id    TEXT PRIMARY KEY,   -- QR 코드에 인코딩되는 병실 ID (예: "R001")
      name  TEXT NOT NULL,      -- 표시용 이름 (예: "1병실")
      x     REAL NOT NULL,      -- Navigation 목표 x 좌표 (map frame)
      y     REAL NOT NULL,      -- Navigation 목표 y 좌표 (map frame)
      theta REAL NOT NULL DEFAULT 0.0  -- 도착 시 바라볼 방향 (라디안)
  );
  ```

* **세부 작업**:
  1. `scripts/init_room_db.py` 작성: DB 파일 생성 + 테이블 초기화 + 병실 3곳 데이터 삽입
  2. 작업 1에서 측정한 실제 좌표로 INSERT 값 채우기
  3. `scripts/` 디렉토리에서 `python3 init_room_db.py`로 실행하여 DB 파일 생성

---

### [작업 3] `path_planner_node.py` DB 조회 로직 추가

* **목표**: START QR 수신 시 QR의 ID로 DB를 조회하여 좌표를 획득하도록 `target_callback`을 수정합니다.
* **세부 작업**:
  1. `__init__`에서 `sqlite3`로 DB 연결 (`hospital_rooms.db` 경로는 ROS 파라미터로 설정)
  2. `target_callback`의 START 분기에서 기존 `tgt` 필드 직접 읽기 → DB 조회로 전환

  ```python
  # 변경 전
  target = logistics_info.get('tgt')
  theta  = logistics_info.get('theta', 0.0)

  # 변경 후
  row = db.execute("SELECT name, x, y, theta FROM rooms WHERE id=?", (task_id,)).fetchone()
  if row is None:
      rospy.logwarn(f"DB에 ID '{task_id}'에 해당하는 병실 정보가 없습니다.")
      return
  dest_name, x, y, theta = row
  ```

  3. DB에 없는 ID를 수신했을 때 경고 로그 출력 후 무시하는 방어 로직 추가
  4. 노드 종료 시 (`rospy.on_shutdown`) DB 연결 정상 종료

---

### [작업 4] `generate_qr_models.py` 경량 포맷으로 수정

* **목표**: QR 데이터에서 좌표(`tgt`, `theta`)와 이름(`name`)을 제거하고 `id`와 `type`만 남겨 QR 버전(밀도)을 최소화합니다.
* **세부 작업**:
  1. `qr_data_list`를 병실 3개 + ARRIVAL 3개 구조로 확장
  2. START QR 데이터를 `{"id": "R001", "type": "START"}` 형태로 단순화
  3. ARRIVAL QR 데이터는 현행 유지 (`{"id": "R001", "type": "ARR"}`)
  4. 스크립트 재실행하여 6개 QR 모델 일괄 재생성

  ```python
  qr_data_list = [
      {"model_name": "qr_start_R001", "data": {"id": "R001", "type": "START"}},
      {"model_name": "qr_start_R002", "data": {"id": "R002", "type": "START"}},
      {"model_name": "qr_start_R003", "data": {"id": "R003", "type": "START"}},
      {"model_name": "qr_arrival_R001", "data": {"id": "R001", "type": "ARR"}},
      {"model_name": "qr_arrival_R002", "data": {"id": "R002", "type": "ARR"}},
      {"model_name": "qr_arrival_R003", "data": {"id": "R003", "type": "ARR"}},
  ]
  ```

---

### [작업 5] 통합 테스트

* **목표**: DB 기반 병실 3곳을 순차적으로 독립 테스트하여 전체 시나리오를 검증합니다.
* **테스트 시나리오 (병실 1개 기준)**:
  1. Gazebo에서 `qr_start_R001` 모델을 로봇 정면(~0.5m)에 배치
  2. `qr_arrival_R001` 모델을 R001 목적지 좌표 근처 벽면에 배치 (로봇 도착 방향 정면)
  3. 노드 3개 순서대로 실행: Navigation → `vision_recognizer_node` → `path_planner_node`
  4. 로봇이 START QR 인식 → DB 조회 → 목적지 이동 → ARRIVAL QR 인식 → 배송 완료 확인
  5. R002, R003도 동일하게 반복

* **검증 체크리스트**:
  - [ ] DB에 없는 ID 수신 시 경고 로그만 출력하고 노드 크래시 없이 계속 동작하는가?
  - [ ] theta 값이 올바르게 적용되어 로봇이 ARRIVAL QR 방향으로 도착하는가?
  - [ ] 3개 병실 모두 START → ARRIVAL 시나리오가 정상 완료되는가?

---

## 3. 진행 순서 및 체크리스트

- [ ] **Step 1**: 병실 3곳 좌표·방향 측정 및 라벨링 표 완성
- [ ] **Step 2**: `init_room_db.py` 작성 및 DB 생성
- [ ] **Step 3**: `path_planner_node.py` DB 조회 로직으로 전환
- [ ] **Step 4**: `generate_qr_models.py` 경량 포맷 + 6개 모델로 확장 후 재생성
- [ ] **Step 5**: 병실 1곳 단독 통합 테스트 통과
- [ ] **Step 6**: 병실 3곳 순차 독립 테스트 통과
