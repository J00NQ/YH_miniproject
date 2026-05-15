# VMWare - Windows 호스트 간 파일 전송 및 동기화 가이드

VMWare Tools가 설치되어 있지 않아 드래그 앤 드롭 기능을 사용할 수 없는 경우, 아래의 두 가지 방법 중 하나를 선택하여 환경을 구성할 수 있습니다. (추천: **방법 1 OpenSSH 방식**이 가장 빠르고 안정적입니다.)

---

## 방법 1: SSH를 이용한 파일 전송 (가장 추천)

우분투에 SSH 서버를 설치하면 윈도우의 터미널(PowerShell, CMD)이나 파일 전송 프로그램(FileZilla 등)을 이용해 안정적으로 파일과 폴더를 통째로 보낼 수 있습니다.

### 1. VMWare 우분투에서 SSH 서버 설치 및 실행
우분투 터미널을 열고 아래 명령어를 순서대로 입력합니다.
```bash
# 패키지 목록 업데이트
sudo apt update

# OpenSSH 서버 설치
sudo apt install openssh-server -y

# SSH 서비스 상태 확인 (active (running)이 나오면 성공)
sudo systemctl status ssh
```

### 2. VMWare 우분투의 IP 주소 확인
우분투 터미널에서 아래 명령어를 입력하여 IP를 확인합니다.
```bash
ip addr
# 또는
ifconfig
```
> 보통 `192.168.x.x` 형태로 나오는 IP 주소를 메모해 둡니다.

### 3. Windows에서 파일 전송하기 (SCP 명령어 사용)
윈도우 PowerShell을 열고, 윈도우에 있는 파일이나 폴더를 우분투로 바로 보낼 수 있습니다.

**단일 압축 파일(ZIP) 전송 예시:**
```powershell
# 호스트(윈도우)의 PowerShell에서 실행
# scp [보낼파일경로] [우분투계정명]@[우분투IP]:[도착경로]
scp C:\Users\406\project\mini_project\src\qr_logistics_robot\models\hospital\parede.jpg ubuntu20@192.168.189.130:~/catkin_ws/src/qr_logistics_robot/models/hospital/
```
*(명령어 입력 후 우분투 계정의 비밀번호를 입력하면 전송이 완료됩니다.)*

> **Tip**: 터미널 환경이 불편하다면 Windows에 `FileZilla`나 `WinSCP` 같은 무료 프로그램을 설치한 뒤, 우분투 IP와 계정/비밀번호만 입력하면 폴더 트리 창에서 편하게 마우스로 드래그하여 파일을 옮길 수 있습니다.

---

## 방법 2: VMWare Tools (open-vm-tools) 설치하기

드래그 앤 드롭 및 클립보드(복사/붙여넣기) 공유 기능을 활성화하려면 리눅스용 VMWare Tools 오픈소스 버전을 설치해야 합니다.

### 1. 우분투에서 패키지 설치
우분투 터미널을 열고 아래 명령어를 입력합니다.
```bash
sudo apt update

# GUI(데스크톱 환경)용 VMWare Tools 패키지 설치
sudo apt install open-vm-tools open-vm-tools-desktop -y
```

### 2. 시스템 재부팅
설치가 완료되면 VMWare 우분투를 완전히 재부팅해야 기능이 활성화됩니다.
```bash
sudo reboot
```

### 3. 드래그 앤 드롭 사용
재부팅 후, Windows의 바탕화면이나 탐색기에서 파일을 집어 VMWare 우분투 바탕화면으로 드래그 앤 드롭합니다. 
> **주의사항**: VMWare Tools가 설치되어도 다수의 이미지 폴더나 무거운 파일 전송 시 오류가 발생할 수 있습니다. 따라서 드래그 앤 드롭을 이용하더라도 가급적 **단일 `.zip` 압축 파일** 형태로 전송하는 것을 권장합니다.
