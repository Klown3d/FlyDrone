# Integrated v3 prospective gate preregistration

## Decision fixed before execution

The selected terminal candidate is a bounded engineering velocity damper. It
acts only after sustained arrival evidence, uses the supervisor's filtered
observed velocity, has gain 0.15 s^-1 and is limited to 0.10 m/s². It is applied
unchanged to every condition and is not part of the reconstructed neural
circuit.

Selection used 48 development flights on cases excluded from this gate. The
exit-only reference achieved 10/12; position-only, velocity-only and weak PD
variants each achieved 12/12. The velocity-only candidate was selected for
parsimony and the best median path efficiency among the four variants.

## Sealed evaluation

The gate contains 30 previously unused cases per condition and six conditions,
for 180 episodes. Bearings, initial headings, scenario parameters, seeds,
source files, processed connectivity and environment versions are frozen in the
protocol lock before execution.

Conditions are the intact FlyWire-derived controller, PFL2 removal, hDeltaB
removal, Delta7/PFL3 steering ablation, a matched direct-velocity readout, and a
conventional navigation baseline. The arrival layer is shared by all six.

## Primary criteria

All ten criteria encoded in the YAML gate must pass. The primary outcomes are
full-controller arrival success and success within each scenario. Dependency
ablations, comparison deficits, arrival-time cost, cross-track cost and motor
saturation are preregistered secondary gate criteria. No threshold may change
after the lock is created.

Passing this gate would support functionality and circuit dependency in this
simulator. It would not establish biological dynamics, superiority over all
conventional controllers, or readiness for a physical drone.
