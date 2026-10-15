# Processing (Java) renderer + Python pose interpreter

この実行経路は **描画をProcessingのJava mode、姿勢検出と動きの解釈をPythonだけ**に分離しています。p5.js / JavaScript Canvasは描画ランタイムに使用しません。

## 構成

- `sender.py`: OpenCVでローカルカメラを読み、MediaPipe Poseを実行。visibilityで点を選別し、手首速度と腰の揺れを計算してOSC送信
- `psychedelic_pose_projection.pde`: OSC受信後の描画のみ。骨格・残像・波紋を表示
- OSC: `127.0.0.1:12000/UDP`

## 1. Processingの準備

1. Processing 4をインストール
2. Processing IDEの **Sketch → Import Library… → Manage Libraries…** を開く
3. `oscP5` を検索してインストール
4. `psychedelic_pose_projection.pde` をIDEで開く

## 2. Pythonの準備（Windows / PowerShell）

リポジトリのルートから実行します。

```powershell
cd processing
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe sender.py
```

または `processing\start.ps1` を実行してください。MediaPipeのwheel対応状況に合わせ、Python 3.11を推奨します。

## 3. 起動順序

1. Processing IDEで `psychedelic_pose_projection.pde` をRun
2. PowerShellで `sender.py` を起動
3. カメラに全身が映る位置に立つ
4. PythonプレビューまたはProcessingウィンドウを確認
5. Pythonプレビューで `q` を押すとPython側を終了

Processingウィンドウは `q` で終了できます。OSCのポート12000を他のアプリが使っていないことを確認してください。

## OSCメッセージ契約

| Address | Payload | 解釈する側 |
|---|---|---|
| `/pose/points` | 14点 × (x,y)、正規化座標 | Pythonが点とvisibilityを選別 |
| `/left_speed` | 左手首のフレーム間移動量 | Python |
| `/right_speed` | 右手首のフレーム間移動量 | Python |
| `/hip_sway` | 腰の横揺れ強度（0〜1.5） | Python |

描画側は属性を再解釈せず、座標・値を画面表現に変換します。visibilityが低い点は画面外座標として送られ、描画されません。

## トラブルシューティング

- **カメラを開けない**: Windowsのカメラ権限と、カメラを占有しているアプリを確認
- **Processingに何も出ない**: Processingを先に起動し、OSC Library `oscP5` がインストールされているか確認
- **動きが遅い**: 他のカメラアプリを閉じ、Pythonのカメラ解像度・MediaPipeモデル複雑度を調整
- **黒背景で投影**: Processingウィンドウをプロジェクタへ移し、OSのディスプレイ設定で拡張表示

カメラ映像は保存せず、OSCデータもローカルホスト内で送受信します。
