# Web Step 1: Flask 대시보드 환경 설정 및 로컬 테스트

## 생성 파일

```
web/
  app.py
  requirements.txt
  templates/
    base.html
    index.html
    robot.html
    rooms.html
    orders.html
  static/css/
    style.css
```

---

## 구현된 라우트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/` | 전체 현황 (robot·orders·rooms 요약) |
| GET | `/robot` | 로봇 상태 (읽기 전용) |
| GET | `/rooms` | 병실 목록 및 좌표 수정 |
| POST | `/rooms/edit/<room_id>` | 병실 정보 저장 |
| GET | `/orders` | 주문 목록 |
| POST | `/orders/add` | 새 주문 추가 (pending) |
| POST | `/orders/cancel/<seq>` | 주문 취소 (pending 상태만 가능) |

---

## Windows 로컬 테스트

### 사전 준비

```bash
cd C:\Users\406\project\mini_project\web
pip install -r requirements.txt
```

### DB 준비 (테스트용 복사본)

Ubuntu DB를 Windows로 복사하거나, 아래 스크립트로 로컬 테스트용 DB를 직접 생성한다.

```bash
# mini_project 루트에서 실행
python src/qr_logistics_robot/scripts/init_room_db.py
```

> DB 생성 위치: `src/qr_logistics_robot/db/hospital_rooms.db`
> app.py의 기본 DB_PATH가 이 경로를 가리킨다.

### 실행

```bash
cd web
python app.py
```

브라우저에서 `http://localhost:5000` 접속.

### 확인 항목

| 페이지 | 확인 내용 |
|--------|-----------|
| `/` | robot·orders·rooms 3개 테이블이 모두 표시되는가 |
| `/robot` | 로봇 상태(대기/이동중/복귀)가 올바르게 표시되는가 |
| `/rooms` | 각 병실 행에 입력 필드가 표시되고 저장 버튼이 작동하는가 |
| `/orders` | 병실 선택 후 주문 추가 → 목록에 반영되는가 |
| `/orders` | pending 주문의 취소 버튼 → 확인 팝업 → 삭제되는가 |
| `/orders` | active·done 주문에는 취소 버튼이 없는가 |

---

## Ubuntu 실행

Windows에서 개발한 `web/` 폴더를 Ubuntu로 복사한 뒤 실행한다.

```bash
# Windows → Ubuntu 복사 (PowerShell)
scp -r C:\Users\406\project\mini_project\web ubuntu20@<VM_IP>:~/catkin_ws/src/qr_logistics_robot/

# Ubuntu에서 실행
cd ~/catkin_ws/src/qr_logistics_robot/web
pip3 install -r requirements.txt
DB_PATH=~/catkin_ws/src/qr_logistics_robot/db/hospital_rooms.db python3 app.py
```

브라우저에서 `http://<VM_IP>:5000` 접속.

---

## 미결 사항

- DB 동기화 (Issue 3): Windows 개발 DB ↔ Ubuntu 운영 DB 동기화 방법 미결
- active 상태 주문 취소 시 로봇 동작 처리 로직 미구현
- 페이지 자동 새로고침 (robot 상태 실시간 반영) 미구현
