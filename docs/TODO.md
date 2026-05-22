# 프로젝트 완료일 기준으로 할 일

## 더이상 사용하지 않는 파일 정리

### `src/qr_logistics_robot/scripts/` 정리 대상

| 파일 | 분류 | 이유 |
|------|------|------|
| `qr_generator.py` | 초기 프로토타입 | day1 실습용. `item_id`, `destination` 등 구식 데이터 구조 사용. `generate_qr_models.py`가 역할 대체 |
| `qr_recognizer.py` | 초기 프로토타입 | 로컬 이미지 파일을 1회 읽어 출력만 하는 테스트 스크립트. ROS 미연결 |
| `qr_recognizer_node.py` | 구버전 ROS 노드 | 로컬 이미지를 1Hz로 반복 읽는 초기 구현. `vision_recognizer_node.py`로 완전 대체됨 |

### 판단 근거

```
qr_generator.py       → generate_qr_models.py 로 대체 (Gazebo SDF 포함)
qr_recognizer.py      → 단독 실행 테스트용, 현재 파이프라인과 무관
qr_recognizer_node.py → vision_recognizer_node.py 로 대체
                         (카메라 토픽 구독, 2단계 감지, ARR 쿨다운 등 미포함)
```

현재 실제로 사용 중인 스크립트:
- `init_room_db.py` — DB 초기화
- `generate_qr_models.py` — QR SDF 모델 생성
- `spawn_qr_models.py` — Gazebo QR 자동 배치
- `vision_recognizer_node.py` — 카메라 QR 인식 노드
- `path_planner_node.py` — DB 폴링 자율 운행 노드


## 보고서 보강
- 순서도, 다이어그램 정리
- docs 설명 추가