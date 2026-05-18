# West Bengal 2026 Election: Statistical Analysis of SIR Voter Exclusion Impact

*Generated: 2026-05-17 | Data source: Election Commission of India (via Internet Archive)*

---

## Executive Summary

This analysis tests whether the ~27 lakh (2,700,000) voters excluded during the
Special Intensive Revision (SIR) of electoral rolls, if they had voted, could have changed
enough seats to deny BJP a majority (148/294 seats).

The analysis **varies voting probability assumptions across the full spectrum** from
BJP-biased to TMC-biased, rather than assuming a single set of probabilities.

### Key Findings

1. **Under all geographically realistic scenarios, BJP retains a comfortable majority.**
2. The **analytical upper bound** — physically impossible scenario where all 27L voters
   are placed optimally in the closest marginal BJP seats regardless of geography —
   yields 91 seat flips and BJP at 115 seats.
   Only under this physically impossible scenario does BJP lose majority..
3. Under **realistic geographic distribution** (80% turnout, full probability spectrum):
   maximum 10 seat flips, **P(BJP retains majority) = 100.0%** across
   10,000 Monte Carlo simulations.
4. The **geographic mismatch** is the binding constraint: Muslim-heavy excluded voters
   are concentrated in districts where TMC was already winning by large margins.
   Their votes pile up in safe TMC seats, not in marginal BJP seats.

---

## Election Data

| Metric | Value |
|---|---|
| Total seats (declared) | 293 of 294 |
| BJP seats | 206 |
| TMC seats | 81 |
| Others | 6 |
| Majority mark | 148 |
| SIR pending (in appeals) | **2,700,000** |
| Demographic split of pending | 65% Muslim, 35% Hindu |

---

## Margin Distribution — BJP Seats

The median BJP victory margin is **26,041 votes**.

| Margin < threshold | BJP seats below threshold |
|---|---|
| 2,000 | 6 |
| 5,000 | 12 |
| 10,000 | 30 |
| 15,000 | 53 |
| 20,000 | 74 |

---

## Sensitivity Analysis: Full Probability Grid

Turnout = 80% | Total effective voters = 2,160,000

### Uniform Distribution (equal voters per seat)

```
                          Hindu→TMC 15%  Hindu→TMC 25%  Hindu→TMC 35%  Hindu→TMC 45%  Hindu→TMC 55%
  Muslim→TMC 50%             0     0     0     0     6
  Muslim→TMC 60%             0     0     0     1     6
  Muslim→TMC 70%             0     0     0     2     6
  Muslim→TMC 80%             0     0     1     4     7
  Muslim→TMC 90%             0     0     1     6     9
```

### Non-uniform Distribution (weighted by district Muslim %)

```
                          Hindu→TMC 15%  Hindu→TMC 25%  Hindu→TMC 35%  Hindu→TMC 45%  Hindu→TMC 55%
  Muslim→TMC 50%             0     0     0     0     2
  Muslim→TMC 60%             0     0     0     1     3
  Muslim→TMC 70%             0     0     0     2     5
  Muslim→TMC 80%             0     1     2     2     8
  Muslim→TMC 90%             1     1     3     6    10
```

**Maximum flips in any grid cell: 9 (uniform) / 10 (non-uniform)**
**Flips needed to deny BJP majority: 59**

---

## Named Scenario Comparison

| Scenario | Muslim→TMC | Hindu→TMC | Turnout | Uniform flips | Non-uniform flips | BJP (uniform) | BJP majority? |
|---|---|---|---|---|---|---|---|
| BJP-biased | 50% | 15% | 80% | 0 | 0 | 206 | Yes |
| Mildly BJP-biased | 60% | 25% | 80% | 0 | 0 | 206 | Yes |
| Midpoint | 70% | 35% | 80% | 0 | 0 | 206 | Yes |
| Mildly TMC-biased | 80% | 45% | 80% | 4 | 2 | 202 | Yes |
| TMC-biased | 90% | 55% | 80% | 9 | 10 | 197 | Yes |
| Max (no discount) | 90% | 55% | 100% | 13 | 12 | 193 | Yes |

*Non-uniform = geographically realistic. Uniform = most favourable possible spread.*

---

## Analytical Upper Bound

Assumptions: 95% Muslim→TMC, 60% Hindu→TMC, 100% turnout,
**all 2,700,000 voters teleported to smallest-margin BJP seats** (physically impossible).

- **Seats flipped: 91**
- **BJP final: 115** (majority threshold = 148)
- **BJP retains majority: NO — but only under this physically impossible scenario**

For TMC to reach 148 seats would require flipping 67 seats,
needing a voter budget of 1,505,070 (best-case, geographic constraints removed).
Available (27L, no discount): 2,700,000. Gap: -1,194,930.

---

## Monte Carlo Simulation (10,000 runs)

Parameter ranges sampled uniformly:
- Muslim → TMC: 50% – 90%
- Hindu → TMC: 15% – 55%
- Turnout: 60% – 90%
- Geographic weights: district Muslim% ± 5% noise

| Metric | Value |
|---|---|
| Median seats flipped | 1 |
| 95th percentile | 5 |
| 99th percentile | 8 |
| Maximum (any simulation) | 12 |
| Flips needed to deny BJP majority | 59 |
| **P(BJP retains majority)** | **100.000%** |
| P(BJP loses majority) | 0.000% |
| P(TMC gets majority) | 0.000% |

---

## Why the Aggregate Vote-Gap Argument Fails

### 1. The Ecological Fallacy

Comparing aggregate vote gaps to the excluded-voter pool is meaningless in a FPTP system.
A party can win 100 seats by 1 vote each and lose 100 seats by 1 million votes each.
Aggregate gaps tell you nothing about seat outcomes.

### 2. Geographic Mismatch

The excluded voters are disproportionately Muslim and concentrated in Muslim-majority
districts, which returned large TMC majorities. Extra votes in these seats increase
TMC's margin in seats it already won — they do not flip BJP-held seats elsewhere.

### 3. Distributional Impossibility

Even distributing all 27L to the most marginal BJP seats (impossible —
voters are registered to specific constituencies), the per-seat allocation is only
~10,485 voters. With a realistic net
swing rate of 0.25–0.55 per voter, this produces a net swing well below the
median BJP margin of 26,041 votes.

---

## Data Sources

| Source | Reference |
|---|---|
| ECI Results | `results.eci.gov.in` (via Internet Archive) |
| SIR exclusion data | Multiple Indian news outlets |
| Muslim population % | Census of India 2011, district-level data |

---

## Limitations

- Constituency-to-district mapping uses ECI 2026 delimitation
- Muslim population percentages from Census 2011; 2026 actuals may differ
- Voting probability distributions parameterised over a grid; reality may fall outside bounds
- The excluded voter count figure comes from news/Wikipedia; ECI has not officially confirmed it

---

*All code and data are provided for research/educational purposes.*
*Analysis does not endorse any political party.*
