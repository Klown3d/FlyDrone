# Integrated v4 prospective gate preregistration

## Frozen change

V4 adds a conventional lateral-velocity damper of 0.25 s^-1 to every neural,
ablation and matched-direct condition. The conventional baseline retains its
own preregistered 2.0 s^-1 damping. No FlyWire connectivity, neural parameter,
arrival parameter or gate threshold changes from v3.

The damper is an engineering stabilizer, not a biological mechanism. It was
selected on 144 development episodes excluded from this gate. On the fine
paired development set, the full circuit achieved 12/12 and median maximum
cross-track fell from 2.325 m without damping to 1.963 m. The hDeltaB ablation
with the selected damper achieved 1/12, preserving an 11-flight dependency gap.
Stronger values were rejected because they increasingly replaced hDeltaB.

## Sealed evaluation

The gate contains 30 new cases per condition and six conditions, for 180
episodes. Bearings, headings, scenario parameters and seeds have not appeared
in v2, v3 or lateral-controller development. The ten v3 thresholds are reused
unchanged, including the maximum 0.80 m cross-track cost versus conventional.

All criteria must pass. Passing supports a robust simulated integration; it
does not establish biological dynamics, physical-drone readiness or superiority
of exact FlyWire connectivity over every matched null graph.
