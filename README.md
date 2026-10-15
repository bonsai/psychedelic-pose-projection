# Psychedelic Pose Projection

MediaPipe Poseを起点に、身体の動きを映像エフェクトへ変換し、評価・改善するための研究・実験プロジェクトです。

**Pose → Attributes → Effect Graph → Render → Evaluate → Experiment → Next Generation**

## Demo / 実行先

GitHub Pagesの既存デモと生成結果は以下にあります。

- [GitHub Pages](https://bonsai.github.io/psychedelic-pose-projection/)
- [生成エフェクト資料](data/captf/)

**リアルタイム実行コードは [bonsai/mpp5](https://github.com/bonsai/mpp5) に集約しました。** 本リポジトリからProcessing/Javaランタイムを移し、姿勢解釈はPython、描画はmpp5側のProcessing（Java）またはp5.jsが担当します。

## 疎結合アーキテクチャ

```text
Local Camera
  ↓
mpp5 / Python: OpenCV + MediaPipe + motion attributes
  ├─ WebSocket → p5.js underwater renderer
  └─ OSC/UDP → Processing Java renderer
  ↓
Display / Projector
```

- Pythonがカメラ、姿勢検出、visibility判定、手首速度、腰の揺れを解釈
- 描画側は受け取った属性を視覚表現に変換するだけ
- 通信はローカルWebSocketまたはOSC。生映像を保存・送信しない
- VLM、LangGraph、評価、素材生成はフレームごとの描画経路から切り離す

セットアップは [mpp5 README](https://github.com/bonsai/mpp5#readme) を参照してください。

## 研究コンセプト

```text
Pose → Attributes → Effect Graph
  → Particle / Trail / Noise / Wave / Glow
  → Render → Evaluate → Experiment
  → Next Generation
```

Poseを単なる座標ではなく、エフェクトを駆動する属性として扱います。VLM/MLLM、ojev、bqmilite、LangGraphは、必要に応じてオフライン評価や次の生成条件の提案に利用します。

## 疎結合設計

[air-shodoのモジュール分割](https://github.com/bonsai/air-shodo/blob/fc98c3126f0707ac292c3469ff28ad9bfd875900/README.md#L4) と同様に、責務ごとに部品を分離し、明示的な契約で接続します。

- **Python interpreter**: カメラ、MediaPipe、信頼度判定、動きの解釈（mpp5）
- **Transport adapters**: WebSocket / OSCによる属性転送（mpp5）
- **Renderers**: p5.js / Processing Java（mpp5）
- **Research / evaluation**: 本リポジトリの資料・実験成果

設計判断: [ADR-002 — Loose Coupling](docs/adr/002-loose-coupling.md)  
属性契約: [Pose Attributes Contract v1](docs/contracts/pose-attributes-v1.md)

## リポジトリの役割

- `bonsai/psychedelic-pose-projection`: 研究、評価、エフェクト設計、成果物
- `bonsai/mpp5`: Python姿勢解釈とWeb/Java描画の実行PoC
- `bonsai/air-shodo`: 疎結合なモジュール分割の参考

既存のLinux / Windows実装は比較・実験用として維持します。
