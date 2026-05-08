# 각 기능 추가시 테스트 및 디버깅 가이드를 작성합니다.

## 변경사항 적용시 공통
```bash
# 변경사항 적용시 실행
cd ~/catkin_ws
source devel/setup.bash
```

### [터미널 1] Gazebo 실행 (테스트 월드)
```bash
roslaunch qr_logistics_robot logistics_world.launch
```

### [터미널 2] Navigation 스택 및 초기 위치 설정
```bash
roslaunch turtlebot3_navigation turtlebot3_navigation.launch map_file:=$HOME/catkin_ws/src/qr_logistics_robot/maps/logistics_map.yaml
```

### [터미널 3] 실시간 비전 인식 노드 가동
```bash
rosrun qr_logistics_robot vision_recognizer_node.py
```

### [터미널 4] 경로 탐색(주행 명령 하달) 노드 가동
```bash
rosrun qr_logistics_robot path_planner_node.py
```

# 월드 추가시 해야할 작업
## [터미널 1] Gazebo 실행 (새로 작성한 월드)
```bash
roslaunch qr_logistics_robot (새로_작성한_월드).launch
```

## [터미널 2] Gmapping 모드로 SLAM 실행
```bash
roslaunch turtlebot3_slam turtlebot3_slam.launch
```

## [터미널 3] RViz 실행
```bash
rosrun rviz rviz
```

## [터미널 4] 수동 조종으로 월드 탐색
```bash
rosrun turtlebot3_teleop turtlebot3_teleop_key
```

## [터미널 5] 맵 저장
```bash
cd ~/catkin_ws/src/qr_logistics_robot/maps
rosrun map_server map_saver -f (저장할 맵 이름).yaml
```
