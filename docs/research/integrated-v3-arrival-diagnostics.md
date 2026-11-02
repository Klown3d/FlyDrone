# Integrated v3 arrival diagnostics

## Scope

These are post-gate diagnostics on the same 30 full-controller cases used by the
integrated v2 gate. They are not confirmatory evidence and must not be reported
as a new prospective gate. The FlyWire-derived steering and drift circuit was
unchanged. Only the explicit engineering arrival interface varied.

## Results

| Variant | Successes | Interpretation |
|---|---:|---|
| Integrated v2 frozen gate | 26/30 | Prospective reference; exit radius was 0.45 m. |
| Exit radius 0.28 m | 27/30 | Best diagnostic; recovered one case. |
| Bounded position/velocity hold | 7/30 | Rejected. Delayed filtered feedback produced excessive residual speed. |
| Absorbing arrival latch | 25/30 | Rejected. Preventing release did not stabilize the vehicle. |

The bounded hold used only filtered observed position and velocity, with gains
0.80 s^-2 and 0.60 s^-1 and a maximum acceleration of 0.35 m/s². It did not
saturate motors, but median final speed was about 0.086 m/s, above the 0.05 m/s
success threshold. Its poor result shows that a conventional position hold
cannot simply be attached to delayed state estimates without a dedicated
stability design.

The absorbing latch also failed to recover the three original terminal cases
and lost two additional cases. Arrival therefore cannot be treated as an
irreversible state in the dynamic plant.

## Decision

Do not promote either new variant to a prospective v3 gate. Keep integrated v2
as the frozen result and the 0.28 m exit-radius run as a post-hoc diagnostic.
The next implementation should be a separately tested terminal controller with
explicit delay/noise robustness, shared unchanged by every neural and
conventional condition. Candidate gains must be selected on development cases
that exclude the future sealed gate cases.

This layer is engineering, not biological. Its performance cannot be credited
to the FlyWire circuit.
