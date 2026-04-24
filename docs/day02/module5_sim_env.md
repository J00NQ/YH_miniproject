# 모듈 5: 시뮬레이션 환경 심화 (로봇 및 QR 모델 배치)

이 문서는 1일차에 만들었던 텅 빈 물류 창고(`logistics.world`) 안에 카메라가 달린 **TurtleBot3**와 1일차에 생성한 **QR 이미지 파일이 입혀진 3D 박스**를 함께 투입하는 과정을 다룹니다.

---

## 1. TurtleBot3 패키지 설치

가상 환경(Ubuntu 20.04)에서 카메라를 지원하는 로봇(TurtleBot3 Waffle Pi)을 사용하기 위해 ROS 공식 패키지들을 설치합니다.

```bash
# 1. TurtleBot3 공식 시뮬레이션 및 의존성 패키지 설치
sudo apt update
sudo apt install ros-noetic-turtlebot3 ros-noetic-turtlebot3-msgs ros-noetic-turtlebot3-simulations -y

# 2. 로봇 모델 환경 변수 등록 (카메라가 있는 waffle_pi 사용)
echo "export TURTLEBOT3_MODEL=waffle_pi" >> ~/.bashrc
source ~/.bashrc
```

---

## 2. 가상 QR 박스 모델 세팅

윈도우 측 작업 폴더(`src/qr_logistics_robot/models/qr_box`)에 만들어 둔 가상의 QR 상자 모델 데이터를 리눅스 가상머신에 그대로 덮어씁니다. (윈도우 폴더를 통째로 리눅스의 `~/catkin_ws/src/`로 복사/동기화해 주세요.)

동기화가 끝난 후, **리눅스 환경에서** 아래 명령어를 통해 1일차에 파이썬 스크립트로 만들었던 `logistics_qr_1.png` 파일을 3D 모델의 텍스처 폴더로 복사해 주어야 합니다.

```bash
# 1일차에 생성된 이미지를 가상 모델의 텍스처(표면 이미지) 폴더로 복사
mkdir -p ~/catkin_ws/src/qr_logistics_robot/models/qr_box/materials/textures
cp ~/catkin_ws/src/qr_logistics_robot/models/logistics_qr_1.png ~/catkin_ws/src/qr_logistics_robot/models/qr_box/materials/textures/
```

그리고 이 모델을 Gazebo 시뮬레이터가 읽을 수 있도록 `GAZEBO_MODEL_PATH` 환경 변수를 추가합니다.
```bash
echo "export GAZEBO_MODEL_PATH=\$GAZEBO_MODEL_PATH:~/catkin_ws/src/qr_logistics_robot/models" >> ~/.bashrc
source ~/.bashrc
```

---

## 3. 실행 및 검증 (테스트)

이제 로봇과 QR 박스가 모두 추가된 `logistics_world.launch` 파일을 실행해 봅니다.

```bash
cd ~/catkin_ws
catkin_make
source devel/setup.bash

# 수정된 시뮬레이션 실행 (Turtlebot3 + QR 박스)
roslaunch qr_logistics_robot logistics_world.launch
```

### ✅ 성공 기준
1. **Gazebo 화면**: 기존 물류 창고 중앙 근처(`[X: -2.0]`)에 거북이 모양의 TurtleBot3(Waffle Pi) 로봇이 스폰되어 있습니다. 그리고 로봇 앞쪽(`[X: 2.0]`)에 허공에 세워져 있는 판자(QR 박스)가 있고, 그 표면에 **우리가 만든 QR 코드 모양이 선명하게 입혀져 있는 것**이 보여야 합니다.
2. **토픽 확인**: 새 터미널을 열고 아래 명령어를 입력했을 때, 카메라 데이터가 성공적으로 출력되어야 합니다.
   ```bash
   rostopic list | grep camera
   ```
   결과에 `/camera/rgb/image_raw` 토픽이 활성화되어 있다면, 2일차 첫 번째 모듈(로봇과 카메라 연동 기반) 구축이 완벽히 성공한 것입니다!
