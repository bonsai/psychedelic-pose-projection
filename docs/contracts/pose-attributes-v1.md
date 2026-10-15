# Pose Attributes Contract v1

Status: Active for the local Python → Processing runtime.

## Purpose

Keep pose interpretation independent from rendering. Python is the producer of interpreted pose data; Processing/Java is a consumer that renders it. Neither side imports code from the other.

## Transport

- Protocol: OSC over UDP
- Host: `127.0.0.1`
- Port: `12000`
- Coordinate space: normalized camera coordinates, origin at the top-left, x increases rightward and y downward
- Update policy: latest value wins; renderers must tolerate dropped packets
- Privacy: raw camera frames are not part of this contract and are not persisted by the runtime

## Messages

| OSC address | Payload | Meaning | Owner |
|---|---|---|---|
| `/pose/points` | ordered x,y float pairs | Normalized landmark positions; `(-1,-1)` means unavailable | Python interprets/filters; Java renders |
| `/left_speed` | one float | Left wrist movement speed, normalized by Python | Python |
| `/right_speed` | one float | Right wrist movement speed, normalized by Python | Python |
| `/hip_sway` | one float, range 0–1.5 | Estimated lateral hip-motion intensity | Python |

The ordered landmark list is defined by `LANDMARKS` in `processing/sender.py`. Any order or payload-shape change is a contract change and must update this document and both ends together.

## Responsibility boundaries

### Python producer

- Capture the local camera and run MediaPipe
- Apply visibility/confidence thresholds
- Derive movement features and reset values when tracking is lost
- Publish only normalized landmarks and semantic attributes

### Processing/Java consumer

- Receive OSC messages
- Map normalized coordinates to display coordinates
- Draw trails, skeletons, particles and visual effects
- Avoid re-detecting poses or inferring gesture semantics

## Compatibility rules

1. Add new OSC addresses without changing existing message meanings.
2. Treat missing/stale attributes as neutral values.
3. Ignore unknown OSC addresses.
4. Keep transport adapters replaceable; a future WebSocket or file-replay adapter must implement the same logical attributes.
5. Test the Python producer with a fake OSC receiver and the Java renderer with recorded OSC samples, without requiring a camera for every test.

## Extension points

A new interpreter (e.g. another pose model) may replace the Python producer if it emits this contract. A new renderer may replace Processing if it consumes the same attributes. Asset, effect, evaluation and orchestration modules should connect through explicit data contracts rather than importing each other's implementation.
