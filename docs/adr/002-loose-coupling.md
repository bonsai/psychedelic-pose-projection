# ADR-002: Loosely Coupled Pose Interpretation and Rendering

- Status: Accepted
- Date: 2026-10-15

## Context

The project combines camera capture, pose estimation, motion interpretation, real-time rendering, effect design and later evaluation. If these concerns share implementation details, changing a pose model or renderer forces unrelated parts to change and makes isolated testing difficult.

The modular approach used in `bonsai/air-shodo` separates hand tracking, brush physics, stroke history, turtle rendering and export behind clear responsibilities. This project applies the same principle to body-pose visuals.

## Decision

Separate the runtime into replaceable components connected by a versioned logical contract:

1. **Python interpreter** owns camera capture, MediaPipe, confidence filtering and semantic motion attributes.
2. **OSC adapter** transports attributes over localhost UDP. It is an adapter, not the place for domain interpretation.
3. **Processing (Java mode) renderer** owns display-coordinate mapping and visual output only.
4. **Replay/evaluation tools** consume recorded attribute samples or rendered frames offline; they must not be required for the live render loop.

The contract is documented in [Pose Attributes Contract v1](../contracts/pose-attributes-v1.md).

## Rules

- No Python implementation imports from Processing; no Java implementation depends on Python modules.
- No renderer runs MediaPipe or makes gesture decisions.
- No interpreter contains visual-effect drawing logic.
- Communication uses primitive, documented attributes; unknown messages are ignored.
- Replaceable components must be testable independently with fake camera data, recorded OSC samples or a mock receiver.
- Keep the live loop deterministic and local. VLM, LangGraph, evaluation and asset-generation systems must not sit in the per-frame critical path.
- New features should be added as a new message/adapter or separate module rather than by expanding a monolith.

## Consequences

Benefits:
- Pose model and renderer can be replaced independently.
- Camera-free tests can validate the renderer; renderer-free tests can validate interpretation.
- Additional consumers (logging, evaluation, 3D scene control) can subscribe without coupling to the renderer.

Costs:
- The OSC contract needs documentation and compatibility discipline.
- OSC messages can be dropped, so consumers must handle stale/missing values.
- Shared contract changes require coordinated tests and version notes.

## Acceptance criteria

- The Python producer sends only filtered landmarks and derived attributes.
- Processing renders received values without calculating gesture meaning.
- The renderer can be exercised using prerecorded OSC samples.
- Camera, raw video and external AI services are not required for renderer unit tests.
