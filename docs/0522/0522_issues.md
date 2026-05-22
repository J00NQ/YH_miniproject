# 0522 테스트 이슈

## 환경

- QR_FORWARD_OFFSET = 0.7 m
- R001 인식 성공 / R002 인식 실패

---

## Issue 1 — R002 QR 방향 뒤틀림으로 미인식

### 현상

R001 QR은 정상 인식되어 배송 완료 → 복귀까지 정상 흐름.
R002 도착 시 QR을 인식하지 못함 ("방향이 뒤틀려" 있는 상태로 확인).

### 원인 분석

현재 `spawn_qr_models.py`는 모든 QR의 방향을 **pitch=−π/2, yaw=0 고정**으로 스폰한다.
이 방향은 QR 면이 −x 방향을 향하게 하며, 로봇이 **+x 방향(theta=0)으로 정확히** 도착할 때만 정면으로 보인다.

R001(x=1.6703)과 R002(x=−0.6141)는 같은 theta=0.0이지만,
**실제 내비게이션 경로와 도착 자세(yaw)가 다를 수 있다.**

가설 A — 도착 orientation 오차
: move_base는 목표 theta를 허용 오차(yaw_tolerance) 내에서만 맞춘다.
  R002 도착 시 로봇이 실제로 theta ≠ 0으로 멈추면 QR이 카메라 시야 밖으로 벗어남.

가설 B — QR 물리적 위치 문제
: R002 QR 스폰 위치 = (−0.6141 + 0.7, −11.0) = **(0.0859, −11.0)**.
  이 지점이 병원 복도 구조물과 겹치거나 맵상 장애물 영역일 가능성.

### 해결 방향

**단기 (직접 값 조정):**
- `QR_FORWARD_OFFSET`을 줄여보거나 (0.5 m)
- `QR_Z` 높이를 올려보기 (0.1 → 0.2 m)
- Gazebo에서 R002 QR 모델의 실제 위치를 육안으로 확인

**근본 해결 (코드 수정):**
`spawn_qr_models.py`의 `_spawn` 호출부에서 yaw를 theta 기반으로 계산.
QR 면이 로봇을 향하려면 `yaw_qr = theta + π`.

```python
# 현재: yaw 고정 (0)
# 수정: room theta 기반으로 계산
yaw_qr = rtheta + math.pi   # QR 면이 로봇 진입 방향 반대를 향함

# quaternion_from_euler(0, -π/2, yaw_qr) 수동 계산
cr, sr = 1.0, 0.0
cp, sp = math.cos(-math.pi/4), math.sin(-math.pi/4)
cy, sy = math.cos(yaw_qr/2), math.sin(yaw_qr/2)
qx = sr*cp*cy - cr*sp*sy
qy = cr*sp*cy + sr*cp*sy
qz = cr*cp*sy - sr*sp*cy
qw = cr*cp*cy + sr*sp*sy
```

---

## Issue 2 — 복귀 중 ARR QR 재인식

### 현상

배송 완료 → 홈 복귀 goal 전송 직후, `수행 중인 임무가 없는데 도착 QR이 인식되었습니다.` 경고가 약 2초간 연속 5회 발생.

```
[INFO]  *** 배송 완료! (seq=1) 홈으로 복귀합니다. ***
[INFO]  --- Goal 전송 완료 (X=0.0000, Y=0.0000, θ=180.0°) ---
[WARN]  수행 중인 임무가 없는데 도착 QR이 인식되었습니다.  ← 5회 반복
...
[INFO]  === 홈 복귀 완료. 대기 상태로 전환합니다. ===
```

### 원인

복귀 출발 직후 로봇이 QR 앞에서 방향 전환하는 동안 카메라가 QR을 계속 포착.
`vision_recognizer_node`는 `qr_type == 'ARR'`이면 `last_published_data`와 무관하게 **항상 발행**하도록 되어 있어 중복 publish가 발생.

`path_planner_node`는 `current_order_seq is None`일 때 경고 후 무시하므로
**현재는 기능 이상 없음.** 하지만 불필요한 토픽 발행이 계속되는 구조적 문제.

### 해결

`vision_recognizer_node`에 ARR 발행 후 **10초 쿨다운** 추가.

```python
# __init__
self.last_arr_time = 0.0
self.ARR_COOLDOWN = 10.0

# image_callback 발행 조건
if qr_type == 'ARR':
    if now - self.last_arr_time < self.ARR_COOLDOWN:
        continue   # 쿨다운 중 → 발행 생략
    self.last_arr_time = now
```

---

## 진행 상태

| 이슈 | 상태 |
|------|------|
| Issue 1 — R002 QR 미인식 | 완료 (2단계 감지로 해결, 근본 원인은 2D Pose Estimate 오차) |
| Issue 2 — 복귀 중 ARR 재인식 | 완료 (ARR 쿨다운 10초 추가) |
