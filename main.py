#!/usr/bin/env python3
"""
Psychedelic Pose Projection - Phase 2
全身骨格追跡 + 体幹波紋 + 手首虹色残像
"""

import cv2
import mediapipe as mp
import numpy as np
from collections import deque
from typing import List, Tuple, Optional

# Mediapipe Pose
mp_pose = mp.solutions.pose

# 軌跡の最大長さ（フレーム数）
TRAIL_LENGTH = 35
SKELETON_TRAIL_LENGTH = 12

# 主要ランドマーク
LEFT_WRIST = mp_pose.PoseLandmark.LEFT_WRIST.value
RIGHT_WRIST = mp_pose.PoseLandmark.RIGHT_WRIST.value
LEFT_ELBOW = mp_pose.PoseLandmark.LEFT_ELBOW.value
RIGHT_ELBOW = mp_pose.PoseLandmark.RIGHT_ELBOW.value
LEFT_SHOULDER = mp_pose.PoseLandmark.LEFT_SHOULDER.value
RIGHT_SHOULDER = mp_pose.PoseLandmark.RIGHT_SHOULDER.value
LEFT_HIP = mp_pose.PoseLandmark.LEFT_HIP.value
RIGHT_HIP = mp_pose.PoseLandmark.RIGHT_HIP.value
LEFT_KNEE = mp_pose.PoseLandmark.LEFT_KNEE.value
RIGHT_KNEE = mp_pose.PoseLandmark.RIGHT_KNEE.value
LEFT_ANKLE = mp_pose.PoseLandmark.LEFT_ANKLE.value
RIGHT_ANKLE = mp_pose.PoseLandmark.RIGHT_ANKLE.value
NOSE = mp_pose.PoseLandmark.NOSE.value

# 描画する骨格コネクション（主要なもの）
POSE_CONNECTIONS = [
    (LEFT_SHOULDER, RIGHT_SHOULDER),
    (LEFT_SHOULDER, LEFT_ELBOW),
    (LEFT_ELBOW, LEFT_WRIST),
    (RIGHT_SHOULDER, RIGHT_ELBOW),
    (RIGHT_ELBOW, RIGHT_WRIST),
    (LEFT_SHOULDER, LEFT_HIP),
    (RIGHT_SHOULDER, RIGHT_HIP),
    (LEFT_HIP, RIGHT_HIP),
    (LEFT_HIP, LEFT_KNEE),
    (LEFT_KNEE, LEFT_ANKLE),
    (RIGHT_HIP, RIGHT_KNEE),
    (RIGHT_KNEE, RIGHT_ANKLE),
]


def speed_to_hue(speed: float, max_speed: float = 45.0) -> int:
    """速度を0-179の色相に変換（速いほど色が回る）"""
    normalized = min(speed / max_speed, 1.0)
    return int((normalized * 180) % 180)


def get_point(landmarks, idx: int, w: int, h: int, min_vis: float = 0.5) -> Optional[Tuple[int, int]]:
    """可視性を確認してピクセル座標を返す"""
    lm = landmarks[idx]
    if lm.visibility < min_vis:
        return None
    return (int(lm.x * w), int(lm.y * h))


def draw_fading_trail(frame, trail: deque, base_hue: int):
    """透明度が減衰する円で軌跡を描画"""
    n = len(trail)
    if n < 2:
        return

    for i, (x, y) in enumerate(trail):
        alpha = (i + 1) / n
        radius = int(7 * alpha + 2)
        hue = (base_hue + int(i * 4)) % 180
        color_hsv = np.uint8([[[hue, 255, 255]]])
        color_bgr = cv2.cvtColor(color_hsv, cv2.COLOR_HSV2BGR)[0][0]
        color = (int(color_bgr[0]), int(color_bgr[1]), int(color_bgr[2]))
        cv2.circle(frame, (int(x), int(y)), radius, color, -1, lineType=cv2.LINE_AA)


def draw_skeleton_with_trail(
    frame,
    landmarks,
    w: int,
    h: int,
    skeleton_history: deque,
    frame_count: int,
):
    """全身骨格を残像付きで描画"""
    # 現在の骨格点を取得
    points = {}
    for idx in [
        LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_ELBOW, RIGHT_ELBOW,
        LEFT_WRIST, RIGHT_WRIST, LEFT_HIP, RIGHT_HIP,
        LEFT_KNEE, RIGHT_KNEE, LEFT_ANKLE, RIGHT_ANKLE, NOSE,
    ]:
        pt = get_point(landmarks, idx, w, h)
        if pt:
            points[idx] = pt

    # 履歴に追加
    skeleton_history.append(points)

    n_hist = len(skeleton_history)
    for hist_i, hist_points in enumerate(skeleton_history):
        # 古いほど薄く
        alpha = (hist_i + 1) / n_hist
        thickness = max(1, int(3 * alpha))
        # 色相を時間でずらす
        base_hue = (frame_count * 2 + hist_i * 8) % 180

        for start_idx, end_idx in POSE_CONNECTIONS:
            if start_idx in hist_points and end_idx in hist_points:
                pt1 = hist_points[start_idx]
                pt2 = hist_points[end_idx]
                hue = (base_hue + (start_idx * 7)) % 180
                color_hsv = np.uint8([[[hue, 220, 255]]])
                color_bgr = cv2.cvtColor(color_hsv, cv2.COLOR_HSV2BGR)[0][0]
                color = (int(color_bgr[0] * alpha), int(color_bgr[1] * alpha), int(color_bgr[2] * alpha))
                cv2.line(frame, pt1, pt2, color, thickness, lineType=cv2.LINE_AA)

        # 関節点も描画
        for idx, pt in hist_points.items():
            hue = (base_hue + idx * 5) % 180
            color_hsv = np.uint8([[[hue, 255, 255]]])
            color_bgr = cv2.cvtColor(color_hsv, cv2.COLOR_HSV2BGR)[0][0]
            r = max(2, int(5 * alpha))
            cv2.circle(frame, pt, r, (int(color_bgr[0]), int(color_bgr[1]), int(color_bgr[2])), -1, cv2.LINE_AA)


def draw_torso_ripples(
    frame,
    hip_center: Optional[Tuple[int, int]],
    sway_history: deque,
    frame_count: int,
):
    """腰の揺れ幅に応じて体幹から波紋を発生させる"""
    if hip_center is None or len(sway_history) < 5:
        return

    # 最近の揺れ幅（水平方向の標準偏差っぽいもの）を計算
    recent = list(sway_history)[-20:]
    xs = [p[0] for p in recent]
    if len(xs) < 3:
        return

    mean_x = np.mean(xs)
    sway_amp = np.std(xs)  # 揺れの大きさ

    # 揺れが小さいときは波紋を弱く / 出さない
    if sway_amp < 3.0:
        return

    cx, cy = hip_center

    # 波紋の強さ・数を揺れ幅に比例
    intensity = min(sway_amp / 25.0, 1.5)
    num_rings = int(2 + intensity * 3)

    for i in range(num_rings):
        # 時間とともに広がる
        phase = (frame_count * 0.15 + i * 1.2) % (np.pi * 2)
        radius = int(30 + i * 28 + np.sin(phase) * 12 * intensity)

        # 透明度（外側ほど薄く）
        alpha = max(0.15, 0.7 - i * 0.12) * min(intensity, 1.0)

        # 色相も揺れと時間で変化
        hue = int((frame_count * 3 + sway_amp * 4 + i * 25) % 180)
        color_hsv = np.uint8([[[hue, 200, 255]]])
        color_bgr = cv2.cvtColor(color_hsv, cv2.COLOR_HSV2BGR)[0][0]
        color = (
            int(color_bgr[0] * alpha),
            int(color_bgr[1] * alpha),
            int(color_bgr[2] * alpha),
        )

        thickness = max(1, int(2.5 * alpha + 1))
        cv2.circle(frame, (cx, cy), radius, color, thickness, lineType=cv2.LINE_AA)

        # 内側にもう一枚薄いリングを重ねて厚みを出す
        if radius > 15:
            cv2.circle(frame, (cx, cy), radius - 4, color, 1, lineType=cv2.LINE_AA)


def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("カメラを開けませんでした")
        return

    # 軌跡バッファ
    left_wrist_trail = deque(maxlen=TRAIL_LENGTH)
    right_wrist_trail = deque(maxlen=TRAIL_LENGTH)
    skeleton_history = deque(maxlen=SKELETON_TRAIL_LENGTH)
    hip_sway_history = deque(maxlen=40)  # 腰の位置履歴（波紋用）

    prev_left = None
    prev_right = None
    frame_count = 0

    with mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        enable_segmentation=False,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ) as pose:

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            overlay = frame.copy()

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(rgb)

            hip_center = None

            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark

                # --- 1. 全身骨格 + 残像 ---
                draw_skeleton_with_trail(
                    overlay, landmarks, w, h, skeleton_history, frame_count
                )

                # --- 2. 体幹波紋（腰の揺れ） ---
                left_hip = get_point(landmarks, LEFT_HIP, w, h)
                right_hip = get_point(landmarks, RIGHT_HIP, w, h)

                if left_hip and right_hip:
                    hip_center = (
                        (left_hip[0] + right_hip[0]) // 2,
                        (left_hip[1] + right_hip[1]) // 2,
                    )
                    hip_sway_history.append(hip_center)
                    draw_torso_ripples(overlay, hip_center, hip_sway_history, frame_count)

                # --- 3. 手首の虹色残像（速度連動） ---
                # 左手首
                lw = get_point(landmarks, LEFT_WRIST, w, h)
                if lw:
                    left_wrist_trail.append(lw)
                    speed = 0.0
                    if prev_left is not None:
                        dx = lw[0] - prev_left[0]
                        dy = lw[1] - prev_left[1]
                        speed = np.sqrt(dx * dx + dy * dy)
                    prev_left = lw
                    hue = speed_to_hue(speed)
                    draw_fading_trail(overlay, left_wrist_trail, hue)
                    cv2.circle(overlay, lw, 11, (0, 255, 255), 2, cv2.LINE_AA)

                # 右手首
                rw = get_point(landmarks, RIGHT_WRIST, w, h)
                if rw:
                    right_wrist_trail.append(rw)
                    speed = 0.0
                    if prev_right is not None:
                        dx = rw[0] - prev_right[0]
                        dy = rw[1] - prev_right[1]
                        speed = np.sqrt(dx * dx + dy * dy)
                    prev_right = rw
                    hue = speed_to_hue(speed)
                    draw_fading_trail(overlay, right_wrist_trail, hue)
                    cv2.circle(overlay, rw, 11, (0, 255, 255), 2, cv2.LINE_AA)

            # ブレンド（元映像を少し残す）
            result = cv2.addWeighted(frame, 0.25, overlay, 0.75, 0)

            # UI
            cv2.putText(
                result,
                "Full Skeleton + Torso Ripples + Wrist Trails  |  q: quit",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

            cv2.imshow("Psychedelic Pose Projection", result)

            frame_count += 1
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
