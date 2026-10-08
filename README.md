# Psychedelic Pose Projection

MediaPipe Poseを起点に、身体の動きを**映像エフェクトへ変換し、評価し、次の動画生成へ戻す**実験プロジェクトです。

単なるPoseエフェクトではなく、

**Pose → Attributes → Effect Graph → Render → Evaluate → Experiment → Next Generation**

という映像生成ループを作ります。

## Demo

GitHub Pages Demo: https://bonsai.github.io/psychedelic-pose-projection/

現在は `data/captf/` に、Poseを使ったサイケデリックなエフェクト生成結果を掲載しています。

## コンセプト

```text
Camera
  ↓
MediaPipe Pose
  ↓
Pose Attributes
  ├─ position
  ├─ velocity
  ├─ speed
  ├─ direction
  ├─ confidence
  └─ energy
  ↓
Houdini-like Effect Graph
  ↓
Particle / Trail / Noise / Wave / Glow
  ↓
WebGL / Canvas / Projection
  ↓
Frame / Video
  ↓
VLM / MLLM + ojev
  ↓
bqmilite
  ↓
Control / Experimental
  ↓
YouTube viewer behavior
  ↓
Next Generation
  ↺
```

## 重要な考え方

### 1. スマホで動く、PCがあると賢くなる

スマートフォン側ではリアルタイム処理を優先します。

- Camera
- MediaPipe Pose
- 軽量なShape / Contour処理
- Particle / WebGL / Canvas
- Projection
- Touch / STT / Gesture

PC側では重い処理や知的な処理を担当します。

- Python
- OpenCV
- ojev
- VLM / MLLM
- LangGraph
- bqmilite
- Rust Particle Simulation

**「PCがないと動かない」ではなく、「PCがあると賢くなる」**を基本方針にします。

### 2. HoudiniライクなAttribute / Graph

Houdiniそのものに依存するのではなく、Node / Attribute / Graphの考え方を取り入れます。

```text
POSE
 ↓
ATTRIBUTES
 ↓
EMITTER
 ↓
PARTICLE
 ├─ TRAIL
 ├─ NOISE
 ├─ WAVE
 ├─ SPARK
 └─ GLOW
 ↓
COMPOSITE
 ↓
PROJECTION
```

Poseを単なる座標ではなく、エフェクトを駆動する属性として扱います。

### 3. 評価は目的ではなく、動画生成の教師

VLM / MLLM、ojev、bqmilite、YouTube視聴維持率などを評価信号として利用します。

特にYouTubeの視聴維持率は**唯一の目的関数ではありません**。

```text
動画生成
  ↓
Control / Experimental
  ↓
公開
  ↓
視聴者の反応
  ↓
評価
  ↓
改善条件
  ↓
次の動画生成
  ↺
```

## 評価・進化パイプライン

- **ojev** — 画像・輪郭・形状などの前処理
- **VLM / MLLM** — 映像としての見え方を評価
- **bqmilite** — 評価値の正規化・重み付け・統計処理
- **LangGraph** — 評価から次の生成条件までのループ制御
- **YouTube** — 実際の視聴者行動を外部教師信号として利用

## リソース分離

リアルタイム性と知的処理を同じ場所で行わない方針です。

```text
Smartphone
  Pose / Contour
      ↓
  Attributes
      ↓
  Effect
      ↓
  Render
      ↓
  Metrics
      ↓
PC
  VLM / MLLM
  LangGraph
  Rust
  Evaluation
      ↓
Effect Parameters / Graph
      ↓
Smartphone
```

詳細はADR-001を参照してください。

## 実験設計

動画生成条件をControl / Experimentalに分け、できるだけ条件を固定して比較します。

記録するもの：

- generation parameters
- Pose / ojev features
- VLM / MLLM scores
- viewer metrics
- 改善内容
- 次のgeneration parameters

実験を一回で終わらせず、世代として追跡します。

```text
exp-001
   ↓
exp-002
   ↓
exp-003
   ↓
...
```

## Repository

```text
data/
  captf/              # GitHub Pages用デモ
  capt_frames/        # 生成フレーム

docs/
  adr/
    001-resource-separation.md

.github/
  workflows/
    pages.yml
```

既存のPython / Windows / Linux / Processing実装は、それぞれ実験・実行環境として維持します。

## Issue Map

### Effect / Runtime

- #2 HoudiniライクなPose Particle Compositor
- #3 iPad対応
- #4 スマホ完結・PC fallback・エフェクト進化

### Evaluation

- #5 VLM / MLLMによるエフェクト評価・進化
  - #13 評価スキーマ
  - #14 ojev / Pose前処理
  - #15 評価→パラメータ提案
  - #16 LangGraphループ
  - #17 評価タイミング最適化

### Pipeline

- #6 動画生成の評価・改善パイプライン
  - #18 ojev前処理
  - #19 bqmilite
  - #20 STT / Gesture
  - #21 自動評価
  - #22 Dashboard

### Experiment

- #7 視聴維持率を教師信号とする対照実験
  - #8 条件固定・記録
  - #9 YouTubeデータ
  - #10 評価統合
  - #11 次の生成条件
  - #12 実験可視化

## Status

現在は、既存のPoseエフェクト実験から**「評価できる動画生成システム」への移行段階**です。

最終的には、

> **身体を動かす → 映像が生まれる → 見られる → 評価される → 次の映像が変わる**

という生成ループを作ります。
