#!/usr/bin/env python3
"""
Psychedelic Pose Projection - OSC sender
MediaPipe Pose で骨格を検出し、Processing へ OSC で送信する。
"""

import math
from collections import deque

import cv2
import mediapipe as mp
from pythonosc import udp_client

mp_pose = mp.solutions.pose

LANDMARKS = [
    mp_pose.PoseLandmark.NOSE,
    mp_pose.PoseLandmark.LEFT_SHOULDER,
    mp_pose.PoseLandmark.RIGHT_SHOULDER,
    mp_pose.PoseLandmark.LEFT_ELBOW,
    mp_pose.PoseLandmark.RIGHT_ELBOW,
    mp_pose.PoseLandmark.LEFT_WRIST,
    mp_pose.PoseLandmark.RIGHT_WRIST,
    mp_pose.PoseLandmark.LEFT_HIP,
    mp_pose.PoseLandmark.RIGHT_HIP,
    mp_pose.PoseLandmark.LEFT_KNEE,
    mp_pose.PoseLandmark.RIGHT_KNEE,
    mp_pose.PoseLandmark.LEFT_ANKLE,
    mp_pose.PoseLandmark.RIGHT_ANKLE,
]


def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("カメラを開けませんでした")
        return

    client = udp_client.SimpleUDPClient("127.0.0.1", 12000)

    prev_left = None
    prev_right = None
    hip_x_history = deque(maxlen=20)

    with mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        enable_segmentation=False,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ) as pose:

        print("OSC 送信開始: 127.0.0.1:12000")
        print("q キーで終了")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(rgb)

            if results.pose_landmarks:
                lm = results.pose_landmarks.landmark

                points = []
                for lm_type in LANDMARKS:
                    l = lm[lm_type.value]
                    # Python owns interpretation and confidence filtering.
                    if l.visibility >= 0.35:
                        points.extend([l.x, l.y])
                    else:
                        points.extend([-1.0, -1.0])

                left_hip = lm[mp_pose.PoseLandmark.LEFT_HIP.value]
                right_hip = lm[mp_pose.PoseLandmark.RIGHT_HIP.value]
                if min(left_hip.visibility, right_hip.visibility) >= 0.35:
                    hip_center_x = (left_hip.x + right_hip.x) / 2.0
                    hip_center_y = (left_hip.y + right_hip.y) / 2.0
                    points.extend([hip_center_x, hip_center_y])
                    hip_x_history.append(hip_center_x)
                    sway_px = 0.0
                    if len(hip_x_history) >= 5:
                        mean_x = sum(hip_x_history) / len(hip_x_history)
                        variance = sum((x - mean_x) ** 2 for x in hip_x_history) / len(hip_x_history)
                        sway_px = min(math.sqrt(variance) * w / 25.0, 1.5)
                else:
                    points.extend([-1.0, -1.0])
                    sway_px = 0.0

                client.send_message("/pose/points", points)
                client.send_message("/hip_sway", float(sway_px))

                left_wrist = (
                    lm[mp_pose.PoseLandmark.LEFT_WRIST.value].x * w,
                    lm[mp_pose.PoseLandmark.LEFT_WRIST.value].y * h,
                )
                right_wrist = (
                    lm[mp_pose.PoseLandmark.RIGHT_WRIST.value].x * w,
                    lm[mp_pose.PoseLandmark.RIGHT_WRIST.value].y * h,
                )

                left_speed = 0.0
                if prev_left is not None:
                    left_speed = math.hypot(
                        left_wrist[0] - prev_left[0], left_wrist[1] - prev_left[1]
                    )
                prev_left = left_wrist

                right_speed = 0.0
                if prev_right is not None:
                    right_speed = math.hypot(
                        right_wrist[0] - prev_right[0], right_wrist[1] - prev_right[1]
                    )
                prev_right = right_wrist

                client.send_message("/left_speed", left_speed)
                client.send_message("/right_speed", right_speed)

            cv2.imshow("Python Pose Interpreter (q: quit)", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
