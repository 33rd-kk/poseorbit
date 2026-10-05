# HTTP API

```sh
pip install "poseorbit[server]"
python -m poseorbit serve --port 7870 [--host 127.0.0.1] [--weights-dir DIR]
```

It listens on 127.0.0.1 unless `--host` says otherwise. Set the environment
variable `POSEORBIT_TOKEN` to require `Authorization: Bearer <token>` on
every request but `/api/health`. Detection runs on the CPU; the models load
on the first `/api/pose`.

A generation server can answer the same requests by calling
[`poseorbit.api.handle`][poseorbit.api.handle] from its own route.

## `GET /api/health`

```json
{ "status": "ok", "version": "0.1.1", "styles": ["dwpose", "openpose"],
  "limits": { "yaw": 90.0, "pitch": 45.0, "zoom": [0.5, 6.0] } }
```

## `POST /api/pose`

### Request

```json
{
  "image_base64": "iVBORw0KGgo…",
  "width": 832, "height": 1216,
  "person": 0,
  "want_3d": true,
  "camera": { "yaw": 30, "pitch": 10,
              "framing": { "zoom": 2, "x": 0.5, "y": 0.35 } },
  "style": "openpose"
}
```

| Field | Required | Meaning |
|---|---|---|
| `image_base64` | yes | The picture, base64, with or without a `data:` URL prefix |
| `width`, `height` | no | The output's size, 64–4096; the picture's own size by default |
| `person` | no | An index into `people` (left to right), `-1` for everyone; absent: the most confident |
| `want_3d` | no | `true` to answer with every person's 3D points |
| `camera.yaw`, `camera.pitch` | no | Degrees; see [Coordinates](../guide/coordinates.md). Clamped to ±90 / ±45 |
| `camera.framing.zoom` | no | 0.5–6, clamped; 1 by default |
| `camera.framing.x`, `.y` | no | The canvas point to centre, fractions 0–1; 0.5 by default |
| `style` | no | `"dwpose"` (default) or `"openpose"` |

### Answer

```json
{
  "skeleton_base64": "iVBORw0KGgo…",
  "width": 832, "height": 1216, "person": 0,
  "camera": { "yaw": 30.0, "pitch": 10.0,
              "framing": { "zoom": 2.0, "x": 0.5, "y": 0.35 } },
  "style": "openpose",
  "limits": { "yaw": 90.0, "pitch": 45.0, "zoom": [0.5, 6.0] },
  "joints_in_frame": 13,
  "people": [
    { "bbox": [0.31, 0.2, 0.8, 1.0],
      "points_3d": [[0.61, 0.24, -0.03], …],
      "scores": [0.92, …] }
  ]
}
```

| Field | Meaning |
|---|---|
| `skeleton_base64` | The skeleton, PNG, base64 (no prefix), at `width` × `height` |
| `person` | Who was drawn: an index, or `-1` |
| `camera` | The camera and framing actually used, after clamping |
| `limits` | How far the camera and zoom may go; a client can hold its controls to these |
| `joints_in_frame` | Body joints (of 17) seen and inside the canvas, for the drawn person with the most |
| `people[].bbox` | Around each person's drawn keypoints, as fractions of the picture, clamped to it |
| `people[].points_3d` | With `want_3d`: 133 points `[x, y, z]` in units of the picture's width (x right, y down, z away) |
| `people[].scores` | With `want_3d`: 133 keypoint scores |

### Errors

`400` with `{"detail": "…"}` for a request that is wrong (no picture, an
unreadable picture, a size out of range, a camera that is not numbers, an
unknown style), a picture with nobody in it, or a person index past the end.
`401` without the right token, when one is set.
