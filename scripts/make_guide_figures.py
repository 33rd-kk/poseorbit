"""Draws the guide's figures (docs/assets/guide/*.png) with poseorbit itself:
the same turn, fit, framing and drawing `pose()` does, on the pose kept in
docs/assets/banner-pose.json (see scripts/make_banner.py). No picture, no
model and no download; deterministic.

Each figure is a row of skeletons as poseorbit outputs them (on black, at a
quarter of 832x1216), with a label under each on a transparent background so
the figure reads in the light and the dark theme.

    python scripts/make_guide_figures.py
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from poseorbit import (
    Camera,
    Edit,
    Framing,
    apply_edits,
    fit,
    frame,
    render,
    scene_centre,
    view,
)

ROOT = Path(__file__).resolve().parent.parent
POSE = ROOT / "docs" / "assets" / "banner-pose.json"
OUT = ROOT / "docs" / "assets" / "guide"
SIZE = (208, 304)  # the 832x1216 output, at a quarter
SCALE = 2  # drawn at twice the size for sharp lines on high-density screens
GAP, LABEL = 16, 30
GREY = (128, 128, 128, 255)  # readable on white and on the dark theme's slate

DATA = json.loads(POSE.read_text())
SOURCE = tuple(DATA["size"])
POINTS = np.array(DATA["points"])
SCORES = np.array(DATA["scores"])


def skeleton(
    people: Sequence[np.ndarray],
    camera: Camera | None = None,
    framing: Framing | None = None,
    edits: Sequence[Edit] = (),
    style: str = "dwpose",
    source: tuple[int, int] = SOURCE,
) -> Image.Image:
    """What `pose()` draws for these people (each (133, 3) in `source` pixels)."""
    camera, framing = camera or Camera(), framing or Framing()
    size = (SIZE[0] * SCALE, SIZE[1] * SCALE)
    points = np.stack(apply_edits(list(people), edits))
    flat = points[..., :2] if camera.is_front else view(points, scene_centre(points), camera)
    keypoints = frame(fit(flat, source, size), size, framing)
    return render(keypoints, np.stack([SCORES] * len(people)), size, style)


def row(name: str, tiles: Sequence[tuple[Image.Image, str]]) -> None:
    """Saves `tiles` (skeleton, label) side by side as docs/assets/guide/<name>.png."""
    s = SCALE
    width = len(tiles) * SIZE[0] + (len(tiles) - 1) * GAP
    image = Image.new("RGBA", (width * s, (SIZE[1] + LABEL) * s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=13 * s)
    for i, (tile, label) in enumerate(tiles):
        x = i * (SIZE[0] + GAP) * s
        mask = Image.new("L", tile.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, tile.width - 1, tile.height - 1], radius=6 * s, fill=255)
        image.paste(tile, (x, 0), mask)
        text = draw.textlength(label, font=font)
        draw.text((x + (SIZE[0] * s - text) / 2, (SIZE[1] + 8) * s), label, font=font, fill=GREY)
    OUT.mkdir(parents=True, exist_ok=True)
    image.save(OUT / f"{name}.png", optimize=True)
    print(f"wrote {OUT / name}.png")


def main() -> None:
    one = [POINTS]

    # Choose people: three of the same figure side by side, numbered as detect() would.
    width = SOURCE[0]
    group = [POINTS + [dx, 0, 0] for dx in (0, width * 0.6, width * 1.2)]
    wide = (round(width * 2.2), SOURCE[1])
    row(
        "people",
        [
            (skeleton(group, source=wide), "ALL_PEOPLE"),
            (skeleton(group[1:2], source=wide), "person=1"),
            (skeleton([group[0], group[2]], source=wide), "person=[0, 2]"),
        ],
    )

    row("yaw", [(skeleton(one, Camera(yaw=yaw)), f"yaw {yaw}") for yaw in (-60, -30, 0, 30, 60)])
    row("pitch", [(skeleton(one, Camera(pitch=pitch)), f"pitch {pitch}") for pitch in (-30, 0, 30, 45)])
    row(
        "framing",
        [
            (skeleton(one), "Framing()"),
            (skeleton(one, framing=Framing(zoom=2, x=0.5, y=0.35)), "zoom 2, y 0.35"),
            (skeleton(one, framing=Framing(zoom=5, x=0.5, y=0.13)), "zoom 5, y 0.13"),
            (skeleton(one, framing=Framing(zoom=0.6)), "zoom 0.6"),
        ],
    )

    # Move a joint: raise the lowered (right) arm. Elbow 8, wrist 10.
    x, y, z = POINTS[8]
    edits = [Edit(0, 8, (x - 60, y - 40, z)), Edit(0, 10, (x - 70, y - 160, z))]
    row("edit", [(skeleton(one), "as detected"), (skeleton(one, edits=edits), "Edit(0, 8, ...), Edit(0, 10, ...)")])

    row(
        "styles",
        [
            (skeleton(one, Camera(yaw=-30)), "dwpose"),
            (skeleton(one, Camera(yaw=-30), style="openpose"), "openpose"),
        ],
    )


if __name__ == "__main__":
    main()
