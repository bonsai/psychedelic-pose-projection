#!/usr/bin/env python3
"""
プロジェクタ ↔ カメラ キャリブレーション

床や壁に十字・グリッドを投影し、カメラで検出してホモグラフィを計算。
結果は calibration.npz に保存し、実行時に効果画像をワープして投影する。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np

CALIB_FILE = "calibration.npz"
CALIB_JSON = "calibration.json"

# チェスボード設定（投影パターン用）
CHESSBOARD_SIZE = (9, 6)  # 内角点数 (cols, rows)
SQUARE_SIZE_PX = 80       # 投影時の1マスのピクセルサイズ


@dataclass
class CalibrationData:
    """カメラ座標 → プロジェクタ座標 のホモグラフィ"""
    H: np.ndarray                    # 3x3
    projector_size: Tuple[int, int]  # (width, height)
    camera_size: Tuple[int, int]     # (width, height)
    method: str = "homography"

    def save(self, path: str = CALIB_FILE) -> None:
        np.savez(
            path,
            H=self.H,
            projector_size=np.array(self.projector_size),
            camera_size=np.array(self.camera_size),
            method=self.method,
        )
        # 人間が読める JSON も併記
        meta = {
            "projector_size": list(self.projector_size),
            "camera_size": list(self.camera_size),
            "method": self.method,
            "H": self.H.tolist(),
        }
        with open(CALIB_JSON, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
        print(f"キャリブレーションを保存しました: {path} / {CALIB_JSON}")

    @classmethod
    def load(cls, path: str = CALIB_FILE) -> Optional["CalibrationData"]:
        if not os.path.exists(path):
            return None
        data = np.load(path, allow_pickle=True)
        return cls(
            H=data["H"],
            projector_size=tuple(data["projector_size"].tolist()),
            camera_size=tuple(data["camera_size"].tolist()),
            method=str(data["method"]),
        )


def create_chessboard_image(
    proj_w: int,
    proj_h: int,
    board_size: Tuple[int, int] = CHESSBOARD_SIZE,
    square_px: int = SQUARE_SIZE_PX,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    プロジェクタに表示するチェスボード画像と、
    その画像上の角点座標（プロジェクタ座標系）を返す。
    """
    cols, rows = board_size
    board_w = cols * square_px
    board_h = rows * square_px

    # 中央配置
    offset_x = (proj_w - board_w) // 2
    offset_y = (proj_h - board_h) // 2

    img = np.ones((proj_h, proj_w, 3), dtype=np.uint8) * 30  # 暗い背景

    for r in range(rows + 1):
        for c in range(cols + 1):
            x0 = offset_x + c * square_px
            y0 = offset_y + r * square_px
            color = 255 if (r + c) % 2 == 0 else 0
            cv2.rectangle(
                img,
                (x0, y0),
                (x0 + square_px, y0 + square_px),
                (color, color, color),
                -1,
            )

    # 外枠を強調
    cv2.rectangle(
        img,
        (offset_x, offset_y),
        (offset_x + board_w, offset_y + board_h),
        (0, 255, 0),
        3,
    )

    # 中央十字（床合わせ用）
    cx, cy = proj_w // 2, proj_h // 2
    cv2.line(img, (cx - 40, cy), (cx + 40, cy), (0, 0, 255), 2)
    cv2.line(img, (cx, cy - 40), (cx, cy + 40), (0, 0, 255), 2)

    # プロジェクタ座標系の角点（内角）
    obj_pts = []
    for r in range(rows):
        for c in range(cols):
            x = offset_x + c * square_px
            y = offset_y + r * square_px
            obj_pts.append([x, y])
    obj_pts = np.array(obj_pts, dtype=np.float32)

    return img, obj_pts


def create_cross_grid_image(proj_w: int, proj_h: int) -> np.ndarray:
    """床合わせ用の十字 + グリッド画像"""
    img = np.zeros((proj_h, proj_w, 3), dtype=np.uint8)
    cx, cy = proj_w // 2, proj_h // 2

    # 太い十字
    cv2.line(img, (0, cy), (proj_w, cy), (0, 255, 0), 3)
    cv2.line(img, (cx, 0), (cx, proj_h), (0, 255, 0), 3)

    # グリッド
    step = 100
    for x in range(0, proj_w, step):
        cv2.line(img, (x, 0), (x, proj_h), (40, 40, 40), 1)
    for y in range(0, proj_h, step):
        cv2.line(img, (0, y), (proj_w, y), (40, 40, 40), 1)

    # 四隅マーカー
    marker = 60
    for px, py in [(0, 0), (proj_w - 1, 0), (0, proj_h - 1), (proj_w - 1, proj_h - 1)]:
        cv2.circle(img, (px, py), marker, (0, 0, 255), 3)

    cv2.putText(
        img,
        "Align camera so the green cross matches the floor mark",
        (30, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2,
    )
    return img


def detect_chessboard(
    frame: np.ndarray,
    board_size: Tuple[int, int] = CHESSBOARD_SIZE,
) -> Optional[np.ndarray]:
    """カメラ画像からチェスボード角点を検出"""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    flags = cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE
    found, corners = cv2.findChessboardCorners(gray, board_size, flags)
    if not found:
        return None

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
    corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
    return corners.reshape(-1, 2)


def compute_homography(
    src_pts: np.ndarray,
    dst_pts: np.ndarray,
) -> Optional[np.ndarray]:
    """src (カメラ) → dst (プロジェクタ) のホモグラフィ"""
    if len(src_pts) < 4 or len(dst_pts) < 4:
        return None
    H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
    return H


def warp_to_projector(
    image: np.ndarray,
    calib: CalibrationData,
) -> np.ndarray:
    """カメラ空間の画像をプロジェクタ空間にワープ"""
    pw, ph = calib.projector_size
    warped = cv2.warpPerspective(
        image,
        calib.H,
        (pw, ph),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0),
    )
    return warped


# ---------------------------------------------------------------------------
# インタラクティブ 4点キャリブレーション
# ---------------------------------------------------------------------------

class FourPointCalibrator:
    """
    プロジェクタに表示した四隅マーカーをカメラでクリックして対応付ける。
    手順:
      1. プロジェクタに四隅マーカー付き画像を出す
      2. カメラ映像上で、投影された四隅を順番にクリック
         （左上 → 右上 → 右下 → 左下）
      3. Enter で確定
    """

    def __init__(self, projector_size: Tuple[int, int]):
        self.proj_w, self.proj_h = projector_size
        self.camera_points: List[Tuple[int, int]] = []
        self.projector_points = np.array(
            [
                [0, 0],
                [self.proj_w - 1, 0],
                [self.proj_w - 1, self.proj_h - 1],
                [0, self.proj_h - 1],
            ],
            dtype=np.float32,
        )
        self.window_name = "Calibration - Click 4 corners (TL→TR→BR→BL)"

    def _mouse_cb(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and len(self.camera_points) < 4:
            self.camera_points.append((x, y))
            print(f"  点 {len(self.camera_points)}: ({x}, {y})")

    def run(self, cap: cv2.VideoCapture) -> Optional[CalibrationData]:
        print("\n=== 4点キャリブレーション ===")
        print("プロジェクタに四隅マーカーを表示しています。")
        print("カメラ映像上で、投影された四隅を 左上→右上→右下→左下 の順にクリック。")
        print("4点クリック後、Enter で確定 / r でリセット / q でキャンセル\n")

        pattern = create_cross_grid_image(self.proj_w, self.proj_h)
        cv2.namedWindow("Projector - Calibration Pattern", cv2.WINDOW_NORMAL)
        cv2.setWindowProperty(
            "Projector - Calibration Pattern", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN
        )
        cv2.imshow("Projector - Calibration Pattern", pattern)

        cv2.namedWindow(self.window_name)
        cv2.setMouseCallback(self.window_name, self._mouse_cb)

        cam_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        cam_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.flip(frame, 1)
            display = frame.copy()

            # クリック済みの点を描画
            for i, (px, py) in enumerate(self.camera_points):
                cv2.circle(display, (px, py), 8, (0, 255, 255), -1)
                cv2.putText(
                    display,
                    str(i + 1),
                    (px + 12, py - 8),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 255),
                    2,
                )
            if len(self.camera_points) >= 2:
                pts = np.array(self.camera_points, dtype=np.int32)
                cv2.polylines(display, [pts], False, (0, 200, 255), 2)

            msg = f"Points: {len(self.camera_points)}/4  |  Enter: confirm  r: reset  q: cancel"
            cv2.putText(
                display, msg, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2
            )

            cv2.imshow(self.window_name, display)
            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                print("キャリブレーションをキャンセルしました")
                cv2.destroyWindow(self.window_name)
                cv2.destroyWindow("Projector - Calibration Pattern")
                return None

            if key == ord("r"):
                self.camera_points.clear()
                print("リセット")

            if key == 13 and len(self.camera_points) == 4:  # Enter
                src = np.array(self.camera_points, dtype=np.float32)
                H = compute_homography(src, self.projector_points)
                if H is None:
                    print("ホモグラフィの計算に失敗しました。点を取り直してください。")
                    self.camera_points.clear()
                    continue

                calib = CalibrationData(
                    H=H,
                    projector_size=(self.proj_w, self.proj_h),
                    camera_size=(cam_w, cam_h),
                    method="4point",
                )
                calib.save()
                print("4点キャリブレーション完了")
                cv2.destroyWindow(self.window_name)
                cv2.destroyWindow("Projector - Calibration Pattern")
                return calib

        cv2.destroyWindow(self.window_name)
        cv2.destroyWindow("Projector - Calibration Pattern")
        return None


# ---------------------------------------------------------------------------
# チェスボード自動キャリブレーション
# ---------------------------------------------------------------------------

def run_chessboard_calibration(
    cap: cv2.VideoCapture,
    projector_size: Tuple[int, int],
) -> Optional[CalibrationData]:
    """
    チェスボードを投影し、カメラで検出してホモグラフィを計算。
    スペースでキャプチャ、q でキャンセル。
    """
    proj_w, proj_h = projector_size
    pattern, proj_corners = create_chessboard_image(proj_w, proj_h)

    print("\n=== チェスボードキャリブレーション ===")
    print("プロジェクタにチェスボードを表示しています。")
    print("カメラで全体が入るように調整し、スペースでキャプチャ / q でキャンセル\n")

    cv2.namedWindow("Projector - Chessboard", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(
        "Projector - Chessboard", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN
    )
    cv2.imshow("Projector - Chessboard", pattern)

    cam_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    cam_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.flip(frame, 1)
        display = frame.copy()

        corners = detect_chessboard(frame)
        if corners is not None:
            cv2.drawChessboardCorners(display, CHESSBOARD_SIZE, corners.reshape(-1, 1, 2), True)
            cv2.putText(
                display,
                "DETECTED - Press SPACE to capture",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2,
            )
        else:
            cv2.putText(
                display,
                "Searching chessboard...  q: cancel",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 100, 255),
                2,
            )

        cv2.imshow("Calibration - Camera", display)
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            print("キャンセル")
            cv2.destroyWindow("Calibration - Camera")
            cv2.destroyWindow("Projector - Chessboard")
            return None

        if key == ord(" ") and corners is not None:
            H = compute_homography(corners, proj_corners)
            if H is None:
                print("ホモグラフィ計算失敗。もう一度試してください。")
                continue

            calib = CalibrationData(
                H=H,
                projector_size=(proj_w, proj_h),
                camera_size=(cam_w, cam_h),
                method="chessboard",
            )
            calib.save()
            print("チェスボードキャリブレーション完了")
            cv2.destroyWindow("Calibration - Camera")
            cv2.destroyWindow("Projector - Chessboard")
            return calib

    cv2.destroyWindow("Calibration - Camera")
    cv2.destroyWindow("Projector - Chessboard")
    return None


def run_calibration_menu(
    cap: cv2.VideoCapture,
    projector_size: Tuple[int, int] = (1920, 1080),
) -> Optional[CalibrationData]:
    """キャリブレーション方法を選択して実行"""
    print("\n==============================")
    print("  プロジェクタキャリブレーション")
    print("==============================")
    print("1. 4点クリック（手軽・おすすめ）")
    print("2. チェスボード自動検出")
    print("3. キャンセル")
    choice = input("選択 [1/2/3]: ").strip()

    if choice == "1":
        cal = FourPointCalibrator(projector_size)
        return cal.run(cap)
    elif choice == "2":
        return run_chessboard_calibration(cap, projector_size)
    else:
        print("キャンセルしました")
        return None
