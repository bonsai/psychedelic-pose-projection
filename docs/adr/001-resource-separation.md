# ADR-001: リソース分離によるエフェクト処理の最適化

- Status: Proposed
- Date: 2026-10-08

## Context

psychedelic-pose-projection は、スマホ単体で動作することを基本とし、PCをfallbackとして利用する。
Pose、輪郭抽出、Particle、AIによる演出判断をすべて同一プロセス・同一デバイスで実行すると、CPU/GPU/メモリ/バッテリーを圧迫する。
エフェクトを進化させるループでは、毎フレーム処理と低頻度の分析・探索処理を分離する必要がある。

## Decision

**処理内容ではなく、リソース特性によって責務を分離する。**

### Smartphone: Real-time layer

- Camera
- MediaPipe Pose
- JEVによる輪郭 / Edge / Silhouette抽出
- 軽量なShape Attributes生成
- JS / WebGL Particle
- Projection
- Touch / UI

毎フレーム必要な処理を中心にする。

### PC: Compute / Intelligence layer

- Python
- LangGraph
- LLM / AI
- OpenCV
- Rust Particle Simulation
- 大量Particle計算
- 輪郭・形状の高度な解析
- エフェクト探索・評価

### Graph layer

HoudiniライクなNode / Attribute / Graphとして処理を表現する。

~~~text
Pose ───────┐
             ├→ Attributes → Effect Graph → Render
JEV Contour ┘
~~~

JEVは「画像上の形状」を、Poseは「身体の意味」を提供する。

## Resource allocation

| Resource | Smartphone | PC fallback |
|---|---|---|
| CPU | Pose / 軽量JEV | Python / OpenCV / LangGraph |
| GPU | WebGL / Particle / Projection | Rust / GPU simulation candidate |
| Memory | フレーム・軽量属性 | 大量Particle / cache |
| Network | 必要時のみ | Effect JSON / metrics |
| Battery | 最小化 | 制約を緩和 |
| AI | optional | primary |

## Optimization rules

1. **毎フレーム処理を最小化する**
2. 重い処理は低頻度またはPCへ移す
3. Pose / Contourは同じ画像を可能な限り共有する
4. Attributesを中間表現として再利用する
5. Effect GraphとRendererを分離する
6. JSONは差分・必要パラメータ中心にする
7. PC fallbackがなくても基本演出は停止しない
8. ボトルネックを計測してからRust/WASMへ移す

## Effect evolution loop

高コストな探索・評価を毎フレーム行わない。

~~~text
Smartphone
  ↓
Pose + JEV Contour
  ↓
Attributes
  ↓
Effect
  ↓
Render
  ↓
Metrics
  ↓
PC fallback
  ↓
LangGraph
  ↓
Evaluate / Modify
  ↓
Effect Parameters / Graph
  ↓
Smartphone
  ↺
~~~

これにより、**リアルタイム描画と、エフェクトを進化させる計算を別リソースとして扱う。**

## Consequences

### Positive

- スマホ単体でも動作できる
- PC接続時だけ高度化できる
- バッテリー消費を抑えやすい
- Particle処理をRustへ段階的に移せる
- JEVの輪郭情報とPose情報を同じGraphで合成できる
- LangGraphによるエフェクト進化を非同期化できる

### Negative

- Smartphone ↔ PC間の通信設計が必要
- リアルタイム状態と探索状態の同期が必要
- 同じEffect Graphを複数runtimeで実装する可能性がある

## Future

- Rust → WASMによるスマホ側高速化
- WebGPUへの移行
- JEVの輪郭処理をGPU化
- Effect Graphを共通JSON/IRとして定義
- Pose / Contour / Particleを同一Attribute systemで扱う