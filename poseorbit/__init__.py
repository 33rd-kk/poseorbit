"""poseorbit: find the people in a picture, pick one (or everyone), turn the
pose in 3D, and draw the skeleton a pose-conditioned image model follows.

    from poseorbit import Detector, Camera, pose

    detector = Detector()
    result = pose(detector, picture, size=(832, 1216), person=0,
                  camera=Camera(yaw=45), style="openpose")
    result.skeleton.save("skeleton.png")
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from PIL import Image

from .body import MOVABLE, NAMES, Edit, apply_edits, bend
from .detect import KEYPOINT_THRESHOLD, Detector, NoPersonError, Person, most_confident
from .draw import STYLES, Style, letterbox, render
from .geometry import MAX_PITCH, MAX_YAW, MAX_ZOOM, MIN_ZOOM, Camera, Framing, fit, frame, scene_centre, view

__version__ = "0.3.0"

# Person index meaning "everyone detected", for a group pose.
ALL_PEOPLE = -1

__all__ = [
    "ALL_PEOPLE",
    "Camera",
    "Detector",
    "Edit",
    "Framing",
    "KEYPOINT_THRESHOLD",
    "MAX_PITCH",
    "MAX_YAW",
    "MAX_ZOOM",
    "MIN_ZOOM",
    "MOVABLE",
    "NAMES",
    "NoPersonError",
    "Person",
    "PoseResult",
    "STYLES",
    "Style",
    "apply_edits",
    "bend",
    "letterbox",
    "pose",
    "render",
]


@dataclass
class PoseResult:
    """What [pose][poseorbit.pose] drew, and what it found on the way.

    Attributes:
        skeleton: The skeleton on black, at the requested size.
        people: Everyone detected, left to right.
        person: Who was drawn: an index into `people`, `ALL_PEOPLE`, or the
            sorted indices when several were chosen by a list.
        camera: The camera actually used, after clamping.
        framing: The framing actually used, after clamping.
        joints_in_frame: Body joints (of 17) seen and inside the canvas, for
            the drawn person with the most. Few left (a close-up) means a
            body-only skeleton has little to follow.
    """

    skeleton: Image.Image
    # Everyone detected, left to right, and which of them was drawn: an index,
    # ALL_PEOPLE for all, or the sorted indices of the ones chosen.
    people: list[Person]
    person: int | list[int]
    # The camera and framing actually used, after clamping.
    camera: Camera
    framing: Framing
    # The drawn people's body joints (of 17 each) that are seen and inside the
    # canvas, for the one with the most: few left (a close-up) means a
    # body-only skeleton has little to follow.
    joints_in_frame: int


def chosen(people: list[Person], person: int | Sequence[int] | None) -> tuple[int | list[int], list[Person]]:
    """`person` resolved (None = the most confident) and the people it means.

    A sequence chooses any of them: the indices come back sorted, without
    repeats, and the people in that (left-to-right) order.

    Raises:
        ValueError: `person` (or one of a sequence) is past the end of
            `people`, or the sequence is empty.
    """
    if person is None:
        person = most_confident(people)
    if isinstance(person, int):
        if person == ALL_PEOPLE:
            return person, people
        if 0 <= person < len(people):
            return person, [people[person]]
        raise ValueError(f"No person {person}: {len(people)} found.")
    indices = sorted(set(person))
    if not indices:
        raise ValueError("Choose at least one person.")
    for index in indices:
        if not 0 <= index < len(people):
            raise ValueError(f"No person {index}: {len(people)} found.")
    return indices, [people[index] for index in indices]


def pose(
    detector: Detector,
    image: Image.Image,
    size: tuple[int, int],
    person: int | Sequence[int] | None = None,
    camera: Camera | None = None,
    style: Style = "dwpose",
    depth: bool = False,
    framing: Framing | None = None,
    edits: Sequence[Edit] = (),
) -> PoseResult:
    """Detect, choose, turn, frame and draw in one call.

    A `camera` other than the front view, or any `edits`, needs depth, so it
    is detected then whatever `depth` says.

    Args:
        detector: A [Detector][poseorbit.Detector]; load it once and reuse it.
        image: The reference picture.
        size: The output's (width, height). The skeleton is drawn at it, the
            picture letterboxed onto it.
        person: An index into the left-to-right order, `ALL_PEOPLE` (-1) for
            everyone, a sequence of indices for some of them (drawn together
            and turned around their shared centre), or None for the most
            confident.
        camera: Where the camera stands; None for the front view.
        style: `"dwpose"` or `"openpose"`; see [render][poseorbit.render].
        depth: Detect depth even for the front view (to read
            `Person.depth` from the result).
        framing: Zoom and centre on the canvas; None for the whole picture.
        edits: Joints to move before turning, in order; see
            [apply_edits][poseorbit.apply_edits]. `PoseResult.people` stays as
            detected.

    Returns:
        The skeleton, everyone found and how it was drawn.

    Raises:
        NoPersonError: Nobody in the picture is seen well enough.
        ValueError: `person` (or one of a sequence) is past the end of the
            people found, or the sequence is empty, or an edit names a
            person past the end or a joint that is not movable.
    """
    camera = (camera or Camera()).clamped()
    framing = (framing or Framing()).clamped()
    people = detector.detect(image, depth=depth or not camera.is_front or bool(edits))
    bent = apply_edits([p.points_3d for p in people], edits)
    person, drawn = chosen(people, person)
    indices = range(len(people)) if person == ALL_PEOPLE else [person] if isinstance(person, int) else person
    points = np.stack([bent[index] for index in indices])
    if camera.is_front:
        flat = points[..., :2]
    else:
        # Everyone turns around one shared centre, so a group keeps its layout.
        flat = view(points, scene_centre(points), camera)
    keypoints = frame(fit(flat, (image.width, image.height), size), size, framing)
    scores = np.stack([p.scores for p in drawn])
    inside = (keypoints >= 0).all(axis=-1) & (keypoints < np.array(size)).all(axis=-1)
    joints = int(((scores[:, :17] >= KEYPOINT_THRESHOLD) & inside[:, :17]).sum(axis=1).max())
    return PoseResult(render(keypoints, scores, size, style), people, person, camera, framing, joints)
