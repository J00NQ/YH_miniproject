# Web Step 3: Flask 대시보드 Ubuntu 이식

## 목표

Windows에서 개발한 `web/` 폴더를 Ubuntu VMware에서 실행하여,  
실제 ROS 노드와 동일한 SQLite DB에 연결한다.

---

## 구조 이해

```
[현재 — Windows 개발]
  mini_project/
    web/app.py          ← Flask 실행 (Python 3.14, DB 없음)
    src/qr_logistics_robot/db/hospital_rooms.db  ← 미존재 (Ubuntu에 있음)

[목표 — Ubuntu 실행]
  /home/ubuntu20/catkin_ws/src/qr_logistics_robot/
    web/app.py          ← Flask 실행 (Python 3.8)
    db/hospital_rooms.db  ← 실제 DB (ROS 노드와 공유)
```

`web/app.py`의 기본 DB 경로가 `../db/hospital_rooms.db`이므로,  
`web/`을 `qr_logistics_robot/` 아래에 두면 **환경변수 없이** 자동으로 DB를 찾는다.

---

## 사전 확인 — Ubuntu Python 버전

```bash
python3 --version   # 3.8.x 확인 (ROS Noetic 기본)
pip3 --version
```

---

## Step 1 — Ubuntu에 web/ 폴더 이식

### 방법 A: scp로 직접 복사

Windows PowerShell에서 실행:
```powershell
# Ubuntu IP 먼저 확인 (Ubuntu 터미널: hostname -I)
scp -r "C:\Users\406\project\mini_project\web" ubuntu20@<Ubuntu_IP>:~/catkin_ws/src/qr_logistics_robot/
```

### 방법 B: GitHub에서 클론

```bash
# Ubuntu 터미널 — qr_logistics_robot/ 안에 web/ 폴더만 가져오기
git clone <GitHub_URL> ~/mini_project_tmp
cp -r ~/mini_project_tmp/web ~/catkin_ws/src/qr_logistics_robot/
rm -rf ~/mini_project_tmp
```

이후 코드 업데이트 시 (방법 A 갱신):
```powershell
scp -r "C:\Users\406\project\mini_project\web" ubuntu20@<Ubuntu_IP>:~/catkin_ws/src/qr_logistics_robot/
```

---

## Step 2 — Python 의존성 설치

```bash
cd ~/catkin_ws/src/qr_logistics_robot/web
pip3 install --user -r requirements.txt
```

> `--user` 옵션으로 ROS 시스템 Python 패키지와 충돌 없이 설치된다.

설치 확인:
```bash
python3 -c "import flask, qrcode; print('OK')"
```

---

## Step 3 — 실행

```bash
python3 ~/catkin_ws/src/qr_logistics_robot/web/app.py
```

정상 기동 시 출력:
```
[DB] /home/ubuntu20/catkin_ws/src/qr_logistics_robot/db/hospital_rooms.db
 * Running on http://0.0.0.0:5000
```

> DB 파일이 없으면 `[WARN]` 메시지가 출력된 뒤 DB 조회 시 오류 발생.  
> `init_room_db.py`를 먼저 실행했는지 확인한다.

---

## Step 4 — Windows에서 접속

Ubuntu IP 확인:
```bash
# Ubuntu 터미널
hostname -I   # 예: 192.168.137.128
```

Windows 브라우저에서:
```
http://<Ubuntu_IP>:5000/
```

Ubuntu 방화벽 허용 필요 시:
```bash
sudo ufw allow 5000/tcp
```

---

## Step 5 — 리소스 확인 (Gazebo 동시 실행)

Flask는 대기 상태에서 메모리 약 20~30 MB를 사용하므로 Gazebo와 병행 실행이 가능하다.  
부담이 크다면 **Gazebo 실행 전** Flask를 먼저 종료하거나, 아래 구성으로 분리한다.

| 상황 | Flask | Gazebo/ROS |
|------|-------|------------|
| 주문 등록·확인 | 실행 | 중지 가능 |
| 배송 시뮬레이션 | 중지 | 실행 |
| 수령 확인 QR | 실행 (`/arrival-qr` 만 필요) | 실행 |

---

## 확인 포인트

| 단계 | 확인 사항 |
|------|-----------|
| Flask 기동 | `[DB] /home/.../hospital_rooms.db` 출력 |
| 대시보드 접속 | `http://<Ubuntu_IP>:5000/` 에서 로봇·주문·병실 표시 |
| 주문 추가 | orders 페이지에서 추가 후 DB 반영 확인 (`sqlite3 ... "SELECT * FROM orders"`) |
| 실시간 상태 | path_planner_node 실행 중 robot 페이지 새로고침 시 상태 변화 |
| QR 표시 | `/arrival-qr` 접속 시 QR 이미지 표시 |

---

## 트러블슈팅

### `ModuleNotFoundError: No module named 'flask'`

```bash
# pip3 --user 설치 경로가 PATH에 없는 경우
python3 -m pip install flask qrcode[pil]
```

### `sqlite3.OperationalError: no such table`

DB가 초기화되지 않은 상태. ROS 노드를 먼저 실행하거나:
```bash
cd ~/catkin_ws/src/qr_logistics_robot
python3 scripts/init_room_db.py
```

### 포트 5000이 이미 사용 중

```bash
# 사용 중인 프로세스 확인
lsof -i :5000
# 포트 변경 시 app.py 마지막 줄 수정 후 재실행
python3 ~/catkin_ws/src/qr_logistics_robot/web/app.py  # port=5001 로 수정
```

### Windows에서 접속 불가

1. Ubuntu IP 재확인: `hostname -I`
2. VMware 네트워크 어댑터가 **NAT** 또는 **브리지**인지 확인 (Host-only는 Windows 접속 불가)
3. 방화벽: `sudo ufw allow 5000/tcp`
