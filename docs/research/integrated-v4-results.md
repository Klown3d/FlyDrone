# Integrated v4 prospective results

## Verdict

The prospectively frozen integrated v4 gate completed 180 simulated flights
and passed all 10 preregistered criteria. This is the first integrated FlyDrone
gate to pass under its frozen all-criteria rule.

| Condition | Successes | Exact 95% interval |
|---|---:|---:|
| Full FlyWire-grounded v4 | 28/30 | 77.9–99.2% |
| Without PFL2 | 29/30 | 82.8–99.9% |
| Without hDeltaB | 4/30 | 3.8–30.7% |
| Delta7/PFL3 ablated | 0/30 | 0.0–11.6% |
| Matched direct-velocity readout | 30/30 | 88.4–100% |
| Conventional navigation | 30/30 | 88.4–100% |

The full condition achieved 15/15 in combined-late perturbations and 13/15 in
heading-and-velocity-loss perturbations. Median arrival time was 23.096 s,
2.766 s slower than conventional navigation and within the frozen 8 s bound.
No motor saturation occurred.

## Resolved v3 failure

V3 failed only the cross-track-cost criterion at 1.109 m. V4 added a weak
engineering lateral damper of 0.25 s^-1, selected on separate development
cases. Median maximum cross-track was 1.974 m for FlyWire and 1.396 m for the
conventional baseline, a preregistered aggregate cost of 0.579 m against the
0.80 m limit.

The paired median FlyWire-minus-conventional difference was 0.555 m. Its
20,000-resample bootstrap 95% interval was 0.396–0.814 m. The fixed gate passes,
but the interval's upper edge indicates that a larger evaluation is needed for
a precise estimate of the trajectory cost.

## Circuit dependency and controls

Removing hDeltaB reduced success from 28/30 to 4/30. Removing the Delta7/PFL3
steering pathway reduced it to 0/30. Thus the weak damper did not replace the
implemented neural pathways. These are computational ablations and establish
dependency within this model, not biological causality.

The matched direct-velocity controller achieved 30/30 and had 0.102 m lower
paired median cross-track than FlyWire (bootstrap interval 0.041–0.286 m).
Consequently, this gate demonstrates useful, comparable and circuit-dependent
navigation, but not performance superiority of exact FlyWire connectivity.

PFL2 removal achieved 29/30. FlyWire had 0.139 m lower paired median cross-track
than the no-PFL2 condition (bootstrap interval 0.003–0.350 m in FlyWire's
favor), but the success comparison does not establish that PFL2 is necessary.

## Two failed full-controller episodes

Both failures occurred in the heading-and-velocity-loss scenario with initial
relative heading 23 degrees. One ended inside the radius at 0.085 m and 0.038
m/s, but its arrival latch changed state three times and observed speed reached
0.182 m/s during the terminal window. The other released its latch and ended
0.469 m from the target at 0.089 m/s. These remain bounded terminal-recovery
failures rather than general navigation divergence.

## Scientific claim

The supported claim is that a FlyWire-grounded computational circuit, combined
with explicit engineering sensing, damping, arrival supervision and a
conventional low-level stabilizer, produced robust high-level navigation in
this simulated 6-DoF benchmark and depended strongly on the implemented
hDeltaB and Delta7/PFL3 pathways.

The experiment does not show that a complete fly brain controls a drone, that
the neural controller outperforms conventional control, or that exact FlyWire
topology is uniquely responsible. Degree- and weight-preserving null networks
are the next required attribution test.

Frozen inputs and result hashes are preserved under `archive/integrated_v4/`.
