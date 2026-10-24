"""Bending joints: bones keep their length and what hangs from a joint goes with it."""

import numpy as np
import pytest

from poseorbit import MOVABLE, NAMES, Edit, apply_edits, bend
from poseorbit.body import PARENT, pivot, subtree


def _figure() -> np.ndarray:
    """A figure with every point somewhere different and some depth."""
    rng = np.random.default_rng(7)
    points = rng.uniform(-50, 50, (133, 3))
    points[:17] = [
        [0, -160, -5], [-8, -168, -3], [8, -168, -3], [-15, -164, 5], [15, -164, 5],
        [-40, -120, 0], [40, -120, 0], [-70, -70, -10], [70, -70, 10],
        [-90, -20, -20], [90, -20, 20], [-25, 0, 0], [25, 0, 0],
        [-28, 80, 5], [28, 80, -5], [-30, 160, 0], [30, 160, 0],
    ]
    points[91:112] += points[9]
    points[112:133] += points[10]
    points[23:91] = points[0] + points[23:91] / 4
    return points


def _bones(points: np.ndarray) -> np.ndarray:
    return np.array([
        np.linalg.norm(points[i] - pivot(points, i)) for i, parent in enumerate(PARENT) if parent is not None
    ])


def _distances(points: np.ndarray) -> np.ndarray:
    return np.linalg.norm(points[:, None] - points[None], axis=-1)


def test_the_tree_names_every_point():
    assert len(NAMES) == len(PARENT) == 133
    assert NAMES[9] == "left_wrist" and NAMES[132] == "right_hand_20"
    assert 11 not in MOVABLE and 12 not in MOVABLE
    assert subtree(7) == (7, 9, *range(91, 112))
    assert set(subtree(0)) == {0, 1, 2, 3, 4, *range(23, 91)}


def test_bones_keep_their_length_and_the_joint_points_at_the_target():
    points = _figure()
    target = np.array([-150.0, -150.0, 40.0])
    bent = bend(points, 7, target)
    np.testing.assert_allclose(_bones(bent), _bones(points), atol=1e-9)
    direction = (bent[7] - bent[5]) / np.linalg.norm(bent[7] - bent[5])
    np.testing.assert_allclose(direction, (target - points[5]) / np.linalg.norm(target - points[5]), atol=1e-12)


def test_the_hand_goes_with_the_wrist_and_the_face_with_the_head():
    points = _figure()
    hand = list(subtree(9))
    bent = bend(points, 9, [-60, -150, 0])
    np.testing.assert_allclose(_distances(bent[hand]), _distances(points[hand]), atol=1e-9)
    head = list(subtree(0))
    bent = bend(points, 0, [30, -150, -60])
    np.testing.assert_allclose(_distances(bent[head]), _distances(points[head]), atol=1e-9)


def test_only_the_subtree_moves():
    points = _figure()
    bent = bend(points, 13, [-80, 60, 30])
    still = [i for i in range(133) if i not in subtree(13)]
    np.testing.assert_array_equal(bent[still], points[still])
    np.testing.assert_array_equal(points, _figure())  # the input is left alone


def test_degenerate_targets_change_nothing_and_straight_back_turns_half_way():
    points = _figure()
    np.testing.assert_array_equal(bend(points, 7, points[5]), points)
    flat = points.copy()
    flat[7] = flat[5]
    np.testing.assert_array_equal(bend(flat, 7, [0, 0, 0]), flat)
    back = bend(points, 7, 2 * points[5] - points[7])
    np.testing.assert_allclose(back[7], 2 * points[5] - points[7], atol=1e-9)
    np.testing.assert_allclose(_bones(back), _bones(points), atol=1e-9)


def test_edits_apply_in_order_and_the_same_edits_give_the_same_pose():
    points = [_figure(), _figure() + [200, 0, 0]]
    edits = [Edit(0, 7, (-150, -100, 0)), Edit(0, 5, (-60, -110, 30)), Edit(1, 16, (260, 150, 40))]
    once = apply_edits(points, edits)
    np.testing.assert_array_equal(once[0], apply_edits(points, edits)[0])
    swapped = apply_edits(points, [edits[1], edits[0], edits[2]])
    assert not np.allclose(once[0], swapped[0])
    assert not np.allclose(once[1], points[1])


@pytest.mark.parametrize("edit", [Edit(0, 11, (0, 0, 0)), Edit(0, 133, (0, 0, 0)), Edit(1, 9, (0, 0, 0))])
def test_hips_unknown_joints_and_people_past_the_end_are_refused(edit):
    with pytest.raises(ValueError):
        apply_edits([_figure()], [edit])
