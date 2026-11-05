# Post-gate obstacle-navigation development

Date: 2026-11-05

## Scope and claim limit

This document records exploratory, post-hoc development performed after obstacle-navigation gate v1. The frozen gate remains failed and authoritative. None of the replays below is confirmatory, and no replay demonstrates biological vision or neural superiority. Obstacle sensing, surface inference, target abandonment, and command safety are engineering layers shared by the FlyWire-grounded and conventional controllers.

## Gate failure audit

Several fixed targets in gate v1 overlapped inflated obstacles. The behavior manager had no rule for abandoning an unreachable target, so both controllers could remain trapped while repeatedly pursuing it. This scenario flaw does not turn the failed gate into a pass, but it prevents interpreting the gate as a clean comparison of steering controllers.

## v36: observed no-progress target abandonment

The manager abandons a mission target after eight seconds of avoidance without 0.25 m of progress. An abandonment is recorded separately and never counted as a completed target. The exact four nominal exploration failures were replayed.

- FlyWire median completed targets: 11.5.
- Conventional median completed targets: 9.5.
- Stalled time fell from roughly 75–79% in gate v1 to roughly 5–7%.
- One FlyWire collision remained; clearance was below the 0.15 m development threshold.

Interpretation: unreachable-target handling causally restored progress, but exposed a separate geometric-safety bottleneck.

## v37: continuous surfaces inferred from adjacent rays

The range layer joins adjacent hit endpoints only when endpoint distance, range jump, and angular separation are all bounded. It uses no simulator obstacle centers, radii, or identities. The predictive barrier checks the swept path against these inferred segments as well as observed points.

- FlyWire: one success in two episodes, median 8 targets, one collision.
- Conventional: zero successes in two episodes, median 11.5 targets, one collision.

Interpretation: closing gaps between sparse points changed behavior but did not solve safety. Fixed repulsion could still accelerate the vehicle in an unsafe direction.

## v38: final-command chord check

The barrier was moved after command composition and evaluated the constant-acceleration chord implied by the complete navigation command. This fixed the defect where a safe current velocity could be followed immediately by acceleration toward an obstacle.

- FlyWire: one success in two episodes, median 10 targets, one collision.
- Conventional: one success in two episodes, median 12 targets, zero collisions.
- Three of the four v37 collision outcomes were removed, but the remaining FlyWire collision penetrated 0.22 m.

Trace inspection showed that the vehicle had slowed to about 0.20 m/s, then fixed-magnitude repulsion accelerated it to more than 1.1 m/s while desired speed was zero. The safety action itself was therefore part of the failure.

## v39: closing-speed acceleration projection

The final safety layer no longer applies unconditional repulsion. For each nearby observed point or inferred segment, it suppresses inward acceleration and requests bounded outward braking based on observed closing speed. It does not push when the vehicle is already moving and accelerating away. Correction remains capped at 1.2 m/s² and is not a formal control-barrier-function guarantee.

| Controller | Episodes | Development successes | Median targets | Collisions | Minimum clearance | Median stalled fraction |
|---|---:|---:|---:|---:|---:|---:|
| FlyWire v34 | 2 | 1 | 8.5 | 0 | 0.238 m | 0.107 |
| Conventional | 2 | 1 | 11.5 | 0 | 0.035 m | 0.032 |

FlyWire episode details:

- heading -37°: 4 completed, 4 abandoned, 0 collisions, 0.245 m clearance, 15.4% stalled;
- heading 137°: 13 completed, 2 abandoned, 0 collisions, 0.238 m clearance, 6.1% stalled.

Interpretation: v39 is the first post-gate candidate in this sequence with zero collisions in all four paired replays and FlyWire clearance above 0.15 m in both episodes. It is not accepted as the next gate candidate because one FlyWire route lost too much progress and exceeded the intended stall bound. Safety improved, but efficiency is not yet robust.

## Next concrete step

Do not tune the neural circuit or hDeltaB based on these failures. First isolate why the -37° FlyWire route abandons four targets under the closing-speed projection. The next development experiment should measure which surface constraints remain active, whether adjacent rays from separate obstacles are being joined, and whether target abandonment occurs while a valid collision-free route exists. Only after resolving that safety/progress tradeoff should the system be tested on new development geometries and then frozen for an obstacle gate v2 with unseen scenarios and seeds.

## v40: current-scan-only constraint — rejected

To test whether stale points caused the v39 progress loss, planning retained the 2.5-second map but the final projection used only current-scan hits and surfaces.

- FlyWire: one success in two episodes, median 9 targets, one collision, minimum clearance -0.049 m.
- Conventional: two successes in two episodes, median 11.5 targets, zero collisions, minimum clearance 0.179 m.
- The difficult FlyWire -37° route improved from 4 to 7 completed targets, but safety regressed.

Interpretation: removing remembered geometry recovers some progress but permits a collision. v40 is rejected and v39 remains the best safety candidate. The next change must preserve relevant memory selectively rather than choosing either all remembered points or only the current scan. A defensible direction is age- and visibility-aware surface tracking with explicit constraint telemetry, followed by new development geometries.

## v41: visibility-checked selective memory

Planning retains the full 2.5-second map, while the final safety projection uses current surfaces plus hits no older than 0.8 seconds that are not contradicted by the current omnidirectional scan.

- FlyWire: median 11 targets, zero collisions, median stalled fraction 0.046, minimum clearance 0.099 m.
- Conventional: median 12 targets, zero collisions, median stalled fraction 0.024, minimum clearance 0.158 m.
- The difficult FlyWire -37° case improved from 4 targets in v39 to 9, while remaining collision-free.

This is the best safety/progress balance so far, but it is not yet a gate candidate because one FlyWire episode remains below the 0.15 m clearance threshold.

## v42–v43: memory-duration interpolation

Single-case post-hoc tests varied only selective-memory duration on the FlyWire -37° case:

| Candidate | Memory | Targets | Collisions | Minimum clearance | Stalled fraction |
|---|---:|---:|---:|---:|---:|
| v41 | 0.8 s | 9 | 0 | 0.099 m | 0.041 |
| v42 | 1.2 s | 10 | 0 | 0.119 m | 0.040 |
| v43 | 1.6 s | 9 | 0 | 0.059 m | 0.063 |

The response is non-monotonic. More memory does not reliably increase clearance, so further scalar duration tuning is not justified. The next implementation must track constraint identity, age, visibility, and contribution so unsafe or trapping surfaces can be diagnosed individually. v42 is only a single-case lead, not an accepted candidate.
