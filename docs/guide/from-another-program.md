# From another program

## The command line

```sh
poseorbit draw reference.png skeleton.png --size 832x1216 --yaw -30
poseorbit draw group.png both.png --size 832x1216 --person -1 --style openpose
poseorbit draw reference.png face.png --size 832x1216 --zoom 5 --centre 0.5,0.13
```

`poseorbit` and `python -m poseorbit` are the same. Every option is in the
[command line reference](../reference/cli.md).

## The HTTP server

```sh
pip install "poseorbit[server]"
POSEORBIT_TOKEN=change-me poseorbit serve --port 7870
```

```sh
curl -s localhost:7870/api/pose -H "Authorization: Bearer change-me" \
  -H 'Content-Type: application/json' -d '{
  "image_base64": "<base64 PNG or JPEG>", "width": 832, "height": 1216,
  "person": 0, "camera": { "yaw": 30, "framing": { "zoom": 2, "y": 0.35 } },
  "style": "openpose" }'
```

The answer carries the skeleton as a base64 PNG, the people found, and what
was used. Everything but `image_base64` is optional; the
[HTTP API reference](../reference/http.md) has every field and error.

It is meant for one machine:

- It listens on **127.0.0.1 only** unless `--host` says otherwise. Before
  opening it to a network, set `POSEORBIT_TOKEN`: then every request but
  `/api/health` needs `Authorization: Bearer <token>`.
- Pictures are read in memory and not kept; the server writes nothing to
  disk but the model files on first use.
- The output size (64 to 4096 a side), a list of people (up to 64) and the
  edits (up to 256) are bounded, and out-of-range angles and zoom are
  clamped.

## Inside your own server

A server that already has its own routes can answer the same requests
without running a second one:

```python
from poseorbit import Detector
from poseorbit.api import handle

detector = Detector()

def pose_route(body: dict) -> dict:          # your framework's handler
    return handle(detector, body, "dwpose")  # same request, same answer
```

[`poseorbit.api.handle`][poseorbit.api.handle] takes the parsed JSON body
and returns the answer as a dict. On a bad request it raises
`poseorbit.api.BadRequest`, [`NoPersonError`][poseorbit.NoPersonError] or
`ValueError` (all `ValueError`s), each with a message to answer as a 400.
So a client written for `poseorbit serve` works against your server
unchanged.
