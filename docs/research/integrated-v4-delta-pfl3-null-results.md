# Prospective Delta7-to-PFL3 connectome-null gate

## Outcome

**The prospectively frozen gate passed.** In 252 paired simulated flights, the intact
FlyWire-grounded controller reached the goal in 12/12 cases. None of the 20 matched
Delta7-to-PFL3 null networks equalled that result. The plus-one empirical rank value
was `1/21 = 0.047619`, meeting the preregistered `p <= 0.05` threshold.

This is evidence that, in this computational model and these scenarios, the exact
FlyWire-grounded partner arrangement from Delta7 neurons to PFL3 neurons contributes
to successful simulated navigation beyond the block-wise degree and row-weight
statistics preserved by the null generator.

It is not evidence that the entire fly brain controls the drone, proof of biological
causality in a living animal, or evidence that this controller is superior to a
conventional controller.

## Frozen design

- Protocol: `flydrone_integrated_v4_delta_pfl3_null_prospective_v1`.
- Dataset: FAFB materialization 783.
- Conditions: one intact circuit plus 20 newly seeded null networks.
- Paired cases: 12 per condition.
- Total flights: 252.
- Rewired projection: Delta7-to-PFL3 only.
- Projection held exactly intact: EPG-to-Delta7.
- Preregistered success criterion:
  - intact circuit at least 10/12 successful arrivals; and
  - plus-one empirical rank `p <= 0.05` against the 20 null networks.

The null networks preserved, within each presynaptic source-side block:

- binary row degree;
- binary column degree; and
- each postsynaptic row's exact multiset of nonzero raw weights.

They did not preserve exact partner identity or weighted column sums. A single global
phase alignment was computed algebraically against the intact transfer before flight;
flight outcomes were not used to choose the alignment.

## Primary result

| Quantity | Result |
|---|---:|
| Intact successes | 12/12 |
| Preregistered intact minimum | 10/12 |
| Null conditions below intact | 20/20 |
| Nulls matching or exceeding intact | 0/20 |
| Empirical plus-one rank p | 0.047619 |
| Primary gate | **PASS** |

Successes across the 20 null networks were:

`[0, 0, 3, 7, 5, 8, 2, 1, 4, 0, 0, 1, 4, 0, 0, 2, 3, 8, 0, 0]`.

Their median was 1.5/12, their mean was 2.4/12, their range was 0--8/12,
and eight null networks had zero successful arrivals.

## Secondary navigation result

The intact controller's median maximum cross-track deviation was 2.419 m. The median
of the 20 null-condition medians was 12.041 m, with a range of 3.335--22.094 m.
All 20 null conditions had a worse condition-median cross-track deviation than the
intact controller.

The mean PFL3 phase residual across null networks ranged from 46.46 to 66.36 degrees,
with a median of 53.66 degrees. This phase metric is secondary and descriptive; it was
not the preregistered primary endpoint.

## Integrity checks

- All EPG-to-Delta7 accepted-swap counts were zero.
- Every null had a positive Delta7-to-PFL3 accepted-swap count.
- The frozen-input archive contains 300 preregistered files.
- SHA-256 hashes were recorded for every preserved result file.
- The run completed without motor saturation in the reported summaries.

The generic benchmark `report.json` contains `passes_gate: false` because the generic
runner had no built-in criterion for this specialized null test. That field is not a
failed scientific result. The authoritative verdict is the preregistered specialized
analysis in `prospective_delta_pfl3_null_analysis.json`.

## What this adds to the project

The earlier joint EPG-to-Delta7 plus Delta7-to-PFL3 null gate showed that the combined
steering pathway's partner arrangement mattered. This new experiment is more specific:
it holds EPG-to-Delta7 exactly intact and changes Delta7-to-PFL3 alone. Its prospective
success therefore supports attribution to the Delta7-to-PFL3 partner arrangement in
the implemented model.

This reduces an important ambiguity in the project's connectome-attribution claim.
The evidence is now stronger than a simple neuron-class ablation, because the nulls
retain neuron count, selected degree structure, and row-weight distributions while
changing partner identity.

## Limitations

1. The result concerns a computational model and simulated drone, not a living fly.
2. The matched nulls do not preserve every possible higher-order graph property.
3. The plus-one rank test has only the minimum resolution `1/21` with 20 nulls.
4. Sensor fusion, arrival supervision, low-level stabilization, and drone dynamics are
   explicit engineering layers and remain necessary parts of the stack.
5. This experiment tests connectome dependence, not superiority to PID or direct control.
6. The biological dynamics still include parameters chosen or inferred for computation
   where experimental measurements are unavailable.

## Reproducible artifacts

- Configuration: `configs/quadrotor_integrated_v4_delta_pfl3_null_prospective.yaml`
- Preregistration: `docs/research/integrated-v4-delta-pfl3-null-preregistration.md`
- Frozen lock: `configs/quadrotor_integrated_v4_delta_pfl3_null_prospective.lock.json`
- Machine analysis: `results/simulation/quadrotor_integrated_v4_delta_pfl3_null_prospective/prospective_delta_pfl3_null_analysis.json`
- Figure: `docs/research/figures/integrated-v4-delta-pfl3-null-gate.png`
- Preservation manifest: `archive/integrated_v4_delta_pfl3_null/preservation-manifest.json`
- Frozen-input archive: `archive/integrated_v4_delta_pfl3_null/flydrone_integrated_v4_delta_pfl3_null_frozen_inputs.zip`

## Next concrete step

Run a separately preregistered EPG-to-Delta7-only prospective gate with new null seeds
and new sealed paired scenarios. If it also passes, the project will have prospective,
projection-specific attribution evidence for both stages of the steering pathway.
