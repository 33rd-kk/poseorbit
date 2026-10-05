# Usage

Everything goes through one [`Detector`][poseorbit.Detector] (it loads its
models once and is safe to share between threads) and, usually, one call to
[`pose`][poseorbit.pose]. The steps below show what that call does, and how
to do each step yourself.

## 1. Find the people

```python
from PIL import Image
from poseorbit import Detector

detector = Detector()                       # or Detector(weights_dir=Path("weights"))
picture = Image.open("reference.png")

people = detector.detect(picture)           # left to right
for index, person in enumerate(people):
    print(index, person.bbox, person.visible)
```

Each [`Person`][poseorbit.Person] has 133 COCO-WholeBody keypoints in the
picture's pixels, their scores, a `bbox` around what would be drawn, and
`visible`, the number of body joints (of 17) seen.

People come back **left to right by the centre of the figure**, so the same
picture numbers its people the same way every time: index 1 is the same
person on every call. A detection with fewer than 8 of 17 body joints seen is
not a person (a blank canvas otherwise "finds" one); with nobody left,
`detect` raises [`NoPersonError`][poseorbit.NoPersonError].

Pass `depth=True` to also get each keypoint's depth (`Person.depth`, in the
same pixels as x and y, positive away from the viewer). It costs about 0.3 s
more; `pose` asks for it only when the camera turns.

## 2. Choose whose pose

```python
from poseorbit import ALL_PEOPLE, pose

pose(detector, picture, size=(832, 1216), person=0)            # the leftmost
pose(detector, picture, size=(832, 1216), person=ALL_PEOPLE)   # everyone (-1)
pose(detector, picture, size=(832, 1216))                      # the most confident
```

Everyone together turns around one shared centre, so a group keeps its
layout.

## 3. Turn it

```python
from poseorbit import Camera

result = pose(detector, picture, size=(832, 1216), camera=Camera(yaw=-30, pitch=10))
```

[`Camera`][poseorbit.Camera] orbits the figure: `yaw` swings it to the
viewer's right (negative: left), `pitch` raises it. It is orthographic, so
turning never makes the figure bigger or smaller. Angles are held to ±90°
yaw and ±45° pitch: depth comes from a single picture, and past a side view
which limb is in front gets unreliable.

!!! tip "Front or back?"
    Some models do not tell front from back by the skeleton alone, and draw
    a strongly turned figure from behind. Turn away from the side the figure
    already shows (the nearer shoulder has the smaller `Person.depth`), keep
    the turn moderate, and put "front view" in the prompt and "from behind"
    in the negative.

## 4. Frame it

```python
from poseorbit import Framing

# The face of a full-body picture: centre on it and zoom about five times.
result = pose(detector, picture, size=(832, 1216),
              framing=Framing(zoom=5, x=0.62, y=0.2))
print(result.joints_in_frame)   # body joints still inside the canvas
```

[`Framing`][poseorbit.Framing] crops the output canvas like a photo: the
canvas point (`x`, `y`, as fractions) moves to the middle and everything
scales by `zoom` (0.5 to 6). Below 1 it pulls back, leaving black around the
figure. Framing never moves the point the camera orbits.

`joints_in_frame` tells how much of the body is left: with a body-only
skeleton (the `openpose` style), a close-up keeps few points to follow.

## 5. Draw it

`pose` draws for you, in `style="dwpose"` or `style="openpose"`; see
[Skeleton styles](styles.md). The result's `skeleton` is a PIL image at
`size`, on black.

To draw keypoints of your own, call [`render`][poseorbit.render]; to fit a
skeleton drawn at another size onto your output, [`letterbox`][poseorbit.letterbox].

## With diffusers

```python
import torch
from diffusers import ControlNetModel, StableDiffusionXLControlNetPipeline

controlnet = ControlNetModel.from_pretrained(
    "xinsir/controlnet-openpose-sdxl-1.0", torch_dtype=torch.float16)
pipe = StableDiffusionXLControlNetPipeline.from_pretrained(
    "stabilityai/stable-diffusion-xl-base-1.0", controlnet=controlnet,
    torch_dtype=torch.float16).to("cuda")

skeleton = pose(detector, picture, size=(832, 1216),
                camera=Camera(yaw=45), style="openpose").skeleton
image = pipe("1girl, full body", image=skeleton, width=832, height=1216).images[0]
```

The skeleton must be drawn at the size you generate at, as here.

## From another program

Run `python -m poseorbit serve` and post to `/api/pose`; see the
[HTTP API](../reference/http.md). A generation server can embed the same
handler, [`poseorbit.api.handle`][poseorbit.api.handle], so both speak one
API.
