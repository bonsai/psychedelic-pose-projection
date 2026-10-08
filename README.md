# Psychedelic Pose Projection

MediaPipe Pose を使ったダンス強調システム。骨格追跡、虹色残像、体幹波紋、体の輪郭を使った炎・水・ダンサー残像エフェクトを含みます。

## 構成

```text
.
├── .github/workflows/         # GitHub Actions（Windows EXE 自動ビルド）
├── linux/                     # 元の Linux 版（OpenCV + MediaPipe Solutions）
│   ├── main.py
│   ├── calibration.py
│   └── requirements.txt
├── windows/                   # Windows 版（MediaPipe Tasks API + モード切替）
│   ├── main_tasks.py
│   ├── build-exe.ps1
│   └── requirements.txt
├── processing/                # Processing + OSC 連携版
│   ├── sender.py
│   └── psychedelic_pose_projection.pde
└── tools/
    ├── attach-camera.ps1      # WSL2 用カメラアタッチスクリプト
    └── mcp-server/            # MCP サーバー
```

## クイックスタート

### Windows ネイティブ

```powershell
cd windows
pip install -r requirements.txt
python main_tasks.py
```

キー：`1` 通常 / `2` 炎 / `3` 水 / `4` ダンサー残像 / `q` 終了

### Windows EXE ビルド

```powershell
cd windows
.\build-exe.ps1
```

出力：`windows/dist/PsychedelicPoseProjection.exe`

### Linux / WSL

```bash
cd linux
pip install -r requirements.txt
python main.py
```

WSL2 でカメラが認識しない場合は `tools/attach-camera.ps1` を Windows PowerShell（管理者）で実行してください。

### Processing 連携

1. `processing/sender.py` を Python で起動
2. Processing IDE で `processing/psychedelic_pose_projection.pde` を開き、`oscP5` ライブラリをインストールして実行

## 自動ビルド

`main` ブランチに push するたび、GitHub Actions で Windows EXE がビルドされます。リポジトリ設定で Workflow の実行許可を有効にしてください。
