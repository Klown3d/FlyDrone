# V4 EPG→Delta7→PFL3 steering-null preregistration

## Question

Does the intact FlyWire-grounded EPG→Delta7→PFL3 arrangement outperform
rewired matrices that preserve binary row and column degrees and every
postsynaptic row's weight multiset within presynaptic source-side blocks?

This is a projection-specific computational test. It does not test the entire
central complex and does not establish biological causality.

## Frozen design

Twenty new deterministic rewiring seeds and one intact condition will be
tested on 12 new paired cases, for 252 simulated flights. Both steering
projections are rewired independently. PFN→hDeltaB, PFL2, sensors, plant,
arrival supervision and engineering damping remain identical.

Each null receives one algebraic global phase alignment to the intact
composite transfer before simulation. Arrival outcomes are not used for that
calibration. Nonuniform PFL3 phase residuals are retained and reported.

The primary metric is arrival success. Intact must achieve at least 10/12. The
one-sided empirical rank value is `(1 + nulls with success >= intact) / 21`.
The primary gate passes only at p <= 0.05, requiring all 20 nulls to perform
worse than intact. Cross-track and phase residuals are secondary.

The five development seeds (52011, 52021, 52027, 52051, 52057), their 12 cases,
and their outcomes are excluded from this gate.
