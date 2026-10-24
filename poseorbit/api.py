"""The `/api/pose` request and answer, independent of any web framework, so
poseorbit's own server and a generation server that embeds poseorbit speak
exactly the same JSON.

Request:
    { "image_base64": "...", "width": 832, "height": 1216,
      "person": 0,                          # optional; -1 = everyone, [0, 2] = those, absent = most confident
      "want_3d": true,                      # optional; answer with each person's 3D points
      "camera": { "yaw": 30, "pitch": 10,   # optional; degrees, see geometry.py
                  "framing": { "zoom": 3, "x": 0.5, "y": 0.2 } },  # optional; the canvas point to centre, and zoom
      "style": "openpose",                  # optional; "dwpose" (default) or "openpose"
      "edits": [ { "person": 0, "joint": 9,  # optional; joints to move, in order (see body.py)
                   "to": [x, y, z] } ] }     # where it points, fractions of the picture's width

Answer:
    { "skeleton_base64": "...png...", "width": 832, "height": 1216, "person": 0,   # or the sorted list asked for
      "person_subsets": true,               # "person" may be a list: a client may offer picking any of them
      "movable": [0, 5, ...],               # the joints "edits" may move
      "camera": { "yaw": 30, "pitch": 10, "framing": { "zoom": 3, "x": 0.5, "y": 0.2 } },
      "style": "openpose",
      "limits": { "yaw": 90, "pitch": 45, "zoom": [0.5, 6] },
      "joints_in_frame": 9,                 # body joints (of 17) seen inside the canvas, best drawn person
      "people": [ { "bbox": [x0, y0, x1, y1],                # fractions of the picture
                    "points_3d": [[x, y, z], ...],          # with want_3d: 133 points as detected (before edits), fractions of the picture's width
                    "scores": [...] } ] }                   # with want_3d: 133 scores
"""

from __future__ import annotations

import base64
import io
import math
from typing import Any

from PIL import Image

from . import ALL_PEOPLE, MAX_PITCH, MAX_YAW, MAX_ZOOM, MIN_ZOOM, MOVABLE, STYLES, Camera, Detector, Edit, Framing, pose
from .draw import Style

# The most people one request may choose by a list: far more than a picture
# usefully holds, and it bounds the list before anything is detected.
MAX_CHOSEN = 64

# The most edits one request may carry: hundreds of drags, and it bounds the
# work before anything is detected.
MAX_EDITS = 256

# How far an edit may point, in picture widths: well past any figure.
_MAX_REACH = 16


class BadRequest(ValueError):
    """The request is wrong; answer 400 with the message."""


def decode_image(data: str) -> Image.Image:
    """A picture from base64, with or without a `data:` URL prefix.

    Raises:
        BadRequest: It is not a picture.
    """
    if data.startswith("data:"):
        data = data.split(",", 1)[1]
    try:
        image = Image.open(io.BytesIO(base64.b64decode(data)))
        image.load()
    except Exception as error:  # noqa: BLE001 - any decode failure is the caller's input
        raise BadRequest("The picture could not be read.") from error
    return image


def encode_png(image: Image.Image) -> str:
    """A picture as base64 PNG (no `data:` prefix)."""
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise BadRequest(f"{name} must be a number")
    return float(value)


def parse_camera(value: Any) -> tuple[Camera | None, Framing | None]:
    """The request's `camera` object as a clamped Camera and Framing (None when absent).

    Raises:
        BadRequest: It is not an object of numbers.
    """
    if value is None:
        return None, None
    if not isinstance(value, dict):
        raise BadRequest("camera must be an object { yaw, pitch, framing }")
    camera = Camera(
        yaw=_number(value.get("yaw", 0), "camera.yaw"),
        pitch=_number(value.get("pitch", 0), "camera.pitch"),
    ).clamped()
    framing = value.get("framing")
    if framing is None:
        return camera, None
    if not isinstance(framing, dict):
        raise BadRequest("camera.framing must be an object { zoom, x, y }")
    return camera, Framing(
        zoom=_number(framing.get("zoom", 1), "camera.framing.zoom"),
        x=_number(framing.get("x", 0.5), "camera.framing.x"),
        y=_number(framing.get("y", 0.5), "camera.framing.y"),
    ).clamped()


def parse_edits(value: Any, width: int) -> list[Edit]:
    """The request's `edits` as [Edit][poseorbit.Edit]s in pixels (empty when absent).

    Args:
        value: The `edits` list: `{ person, joint, to: [x, y, z] }` each, `to`
            in fractions of the picture's width.
        width: The picture's width in pixels.

    Raises:
        BadRequest: It is not such a list, too long, names a joint that is
            not movable, or points too far.
    """
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > MAX_EDITS:
        raise BadRequest(f"edits must be a list of at most {MAX_EDITS}")
    edits = []
    for edit in value:
        if not isinstance(edit, dict):
            raise BadRequest("each edit must be an object { person, joint, to }")
        person, joint, to = edit.get("person"), edit.get("joint"), edit.get("to")
        if isinstance(person, bool) or not isinstance(person, int) or person < 0:
            raise BadRequest("edit.person must be an index")
        if isinstance(joint, bool) or not isinstance(joint, int) or joint not in MOVABLE:
            raise BadRequest(f"edit.joint must be one of {sorted(MOVABLE)}")
        if not isinstance(to, list) or len(to) != 3:
            raise BadRequest("edit.to must be [x, y, z]")
        point = [_number(v, "edit.to") for v in to]
        if any(abs(v) > _MAX_REACH for v in point):
            raise BadRequest(f"edit.to must be within {_MAX_REACH} picture widths")
        edits.append(Edit(person, joint, (point[0] * width, point[1] * width, point[2] * width)))
    return edits


def handle(detector: Detector, body: dict[str, Any], default_style: Style = "dwpose") -> dict[str, Any]:
    """Answers one `/api/pose` request (the JSON above), without a web framework.

    Args:
        detector: The [Detector][poseorbit.Detector] to use.
        body: The request's JSON object.
        default_style: The style when the request names none; a generation
            server passes the one its loaded model needs.

    Returns:
        The answer's JSON object.

    Raises:
        BadRequest: The request is wrong; answer 400 with its message.
        NoPersonError: Nobody in the picture; also a 400.
        ValueError: A person index past the end, in `person` or an edit; also a 400.
    """
    data = body.get("image_base64")
    if not isinstance(data, str) or not data:
        raise BadRequest("image_base64 is required")
    image = decode_image(data)
    edits = parse_edits(body.get("edits"), image.width)
    width = int(_number(body.get("width", image.width), "width"))
    height = int(_number(body.get("height", image.height), "height"))
    if not (64 <= width <= 4096 and 64 <= height <= 4096):
        raise BadRequest("width and height must be 64-4096")
    person = body.get("person")
    if isinstance(person, list):
        # Bounded before anything is detected; past the people found is a ValueError later.
        if not 1 <= len(person) <= MAX_CHOSEN or any(isinstance(index, bool) or not isinstance(index, int) or index < 0 for index in person):
            raise BadRequest(f"person as a list must hold 1-{MAX_CHOSEN} indices")
    elif person is not None and (isinstance(person, bool) or not isinstance(person, int) or person < ALL_PEOPLE):
        raise BadRequest("person must be an index, a list of indices, or -1 for everyone")
    style = body.get("style") or default_style
    if style not in STYLES:
        raise BadRequest(f"style must be one of {', '.join(STYLES)}")
    want_3d = body.get("want_3d") is True

    camera, framing = parse_camera(body.get("camera"))
    result = pose(detector, image, (width, height), person, camera, style, depth=want_3d, framing=framing, edits=edits)
    people = []
    for found in result.people:
        x0, y0, x1, y1 = found.bbox
        # Keypoints can be guessed past the edge (feet below the frame); the
        # box is for drawing over the picture, so it stays inside it.
        box = [x0 / image.width, y0 / image.height, x1 / image.width, y1 / image.height]
        entry: dict[str, Any] = {"bbox": [round(min(1.0, max(0.0, edge)), 5) for edge in box]}
        if want_3d:
            # One unit for all three axes (the picture's width), so a viewer
            # can draw them without knowing the picture's size or aspect.
            entry["points_3d"] = (found.points_3d / image.width).round(5).tolist()
            entry["scores"] = found.scores.round(3).tolist()
        people.append(entry)
    return {
        "skeleton_base64": encode_png(result.skeleton),
        "width": width,
        "height": height,
        "person": result.person,
        "person_subsets": True,
        "movable": sorted(MOVABLE),
        "camera": {
            "yaw": result.camera.yaw,
            "pitch": result.camera.pitch,
            "framing": {"zoom": result.framing.zoom, "x": result.framing.x, "y": result.framing.y},
        },
        "style": style,
        "limits": {"yaw": MAX_YAW, "pitch": MAX_PITCH, "zoom": [MIN_ZOOM, MAX_ZOOM]},
        "joints_in_frame": result.joints_in_frame,
        "people": people,
    }
