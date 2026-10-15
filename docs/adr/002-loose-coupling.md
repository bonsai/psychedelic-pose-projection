# ADR-002: Loosely Coupled Pose Interpretation and Rendering

- Status: Accepted
- Date: 2026-10-15

## Context

Pose capture, motion interpretation, real-time rendering, effect design and evaluation should be independently replaceable. Mixing them makes model changes ripple into renderers and makes isolated tests difficult.

The modular approach used in `bonsai/air-shodo` separates tracking, physics, stroke history, rendering and export. This project follows the same principle and keeps the live runtime in `bonsai/mpp5`.

## Decision

The executable runtime is centralized in [mpp5](https://github.com/bonsai/mpp5):

1. **Python interpreter** owns camera capture, MediaPipe, confidence filtering and motion attributes.
2. **WebSocket adapter** publishes game-state features to the p5.js renderer.
3. **OSC adapter** publishes normalized landmarks and derived attributes to Processing/Java.
4. **Renderers** draw visuals only; they do not run pose detection or infer gesture semantics.
5. **Research/evaluation** stays in this repository and does not sit on the per-frame critical path.

The OSC payload is described in [Pose Attributes Contract v1](../contracts/pose-attributes-v1.md).

## Rules

- Runtime code belongs in `bonsai/mpp5`; this repository is for research, evaluation and effect design.
- Python and renderer implementations do not import each other's code.
- No renderer runs MediaPipe or makes gesture decisions.
- No interpreter contains visual-effect drawing logic.
- Communication uses primitive, documented attributes; unknown messages are ignored.
- Keep VLM, LangGraph, evaluation and asset-generation systems off the per-frame critical path.
- Add features through new messages/adapters or separate modules rather than expanding a monolith.

## Consequences

- Pose models and renderers can be replaced independently.
- The Python interpreter can feed multiple renderers from one camera session.
- Additional consumers (logging, evaluation, 3D scene control) can subscribe without coupling to a renderer.
- The OSC contract requires compatibility discipline and tests for dropped/stale packets.

## Acceptance criteria

- One Python camera/MediaPipe process publishes to WebSocket and OSC.
- p5.js and Processing renderers can be used independently or simultaneously.
- Renderers can be exercised using recorded OSC samples without a camera.
- Raw camera frames are not persisted.
