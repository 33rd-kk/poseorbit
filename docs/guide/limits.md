# Limits and tips

poseorbit guesses a 3D pose from one picture. That goes a long way, and it
runs out in known places.

## Turning

- **Depth is a guess.** Past a side view, which limb is in front gets
  unreliable; that is why the camera stops at ±90° yaw and ±45° pitch. A
  moderate turn (up to about 45°) is the safe range.
- **A stray point is held in.** A foot, face or hand point's depth is kept
  close to the middle depth of its foot, face or hand
  (`poseorbit.detect.DETAIL_REACH`), so one wrong guess cannot draw a long
  line once the pose is turned.
- **Front or back?** Some models do not tell front from back by the skeleton
  alone and draw a strongly turned figure from behind. What helps:
    - turn away from the side the figure already shows (the nearer shoulder
      has the smaller `Person.depth`);
    - keep the turn moderate;
    - put "front view" in the prompt and "from behind" in the negative.

## Detection

- **Small figures.** A person is drawn where they stand in the picture, so a
  small figure gives a small skeleton, which models follow loosely. Zoom in
  with [framing](turn-and-frame.md#frame-it).
- **Hidden joints.** Points the detector does not see well (score under
  0.3) are not drawn; a figure needs 8 of its 17 body joints seen to count
  as a person.
- **People only.** Animals and other non-human figures are not detected.

## Close-ups

A body-only skeleton (`openpose`) keeps few points in a face close-up: check
`result.joints_in_frame`. The `dwpose` style keeps the face and hands, and
models that read it follow a close-up's head tilt and turn.

## How well models follow

Measured numbers for both styles, with and without the skeleton, are in
[Skeleton styles](styles.md#measured).
