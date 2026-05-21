# 작업 2: SQLite DB 설정 가이드

`init_room_db.py`를 실행하여 `hospital_rooms.db`를 생성하고,  
병실 좌표 데이터를 삽입하는 절차입니다.

---

## 1. init_room_db.py 좌표 값 반영

`coordinate.md`에서 확정된 좌표를 스크립트에 입력합니다.

```bash
nano ~/catkin_ws/src/qr_logistics_robot/scripts/init_room_db.py
```

`ROOMS` 리스트를 아래 값으로 교체합니다:

```python
ROOMS = [
    # (id,    name,    x,       y,      theta)
    ("R001", "1병실",  1.6703,  -11.0,  -1.5708),
    ("R002", "2병실", -0.6141,  -11.0,  -1.5708),
    ("R003", "3병실", -3.0615,  -11.0,  -1.5708),
]
```

저장 후 종료: `Ctrl+O` → `Enter` → `Ctrl+X`

---

## 2. DB 생성 실행

```bash
cd ~/catkin_ws/src/qr_logistics_robot/scripts
python3 init_room_db.py
```

정상 출력 예시:
```
DB 초기화 완료: .../db/hospital_rooms.db
  ('R001', '1병실', 1.6703, -11.0, -1.5708)
  ('R002', '2병실', -0.6141, -11.0, -1.5708)
  ('R003', '3병실', -3.0615, -11.0, -1.5708)
```

---

## 3. DB 내용 확인

생성된 DB를 직접 조회하여 데이터가 올바르게 들어갔는지 검증합니다.

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

---

## 4. DB 수정이 필요한 경우

좌표를 잘못 입력했을 때는 스크립트를 수정 후 재실행합니다.  
`INSERT OR REPLACE`로 작성되어 있어 재실행 시 기존 데이터를 덮어씁니다.

```bash
# 스크립트 수정 후
python3 init_room_db.py
```

또는 sqlite3로 직접 수정:
```bash
sqlite3 hospital_rooms.db \
  "UPDATE rooms SET x=1.6703, y=-11.0, theta=-1.5708 WHERE id='R001';"
```

---

## 5. path_planner_node DB 연결 확인

노드 실행 시 DB 경로를 파라미터로 넘길 수 있습니다 (기본값: 자동 감지).

```bash
cd ~/catkin_ws && source devel/setup.bash

# 기본 경로 사용
rosrun qr_logistics_robot path_planner_node.py

# 경로 직접 지정
rosrun qr_logistics_robot path_planner_node.py \
  _db_path:=/home/ubuntu20/catkin_ws/src/qr_logistics_robot/db/hospital_rooms.db
```

정상 로그:
```
[INFO] 병실 DB 연결 완료: .../db/hospital_rooms.db
[INFO] 경로 탐색 노드가 시작되었습니다. 비전 인식기의 좌표 하달을 기다립니다...
```
