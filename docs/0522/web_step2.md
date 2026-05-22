# Web Step 2: 웹 QR 코드 표시 — 스마트폰 → 로봇 카메라 수령 확인

## 시나리오

```
로봇 → 병실 도착 (move_base SUCCEEDED)
  │
  ├─ 로봇 카메라: 가제보 ARR QR 패널 인식 (기존 Step 4 방식)
  │    └─ 물리 QR 패널이 보이지 않거나 없을 경우 대체 수단 필요
  │
  └─ 대체 수단: 스마트폰 화면으로 QR 제시
       ① 환자/보호자가 웹 대시보드 ARR QR 페이지 접속
       ② 스마트폰 화면에 ARR QR 코드가 크게 표시됨
       ③ 스마트폰 화면을 로봇 카메라 앞에 제시
       ④ vision_recognizer_node가 ARR 인식 → 복귀 명령 전송
```

---

## 구현 항목

### 1. Flask — QR 이미지 동적 생성 라우트

ARR QR 데이터(`{"type":"ARR"}`)를 서버에서 실시간 생성해 PNG로 반환.

```
GET /arrival-qr/image   → PNG 이미지 (Content-Type: image/png)
GET /arrival-qr         → QR 표시 전용 페이지 (스마트폰 최적화)
```

의존 라이브러리: `qrcode[pil]` (generate_qr_models.py에서 이미 사용 중)

```python
# requirements.txt에 추가
qrcode[pil]>=7.4
```

```python
# app.py 추가 라우트
import qrcode, io
from flask import send_file

ARR_QR_DATA = '{"type":"ARR"}'

@app.route('/arrival-qr/image')
def arrival_qr_image():
    qr  = qrcode.QRCode(version=1, box_size=12, border=4)
    qr.add_data(ARR_QR_DATA)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

@app.route('/arrival-qr')
def arrival_qr():
    return render_template('arrival_qr.html')
```

---

### 2. 템플릿 — arrival_qr.html

스마트폰에서 접속했을 때 QR이 화면을 최대한 채우도록 설계.

- 배경 흰색, QR 이미지 중앙 배치
- 화면 밝기 최대화 유도 안내 문구
- 대시보드 nav 숨김 (QR만 집중 표시)
- QR 크기: `min(90vw, 90vh)` — 가로/세로 중 짧은 쪽 기준으로 채움

---

### 3. 대시보드 연동

대시보드(`/`) 및 주문 관리(`/orders`) 페이지에서 현재 `active` 주문이 있을 때
**"수령 확인 QR 보기"** 버튼 표시 → `/arrival-qr` 링크.

```
주문 목록
  seq=1  R001  active   [수령 확인 QR 보기 →]
  seq=2  R002  pending  —
```

---

## 기술적 고려사항

### 로봇 카메라 인식 가능성

| 항목 | 가제보 QR 패널 | 스마트폰 화면 QR |
|------|--------------|----------------|
| 대비 | 텍스처 기반 (합성) | LCD/OLED 발광 (고대비) |
| 반사 | 없음 | 화면 반사 가능 |
| 크기 | 0.2×0.2m 고정 | 스마트폰 크기에 따라 다름 |
| 거리 | 0.7m 고정 배치 | 환자가 직접 조정 가능 |

스마트폰 화면은 발광 소스이므로 raw 그레이스케일(1차 시도)에서 인식 가능성이 높음.
반사 방지를 위해 환자에게 화면을 약간 기울여 제시하도록 안내.

### 현재 vision_recognizer_node와의 호환성

- 코드 변경 불필요 — 동일한 `{"type":"ARR"}` 데이터를 인식하면 동작
- 쿨다운(10초) 주의: 가제보 ARR QR 인식 후 10초 이내에는 웹 QR이 무시됨
  → 가제보 QR 패널 제거(스폰 안 함) 또는 쿨다운 시간 조정 검토 필요

### 네트워크 요건

- 스마트폰과 Flask 서버(Ubuntu)가 **같은 Wi-Fi** 네트워크에 있어야 함
- Ubuntu IP 주소로 접속: `http://<Ubuntu_IP>:5000/arrival-qr`
- Ubuntu 방화벽에서 포트 5000 허용 필요

---

## 구현 순서

1. `requirements.txt`에 `qrcode[pil]` 추가
2. `app.py`에 `/arrival-qr`, `/arrival-qr/image` 라우트 추가
3. `templates/arrival_qr.html` 작성 (스마트폰 최적화)
4. `orders.html`, `index.html`에 active 주문 시 QR 링크 버튼 추가
5. Ubuntu 환경에서 스마트폰 접속 테스트
6. 로봇 카메라 인식 테스트 (거리·각도 조정)

---

## 미결 사항

| 항목 | 내용 |
|------|------|
| 쿨다운 충돌 | 가제보 ARR QR 인식 후 10초 쿨다운으로 웹 QR 즉시 인식 불가 가능 |
| 가제보 QR 패널 공존 | 물리 패널과 웹 QR 중복 사용 시 먼저 인식되는 쪽이 처리됨 |
| 스마트폰 화면 반사 | 조명 환경에 따라 인식률 저하 가능 |
| Ubuntu IP 안내 | 접속 URL을 대시보드에 표시하는 기능 추가 검토 |
