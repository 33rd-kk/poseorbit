# Changelog

## 0.1.2 (unreleased)

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
