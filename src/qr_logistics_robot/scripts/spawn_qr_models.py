#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
spawn_qr_models.py
기동 시 각 병실 nav goal 앞 0.4m 지점에 qr_arrival 모델을 Gazebo에 스폰.

map 프레임(AMCL) ↔ world 프레임(Gazebo) 간 원점 오차를 자동으로 보정한다.
  - auto_offset=True(기본): 로봇의 현재 위치를 양쪽 프레임에서 읽어 오프셋 계산
  - 수동 지정: _map_to_world_offset_x / _map_to_world_offset_y ROS 파라미터로 강제 지정
"""

import rospy
import sqlite3
import os
import math

from geometry_msgs.msg import Pose, PoseWithCovarianceStamped
from gazebo_msgs.srv import SpawnModel, GetModelState

# ── 경로 설정 ──────────────────────────────────────────────────────────────
_DIR      = os.path.dirname(__file__)
DB_PATH   = os.path.abspath(os.path.join(_DIR, '../db/hospital_rooms.db'))
MODEL_DIR = os.path.abspath(os.path.join(_DIR, '../models/qr_arrival'))

# QR 패널을 도착 지점 앞 몇 m에 배치할지
QR_FORWARD_OFFSET = 0.4   # m  (theta 방향)
QR_Z              = 0.1   # m  (바닥에서 중심까지 높이)

# pitch = -π/2 → +z 면이 -x 방향을 향함 (로봇 카메라가 +x를 보므로 정면 일치)
# quaternion_from_euler(0, -π/2, 0) = (0, -√2/2, 0, √2/2)
_Q_X = 0.0
_Q_Y = -0.7071067811865476
_Q_Z = 0.0
_Q_W =  0.7071067811865476


def _load_sdf() -> str:
    with open(os.path.join(MODEL_DIR, 'model.sdf'), 'r') as f:
        return f.read()


def _load_rooms():
    con = sqlite3.connect(DB_PATH)
    rows = con.execute("SELECT id, x, y, theta FROM rooms").fetchall()
    con.close()
    return rows   # [(id, x, y, theta), ...]


class QRSpawner:
    def __init__(self):
        rospy.init_node('qr_spawner_node', anonymous=False)

        # ── 서비스 대기 ───────────────────────────────────────────────────
        rospy.loginfo("[QRSpawner] Gazebo 서비스 대기 중...")
        rospy.wait_for_service('/gazebo/spawn_sdf_model')
        rospy.wait_for_service('/gazebo/get_model_state')
        self._spawn_svc = rospy.ServiceProxy('/gazebo/spawn_sdf_model', SpawnModel)
        self._state_svc = rospy.ServiceProxy('/gazebo/get_model_state', GetModelState)

        # ── 오프셋 결정 ───────────────────────────────────────────────────
        manual_x = rospy.get_param('~map_to_world_offset_x', None)
        manual_y = rospy.get_param('~map_to_world_offset_y', None)

        if manual_x is not None and manual_y is not None:
            self.offset_x = float(manual_x)
            self.offset_y = float(manual_y)
            rospy.loginfo(f"[QRSpawner] 수동 오프셋 사용: dx={self.offset_x:.4f}, dy={self.offset_y:.4f}")
        else:
            self.offset_x, self.offset_y = self._compute_offset()

        # ── 스폰 ─────────────────────────────────────────────────────────
        sdf   = _load_sdf()
        rooms = _load_rooms()
        for room_id, rx, ry, rtheta in rooms:
            # map 프레임 기준 QR 위치 계산 (도착 방향으로 0.4m 앞)
            qr_map_x = rx + QR_FORWARD_OFFSET * math.cos(rtheta)
            qr_map_y = ry + QR_FORWARD_OFFSET * math.sin(rtheta)
            # world 프레임으로 변환
            qr_world_x = qr_map_x + self.offset_x
            qr_world_y = qr_map_y + self.offset_y
            self._spawn(f"qr_arrival_{room_id}", sdf, qr_world_x, qr_world_y)

        rospy.loginfo("[QRSpawner] 모든 QR 모델 스폰 완료.")

    # ── 오프셋 자동 계산 ──────────────────────────────────────────────────
    def _compute_offset(self):
        """
        현재 로봇 위치를 Gazebo world 프레임과 map 프레임에서 각각 읽어
        offset = world_pos - map_pos 를 계산한다.

        로봇이 아직 이동하지 않은 시점(시작 직후)에 호출해야 정확하다.
        """
        rospy.loginfo("[QRSpawner] map→world 오프셋 자동 계산 중...")

        # Gazebo world 좌표
        robot_model = rospy.get_param('~robot_model_name', 'turtlebot3_waffle_pi')
        try:
            resp     = self._state_svc(robot_model, 'world')
            world_x  = resp.pose.position.x
            world_y  = resp.pose.position.y
        except Exception as e:
            rospy.logwarn(f"[QRSpawner] Gazebo 로봇 위치 획득 실패: {e} → offset=0 사용")
            return 0.0, 0.0

        # AMCL map 좌표 (최대 15초 대기)
        try:
            msg    = rospy.wait_for_message('/amcl_pose', PoseWithCovarianceStamped, timeout=15.0)
            map_x  = msg.pose.pose.position.x
            map_y  = msg.pose.pose.position.y
        except rospy.ROSException:
            rospy.logwarn("[QRSpawner] /amcl_pose 수신 실패(timeout) → offset=0 사용. "
                          "navigation 실행 후 재시작하거나 ~map_to_world_offset 파라미터를 직접 지정하세요.")
            return 0.0, 0.0

        dx = world_x - map_x
        dy = world_y - map_y
        rospy.loginfo(f"[QRSpawner] world({world_x:.3f},{world_y:.3f}) - map({map_x:.3f},{map_y:.3f})"
                      f" → 오프셋 dx={dx:.4f}, dy={dy:.4f}")
        return dx, dy

    # ── Gazebo 스폰 ───────────────────────────────────────────────────────
    def _spawn(self, name: str, sdf: str, x: float, y: float):
        pose = Pose()
        pose.position.x  = x
        pose.position.y  = y
        pose.position.z  = QR_Z
        pose.orientation.x = _Q_X
        pose.orientation.y = _Q_Y
        pose.orientation.z = _Q_Z
        pose.orientation.w = _Q_W
        try:
            self._spawn_svc(name, sdf, '', pose, 'world')
            rospy.loginfo(f"[QRSpawner] 스폰: {name}  world({x:.3f}, {y:.3f})")
        except Exception as e:
            rospy.logerr(f"[QRSpawner] 스폰 실패 {name}: {e}")


if __name__ == '__main__':
    try:
        QRSpawner()
    except rospy.ROSInterruptException:
        pass
