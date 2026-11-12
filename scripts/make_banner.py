"""Draws the README banner (docs/assets/banner-{light,dark}.png): the name and
what poseorbit does on the left, and on the right one skeleton, turned by
poseorbit itself, inside the sphere its camera moves on: dots on the orbit
where it can stand (yaw), the meridian it climbs to the 45-degree limit
(pitch), and the camera that drew the skeleton, looking at the hips.

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
from itertools import pairwise
from pathlib import Path

import numpy as np
from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont

from poseorbit import (
    KEYPOINT_THRESHOLD,
    MAX_PITCH,
    Camera,
    fit,
    render,
    scene_centre,
    view,
)

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "docs" / "assets"
W, H, SCALE = 1280, 320, 2

# "ring" is the orbit and the camera's other places, "accent" the camera in
# use and where it can go. Both stay at least 3:1 against "bg" (WCAG 1.4.11
# for graphics), the accent clearly above the ring.
THEMES = {
    "light": {"bg": "#fafafa", "fg": "#171717", "white": "#525252", "muted": "#737373", "ring": "#8a7fdc", "accent": "#5b4ad6"},
    "dark": {"bg": "#0a0a0a", "fg": "#fafafa", "white": "#ffffff", "muted": "#a3a3a3", "ring": "#6459b4", "accent": "#b4abfa"},
}

CAMERA = Camera(yaw=-30, pitch=12)
FIGURE = (240, 296)  # the box the turned skeleton is fitted into
LEFT_TOP = (830, 8)  # where that box goes
# The camera's sphere around the hips, as drawn: the orbit's half width and
# half height, and how tall the sphere looks above it (not to scale: the real
# sphere would not fit the banner).
RING = (215, 40)
RISE = 120
YAW_STEP = 30  # a dot on the orbit every this many degrees of yaw

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


def on_sphere(centre: tuple[float, float], yaw: float, pitch: float = 0.0) -> tuple[float, float]:
    """Where the camera at (`yaw`, `pitch`) is drawn, in scaled pixels. Yaw 0
    is the near side of the orbit (lower on screen), +yaw to the viewer's
    right; pitch lifts it towards the top of the sphere."""
    a, e = math.pi / 2 - math.radians(yaw), math.radians(pitch)
    return (
        (centre[0] + RING[0] * math.cos(e) * math.cos(a)) * SCALE,
        (centre[1] + RING[1] * math.cos(e) * math.sin(a) - RISE * math.sin(e)) * SCALE,
    )


def arrow_head(draw: ImageDraw.ImageDraw, tip: tuple[float, float], towards: tuple[float, float], colour: str) -> None:
    """A filled arrow head at `tip` (scaled pixels), pointing along `towards`."""
    length = math.hypot(*towards)
    ux, uy = towards[0] / length, towards[1] / length
    back, half = 12 * SCALE, 6 * SCALE
    bx, by = tip[0] - ux * back, tip[1] - uy * back
    draw.polygon([tip, (bx - uy * half, by + ux * half), (bx + uy * half, by - ux * half)], fill=colour)


def dot(draw: ImageDraw.ImageDraw, at: tuple[float, float], radius: float, theme: dict, filled: bool) -> None:
    r = radius * SCALE
    box = [at[0] - r, at[1] - r, at[0] + r, at[1] + r]
    if filled:
        draw.ellipse(box, fill=theme["accent"])
    else:
        draw.ellipse(box, outline=theme["ring"], width=2 * SCALE, fill=theme["bg"])


def dashed(draw: ImageDraw.ImageDraw, points: list[tuple[float, float]], colour: str, dash: float = 6, gap: float = 5) -> None:
    """A dashed line along `points` (scaled pixels)."""
    pattern = [dash * SCALE, gap * SCALE]
    phase, left, segment = 0, pattern[0], [points[0]]
    for p, q in pairwise(points):
        length, done = math.dist(p, q), 0.0
        while length - done > left:
            done += left
            point = (p[0] + (q[0] - p[0]) * done / length, p[1] + (q[1] - p[1]) * done / length)
            if phase == 0:
                draw.line(segment + [point], fill=colour, width=2 * SCALE)
            phase, left, segment = 1 - phase, pattern[1 - phase], [point]
        left -= length - done
        if phase == 0:
            segment.append(q)
    if phase == 0 and len(segment) > 1:
        draw.line(segment, fill=colour, width=2 * SCALE)


def banner(theme: dict, figure: Image.Image, centre: tuple[float, float]) -> Image.Image:
    s = SCALE
    image = Image.new("RGBA", (W * s, H * s), theme["bg"])
    draw = ImageDraw.Draw(image)

    draw.text((56 * s, 104 * s), "poseorbit", font=font(60), fill=theme["fg"])
    draw.text((58 * s, 178 * s), "Pick a person, turn the pose in 3D, frame it,", font=font(18), fill=theme["muted"])
    draw.text((58 * s, 203 * s), "and draw the skeleton your image model follows.", font=font(18), fill=theme["muted"])

    # The far half of the orbit, behind the figure (yaw beyond +-90).
    far = [on_sphere(centre, yaw) for yaw in np.linspace(90, 270, 120)]
    draw.line(far, fill=theme["ring"], width=2 * s, joint="curve")

    # rtmlib draws the face in white, lost on a light background: tint it.
    pixels = np.array(figure)
    white = (pixels[..., :3] > 200).all(axis=2)
    pixels[white, :3] = np.array(ImageColor.getrgb(theme["white"]), np.uint8)
    image.alpha_composite(Image.fromarray(pixels), (LEFT_TOP[0] * s, LEFT_TOP[1] * s))
    draw = ImageDraw.Draw(image)

    # The near half, in front of the figure, with the places the camera can
    # stand as it swings around (yaw), up to the side views.
    near = [on_sphere(centre, yaw) for yaw in np.linspace(-90, 90, 120)]
    draw.line(near, fill=theme["ring"], width=2 * s, joint="curve")
    for yaw in range(-90, 91, YAW_STEP):
        if yaw != round(CAMERA.yaw):
            dot(draw, on_sphere(centre, yaw), 5, theme, False)

    # The meridian through the camera: it climbs along it (pitch), solid to
    # the 45-degree limit, dashed beyond.
    climb = [on_sphere(centre, CAMERA.yaw, e) for e in np.linspace(0, MAX_PITCH, 40)]
    dashed(draw, [on_sphere(centre, CAMERA.yaw, e) for e in np.linspace(MAX_PITCH, 90, 30)], theme["ring"])
    draw.line(climb, fill=theme["accent"], width=2 * s, joint="curve")
    for e in (30,):  # 15 would sit under the camera
        dot(draw, on_sphere(centre, CAMERA.yaw, e), 4, theme, False)
    arrow_head(draw, climb[-1], (climb[-1][0] - climb[-4][0], climb[-1][1] - climb[-4][1]), theme["accent"])

    # The camera in use, and its line of sight to the hips.
    camera = on_sphere(centre, CAMERA.yaw, CAMERA.pitch)
    draw.line([camera, (centre[0] * s, centre[1] * s)], fill=theme["accent"], width=2 * s)
    dot(draw, camera, 9, theme, True)
    return image.convert("RGB")

def main() -> None:
    figure, centre = skeleton()
    for name, theme in THEMES.items():
        path = ASSETS / f"banner-{name}.png"
        banner(theme, figure, centre).save(path, optimize=True)
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
