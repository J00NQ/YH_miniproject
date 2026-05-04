# 모듈 8: 2D 정밀 지도 생성 (SLAM Mapping)

이 문서는 시뮬레이션 환경(`logistics.world`) 내부를 로봇이 직접 돌아다니며, 레이저 센서(LiDAR)를 이용해 2D 점유 격자 지도(Occupancy Grid Map)를 그리는 과정을 다룹니다.

---

## 1. 개요
* **사용 알고리즘**: `gmapping` (ROS에서 가장 널리 쓰이는 안정적인 2D SLAM 알고리즘)
* **원리**: 로봇을 수동으로 조종하여 맵 구석구석을 돌아다니면, LiDAR 센서가 스캔한 장애물(벽) 데이터를 누적하여 하나의 온전한 흑백 지도로 완성합니다.

---

## 2. 매핑 진행 방법

아래 순서대로 총 4개의 터미널을 띄워서 매핑을 진행하고 지도를 저장합니다.

### [터미널 1] 시뮬레이션 (Gazebo) 실행
로봇과 물류 창고가 있는 맵을 띄웁니다.
```bash
roslaunch qr_logistics_robot logistics_world.launch
```

### [터미널 2] SLAM 노드 가동
지도를 그리는 핵심 노드를 실행합니다. 실행 시 시각화 툴인 RViz가 자동으로 함께 열립니다.
```bash
# (주의) ~/.bashrc에 TURTLEBOT3_MODEL=waffle_pi 가 설정되어 있어야 합니다.
roslaunch turtlebot3_slam turtlebot3_slam.launch slam_methods:=gmapping
```
*(RViz 창이 열리면 로봇 주변으로 장애물이 까만 점으로 찍히는 것을 볼 수 있습니다.)*

### [터미널 3] 로봇 수동 조종 (Teleop)
로봇을 키보드로 조종하여 맵의 구석구석을 탐색합니다.
```bash
rosrun turtlebot3_teleop turtlebot3_teleop_key
```
* **조종 팁**: `w`(전진), `x`(후진), `a`/`d`(회전), `s`(정지) 키를 적절히 섞어 벽면의 형태가 사각형으로 뚜렷하게 닫힐 때까지 맵 전체를 천천히 돌아다닙니다. 중앙의 빨간 원기둥이나, 우리가 부착해 둔 QR 박스 근처도 레이저가 닿도록 잘 훑어주세요.

---

## 3. 맵 저장 및 검증

RViz 화면을 보고 "이 정도면 지도가 충분히 완성되었다"고 판단되면, **절대 터미널 1이나 2를 끄지 마시고** 새 터미널을 열어 완성된 지도를 캡처하여 저장합니다.

### [터미널 4] 맵 저장 노드 실행
나중에 Navigation 모듈에서 쉽게 불러오기 위해, 우리 패키지 디렉토리에 `maps` 폴더를 만들고 그곳에 저장합니다.
```bash
# 저장할 폴더 생성 및 이동
mkdir -p ~/catkin_ws/src/qr_logistics_robot/maps
cd ~/catkin_ws/src/qr_logistics_robot/maps

# 현재 그려진 맵 데이터를 logistics_map 이라는 이름으로 캡처 및 저장
rosrun map_server map_saver -f logistics_map
```

---

### ✅ 체크포인트 1 (성공 기준)
저장 명령어를 치면 즉시 해당 폴더에 다음 2개의 파일이 생성됩니다.
1. `logistics_map.yaml` (맵의 메타데이터 및 해상도 정보 파일)
2. `logistics_map.pgm` (실제 지도가 그려진 흑백 이미지 파일)

터미널에서 아래 명령어로 파일이 정상 생성되었는지 확인해 보세요.
```bash
ls -l ~/catkin_ws/src/qr_logistics_robot/maps
```

그리고 리눅스의 기본 폴더 탐색기 창을 열어 `logistics_map.pgm` 이미지를 더블클릭해 보세요. **회색 바탕에 까만색 선으로 창고의 네 면(외벽)과 맵 안의 장애물 형태가 예쁘게 그려져 있다면 매핑에 완벽히 성공**하신 것입니다! 

맵 이미지 확인까지 완료되었다면 켜두었던 터미널(1~3)들을 모두 `Ctrl+C`로 완전히 종료하신 뒤 말씀해 주세요!
