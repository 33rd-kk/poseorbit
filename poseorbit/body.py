"""Moving a joint: the 133 COCO-WholeBody points as a tree, and bending it.

A joint turns about its parent, and everything hanging from it turns with
it: bending an elbow swings the forearm and the whole hand, and no bone
changes length. The hips are the root and stay where they are; turning the
whole figure is the camera's job.

    from poseorbit import Edit, apply_edits

    left_wrist = 9
    moved = apply_edits([person.points_3d], [Edit(0, left_wrist, (420, 180, -40))])
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

_BODY = (
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle",
)
_FEET = ("left_big_toe", "left_small_toe", "left_heel", "right_big_toe", "right_small_toe", "right_heel")

NAMES: tuple[str, ...] = (
    _BODY
    + _FEET
    + tuple(f"face_{i}" for i in range(68))
    + tuple(f"left_hand_{i}" for i in range(21))
    + tuple(f"right_hand_{i}" for i in range(21))
)
"""The 133 keypoints' names, in COCO-WholeBody order."""

NECK = -1
"""`PARENT` of the nose: the middle of the shoulders, found when bending."""

# Each point's parent: hips are roots, shoulders hang from the hips, the
# head from the neck, hands from the wrists and the face from the nose.
PARENT: tuple[int | None, ...] = (
    (NECK, 0, 0, 1, 2, 11, 12, 5, 6, 7, 8, None, None, 11, 12, 13, 14)
    + (15, 15, 15, 16, 16, 16)
    + (0,) * 68
    + (9,) * 21
    + (10,) * 21
)
"""Each keypoint's parent index; None for the hips, `NECK` for the nose."""

MOVABLE: frozenset[int] = frozenset({0, *range(5, 11), *range(13, 23)})
"""The joints [bend][poseorbit.bend] moves: the head, arms, legs and feet."""

_CHILDREN: dict[int, list[int]] = {}
for _point, _parent in enumerate(PARENT):
    if _parent is not None and _parent != NECK:
        _CHILDREN.setdefault(_parent, []).append(_point)


def subtree(joint: int) -> tuple[int, ...]:
    """`joint` and every point hanging from it, in index order."""
    found = [joint]
    for point in found:
        found.extend(_CHILDREN.get(point, ()))
    return tuple(sorted(found))


def pivot(points: np.ndarray, joint: int) -> np.ndarray:
    """The point `joint` turns about: its parent, or the neck for the nose.

    Raises:
        ValueError: `joint` is a hip, which has no parent.
    """
    parent = PARENT[joint]
    if parent is None:
        raise ValueError(f"{NAMES[joint]} is a root and does not turn.")
    if parent == NECK:
        return (points[5] + points[6]) / 2
    return points[parent]


def _rotation(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """The smallest rotation taking direction `u` onto `v` (both unit length)."""
    axis = np.cross(u, v)
    sine = float(np.linalg.norm(axis))
    cosine = float(np.dot(u, v))
    if sine < 1e-12:
        if cosine > 0:
            return np.eye(3)
        # Straight back: half a turn about any axis square to u.
        axis = np.cross(u, (1.0, 0.0, 0.0))
        if np.linalg.norm(axis) < 1e-6:
            axis = np.cross(u, (0.0, 1.0, 0.0))
        axis = axis / np.linalg.norm(axis)
        return 2 * np.outer(axis, axis) - np.eye(3)
    axis = axis / sine
    cross = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + sine * cross + (1 - cosine) * (cross @ cross)


def bend(points: np.ndarray, joint: int, target: Sequence[float] | np.ndarray) -> np.ndarray:
    """Turn `joint` about its parent to point at `target`, carrying its subtree.

    The joint keeps its distance from the parent, so it ends on the line from
    the parent through `target`, not on `target` itself.

    Args:
        points: (133, 3) x, y and depth, as [Person.points_3d][poseorbit.Person].
        joint: One of `MOVABLE`.
        target: Where the joint should point, in the same units as `points`.

    Returns:
        A new (133, 3) array; `points` is left as it was.

    Raises:
        ValueError: `joint` is not movable.
    """
    if joint not in MOVABLE:
        raise ValueError(f"Joint {joint} cannot be moved.")
    points = np.array(points, dtype=float)
    centre = pivot(points, joint)
    u = points[joint] - centre
    v = np.asarray(target, dtype=float) - centre
    length, reach = float(np.linalg.norm(u)), float(np.linalg.norm(v))
    if length < 1e-9 or reach < 1e-9:
        return points
    rotation = _rotation(u / length, v / reach)
    moved = list(subtree(joint))
    points[moved] = (points[moved] - centre) @ rotation.T + centre
    return points


@dataclass(frozen=True)
class Edit:
    """One joint moved on one person.

    Attributes:
        person: An index into the people detected, left to right.
        joint: One of `MOVABLE`.
        to: Where the joint should point: x, y and depth in the picture's pixels.
    """

    person: int
    joint: int
    to: tuple[float, float, float]


def apply_edits(points: Sequence[np.ndarray], edits: Sequence[Edit]) -> list[np.ndarray]:
    """Everyone's (133, 3) points with `edits` bent in, one after another.

    Order matters: each edit bends the pose the ones before it left.

    Args:
        points: Each person's (133, 3) points, left to right.
        edits: The joints to move.

    Returns:
        New arrays, one per person; `points` is left as it was.

    Raises:
        ValueError: An edit names a person past the end or a joint that is
            not movable.
    """
    bent = [np.array(p, dtype=float) for p in points]
    for edit in edits:
        if not 0 <= edit.person < len(bent):
            raise ValueError(f"No person {edit.person}: {len(bent)} found.")
        bent[edit.person] = bend(bent[edit.person], edit.joint, edit.to)
    return bent
