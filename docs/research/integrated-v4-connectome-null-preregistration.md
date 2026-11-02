# V4 PFN-to-hDeltaB connectome-null preregistration

## Question

Does the intact FlyWire PFN-to-hDeltaB arrangement outperform a distribution
of rewired matrices that preserve binary row and column degrees and each
hDeltaB neuron's nonzero weight multiset within PFN type/side blocks?

This test is projection-specific. It does not test uniqueness of the whole
central-complex graph, and column weight sums are not preserved.

## Frozen design

Twenty deterministic rewiring seeds and one intact condition are evaluated on
12 previously unused paired cases, for 252 simulated flights. Every null is
given one global angular recalibration so a constant phase rotation alone does
not cause failure. Sensors, neural dynamics, engineering layers and plant are
otherwise identical.

The primary metric is arrival success. The intact circuit must achieve at least
10/12. The one-sided empirical rank p-value uses a plus-one correction:
`(1 + number of nulls with success >= intact) / 21`. The primary attribution
gate passes only at p <= 0.05, which requires all 20 nulls to score below the
intact circuit. Cross-track, arrival time and path efficiency are secondary.

The strict rank criterion was fixed after a five-seed development diagnostic
in which null successes were 12, 4, 0, 0 and 0 against intact 12/12. Those
development cases and seeds are excluded here.
