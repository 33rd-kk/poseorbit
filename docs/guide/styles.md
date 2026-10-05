# Skeleton styles

A pose-conditioned model follows the kind of skeleton drawing it was trained
on, so poseorbit draws two.

| Style | Drawing | For |
|---|---|---|
| `dwpose` | rtmlib's COCO-WholeBody drawing: thin coloured lines and dots for the body, feet, hands and face | DWPose-trained adapters, such as Anima-Control-Pose |
| `openpose` | The 18 OpenPose body points, thick translucent limbs whose width grows with the canvas | OpenPose ControlNets, such as `xinsir/controlnet-openpose-sdxl-1.0` |

Both are on black, at the output's size.

## `dwpose`

Drawn by rtmlib's `draw_skeleton` with the same keypoint threshold (0.3),
from the same DWPose detector skeleton-conditioned models are commonly
trained on, so a skeleton looks like their training data. Hands and face are
included, which helps in close-ups and for which way the head faces.

## `openpose`

Follows the drawing on the model card of
[xinsir/controlnet-openpose-sdxl-1.0](https://huggingface.co/xinsir/controlnet-openpose-sdxl-1.0),
which replaced controlnet_aux's thinner one: limb and joint thickness steps
up with the canvas's longer side (one size below 500 px, two below 1000,
then one more per 1000 px). Body only, as that model was trained. In a close-up
few body points remain; check
[`PoseResult.joints_in_frame`][poseorbit.PoseResult].

## Measured

Generated with and without the skeleton, same seed, 832×1216; PCK@0.1 of the
re-detected output against the skeleton (1.0: every point within 10% of the
diagonal of where the skeleton put it).

| Model | Pose | Without | With |
|---|---|---|---|
| Illustrious XL 2.0 + xinsir ControlNet (`openpose`) | walking, front | 0.76 | **0.94** |
| same | walking, turned yaw 45° / yaw −60° pitch 15° | — | **0.94 / 0.88** |
| same | upper body ×2 / face ×5 | 0.02 / 0.48 | **1.00 / 0.99** |
| Anima Base 1.0 + Anima-Control-Pose (`dwpose`) | walking, front | 0.06 | **0.71** |
| same | walking, turned yaw 45° | — | **0.94** |
