# 5월 15일 작업 1: 병원 월드 환경 추가

## 1. 개요
기존의 단순한 물류 창고 환경(`logistics.world`)을 벗어나, 병원 구조(`turtlebot3_hospital_sim`)의 복잡한 맵 환경으로 전환합니다. 
이 과정에서 VMWare 리소스의 한계를 고려하여 무거운 전체 패키지를 받지 않고, 핵심적인 월드 파일과 모델 리소스만을 선별하여 현재 프로젝트에 통합하는 방식으로 최적화를 진행했습니다.

---

## 2. 병원 월드 파일 통합 (경량화 구성)

오픈소스 `turtlebot3_hospital_sim` 리포지토리에서 다음 리소스를 `qr_logistics_robot` 패키지로 직접 가져와 통합했습니다.

### 2.1 파일 복사 내역
1. **월드 파일**: 
   - `pseudo_hospital.world` 파일을 복사하여 패키지 내 `worlds/hospital.world`로 이름 변경 및 저장했습니다.
2. **모델 리소스**: 
   - `models/hospital` 폴더 (콜리전, 비주얼 DAE 파일 및 매테리얼 텍스처 등 포함) 전체를 복사하여 패키지 내 `models/hospital` 경로에 배치했습니다.

### 2.2 라이선스 보존 (MIT)
`turtlebot3_hospital_sim`은 MIT 라이선스를 따릅니다. 따라서 가져온 모델 폴더(`models/hospital`) 내에 원작자(Gabriel F P Araujo)의 원본 `LICENSE` 사본을 그대로 보존하여 배포 조건을 철저히 준수했습니다.

---

## 3. 런치 파일(Launch File) 신규 작성

새로운 병원 월드를 Gazebo 상에서 로드하기 위해 `launch/hospital_world.launch` 파일을 작성했습니다.

```xml
<?xml version="1.0"?>
<launch>
  <arg name="paused" default="false"/>
  <arg name="use_sim_time" default="true"/>
  <arg name="gui" default="true"/>

  <arg name="model" default="waffle_pi"/>
  <!-- 시작 좌표를 기존 물류월드의 (-2.0, 0.0)에서 (0.0, 0.0)으로 변경 -->
  <arg name="x_pos" default="0.0"/>
  <arg name="y_pos" default="0.0"/>
  <arg name="z_pos" default="0.0"/>

  <include file="$(find gazebo_ros)/launch/empty_world.launch">
    <!-- 새롭게 추가한 병원 월드 지정 -->
    <arg name="world_name" value="$(find qr_logistics_robot)/worlds/hospital.world"/>
    <arg name="paused" value="$(arg paused)"/>
    <arg name="use_sim_time" value="$(arg use_sim_time)"/>
    <arg name="gui" value="$(arg gui)"/>
  </include>

  <param name="robot_description" command="$(find xacro)/xacro --inorder $(find turtlebot3_description)/urdf/turtlebot3_$(arg model).urdf.xacro" />
  <node pkg="gazebo_ros" type="spawn_model" name="spawn_urdf" args="-urdf -model turtlebot3_$(arg model) -x $(arg x_pos) -y $(arg y_pos) -z $(arg z_pos) -param robot_description" />
</launch>
```
- 로봇 초기 시작 위치(`x_pos`, `y_pos`)를 `0.0, 0.0`으로 재설정하여 병원 입구 주변에서 안정적으로 스폰되도록 했습니다.
- `world_name` 파라미터에 복사해 온 `hospital.world` 경로를 매핑하여 로드하도록 구성했습니다.

---

## 4. 월드 실행 및 맵 생성 가이드

### 4.1 시뮬레이션 구동 테스트
아래 명령어를 통해 새로 추가한 병원 월드가 오류 없이 켜지는지 확인합니다.
```bash
roslaunch qr_logistics_robot hospital_world.launch
```
> 초기 로딩 시 모델 파일을 읽어오느라 Gazebo 화면이 검게 보일 수 있으나 잠시 기다리면 정상 표출됩니다.

### 4.2 SLAM 매핑 (hospital_map)
새로운 월드에서 Navigation 스택을 사용하기 위해 최초 1회 SLAM을 구동하여 전체 지도를 맵 서버에 저장해야 합니다.
1. 터미널 1 (SLAM 런치): `roslaunch turtlebot3_slam turtlebot3_slam.launch slam_methods:=gmapping`
2. 터미널 2 (수동 조작): `roslaunch turtlebot3_teleop turtlebot3_teleop_key.launch` (로봇을 조종하며 맵 전체 스캔)
3. 터미널 3 (맵 저장): 맵 스캔 완료 후 `rosrun map_server map_saver -f ~/catkin_ws/src/qr_logistics_robot/maps/hospital_map` 명령으로 `hospital_map.yaml` 파일 저장.
