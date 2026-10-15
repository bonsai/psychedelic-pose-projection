# Pose Attributes Contract v1

Status: Active for the Python → Processing runtime in [bonsai/mpp5](https://github.com/bonsai/mpp5).

## Purpose

Keep pose interpretation independent from rendering. Python produces interpreted pose data; renderers consume it. Neither side imports code from the other.

## OSC transport

- Protocol: OSC over UDP
- Host: `127.0.0.1`
- Port: `12000`
- Coordinate space: normalized camera coordinates, origin at top-left, x increases rightward and y downward
- Update policy: latest value wins; renderers must tolerate dropped packets
- Privacy: raw camera frames are not part of this contract and are not persisted

## Messages

| OSC address | Payload | Meaning | Owner |
|---|---|---|---|
| `/pose/points` | 14 ordered x,y float pairs | 13 filtered landmarks + hip center; `(-1,-1)` means unavailable | Python interprets/filters; Processing renders |
| `/left_speed` | one float | Left wrist movement speed in pixels per frame | Python |
| `/right_speed` | one float | Right wrist movement speed in pixels per frame | Python |
| `/hip_sway` | one float, range 0–1.5 | Estimated lateral hip-motion intensity | Python |

Landmark order is defined in `camera_worker()` in `mpp5/server.py`. Changing order or payload shape is a contract change and must update both ends together.

## Responsibility boundaries

### Python producer (mpp5)

- Capture the local camera and run MediaPipe
- Apply visibility/confidence thresholds
- Derive movement features and reset values when tracking is lost
- Publish normalized landmarks and semantic attributes through WebSocket and OSC

### Processing / Java consumer (mpp5)

- Receive OSC messages
- Map normalized coordinates to display coordinates
- Draw trails, skeletons and visual effects
- Avoid pose detection or gesture interpretation

## Compatibility rules

1. Add new OSC addresses without changing existing message meanings.
2. Treat missing/stale attributes as neutral values.
3. Ignore unknown OSC addresses.
4. Keep transport adapters replaceable; WebSocket, OSC and file replay are adapters over the same logical attributes.
5. Test interpretation and rendering independently where practical.

## Extension points

A new pose model may replace the Python producer if it emits this contract. A new renderer may replace Processing if it consumes the same attributes. Asset, effect, evaluation and orchestration modules connect through explicit contracts rather than importing each other's implementation.
