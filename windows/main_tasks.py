#!/usr/bin/env python3
"""
Psychedelic Pose Projection — MediaPipe Tasks API 版
体の輪郭セグメンテーション + モード切替（炎 / 水 / ダンサー残像）
"""

import math
import os
import random
import time
import urllib.request
from collections import deque
from datetime import datetime
from typing import Optional, Tuple

# MediaPipe / TensorFlow の不要なログを抑制
os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core.base_options import BaseOptions

# ---------- ランドマークインデックス ----------
NOSE = 0
LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12
LEFT_ELBOW = 13
RIGHT_ELBOW = 14
LEFT_WRIST = 15
RIGHT_WRIST = 16
LEFT_HIP = 23
RIGHT_HIP = 24
LEFT_KNEE = 25
RIGHT_KNEE = 26
LEFT_ANKLE = 27
RIGHT_ANKLE = 28

POSE_CONNECTIONS = [
    (NOSE, LEFT_SHOULDER), (NOSE, RIGHT_SHOULDER),
    (LEFT_SHOULDER, RIGHT_SHOULDER),
    (LEFT_SHOULDER, LEFT_ELBOW), (LEFT_ELBOW, LEFT_WRIST),
    (RIGHT_SHOULDER, RIGHT_ELBOW), (RIGHT_ELBOW, RIGHT_WRIST),
    (LEFT_SHOULDER, LEFT_HIP), (RIGHT_SHOULDER, RIGHT_HIP),
    (LEFT_HIP, RIGHT_HIP),
    (LEFT_HIP, LEFT_KNEE), (LEFT_KNEE, LEFT_ANKLE),
    (RIGHT_HIP, RIGHT_KNEE), (RIGHT_KNEE, RIGHT_ANKLE),
]

TRAIL_LENGTH = 35
SKELETON_TRAIL_LENGTH = 12
BODY_HISTORY_LENGTH = 8
MAX_PARTICLES = 600

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
)
MODEL_FILENAME = "pose_landmarker_lite.task"

# ---------- モード定義 ----------
MODES = ["normal", "fire", "water", "dancer"]
mode_index = 0


def download_model() -> str:
    path = os.path.join(os.path.dirname(__file__), MODEL_FILENAME)
    if os.path.exists(path):
        return path
    print(f"モデルをダウンロード中: {MODEL_URL}")
    urllib.request.urlretrieve(MODEL_URL, path)
    print(f"保存完了: {path}")
    return path


# ---------- ユーティリティ ----------
def speed_to_hue(speed: float, max_speed: float = 45.0) -> int:
    normalized = min(speed / max_speed, 1.0)
    return int((normalized * 180) % 180)


def get_point(landmarks, idx: int, w: int, h: int, min_vis: float = 0.5) -> Optional[Tuple[int, int]]:
    lm = landmarks[idx]
    if lm.visibility < min_vis:
        return None
    return (int(lm.x * w), int(lm.y * h))


def hsv_color(h: float, s: int = 255, v: int = 255) -> Tuple[int, int, int]:
    c = np.uint8([[[h % 180, s, v]]])
    bgr = cv2.cvtColor(c, cv2.COLOR_HSV2BGR)[0][0]
    return (int(bgr[0]), int(bgr[1]), int(bgr[2]))


# ---------- 既存エフェクト ----------
def draw_fading_trail(frame, trail: deque, base_hue: int):
    n = len(trail)
    if n < 2:
        return
    for i, (x, y) in enumerate(trail):
        alpha = (i + 1) / n
        radius = int(7 * alpha + 2)
        color = hsv_color(base_hue + i * 4)
        cv2.circle(frame, (int(x), int(y)), radius, color, -1, lineType=cv2.LINE_AA)


def draw_skeleton_with_trail(frame, landmarks, w, h, skeleton_history, frame_count):
    points = {}
    for idx in [LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_ELBOW, RIGHT_ELBOW,
                LEFT_WRIST, RIGHT_WRIST, LEFT_HIP, RIGHT_HIP,
                LEFT_KNEE, RIGHT_KNEE, LEFT_ANKLE, RIGHT_ANKLE, NOSE]:
        pt = get_point(landmarks, idx, w, h)
        if pt:
            points[idx] = pt

    skeleton_history.append(points)

    n_hist = len(skeleton_history)
    for hist_i, hist_points in enumerate(skeleton_history):
        alpha = (hist_i + 1) / n_hist
        thickness = max(1, int(3 * alpha))
        base_hue = (frame_count * 2 + hist_i * 8) % 180

        for start_idx, end_idx in POSE_CONNECTIONS:
            if start_idx in hist_points and end_idx in hist_points:
                pt1, pt2 = hist_points[start_idx], hist_points[end_idx]
                color = hsv_color(base_hue + start_idx * 7, 220, int(255 * alpha))
                cv2.line(frame, pt1, pt2, color, thickness, lineType=cv2.LINE_AA)

        for idx, pt in hist_points.items():
            color = hsv_color(base_hue + idx * 5)
            r = max(2, int(5 * alpha))
            cv2.circle(frame, pt, r, color, -1, cv2.LINE_AA)


def draw_torso_ripples(frame, hip_center, sway_history, frame_count):
    if hip_center is None or len(sway_history) < 5:
        return
    recent = list(sway_history)[-20:]
    xs = [p[0] for p in recent]
    if len(xs) < 3:
        return
    mean_x = np.mean(xs)
    sway_amp = np.std(xs)
    if sway_amp < 3.0:
        return

    cx, cy = hip_center
    intensity = min(sway_amp / 25.0, 1.5)
    num_rings = int(2 + intensity * 3)
    for i in range(num_rings):
        phase = (frame_count * 0.15 + i * 1.2) % (math.pi * 2)
        radius = int(30 + i * 28 + math.sin(phase) * 12 * intensity)
        alpha = max(0.15, 0.7 - i * 0.12) * min(intensity, 1.0)
        color = hsv_color(frame_count * 3 + sway_amp * 4 + i * 25, 200, int(255 * alpha))
        thickness = max(1, int(2.5 * alpha + 1))
        cv2.circle(frame, (cx, cy), radius, color, thickness, lineType=cv2.LINE_AA)
        if radius > 15:
            cv2.circle(frame, (cx, cy), radius - 4, color, 1, lineType=cv2.LINE_AA)


# ---------- パーティクル ----------
class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size")

    def __init__(self, x, y, mode):
        self.x = float(x)
        self.y = float(y)
        self.life = 1.0
        if mode == "fire":
            self.vx = random.uniform(-1.2, 1.2)
            self.vy = random.uniform(-5.0, -1.5)
            self.max_life = random.uniform(0.6, 1.0)
            hue = random.uniform(0, 25)
            self.color = hsv_color(hue, 255, 255)
            self.size = random.uniform(2, 6)
        else:  # water
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1.5, 4.5)
            self.vx = math.cos(angle) * speed
            self.vy = math.sin(angle) * speed + 0.5
            self.max_life = random.uniform(0.5, 0.9)
            hue = random.uniform(90, 130)
            self.color = hsv_color(hue, 200, 255)
            self.size = random.uniform(2, 5)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 0.015
        # 炎は上昇中に少し揺らぐ
        self.vx += random.uniform(-0.08, 0.08)
        return self.life > 0

    def draw(self, frame):
        alpha = max(0, self.life / self.max_life)
        if alpha <= 0:
            return
        color = tuple(int(c * alpha) for c in self.color)
        cv2.circle(frame, (int(self.x), int(self.y)), int(self.size * alpha + 1),
                   color, -1, lineType=cv2.LINE_AA)


particles: list[Particle] = []


def spawn_particles_along_contour(contour, mode, count):
    if len(contour) == 0:
        return
    pts = contour.reshape(-1, 2)
    if len(pts) == 0:
        return
    for _ in range(count):
        if len(particles) >= MAX_PARTICLES:
            break
        idx = random.randrange(len(pts))
        x, y = pts[idx]
        # 輪郭の法線方向に少しずらして出現させる
        offset = random.randint(-8, 8)
        particles.append(Particle(x + offset, y + offset, mode))


def update_and_draw_particles(frame):
    for p in particles[:]:
        if not p.update():
            particles.remove(p)
        else:
            p.draw(frame)


# ---------- セグメンテーション / 輪郭 ----------
def get_body_mask(frame, results):
    if not results.segmentation_masks:
        return None
    mask_img = results.segmentation_masks[0]
    mask = mask_img.numpy_view()
    if mask.dtype != np.uint8:
        mask = (mask > 0.5).astype(np.uint8) * 255
    # チャンネル軸があれば削除（H,W,1 → H,W）
    mask = np.squeeze(mask)
    h, w = frame.shape[:2]
    if mask.shape[:2] != (h, w):
        mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_LINEAR)
    return mask


def get_main_contour(mask):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    return max(contours, key=cv2.contourArea)


# ---------- モード別エフェクト ----------
body_history = deque(maxlen=BODY_HISTORY_LENGTH)


def draw_dancer_afterimage(frame, mask, frame_count):
    if mask is None:
        return
    body_history.append(mask.copy())
    n = len(body_history)
    for i, hist in enumerate(body_history):
        alpha = (i + 1) / n * 0.35
        hue = (frame_count * 3 + i * 30) % 180
        color = hsv_color(hue, 200, 255)
        colored = np.zeros_like(frame)
        colored[hist > 127] = color
        cv2.addWeighted(frame, 1.0, colored, alpha, 0, frame)


def draw_fire(frame, mask, contour):
    if contour is not None and len(contour) > 0:
        # 輪郭の下側ほど炎を多く発生
        spawn_count = min(25, MAX_PARTICLES - len(particles))
        spawn_particles_along_contour(contour, "fire", spawn_count)
    update_and_draw_particles(frame)


def draw_water(frame, mask, contour, frame_count):
    if contour is not None and len(contour) > 0:
        spawn_count = min(20, MAX_PARTICLES - len(particles))
        spawn_particles_along_contour(contour, "water", spawn_count)
    update_and_draw_particles(frame)

    # 輪郭に波紋リング
    if contour is not None:
        pts = contour.reshape(-1, 2)
        if len(pts) > 0:
            for _ in range(5):
                idx = random.randrange(len(pts))
                x, y = pts[idx]
                radius = int(8 + 6 * math.sin(frame_count * 0.3 + idx))
                color = hsv_color(105 + random.uniform(-10, 10), 180, 255)
                cv2.circle(frame, (int(x), int(y)), radius, color, 1, lineType=cv2.LINE_AA)


# ---------- メイン ----------
def create_video_writer(w, h, fps):
    recordings_dir = os.path.join(os.path.dirname(__file__), "recordings")
    os.makedirs(recordings_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(recordings_dir, f"psychedelic_pose_{timestamp}.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(path, fourcc, fps, (w, h))
    if not writer.isOpened():
        # mp4v が使えない環境では XVID/avi に fallback
        path = os.path.join(recordings_dir, f"psychedelic_pose_{timestamp}.avi")
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        writer = cv2.VideoWriter(path, fourcc, fps, (w, h))
    print(f"録画開始: {path}")
    return writer, path


def main():
    global mode_index

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("カメラを開けませんでした")
        return

    model_path = download_model()

    base_options = BaseOptions(model_asset_path=model_path)
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        output_segmentation_masks=True,
    )
    detector = vision.PoseLandmarker.create_from_options(options)

    left_wrist_trail = deque(maxlen=TRAIL_LENGTH)
    right_wrist_trail = deque(maxlen=TRAIL_LENGTH)
    skeleton_history = deque(maxlen=SKELETON_TRAIL_LENGTH)
    hip_sway_history = deque(maxlen=40)

    prev_left = None
    prev_right = None
    frame_count = 0

    is_recording = False
    writer = None
    writer_path = None

    print("カメラ起動中...")
    print("q: 終了 / 1: 通常 / 2: 炎 / 3: 水 / 4: ダンサー残像 / r: 録画")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        overlay = frame.copy()

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        timestamp_ms = int(cap.get(cv2.CAP_PROP_POS_MSEC))
        results = detector.detect_for_video(mp_image, timestamp_ms)

        hip_center = None

        if results.pose_landmarks:
            landmarks = results.pose_landmarks[0]
            draw_skeleton_with_trail(overlay, landmarks, w, h, skeleton_history, frame_count)

            left_hip = get_point(landmarks, LEFT_HIP, w, h)
            right_hip = get_point(landmarks, RIGHT_HIP, w, h)
            if left_hip and right_hip:
                hip_center = ((left_hip[0] + right_hip[0]) // 2,
                              (left_hip[1] + right_hip[1]) // 2)
                hip_sway_history.append(hip_center)
                draw_torso_ripples(overlay, hip_center, hip_sway_history, frame_count)

            lw = get_point(landmarks, LEFT_WRIST, w, h)
            if lw:
                left_wrist_trail.append(lw)
                speed = math.hypot(lw[0] - (prev_left[0] if prev_left else lw[0]),
                                   lw[1] - (prev_left[1] if prev_left else lw[1]))
                prev_left = lw
                draw_fading_trail(overlay, left_wrist_trail, speed_to_hue(speed))
                cv2.circle(overlay, lw, 11, (0, 255, 255), 2, cv2.LINE_AA)

            rw = get_point(landmarks, RIGHT_WRIST, w, h)
            if rw:
                right_wrist_trail.append(rw)
                speed = math.hypot(rw[0] - (prev_right[0] if prev_right else rw[0]),
                                   rw[1] - (prev_right[1] if prev_right else rw[1]))
                prev_right = rw
                draw_fading_trail(overlay, right_wrist_trail, speed_to_hue(speed))
                cv2.circle(overlay, rw, 11, (0, 255, 255), 2, cv2.LINE_AA)

        # 体の輪郭マスクを取得
        mask = get_body_mask(frame, results)
        contour = get_main_contour(mask) if mask is not None else None

        mode = MODES[mode_index]
        if mode == "fire":
            draw_fire(overlay, mask, contour)
        elif mode == "water":
            draw_water(overlay, mask, contour, frame_count)
        elif mode == "dancer":
            draw_dancer_afterimage(overlay, mask, frame_count)

        result = cv2.addWeighted(frame, 0.25, overlay, 0.75, 0)

        # UI
        # 録画中インジケーター
        if is_recording:
            cv2.circle(result, (w - 35, 35), 10, (0, 0, 255), -1, cv2.LINE_AA)
            cv2.putText(result, "REC", (w - 110, 42),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)

        cv2.putText(result, f"Mode: {mode.upper()}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(result, "1:normal 2:fire 3:water 4:dancer  r:rec  q:quit", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA)

        cv2.imshow("Psychedelic Pose Projection", result)

        if is_recording and writer is not None:
            writer.write(result)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("1"):
            mode_index = 0
            particles.clear()
            body_history.clear()
        elif key == ord("2"):
            mode_index = 1
            particles.clear()
            body_history.clear()
        elif key == ord("3"):
            mode_index = 2
            particles.clear()
            body_history.clear()
        elif key == ord("4"):
            mode_index = 3
            particles.clear()
            body_history.clear()
        elif key == ord("r"):
            if is_recording:
                is_recording = False
                if writer is not None:
                    writer.release()
                    print(f"録画終了: {writer_path}")
                    writer = None
                    writer_path = None
            else:
                fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
                writer, writer_path = create_video_writer(w, h, fps)
                is_recording = True

        frame_count += 1

    if writer is not None:
        writer.release()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
