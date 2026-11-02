# Connectome-attribution synthesis

## Question

Does simulated FlyDrone navigation depend on the specific FlyWire-grounded
partner arrangements, or would matched networks with the same basic graph
statistics perform similarly?

## Prospective evidence

Four independently frozen gates tested this question. Each used 12 new paired
cases for the intact controller and each of 20 null networks. All four reached
the preregistered minimum attainable plus-one rank value of `1/21 = 0.047619`.

| Tested connectivity | Intact | Null median | Best null | Zero-success nulls | Median cross-track: intact / null (m) |
|---|---:|---:|---:|---:|---:|
| PFN-to-hDeltaB | 12/12 | 0/12 | 6/12 | 12/20 | 1.80 / 5.89 |
| EPG-to-Delta7 and Delta7-to-PFL3 jointly | 12/12 | 1.5/12 | 7/12 | 7/20 | 1.84 / 8.91 |
| Delta7-to-PFL3 only | 12/12 | 1.5/12 | 8/12 | 8/20 | 2.42 / 12.04 |
| EPG-to-Delta7 only | 12/12 | 1/12 | 6/12 | 8/20 | 2.47 / 10.95 |

Across these gates there were 80 prospectively generated null networks and
960 null-network flights, plus 48 paired intact flights. No null network
matched the 12/12 intact result. Every null condition also had worse median
maximum cross-track deviation than its paired intact condition.

These experiments are separate tests with different sealed cases. Their
p-values are reported individually and are not multiplied, pooled or treated
as four independent measurements of one biological effect.

## Supported conclusion

Within the implemented computational model, useful simulated navigation
depends on specific FlyWire-grounded partner arrangements in multiple pathway
stages, beyond the neuron counts and selected degree/row-weight statistics
preserved by the matched null generators.

The projection-specific gates reduce the ambiguity of the earlier joint gate:
EPG-to-Delta7 and Delta7-to-PFL3 each show prospective loss of function when
rewired while the other projection is kept intact. PFN-to-hDeltaB independently
shows the same pattern for the travel-direction/drift pathway.

## What is not demonstrated

- The complete fly brain is not simulated.
- These results do not establish causal neural function in a living fly.
- The connectome controller has not been shown to outperform conventional
  control; direct and conventional baselines remain highly competitive.
- The null models do not preserve every possible higher-order structural
  statistic.
- Synapse counts are used as computational weights, but anatomy alone does not
  determine all physiological gains, time constants, signs or modulation.
- Sensor encoding, state estimation, arrival supervision, low-level
  stabilization and drone physics contain explicit engineering choices.

## Current scientific status

The project has moved beyond module ablation. It now has prospective evidence
that controlled changes to partner identity impair navigation while important
low-order graph statistics are retained. This substantially strengthens the
claim of connectome dependence within simulation.

The next scientific priority is not another similar null gate. It is an
out-of-distribution evaluation with a sealed scenario generator, larger
confidence intervals and a sensitivity analysis over engineering gains and
neural time constants. That work would test whether the attribution result is
robust rather than specific to the present simulator regime.
