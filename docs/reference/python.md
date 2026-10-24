# Python API

Everything below is importable from `poseorbit` unless its heading says
otherwise.

## Detecting, choosing, turning and drawing

::: poseorbit.pose

::: poseorbit.PoseResult

::: poseorbit.Detector

::: poseorbit.Person

::: poseorbit.NoPersonError

## Camera and framing

::: poseorbit.Camera

::: poseorbit.Framing

## Moving joints

::: poseorbit.Edit

::: poseorbit.apply_edits

::: poseorbit.bend

::: poseorbit.body.subtree

::: poseorbit.body.pivot

## Drawing

::: poseorbit.render

::: poseorbit.letterbox

## Constants

| Name | Value | Meaning |
|---|---|---|
| `ALL_PEOPLE` | `-1` | `person` for everyone detected |
| `MAX_YAW` | `90.0` | The largest yaw, either way, in degrees |
| `MAX_PITCH` | `45.0` | The largest pitch, either way, in degrees |
| `MIN_ZOOM` / `MAX_ZOOM` | `0.5` / `6.0` | The framing's zoom range |
| `KEYPOINT_THRESHOLD` | `0.3` | A keypoint is seen (and drawn) at this score |
| `MOVABLE` | `{0, 5–10, 13–22}` | The joints an edit may move |
| `NAMES` | 133 names | Each keypoint's name, in COCO-WholeBody order (`poseorbit.body`) |
| `PARENT` | 133 indices | Each keypoint's parent; `None` for the hips, `NECK` (`-1`) for the nose (`poseorbit.body`) |
| `STYLES` | `("dwpose", "openpose")` | The skeleton styles |

## Geometry

The steps `pose` takes, for drawing keypoints of your own.

::: poseorbit.geometry.view

::: poseorbit.geometry.scene_centre

::: poseorbit.geometry.fit

::: poseorbit.geometry.frame

## The HTTP handler

For a server of your own; see the [HTTP API](http.md) for the JSON.

::: poseorbit.api.handle

::: poseorbit.api.parse_edits

::: poseorbit.api.BadRequest

::: poseorbit.server.create_app
