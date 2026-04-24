# 모듈 1: ROS/Gazebo 기반 환경 구축 및 워크스페이스 설계 가이드

이 문서는 VMware (Ubuntu 20.04) 설치가 완료된 직후, 가상 환경에서 터미널을 열고 순차적으로 복사/붙여넣기하여 프로젝트 기반을 다질 수 있도록 작성된 매뉴얼입니다.

---

## 1. 필수 패키지 및 ROS Noetic 설치
가상 머신이 켜지면 터미널(Ctrl+Alt+T)을 열고 아래 명령어를 순서대로 실행합니다.

### 1.1 시스템 업데이트 및 ROS 설치
```bash
# 1. 저장소 설정 및 키 등록
sudo sh -c 'echo "deb http://packages.ros.org/ros/ubuntu $(lsb_release -sc) main" > /etc/apt/sources.list.d/ros-latest.list'
sudo apt install curl -y
curl -s https://raw.githubusercontent.com/ros/rosdistro/master/ros.asc | sudo apt-key add -

# 2. 시스템 패키지 목록 업데이트
sudo apt update

# 3. ROS Noetic Desktop Full 설치 (Gazebo 포함)
sudo apt install ros-noetic-desktop-full -y

# 4. 환경 변수 설정
echo "source /opt/ros/noetic/setup.bash" >> ~/.bashrc
source ~/.bashrc

# [설치 확인] ROS 버전을 출력하여 정상 설치 여부 확인 (noetic 출력 시 성공)
rosversion -d
```

### 1.2 Python 기초 환경 설정 및 ROS 의존성 도구 설치
> [!IMPORTANT]
> 우분투 20.04의 기본 파이썬 버전은 3.8입니다. ROS Noetic 패키지들은 모두 Python 3.8에 맞춰 빌드되어 있으므로, 다른 파이썬 버전(예: 3.10)을 강제로 설치하면 ROS 실행 시 심각한 충돌이 발생할 수 있습니다. 기본 버전을 유지하는 것을 강력히 권장합니다.

```bash
# 1. 파이썬 기본 명령어 연결 및 추가 라이브러리 설치 (zbar 포함)
sudo apt install python-is-python3 python3-pip python3-opencv libzbar0 -y

# 2. 빌드 도구 및 rosdep 설치
sudo apt install python3-rosdep python3-rosinstall python3-rosinstall-generator python3-wstool build-essential python3-osrf-pycommon -y

# 3. rosdep 초기화
sudo rosdep init
rosdep update

# 4. 모듈 2, 3에서 사용할 Python 모듈(QR 생성/인식) 미리 설치
pip3 install qrcode[pil] pyzbar

# [설치 확인] 파이썬 버전 확인, 주요 라이브러리 임포트 테스트 및 rosdep 버전 확인
python3 --version
rosdep --version
python3 -c "import cv2; import qrcode; import pyzbar; print('Python libraries installed successfully')"
```

---

## 2. ROS 워크스페이스(catkin_ws) 생성
프로젝트 파일들이 담길 작업 공간을 만듭니다.

```bash
# 1. 워크스페이스 폴더 생성
mkdir -p ~/catkin_ws/src
cd ~/catkin_ws/

# 2. 워크스페이스 빌드 초기화
catkin_make

# 3. 로컬 워크스페이스 환경 변수 등록
echo "source ~/catkin_ws/devel/setup.bash" >> ~/.bashrc
source ~/.bashrc

# [설치 확인] ROS_PACKAGE_PATH에 catkin_ws 경로가 포함되어 있는지 확인
echo $ROS_PACKAGE_PATH
```

---

## 3. 프로젝트 패키지 생성 및 구조 설계
`qr_logistics_robot` 이라는 이름으로 메인 패키지를 생성하고, 향후 모듈별로 관리하기 편하도록 디렉토리 구조를 잡습니다.

### 3.1 패키지 생성
```bash
cd ~/catkin_ws/src
# 사용할 주요 의존성(rospy, std_msgs, sensor_msgs, cv_bridge)을 포함하여 패키지 생성
catkin_create_pkg qr_logistics_robot std_msgs rospy roscpp sensor_msgs cv_bridge
```

### 3.2 권장 디렉토리 구조 세팅
유지보수를 위해 용도별로 폴더를 엄격하게 나눕니다.
```bash
cd ~/catkin_ws/src/qr_logistics_robot

# 필요한 디렉토리 생성
mkdir launch scripts models worlds rviz
chmod +x scripts  # 스크립트 폴더 실행 권한 부여

# [설치 확인] ROS가 새 패키지를 인식하는지 경로를 출력하여 확인
rospack find qr_logistics_robot
ls -l ~/catkin_ws/src/qr_logistics_robot
```

**[최종 패키지 구조 트리]**
```text
qr_logistics_robot/
├── CMakeLists.txt
├── package.xml
├── launch/          # [모듈 1] Gazebo, Rviz, 혹은 통합 실행 런치 파일 저장
├── scripts/         # [모듈 2, 3] 파이썬 노드 및 단독 실행 스크립트 저장
│   ├── qr_generator.py      (모듈 2: QR 생성기)
│   └── qr_recognizer.py     (모듈 3: QR 인식기)
├── models/          # 시뮬레이션용 로봇 모델(urdf/xacro) 및 QR 코드 이미지 저장
├── worlds/          # Gazebo 맵 환경 파일 저장
└── rviz/            # Rviz 시각화 설정 파일 저장
```

---

## 4. 모듈 1 검증: Gazebo Empty World 구동 테스트
설정된 워크스페이스가 정상적으로 동작하는지 확인하기 위해 아주 기본적인 런치 파일을 작성하고 실행해 봅니다.

### 4.1 기본 런치 파일 생성
```bash
# launch 폴더 안에 empty_world.launch 파일 생성
nano ~/catkin_ws/src/qr_logistics_robot/launch/empty_world.launch
```
아래의 내용을 복사하여 넣고 저장(Ctrl+O, Enter, Ctrl+X)합니다.
```xml
<?xml version="1.0"?>
<launch>
  <!-- Gazebo 기본 empty_world를 실행 -->
  <include file="$(find gazebo_ros)/launch/empty_world.launch">
    <arg name="paused" value="false"/>
    <arg name="use_sim_time" value="true"/>
    <arg name="gui" value="true"/>
    <arg name="headless" value="false"/>
    <arg name="debug" value="false"/>
  </include>
</launch>
```

### 4.2 실행 확인
```bash
# 빌드 업데이트 적용
cd ~/catkin_ws
catkin_make
source devel/setup.bash

# 생성한 런치 파일 실행
roslaunch qr_logistics_robot empty_world.launch
```
**성공 기준**: 오류 로그 없이 빈 공간으로 이루어진 Gazebo 시뮬레이터 창이 정상적으로 켜지면 모듈 1 환경 구축이 완벽하게 완료된 것입니다.
