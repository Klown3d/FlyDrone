# EPG→Delta7→PFL3 steering-null development results

## Result

The intact steering projection completed 12/12 simulated flights. The five
side-block degree- and row-weight-preserving null networks completed 2, 0, 3,
4 and 1 of 12 flights. Every null performed worse than intact; their median was
2/12.

| Condition | Successes | Median maximum cross-track |
|---|---:|---:|
| Intact FlyWire-grounded steering | 12/12 | 2.242 m |
| Null seed 52011 | 2/12 | 8.483 m |
| Null seed 52021 | 0/12 | 8.263 m |
| Null seed 52027 | 3/12 | 8.418 m |
| Null seed 52051 | 4/12 | 7.799 m |
| Null seed 52057 | 1/12 | 10.374 m |

All nulls accepted 9,280 EPG→Delta7 swaps and 2,380 Delta7→PFL3 swaps. The
controlled rewiring preserved binary row and column degrees and each
postsynaptic row's weight multiset within presynaptic source-side blocks.

## Phase-control interpretation

Every null received a single global phase alignment calculated from its
composite transfer relative to intact, without using flight outcomes. After
that correction, mean nonuniform PFL3 phase residuals remained between 72.95°
and 82.57°, with maximum residuals between 153.04° and 177.62°. Thus the poor
navigation cannot be explained only by an arbitrary constant rotation; the
rewiring disrupted the across-PFL3 phase structure.

This does not yet prove that FlyWire steering connectivity is uniquely
required. The diagnostic used only five nulls and deliberately reused 12
development cases. The descriptive corrected rank value would be 1/6 = 0.167,
which is not a confirmatory test and cannot reach 0.05 with only five nulls.

## Decision

The separation is strong enough to justify a prospective steering-attribution
gate with at least 20 new null seeds and new paired scenarios. Its design must
be frozen before execution, use arrival success as the primary metric, retain
the algebraic global-phase allowance, and report trajectory cost and phase
residuals as secondary outcomes.

Machine-readable analysis is stored at
`results/simulation/quadrotor_integrated_v4_steering_null_development/steering_null_development_analysis.json`.
