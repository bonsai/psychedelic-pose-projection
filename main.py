#!/usr/bin/env python3
"""
Psychedelic Pose Projection - Phase 1
手首追尾 + 速度連動虹色残像
"""

import cv2
import mediapipe as mp
import numpy as np
from collections import deque

# Mediapipe Pose
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

# 軌跡の最大長さ（フレーム数）
TRAIL_LENGTH = 40

# 手首ランドマークインデックス
LEFT_WRIST = mp_pose.PoseLandmark.LEFT_WRIST.value
RIGHT_WRIST = mp_pose.PoseLandmark.RIGHT_WRIST.value


def speed_to_hue(speed: float, max_speed: float = 50.0) -> int:
    """速度を0-179の色相に変換（速いほど色が回る）"""
    # 正規化して色相をぐるぐる回す
    normalized = min(speed / max_speed, 1.0)
    hue = int((normalized * 180) % 180)
    return hue


def draw_fading_trail(frame, trail, base_hue: int):
    """透明度が減衰する円で軌跡を描画"""
    n = len(trail)
    if n < 2:
        return

    for i, (x, y) in enumerate(trail):
        # 古いほど薄く・小さく
        alpha = (i + 1) / n
        radius = int(8 * alpha + 2)
        # 色相を少しずつずらして虹っぽく
        hue = (base_hue + int(i * 3)) % 180
        color_hsv = np.uint8([[[hue, 255, 255]]])
        color_bgr = cv2.cvtColor(color_hsv, cv2.COLOR_HSV2BGR)[0][0]
        color = (int(color_bgr[0]), int(color_bgr[1]), int(color_bgr[2]))

        # 半透明っぽく重ねるために複数回薄く描く代わりに直接描画
        cv2.circle(frame, (int(x), int(y)), radius, color, -1, lineType=cv2.LINE_AA)


def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("カメラを開けませんでした")
        return

    # 軌跡バッファ（左右手首）
    left_trail = deque(maxlen=TRAIL_LENGTH)
    right_trail = deque(maxlen=TRAIL_LENGTH)

    prev_left = None
    prev_right = None

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

            # 鏡像にして自然な操作感に
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape

            # 暗い背景で残像を目立たせる（任意）
            overlay = frame.copy()

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(rgb)

            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark

                # 左手首
                lw = landmarks[LEFT_WRIST]
                if lw.visibility > 0.5:
                    lx, ly = int(lw.x * w), int(lw.y * h)
                    left_trail.append((lx, ly))

                    # 速度計算
                    speed = 0.0
                    if prev_left is not None:
                        dx = lx - prev_left[0]
                        dy = ly - prev_left[1]
                        speed = np.sqrt(dx * dx + dy * dy)
                    prev_left = (lx, ly)

                    hue = speed_to_hue(speed)
                    draw_fading_trail(overlay, left_trail, hue)

                    # 現在位置の強調
                    cv2.circle(overlay, (lx, ly), 12, (0, 255, 255), 2, cv2.LINE_AA)

                # 右手首
                rw = landmarks[RIGHT_WRIST]
                if rw.visibility > 0.5:
                    rx, ry = int(rw.x * w), int(rw.y * h)
                    right_trail.append((rx, ry))

                    speed = 0.0
                    if prev_right is not None:
                        dx = rx - prev_right[0]
                        dy = ry - prev_right[1]
                        speed = np.sqrt(dx * dx + dy * dy)
                    prev_right = (rx, ry)

                    hue = speed_to_hue(speed)
                    draw_fading_trail(overlay, right_trail, hue)

                    cv2.circle(overlay, (rx, ry), 12, (0, 255, 255), 2, cv2.LINE_AA)

            # 少しブレンドして元画像を残す
            result = cv2.addWeighted(frame, 0.3, overlay, 0.7, 0)

            # 操作説明
            cv2.putText(
                result,
                "Move your wrists! Speed = Hue  |  q: quit",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

            cv2.imshow("Psychedelic Pose - Wrist Trails", result)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
