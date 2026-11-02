# Integrated v3 prospective results

## Verdict

The prospectively frozen v3 gate completed 180 simulated flights and passed 9
of 10 preregistered criteria. Under the preregistered all-criteria rule, the
gate therefore **did not pass**. Parameters and thresholds were not changed
after inspecting the results.

## Primary results

| Condition | Successes |
|---|---:|
| Full FlyWire-grounded v3 | 29/30 |
| Without PFL2 | 27/30 |
| Without hDeltaB | 0/30 |
| Delta7/PFL3 ablated | 0/30 |
| Matched direct-velocity readout | 30/30 |
| Conventional navigation | 30/30 |

The full model achieved 15/15 in the combined-late scenario and 14/15 in the
heading-and-velocity-loss scenario. Its only failed episode ended 0.426 m from
the target at 0.184 m/s. The weak terminal velocity damper therefore improved
prospective success from v2's 26/30 to 29/30 on a new case set, but this is a
cross-version descriptive comparison rather than a paired causal estimate.

## Gate criteria

Nine criteria passed: full functionality, per-scenario functionality, hDeltaB
dependency, Delta7/PFL3 dependency, direct-readout comparability, conventional
comparability, PFL2 non-degradation, bounded arrival-time cost and motor
saturation.

The failed criterion was bounded cross-track cost. Median maximum cross-track
was 2.455 m for FlyWire and 1.346 m for the conventional controller, a cost of
1.109 m against the frozen maximum of 0.80 m. The gate must remain classified
as failed even though success rate and arrival stability improved.

Median arrival time was 23.716 s for FlyWire and 20.451 s for conventional
navigation, a 3.265 s cost within the allowed 8.0 s. FlyWire was one success
behind both the direct and conventional controls and two successes ahead of
the no-PFL2 condition. No condition saturated the motors.

## Interpretation

The result supports useful simulated navigation and strong dependency on the
implemented hDeltaB and Delta7/PFL3 pathways. It does not establish that exact
FlyWire connectivity is superior to a matched non-neural rule: the direct
readout achieved 30/30. The remaining engineering weakness is trajectory
geometry, especially lateral excursions, rather than general goal reaching.

The arrival damper is an engineering layer shared by every condition and must
not be credited to the reconstructed neural circuit. The circuit remains a
FlyWire-grounded computational model, not a complete fly brain.

## Next experiment

Do not retune this frozen gate. Develop lateral-path control on separate cases,
then test exact-connectivity attribution with degree- and weight-preserving
null networks. Any later confirmatory gate must use newly sealed cases.

Frozen inputs and result hashes are preserved under `archive/integrated_v3/`.
