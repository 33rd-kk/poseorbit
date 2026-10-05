# Coordinates

The whole mapping from picture to skeleton is specified, so a viewer (a 3D
preview in a browser, say) can show exactly what will be drawn.

## Points

x right, y down, depth away from the viewer, all in the picture's pixels.
Depth is relative to each person's hips (the middle of keypoints 11 and 12).
The HTTP API divides all three by the picture's width, so a client needs
neither its size nor its aspect.

## The camera

The camera orbits the **scene centre**: the middle of the drawn people's
hips, at the hips' depth. With `yaw` and `pitch` in degrees it stands, as a
unit vector from the centre (y down, z away), at

```
(sin yaw · cos pitch,  −sin pitch,  −cos yaw · cos pitch)
```

and looks at the centre with y down as its up reference. It is
orthographic: a point's screen position is its offset from the centre along
the camera's right and down vectors, plus the centre's x and y. The front
view (yaw 0, pitch 0) leaves x and y unchanged.

In a y-up, z-toward-viewer frame such as three.js, the same camera stands at

```
(sin yaw · cos pitch,  sin pitch,  cos yaw · cos pitch)
```

and the angles read back as `yaw = atan2(x, z)`, `pitch = atan2(y, hypot(x, z))`.

## Onto the output canvas

The turned picture is **letterboxed** onto the output canvas: scaled
uniformly by `min(W / w, H / h)` and centred, never stretched (a landscape
reference is not squashed onto a portrait canvas).

## Framing

Then the **framing** crops the canvas like a photo: the canvas point
(`x · W`, `y · H`) moves to the middle, and everything scales by `zoom`
around it:

```
p' = (p − (x·W, y·H)) · zoom + (W/2, H/2)
```

## Matching it in a viewer

An orthographic three.js camera aimed as above shows the same skeleton when
its bounds are the framed part of the canvas, mapped back to picture units
around the scene centre. [Latentry](https://github.com/33rd-kk/latentry)'s 3D
view does exactly this and is tested against poseorbit's numbers to within
0.05 px.
