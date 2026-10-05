# Command line

`poseorbit` (or `python -m poseorbit`) has two commands.

## `draw`

Draws one picture's skeleton to a PNG.

```sh
poseorbit draw PICTURE OUT.png [options]
```

| Option | Default | Meaning |
|---|---|---|
| `--size WxH` | the picture's | The output's size, e.g. `832x1216` |
| `--person N` | the most confident | An index (left to right), or `-1` for everyone |
| `--yaw D` | `0` | Degrees; positive swings the camera to the viewer's right |
| `--pitch D` | `0` | Degrees; positive raises the camera |
| `--zoom Z` | `1` | Framing zoom, 0.5–6 |
| `--centre X,Y` | `0.5,0.5` | The canvas point to centre, as fractions |
| `--style S` | `dwpose` | `dwpose` or `openpose` |
| `--weights-dir DIR` | `~/.cache/poseorbit` | Where the model files are kept |

It prints how many people it found and what it drew:

```text
$ poseorbit draw group.png out.png --size 832x1216 --person 1 --yaw 30
2 found; drew person 1 at yaw 30.0, pitch 0.0, zoom 1.0; 17 body joints in frame
```

## `serve`

Answers the [HTTP API](http.md); needs `pip install "poseorbit[server]"`.

```sh
poseorbit serve [--host 127.0.0.1] [--port 7870] [--weights-dir DIR]
```

Set `POSEORBIT_TOKEN` to require a Bearer token.
