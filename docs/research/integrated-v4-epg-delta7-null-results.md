# Prospective EPG-to-Delta7 connectome-null gate

## Outcome

**The prospectively frozen gate passed.** Across 252 paired simulated flights,
the intact FlyWire-grounded controller reached the goal in 12/12 cases. None of
20 matched EPG-to-Delta7 null networks equalled that result. The plus-one
empirical rank value was `1/21 = 0.047619`, meeting the preregistered threshold.

This supports the limited claim that, in this implemented model and these sealed
scenarios, exact FlyWire-grounded EPG-to-Delta7 partner identity contributes to
successful simulated navigation beyond the block-wise degree and row-weight
statistics retained by the null generator.

## Frozen design

- Protocol: `flydrone_integrated_v4_epg_delta7_null_prospective_v1`.
- Dataset: FAFB materialization 783.
- One intact circuit and 20 newly seeded null networks.
- Twelve paired cases per condition; 252 flights total.
- EPG-to-Delta7 rewired; Delta7-to-PFL3 held exactly intact.
- Intact circuit required at least 10/12 arrivals.
- Corrected empirical rank required `p <= 0.05`.

Within each EPG source-side block, rewiring preserved binary row degree,
binary column degree and each Delta7 row's exact multiset of nonzero raw
weights. It did not preserve exact partner identity or weighted column sums.
The global phase alignment was computed algebraically before flight and did
not use navigation outcomes.

## Primary result

| Quantity | Result |
|---|---:|
| Intact successes | 12/12 |
| Nulls below intact | 20/20 |
| Nulls matching or exceeding intact | 0/20 |
| Null median | 1/12 |
| Null mean | 1.45/12 |
| Null range | 0--6/12 |
| Zero-success nulls | 8/20 |
| Empirical plus-one rank p | 0.047619 |
| Gate | **PASS** |

Null successes were:

`[1, 0, 3, 1, 0, 6, 0, 1, 2, 1, 0, 0, 2, 5, 0, 0, 1, 0, 5, 1]`.

## Secondary results

The intact median maximum cross-track deviation was 2.475 m. The median of
the null-condition medians was 10.948 m, with a range of 3.723--19.262 m.
All 20 null conditions were worse than the intact condition on this secondary
measure.

Mean PFL3 phase residuals ranged from 50.87 to 80.25 degrees, with a median of
69.34 degrees. This was descriptive and was not the primary endpoint.

## Integrity checks

- Every null had positive EPG-to-Delta7 accepted swaps.
- Every Delta7-to-PFL3 accepted-swap count was zero.
- The frozen archive contains 301 preregistered input files.
- SHA-256 hashes were recorded for 228 original result files before analysis.
- The specialized result is authoritative; the generic benchmark's empty
  `gate` field is not a failed scientific gate.

## Interpretation and limits

This result is stronger than simply removing EPG or Delta7 neurons: the nulls
retain the population sizes, selected degree structure and row-weight
distributions while changing partner identity. It therefore tests whether
specific connectome organization matters in the computational controller.

It does not demonstrate biological causality in a living fly, does not test
every higher-order graph property, and does not establish superiority over
PID or direct control. Sensor fusion, arrival supervision, low-level flight
stabilization and simulated vehicle dynamics remain engineering components.

## Artifacts

- Configuration: `configs/quadrotor_integrated_v4_epg_delta7_null_prospective.yaml`
- Preregistration: `docs/research/integrated-v4-epg-delta7-null-preregistration.md`
- Lock: `configs/quadrotor_integrated_v4_epg_delta7_null_prospective.lock.json`
- Analysis: `results/simulation/quadrotor_integrated_v4_epg_delta7_null_prospective/prospective_epg_delta7_null_analysis.json`
- Figure: `docs/research/figures/integrated-v4-epg-delta7-null-gate.png`
- Preservation manifest: `archive/integrated_v4_epg_delta7_null/preservation-manifest.json`

