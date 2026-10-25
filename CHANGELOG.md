# Changelog

## 0.3.1 (unreleased)

- **Fixed**: a foot, face or hand point's depth is kept close to the
  middle depth of its hand, face or foot (`DETAIL_REACH`: 0.1 m for hands,
  0.12 m for the face, 0.25 m for feet). RTMW3D now and then
  guessed one such point far in front or behind, as much as half a metre
  for a fingertip, while its x and y were right. From the front nothing
  showed, but a turned pose or a moved wrist drew it as a long stray line.

## 0.3.0 (2026-10-25)

- **Move a joint**: `pose(..., edits=[Edit(person, joint, to)])` turns a
  joint about its parent to point at `to`, carrying everything hanging from
  it, so no bone changes length. The head, arms, legs and feet move
  (`MOVABLE`); a hand moves with its wrist and the face with the head; the
  hips stay put. Edits apply in order. `bend` and `apply_edits` do the same
  for points of your own, and `poseorbit.body` holds the keypoint names and
  their tree.
- `/api/pose` takes `"edits": [{ "person", "joint", "to": [x, y, z] }]`
  (up to 256, `to` in picture widths like `points_3d`) and answers
  `"movable"`, the joints it may move, so a client knows it may send them.
  `points_3d` stays as detected.
- A request with edits detects depth even for the front view.
- The command line does not take edits yet.

## 0.2.0 (2026-10-11)

- **Choose some of the people**: `pose(..., person=[0, 2])` draws just those
  (turned together around their shared centre), and `/api/pose` takes
  `"person": [0, 2]` (up to 64 indices). The list comes back sorted and
  without repeats; an empty list or an index past the end is refused.
  `python -m poseorbit draw --person 0,2` does the same.
- `/api/pose` answers `"person_subsets": true`, so a client knows it may
  send a list.
- **Changed:** `PoseResult.person` (and the answer's `person`) is a list when
  a list was asked for; code that only passes an int or `ALL_PEOPLE` still
  gets an int.

## 0.1.2 (2026-10-11)

- **Pinned model downloads**: the three ONNX files come from a fixed commit
  of their Hugging Face repository, and both the download and the onnx kept
  are checked against their SHA-256 before use. A file already in the
  weights folder that does not match is downloaded again; one that does
  match is hashed once per process, in memory only.
- Downloads go through a temporary folder inside the weights folder, so no
  second copy stays in Hugging Face's shared cache (`~/.cache/huggingface`).
  Copies left there by 0.1.1 can be deleted.

## 0.1.1 (2026-10-06)

- Published on PyPI: `pip install poseorbit`. Releases are uploaded from
  GitHub Actions with Trusted Publishing and signed attestations.
- The README's pictures and links are absolute, so they show on PyPI too.

## 0.1.0 (2026-10-05)

First release.

- Find people with YOLOX and DWPose (133 whole-body keypoints), left to
  right; choose one, or everyone.
- Depth for every keypoint from RTMW3D-x on the same boxes; turn the pose
  with an orthographic camera (yaw ±90°, pitch ±45°).
- Frame the output canvas: zoom ×0.5 to ×6 around any point.
- Draw `dwpose` (rtmlib's COCO-WholeBody) or `openpose` (thick, body-only, as
  xinsir's SDXL ControlNet was trained) skeletons, letterboxed onto the
  output's size.
- Library, `python -m poseorbit draw`, and `python -m poseorbit serve`
  (`POST /api/pose`, optional Bearer token).
