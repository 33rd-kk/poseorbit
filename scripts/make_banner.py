"""Draws the README banner (docs/assets/banner-{light,dark}.png): the name and
what poseorbit does on the left, and on the right one skeleton, turned by
poseorbit itself, inside the orbit its camera moves on (yaw around the
figure, pitch over it).

The pose is docs/assets/banner-pose.json: one whole-body pose (133 points,
x, y and depth in the pixels of a `size` picture, and their scores), detected
once with `Detector().detect(picture, depth=True)` and kept as numbers, so
the banner needs no picture, no model and no download. Deterministic:
re-running only changes the files when this script, the pose or poseorbit's
drawing change.

    python scripts/make_banner.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont

from poseorbit import KEYPOINT_THRESHOLD, Camera, fit, render, scene_centre, view

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "docs" / "assets"
W, H, SCALE = 1280, 320, 2

THEMES = {
    "light": {"bg": "#fafafa", "fg": "#171717", "white": "#525252", "muted": "#737373", "ring": "#c9c3f5", "accent": "#7c6cf0"},
    "dark": {"bg": "#0a0a0a", "fg": "#fafafa", "white": "#ffffff", "muted": "#a3a3a3", "ring": "#3d3570", "accent": "#8b7cf6"},
}

CAMERA = Camera(yaw=-30, pitch=12)
FIGURE = (240, 296)  # the box the turned skeleton is fitted into
LEFT_TOP = (830, 8)  # where that box goes
# The orbit is centred on the hips, wherever the pose puts them in the box.
RING = (215, 40)  # the orbit's half width and half height
PITCH_RISE = 105  # how high the pitch arc climbs over the orbit


def font(size: int) -> ImageFont.FreeTypeFont:
    # Pillow's bundled font, so the script needs no font files (it has no
    # minus, times or arrow signs: labels stay ASCII, arrows are drawn).
    return ImageFont.load_default(size=size * SCALE)


def skeleton() -> tuple[Image.Image, tuple[float, float]]:
    """The turned skeleton (its black background made transparent) and the
    middle of the orbit: under the box's middle, at the hips' height."""
    data = json.loads((ASSETS / "banner-pose.json").read_text())
    points = np.array(data["points"])[None]
    scores = np.array(data["scores"])[None]
    flat = view(points, scene_centre(points), CAMERA)
    # Fit the figure itself, not the picture it came from, into the box.
    shown = flat[0][scores[0] >= KEYPOINT_THRESHOLD]
    low, high = shown.min(axis=0), shown.max(axis=0)
    size = (FIGURE[0] * SCALE, FIGURE[1] * SCALE)
    keypoints = fit(flat - low, tuple(high - low), size)
    # rtmlib draws 2-pixel lines, thin at this scale: thicken them a little.
    drawn = render(keypoints, scores, size, "dwpose").filter(ImageFilter.MaxFilter(3))
    alpha = Image.fromarray(np.asarray(drawn).max(axis=2)).point(lambda v: min(255, v * 4))
    figure = drawn.convert("RGBA")
    figure.putalpha(alpha)
    hips = keypoints[0, [11, 12]].mean(axis=0) / SCALE
    # The figure is centred in its box; so is the orbit under it.
    return figure, (LEFT_TOP[0] + FIGURE[0] / 2, LEFT_TOP[1] + float(hips[1]))


def on_ring(centre: tuple[float, float], angle: float) -> tuple[float, float]:
    """A point of the orbit ring in scaled pixels; angle 0 is the right end,
    pi/2 the near side (lower on screen)."""
    return (
        (centre[0] + RING[0] * math.cos(angle)) * SCALE,
        (centre[1] + RING[1] * math.sin(angle)) * SCALE,
    )


def arrow_head(draw: ImageDraw.ImageDraw, tip: tuple[float, float], towards: tuple[float, float], colour: str) -> None:
    """A filled arrow head at `tip` (scaled pixels), pointing along `towards`."""
    length = math.hypot(*towards)
    ux, uy = towards[0] / length, towards[1] / length
    back, half = 12 * SCALE, 6 * SCALE
    bx, by = tip[0] - ux * back, tip[1] - uy * back
    draw.polygon([tip, (bx - uy * half, by + ux * half), (bx + uy * half, by - ux * half)], fill=colour)


def banner(theme: dict, figure: Image.Image, centre: tuple[float, float]) -> Image.Image:
    s = SCALE
    image = Image.new("RGBA", (W * s, H * s), theme["bg"])
    draw = ImageDraw.Draw(image)

    draw.text((56 * s, 104 * s), "poseorbit", font=font(60), fill=theme["fg"])
    draw.text((58 * s, 178 * s), "Pick a person, turn the pose in 3D, frame it,", font=font(18), fill=theme["muted"])
    draw.text((58 * s, 203 * s), "and draw the skeleton your image model follows.", font=font(18), fill=theme["muted"])

    # The far half of the orbit, behind the figure.
    far = [on_ring(centre, a) for a in np.linspace(math.pi, 2 * math.pi, 120)]
    draw.line(far, fill=theme["ring"], width=2 * s, joint="curve")

    # rtmlib draws the face in white, lost on a light background: tint it.
    pixels = np.array(figure)
    white = (pixels[..., :3] > 200).all(axis=2)
    pixels[white, :3] = np.array(ImageColor.getrgb(theme["white"]), np.uint8)
    image.alpha_composite(Image.fromarray(pixels), (LEFT_TOP[0] * s, LEFT_TOP[1] * s))
    draw = ImageDraw.Draw(image)

    # The near half, in front of the figure: the camera swings along it (yaw).
    near = [on_ring(centre, a) for a in np.linspace(0, math.pi, 120)]
    draw.line(near, fill=theme["accent"], width=2 * s, joint="curve")
    a = math.radians(125)
    arrow_head(draw, on_ring(centre, a), (-RING[0] * math.sin(a), RING[1] * math.cos(a)), theme["accent"])
    label = on_ring(centre, math.radians(140))
    draw.text((label[0] - 30 * s, label[1] + 6 * s), "yaw", font=font(14), fill=theme["accent"])

    # The pitch arc: from the right end of the orbit, up over the figure.
    start = on_ring(centre, 0)
    arc = [
        (start[0] - (1 - math.cos(t)) * 70 * s, start[1] - math.sin(t) * PITCH_RISE * s)
        for t in np.linspace(math.radians(6), math.radians(70), 60)
    ]
    draw.line(arc, fill=theme["accent"], width=2 * s, joint="curve")
    arrow_head(draw, arc[-1], (arc[-1][0] - arc[-4][0], arc[-1][1] - arc[-4][1]), theme["accent"])
    draw.text((start[0] + 12 * s, start[1] - 70 * s), "pitch", font=font(14), fill=theme["accent"])
    return image.convert("RGB")


def main() -> None:
    figure, centre = skeleton()
    for name, theme in THEMES.items():
        path = ASSETS / f"banner-{name}.png"
        banner(theme, figure, centre).save(path, optimize=True)
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
