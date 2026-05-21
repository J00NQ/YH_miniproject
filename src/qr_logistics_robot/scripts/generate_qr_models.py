#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import qrcode
import json
import os

# 생성할 모델들이 저장될 최상위 경로 (현재 경로의 ../models)
MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../models'))

# QR 데이터 정의 — START는 단일 QR, 목적지는 orders DB에서 결정
qr_data_list = [
    {"model_name": "qr_start",        "data": {"type": "START"}},
    {"model_name": "qr_arrival_R001", "data": {"id": "R001", "type": "ARR"}},
    {"model_name": "qr_arrival_R002", "data": {"id": "R002", "type": "ARR"}},
    {"model_name": "qr_arrival_R003", "data": {"id": "R003", "type": "ARR"}},
]

# 가제보 모델 SDF 템플릿 (크기: 0.2 0.2 0.01)
SDF_TEMPLATE = """<?xml version="1.0" ?>
<sdf version="1.6">
  <model name="{model_name}">
    <static>true</static>
    <link name="link">
      <collision name="collision">
        <geometry>
          <box>
            <size>0.2 0.2 0.01</size>
          </box>
        </geometry>
      </collision>
      <visual name="visual">
        <geometry>
          <box>
            <size>0.2 0.2 0.01</size>
          </box>
        </geometry>
        <material>
          <script>
            <uri>model://{model_name}/materials/scripts</uri>
            <uri>model://{model_name}/materials/textures</uri>
            <name>{model_name}/Image</name>
          </script>
        </material>
      </visual>
    </link>
  </model>
</sdf>
"""

CONFIG_TEMPLATE = """<?xml version="1.0" ?>
<model>
  <name>{model_name}</name>
  <version>1.0</version>
  <sdf version="1.6">model.sdf</sdf>
  <author>
    <name>Developer</name>
    <email>dev@example.com</email>
  </author>
  <description>QR Code Model: {model_name}</description>
</model>
"""

MATERIAL_TEMPLATE = """material {model_name}/Image
{{
  technique
  {{
    pass
    {{
      texture_unit
      {{
        texture qr.png
      }}
    }}
  }}
}}
"""

def generate_gazebo_model(item):
    model_name = item["model_name"]
    data_dict = item["data"]
    
    # JSON 문자열 변환 (띄어쓰기 없이 컴팩트하게)
    json_str = json.dumps(data_dict, separators=(',', ':'), ensure_ascii=False)
    
    # 폴더 구조 생성
    model_path = os.path.join(MODELS_DIR, model_name)
    mat_scripts_path = os.path.join(model_path, 'materials', 'scripts')
    mat_textures_path = os.path.join(model_path, 'materials', 'textures')
    
    os.makedirs(mat_scripts_path, exist_ok=True)
    os.makedirs(mat_textures_path, exist_ok=True)
    
    # 1. QR 이미지 생성
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(json_str)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img_path = os.path.join(mat_textures_path, 'qr.png')
    img.save(img_path)
    
    # 2. SDF 및 Config 생성
    with open(os.path.join(model_path, 'model.sdf'), 'w') as f:
        f.write(SDF_TEMPLATE.format(model_name=model_name))
        
    with open(os.path.join(model_path, 'model.config'), 'w') as f:
        f.write(CONFIG_TEMPLATE.format(model_name=model_name))
        
    with open(os.path.join(mat_scripts_path, f'{model_name}.material'), 'w') as f:
        f.write(MATERIAL_TEMPLATE.format(model_name=model_name))
        
    print(f"[완료] {model_name} 가제보 모델 생성 (경로: {model_path})")

if __name__ == "__main__":
    print("=== 서빙로봇 QR 코드 모델 생성 시작 ===")
    for item in qr_data_list:
        generate_gazebo_model(item)
    print("=== 모든 QR 코드 모델이 생성되었습니다 ===")
