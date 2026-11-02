# Projection-separated steering-null development results

## Result

The intact FlyWire-grounded steering pathway completed 12/12 development
cases. Rewiring only EPG→Delta7 produced `[7, 2, 1, 4, 2]` successes. Rewiring
only Delta7→PFL3 produced `[3, 3, 3, 4, 1]` successes.

| Group | Null success range | Median | Mean | Median cross-track |
|---|---:|---:|---:|---:|
| Intact | 12/12 | 12 | 12 | 2.242 m |
| EPG→Delta7-only nulls | 1–7/12 | 2 | 3.2 | 9.284 m |
| Delta7→PFL3-only nulls | 1–4/12 | 3 | 2.8 | 9.681 m |

Every one of the ten null networks performed worse than intact and had a
higher condition-level median maximum cross-track displacement.

## Interpretation

The earlier prospective steering gate rewired both projections together. This
diagnostic shows that neither effect is attributable only to the other
projection: EPG→Delta7 rewiring degraded navigation while Delta7→PFL3 remained
intact, and Delta7→PFL3 rewiring degraded navigation while EPG→Delta7 remained
intact.

The Delta7→PFL3 group was more uniform across seeds, whereas EPG→Delta7
included one partially functional 7/12 null. This is a useful mechanistic
difference, not evidence that one projection is biologically more important.

Each null preserved binary row and column degrees and postsynaptic row-weight
multisets inside presynaptic source-side blocks. The untouched projection was
identical to intact, and each null received an outcome-independent algebraic
global phase alignment.

## Limits and decision

These are reused development cases with five nulls per projection. The
descriptive minimum rank value is only `1/6 = 0.167`; no projection-specific
confirmatory claim is made.

Both projections justify independent prospective gates. Delta7→PFL3 is the
best first choice because its development effect was more consistent. The
prospective experiment must use 20 new seeds, new paired cases and a frozen
rank rule before execution. EPG→Delta7 should then be tested separately rather
than combined with the same null distribution.

Machine-readable analysis is stored at
`results/simulation/quadrotor_integrated_v4_steering_projection_null_development/projection_null_development_analysis.json`.
