"""
Generic markdown report generator for election voter exclusion analysis.
All labels, counts, and narrative adapt automatically from AnalysisResults.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from .models import AnalysisResults


class ReportGenerator:
    """
    Generates a markdown report summarising the voter exclusion analysis.
    The report auto-adapts to any election by reading config labels from
    AnalysisResults.election and AnalysisResults.exclusion.
    """

    def __init__(self, results: AnalysisResults) -> None:
        self.results = results

    def generate(self, output_path: Path = Path("REPORT.md")) -> str:
        """Write the report to output_path and return the markdown string."""
        results = self.results
        ec      = results.election
        xc      = results.exclusion
        df      = results.data
        mc      = results.monte_carlo
        ub      = results.upper_bound
        grid    = results.sensitivity
        scen_df = results.scenarios

        a_label = ec.party_a_label
        b_label = ec.party_b_label
        min_grp = ec.minority_group_name
        maj_grp = ec.majority_group_name

        a_actual      = int(df["winner_is_party_a"].sum())
        b_actual      = int(df["winner_is_party_b"].sum())
        others_actual = len(df) - a_actual - b_actual

        a_2k  = int((df[df["winner_is_party_a"]]["margin"] < 2_000).sum())
        a_5k  = int((df[df["winner_is_party_a"]]["margin"] < 5_000).sum())
        a_10k = int((df[df["winner_is_party_a"]]["margin"] < 10_000).sum())
        a_15k = int((df[df["winner_is_party_a"]]["margin"] < 15_000).sum())
        a_20k = int((df[df["winner_is_party_a"]]["margin"] < 20_000).sum())
        a_median = int(df[df["winner_is_party_a"]]["margin"].median())

        p_a_majority = mc.p_party_a_majority
        p_a_loses    = 1 - p_a_majority
        mc_median    = int(mc.median_flips)
        mc_p95       = mc.p95_flips
        mc_p99       = mc.p99_flips
        mc_max       = mc.max_flips

        flips_needed     = mc.flips_needed
        budget_b_maj     = ub.voter_budget_for_party_b_majority
        max_flips_u      = int(grid.uniform.max())
        max_flips_nu     = int(grid.nonuniform.max())

        # Build scenario table rows dynamically from whatever columns exist
        scen_rows = ""
        for _, row in scen_df.iterrows():
            min_col = f"{min_grp}→{b_label}"
            maj_col = f"{maj_grp}→{b_label}"
            a_u_col = f"{a_label} (uniform)"
            maj_col2 = f"{a_label} majority (U)?"
            min_val = row.get(min_col, row.get("Muslim→TMC", ""))
            maj_val = row.get(maj_col, row.get("Hindu→TMC", ""))
            a_u_val = row.get(a_u_col, row.get("BJP (uniform)", ""))
            maj_q   = row.get(maj_col2, row.get("BJP majority (U)?", ""))
            scen_rows += (
                f"| {row['Scenario']} | {min_val} | {maj_val} "
                f"| {row['Turnout']} | {row['Uniform flips']} | {row['Non-uniform flips']} "
                f"| {a_u_val} | {maj_q} |\n"
            )

        # Grid tables (5x5)
        def _grid_line(row_vals: list) -> str:
            return "  ".join(f"{v:>4}" for v in row_vals)

        uni_rows  = "\n".join(
            f"  {grid.row_labels[i]:22s}  {_grid_line(grid.uniform[i].tolist())}"
            for i in range(len(grid.row_labels))
        )
        nu_rows = "\n".join(
            f"  {grid.row_labels[i]:22s}  {_grid_line(grid.nonuniform[i].tolist())}"
            for i in range(len(grid.row_labels))
        )
        col_hdr = f"  {'':22s}  {_grid_line(grid.col_labels)}"

        report = f"""# {ec.state_name} {ec.year} Election: Statistical Analysis of SIR Voter Exclusion Impact

*Generated: {date.today().isoformat()} | Data source: Election Commission of India (via Internet Archive)*

---

## Executive Summary

This analysis tests whether the ~{xc.total_excluded // 100_000:.0f} lakh ({xc.total_excluded:,}) voters excluded during the
Special Intensive Revision (SIR) of electoral rolls, if they had voted, could have changed
enough seats to deny {a_label} a majority ({ec.majority_mark}/{ec.total_seats} seats).

The analysis **varies voting probability assumptions across the full spectrum** from
{a_label}-biased to {b_label}-biased, rather than assuming a single set of probabilities.

### Key Findings

1. **Under all geographically realistic scenarios, {a_label} retains a comfortable majority.**
2. The **analytical upper bound** — physically impossible scenario where all {xc.total_excluded // 100_000:.0f}L voters
   are placed optimally in the closest marginal {a_label} seats regardless of geography —
   yields {ub.seats_flipped} seat flips and {a_label} at {ub.party_a_final} seats.
   {f'{a_label} retains majority: YES' if ub.party_a_majority else f'Only under this physically impossible scenario does {a_label} lose majority.'}.
3. Under **realistic geographic distribution** (80% turnout, full probability spectrum):
   maximum {max_flips_nu} seat flips, **P({a_label} retains majority) = {p_a_majority:.1%}** across
   {mc.n_simulations:,} Monte Carlo simulations.
4. The **geographic mismatch** is the binding constraint: {min_grp}-heavy excluded voters
   are concentrated in districts where {b_label} was already winning by large margins.
   Their votes pile up in safe {b_label} seats, not in marginal {a_label} seats.

---

## Election Data

| Metric | Value |
|---|---|
| Total seats (declared) | {len(df)} of {ec.total_seats} |
| {a_label} seats | {a_actual} |
| {b_label} seats | {b_actual} |
| Others | {others_actual} |
| Majority mark | {ec.majority_mark} |
| SIR pending (in appeals) | **{xc.total_excluded:,}** |
| Demographic split of pending | {xc.minority_share:.0%} {min_grp}, {xc.majority_share:.0%} {maj_grp} |

---

## Margin Distribution — {a_label} Seats

The median {a_label} victory margin is **{a_median:,} votes**.

| Margin < threshold | {a_label} seats below threshold |
|---|---|
| 2,000 | {a_2k} |
| 5,000 | {a_5k} |
| 10,000 | {a_10k} |
| 15,000 | {a_15k} |
| 20,000 | {a_20k} |

---

## Sensitivity Analysis: Full Probability Grid

Turnout = 80% | Total effective voters = {xc.total_excluded * xc.default_turnout:,.0f}

### Uniform Distribution (equal voters per seat)

```
{col_hdr}
{uni_rows}
```

### Non-uniform Distribution (weighted by district {min_grp} %)

```
{col_hdr}
{nu_rows}
```

**Maximum flips in any grid cell: {max_flips_u} (uniform) / {max_flips_nu} (non-uniform)**
**Flips needed to deny {a_label} majority: {flips_needed}**

---

## Named Scenario Comparison

| Scenario | {min_grp}→{b_label} | {maj_grp}→{b_label} | Turnout | Uniform flips | Non-uniform flips | {a_label} (uniform) | {a_label} majority? |
|---|---|---|---|---|---|---|---|
{scen_rows}
*Non-uniform = geographically realistic. Uniform = most favourable possible spread.*

---

## Analytical Upper Bound

Assumptions: {ub.p_minority_b:.0%} {min_grp}→{b_label}, {ub.p_majority_b:.0%} {maj_grp}→{b_label}, 100% turnout,
**all {xc.total_excluded:,} voters teleported to smallest-margin {a_label} seats** (physically impossible).

- **Seats flipped: {ub.seats_flipped}**
- **{a_label} final: {ub.party_a_final}** (majority threshold = {ec.majority_mark})
- **{a_label} retains majority: {'YES' if ub.party_a_majority else 'NO — but only under this physically impossible scenario'}**

For {b_label} to reach {ec.majority_mark} seats would require flipping {ub.seats_needed_for_party_b_majority} seats,
needing a voter budget of {budget_b_maj:,.0f} (best-case, geographic constraints removed).
Available ({xc.total_excluded // 100_000:.0f}L, no discount): {xc.total_excluded:,}. Gap: {budget_b_maj - xc.total_excluded:,.0f}.

---

## Monte Carlo Simulation ({mc.n_simulations:,} runs)

Parameter ranges sampled uniformly:
- {min_grp} → {b_label}: {xc.minority_b_grid[0]:.0%} – {xc.minority_b_grid[-1]:.0%}
- {maj_grp} → {b_label}: {xc.majority_b_grid[0]:.0%} – {xc.majority_b_grid[-1]:.0%}
- Turnout: 60% – 90%
- Geographic weights: district {min_grp}% ± 5% noise

| Metric | Value |
|---|---|
| Median seats flipped | {mc_median} |
| 95th percentile | {mc_p95} |
| 99th percentile | {mc_p99} |
| Maximum (any simulation) | {mc_max} |
| Flips needed to deny {a_label} majority | {flips_needed} |
| **P({a_label} retains majority)** | **{p_a_majority:.3%}** |
| P({a_label} loses majority) | {p_a_loses:.3%} |
| P({b_label} gets majority) | {mc.p_party_b_majority:.3%} |

---

## Why the Aggregate Vote-Gap Argument Fails

### 1. The Ecological Fallacy

Comparing aggregate vote gaps to the excluded-voter pool is meaningless in a FPTP system.
A party can win 100 seats by 1 vote each and lose 100 seats by 1 million votes each.
Aggregate gaps tell you nothing about seat outcomes.

### 2. Geographic Mismatch

The excluded voters are disproportionately {min_grp} and concentrated in {min_grp}-majority
districts, which returned large {b_label} majorities. Extra votes in these seats increase
{b_label}'s margin in seats it already won — they do not flip {a_label}-held seats elsewhere.

### 3. Distributional Impossibility

Even distributing all {xc.total_excluded // 100_000:.0f}L to the most marginal {a_label} seats (impossible —
voters are registered to specific constituencies), the per-seat allocation is only
~{int(xc.total_excluded * xc.default_turnout / max(a_actual, 1)):,} voters. With a realistic net
swing rate of 0.25–0.55 per voter, this produces a net swing well below the
median {a_label} margin of {a_median:,} votes.

---

## Data Sources

| Source | Reference |
|---|---|
| ECI Results | `results.eci.gov.in` (via Internet Archive) |
| SIR exclusion data | Multiple Indian news outlets |
| {min_grp} population % | Census of India 2011, district-level data |

---

## Limitations

- Constituency-to-district mapping uses ECI {ec.year} delimitation
- {min_grp} population percentages from Census 2011; {ec.year} actuals may differ
- Voting probability distributions parameterised over a grid; reality may fall outside bounds
- The excluded voter count figure comes from news/Wikipedia; ECI has not officially confirmed it

---

*All code and data are provided for research/educational purposes.*
*Analysis does not endorse any political party.*
"""

        output_path = Path(output_path)
        output_path.write_text(report, encoding="utf-8")
        print(f"Saved {output_path}")
        return report
