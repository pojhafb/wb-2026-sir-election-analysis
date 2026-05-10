"""
Generic voter exclusion impact analyzer for Indian elections.

Methodology:
    Given a pool of excluded voters and assumptions about how they would have
    voted, estimate how many seats could have flipped under various scenarios.
    The analysis uses constituency-level margin data and a geographic voter
    allocation model.
"""
from __future__ import annotations

import itertools
from typing import Optional

import numpy as np
import pandas as pd

from .models import (
    AnalysisResults,
    ElectionConfig,
    MonteCarloSummary,
    SensitivityGrid,
    UpperBoundResult,
    VoterExclusionConfig,
)


class VoterExclusionAnalyzer:
    """
    Analyzes the potential impact of excluded voters on election outcomes.

    The analysis runs five methods:
      1. Margin distribution summary
      2. Sensitivity grid across the full probability space
      3. Turnout sensitivity
      4. Analytical upper bound (geographic constraints removed)
      5. Monte Carlo simulation
    """

    def __init__(
        self,
        df: pd.DataFrame,
        election: ElectionConfig,
        exclusion: VoterExclusionConfig,
    ) -> None:
        self.ec = election
        self.xc = exclusion

        # Work on a copy so we don't mutate the caller's DataFrame
        self.df = df.copy()

        # Handle legacy CSV column names (bjp_votes / tmc_votes → party_a/b_votes)
        if "bjp_votes" in self.df.columns and "party_a_votes" not in self.df.columns:
            self.df.rename(columns={"bjp_votes": "party_a_votes"}, inplace=True)
        if "tmc_votes" in self.df.columns and "party_b_votes" not in self.df.columns:
            self.df.rename(columns={"tmc_votes": "party_b_votes"}, inplace=True)

        # Add derived columns
        self.df["winner_is_party_a"] = self.df["winner_party"].str.contains(
            election.party_a_name, na=False
        )
        self.df["winner_is_party_b"] = self.df["winner_party"].str.contains(
            election.party_b_name, na=False
        )
        self.df["district"] = self.df["const_no"].map(election.constituency_district)
        self.df["minority_pct"] = (
            self.df["district"]
            .map(election.district_minority_pct)
            .fillna(election.default_minority_pct)
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_all(self) -> AnalysisResults:
        """Run all five analyses and return a consolidated AnalysisResults."""
        ec = self.ec
        df = self.df

        print(f"Loaded {len(df)} constituencies")
        print(
            f"{ec.party_a_label} seats: {df['winner_is_party_a'].sum()} | "
            f"{ec.party_b_label}: {df['winner_is_party_b'].sum()} | "
            f"Others: {(~df['winner_is_party_a'] & ~df['winner_is_party_b']).sum()}"
        )
        pa_col = "party_a_votes"
        if pa_col in df.columns:
            print(f"Missing vote data: {df[pa_col].isna().sum()}")
        else:
            print("Missing vote data: N/A (margin-only mode)")

        self.margin_distribution()
        grid    = self.sensitivity_grid()
        self.turnout_sensitivity()
        ub      = self.upper_bound()
        mc      = self.monte_carlo()
        scen_df = self.named_scenarios()

        return AnalysisResults(
            election=ec,
            exclusion=self.xc,
            data=self.df,
            sensitivity=grid,
            scenarios=scen_df,
            upper_bound=ub,
            monte_carlo=mc,
        )

    def margin_distribution(self) -> dict:
        """Print and return margin distribution statistics."""
        ec = self.ec
        df = self.df

        print("\n" + "=" * 60)
        print("ANALYSIS 1: Victory Margin Distribution")
        print("=" * 60)

        a_seats = df[df["winner_is_party_a"]].copy()
        b_seats = df[df["winner_is_party_b"]].copy()

        print(f"\n{ec.party_a_label} won {len(a_seats)} seats  |  {ec.party_b_label} won {len(b_seats)} seats")
        thresholds = [2_000, 5_000, 10_000, 15_000, 20_000, 30_000, 50_000]
        print(f"\n{'Margin <':>15}  {ec.party_a_label+' seats':>10}  {ec.party_b_label+' seats':>10}")
        print("-" * 42)
        for t in thresholds:
            a = int((a_seats["margin"] < t).sum())
            b = int((b_seats["margin"] < t).sum())
            print(f"{t:>15,}  {a:>10}  {b:>10}")

        print(f"\n{ec.party_a_label} margin stats (votes):")
        print(a_seats["margin"].describe().apply(lambda x: f"{x:,.0f}").to_string())
        print(f"\n{ec.party_b_label} margin stats (votes):")
        print(b_seats["margin"].describe().apply(lambda x: f"{x:,.0f}").to_string())

        return {
            f"{ec.party_a_label}_seats": a_seats,
            f"{ec.party_b_label}_seats": b_seats,
        }

    def sensitivity_grid(self, turnout: Optional[float] = None) -> SensitivityGrid:
        """
        Compute seats flipped across the full probability grid.
        Two sub-grids: uniform distribution and non-uniform (minority-district-weighted).
        """
        if turnout is None:
            turnout = self.xc.default_turnout

        ec = self.ec
        xc = self.xc
        df = self.df

        print("\n" + "=" * 60)
        print("ANALYSIS 2: Sensitivity Grid — Seats Flipped Across Probability Assumptions")
        print(f"(Turnout = {turnout:.0%}  |  Total effective voters = {xc.total_excluded * turnout:,.0f})")
        print("=" * 60)

        a_df = df[df["winner_is_party_a"]].copy()
        effective = xc.total_excluded * turnout

        n_rows = len(xc.minority_b_grid)
        n_cols = len(xc.majority_b_grid)
        results_uniform    = np.zeros((n_rows, n_cols), dtype=int)
        results_nonuniform = np.zeros((n_rows, n_cols), dtype=int)

        for i, p_min in enumerate(xc.minority_b_grid):
            for j, p_maj in enumerate(xc.majority_b_grid):
                if (p_min + xc.minority_others > 1.0) or (p_maj + xc.majority_others > 1.0):
                    results_uniform[i, j]    = -1
                    results_nonuniform[i, j] = -1
                    continue
                results_uniform[i, j]    = self._count_flips_uniform(a_df, effective, p_min, p_maj)
                results_nonuniform[i, j] = self._count_flips_nonuniform(a_df, df, effective, p_min, p_maj)

        min_grp = ec.minority_group_name
        maj_grp = ec.majority_group_name
        b_label = ec.party_b_label
        col_labels = [f"{maj_grp}→{b_label} {p:.0%}" for p in xc.majority_b_grid]
        row_labels  = [f"{min_grp}→{b_label} {p:.0%}" for p in xc.minority_b_grid]

        print(f"\n-- Uniform Distribution --")
        print(f"Rows = {min_grp} {b_label} vote share | Cols = {maj_grp} {b_label} vote share")
        self._print_grid(results_uniform, row_labels, col_labels)

        print(f"\n-- Non-Uniform Distribution (weighted by district {min_grp} %) --")
        self._print_grid(results_nonuniform, row_labels, col_labels)

        a_declared = int(df["winner_is_party_a"].sum())
        flips_needed = a_declared - ec.majority_mark + 1
        print(f"\nFlips needed to deny {ec.party_a_label} majority: {flips_needed}")
        print(f"Max flips in uniform grid:         {results_uniform.max()}")
        print(f"Max flips in non-uniform grid:     {results_nonuniform.max()}")

        return SensitivityGrid(
            uniform=results_uniform,
            nonuniform=results_nonuniform,
            row_labels=row_labels,
            col_labels=col_labels,
            flips_needed=flips_needed,
        )

    def turnout_sensitivity(self) -> pd.DataFrame:
        """Show how seats flipped change as turnout varies across named scenarios."""
        ec = self.ec
        xc = self.xc
        df = self.df

        print("\n" + "=" * 60)
        print("ANALYSIS 3: Turnout Sensitivity")
        print("=" * 60)

        a_df = df[df["winner_is_party_a"]].copy()

        # Use first, middle, last of named_scenarios as reference points
        named = xc.named_scenarios
        mid_idx = len(named) // 2
        scenarios = [named[0], named[mid_idx], named[-1]]

        b = ec.party_b_label
        min_grp = ec.minority_group_name
        maj_grp = ec.majority_group_name

        print(f"\n{'Scenario':>20}  {min_grp+'→'+b:>12}  {maj_grp+'→'+b:>12}", end="")
        for t in xc.turnout_grid:
            print(f"  {'Turnout '+f'{t:.0%}':>12}", end="")
        print()
        print("-" * (46 + 14 * len(xc.turnout_grid)))

        records = []
        for label, p_min, p_maj, _default_t in scenarios:
            print(f"{label:>20}  {p_min:>12.0%}  {p_maj:>12.0%}", end="")
            row = {"Scenario": label, f"{min_grp}→{b}": f"{p_min:.0%}", f"{maj_grp}→{b}": f"{p_maj:.0%}"}
            for turnout in xc.turnout_grid:
                effective = xc.total_excluded * turnout
                flips = self._count_flips_uniform(a_df, effective, p_min, p_maj)
                print(f"  {flips:>12}", end="")
                row[f"Turnout {turnout:.0%}"] = flips
            print()
            records.append(row)

        return pd.DataFrame(records)

    def upper_bound(self) -> UpperBoundResult:
        """
        Compute the analytical upper bound: maximum possible seats that could flip
        if all geographic constraints are removed (voters placed optimally).
        """
        ec = self.ec
        xc = self.xc
        df = self.df

        p_min_b = 0.95
        p_maj_b = 0.60

        print("\n" + "=" * 60)
        print(f"ANALYSIS 4: Analytical Upper Bound (Max {ec.party_b_label} Benefit)")
        print("=" * 60)
        print(f"\nAssumptions: 100% turnout, {p_min_b:.0%} {ec.minority_group_name}→{ec.party_b_label}, {p_maj_b:.0%} {ec.majority_group_name}→{ec.party_b_label}")
        print(f"Geographic: all {xc.total_excluded:,} concentrated in smallest-margin {ec.party_a_label} seats")
        print("(This is physically impossible — just tests the ceiling)")

        a_df = df[df["winner_is_party_a"]].copy().sort_values("margin")
        budget = float(xc.total_excluded)

        flipped_seats = []
        remaining = budget
        for _, row in a_df.iterrows():
            m = row["minority_pct"]
            p_min_a = max(0.0, 1.0 - p_min_b - xc.minority_others)
            p_maj_a = max(0.0, 1.0 - p_maj_b - xc.majority_others)
            net_rate = (p_min_b - p_min_a) * m + (p_maj_b - p_maj_a) * (1 - m)
            if net_rate <= 0:
                continue
            needed = row["margin"] / net_rate
            if remaining >= needed:
                remaining -= needed
                flipped_seats.append({
                    "const_name":     row["const_name"],
                    "district":       row.get("district", "?"),
                    "margin":         row["margin"],
                    "voters_needed":  int(needed),
                })
            else:
                break

        a_declared = int(df["winner_is_party_a"].sum())
        b_declared = int(df["winner_is_party_b"].sum())
        a_final = a_declared - len(flipped_seats)
        b_final = b_declared + len(flipped_seats)

        print(f"\nSeats that flip under absolute upper bound: {len(flipped_seats)}")
        print(f"{ec.party_a_label} final: {a_final}  |  {ec.party_b_label} final: {b_final}")
        print(f"{ec.party_a_label} retains majority? {'YES' if a_final >= ec.majority_mark else 'NO'}")

        if flipped_seats:
            print(f"\nFlipped seats:")
            for s in flipped_seats:
                dist = str(s.get("district") or "Unknown")
                print(
                    f"  {s['const_name']:30s} ({dist:20s}) "
                    f"margin={s['margin']:>7,}  voters needed={s['voters_needed']:>7,}"
                )

        seats_needed = ec.majority_mark - b_declared
        cost = 0.0
        for i, (_, row) in enumerate(a_df.iterrows()):
            if i >= seats_needed:
                break
            m = row["minority_pct"]
            p_min_a = max(0.0, 1.0 - p_min_b - xc.minority_others)
            p_maj_a = max(0.0, 1.0 - p_maj_b - xc.majority_others)
            net_rate = (p_min_b - p_min_a) * m + (p_maj_b - p_maj_a) * (1 - m)
            cost += row["margin"] / max(net_rate, 1e-9)

        print(f"\nFor {ec.party_b_label} to reach {ec.majority_mark} seats would need {seats_needed} flips")
        print(f"Voter budget needed (best-case): {cost:>12,.0f}")
        print(f"Available ({xc.total_excluded // 100_000:.0f}L, no discount):   {xc.total_excluded:>12,}")
        print(f"Gap (shortfall):                {cost - xc.total_excluded:>12,.0f}")

        return UpperBoundResult(
            p_minority_b=p_min_b,
            p_majority_b=p_maj_b,
            seats_flipped=len(flipped_seats),
            party_a_final=a_final,
            party_b_final=b_final,
            party_a_majority=(a_final >= ec.majority_mark),
            voter_budget_for_party_b_majority=cost,
            seats_needed_for_party_b_majority=seats_needed,
            flipped_seats=flipped_seats,
        )

    def monte_carlo(self) -> MonteCarloSummary:
        """
        Monte Carlo simulation sampling the full parameter space:
        - Minority b-party vote share: U[minority_b_grid[0], minority_b_grid[-1]]
        - Majority b-party vote share: U[majority_b_grid[0], majority_b_grid[-1]]
        - Turnout: U[0.60, 0.90]
        - Geographic weights: minority_pct + N(0, 0.05) noise (clipped)
        """
        ec = self.ec
        xc = self.xc
        df = self.df

        n_sim = xc.mc_simulations
        print("\n" + "=" * 60)
        print(f"ANALYSIS 5: Monte Carlo Simulation ({n_sim:,} runs)")
        print("=" * 60)
        print("Parameter ranges:")
        print(f"  {ec.minority_group_name}→{ec.party_b_label} vote share: U[{xc.minority_b_grid[0]:.0%}, {xc.minority_b_grid[-1]:.0%}]")
        print(f"  {ec.majority_group_name}→{ec.party_b_label} vote share:  U[{xc.majority_b_grid[0]:.0%},  {xc.majority_b_grid[-1]:.0%}]")
        print(f"  Turnout:               U[60%, 90%]")
        print(f"  Geography:             minority% ± 5% noise")

        rng = np.random.default_rng(xc.mc_seed)

        a_df = df[df["winner_is_party_a"]].copy()
        margins    = a_df["margin"].values
        min_pcts   = a_df["minority_pct"].values

        a_declared = int(df["winner_is_party_a"].sum())
        b_declared = int(df["winner_is_party_b"].sum())

        sim_results = []
        for _ in range(n_sim):
            p_min_b = rng.uniform(xc.minority_b_grid[0], xc.minority_b_grid[-1])
            p_maj_b = rng.uniform(xc.majority_b_grid[0], xc.majority_b_grid[-1])
            turnout  = rng.uniform(0.60, 0.90)
            effective = xc.total_excluded * turnout

            p_min_a = max(0.0, 1.0 - p_min_b - xc.minority_others)
            p_maj_a = max(0.0, 1.0 - p_maj_b - xc.majority_others)

            # Non-uniform distribution with geographic noise on all seats
            all_weights = np.clip(
                df["minority_pct"].values + rng.normal(0, 0.05, len(df)), 0.01, 0.99
            )
            all_weights = all_weights / all_weights.sum()
            bjp_alloc = all_weights[df["winner_is_party_a"].values] * effective

            n_min = bjp_alloc * min_pcts
            n_maj = bjp_alloc * (1 - min_pcts)
            b_extra = n_min * p_min_b + n_maj * p_maj_b
            a_extra = n_min * p_min_a + n_maj * p_maj_a
            net_gains = b_extra - a_extra

            flipped = int((net_gains > margins).sum())
            sim_results.append({
                "seats_flipped": flipped,
                "party_a_final": a_declared - flipped,
                "party_b_final": b_declared + flipped,
                "party_a_majority": (a_declared - flipped) >= ec.majority_mark,
                "party_b_majority": (b_declared + flipped) >= ec.majority_mark,
                "p_min_b": p_min_b,
                "p_maj_b": p_maj_b,
                "turnout": turnout,
            })

        mc_df = pd.DataFrame(sim_results)
        flips_needed = a_declared - ec.majority_mark + 1

        med  = mc_df["seats_flipped"].median()
        mean = mc_df["seats_flipped"].mean()
        p95  = int(mc_df["seats_flipped"].quantile(0.95))
        p99  = int(mc_df["seats_flipped"].quantile(0.99))
        mx   = int(mc_df["seats_flipped"].max())
        p_a  = mc_df["party_a_majority"].mean()
        p_b  = mc_df["party_b_majority"].mean()

        print(f"\nMonte Carlo results:")
        print(f"  Median seats flipped:         {med:.0f}")
        print(f"  Mean seats flipped:           {mean:.1f}")
        print(f"  95th percentile flips:        {p95}")
        print(f"  99th percentile flips:        {p99}")
        print(f"  Max seats flipped (any sim):  {mx}")
        print(f"")
        print(f"  Flips needed to deny {ec.party_a_label} majority: {flips_needed}")
        print(f"  P({ec.party_a_label} retains majority):  {p_a:.3%}")
        print(f"  P({ec.party_a_label} loses majority):    {1-p_a:.3%}")
        print(f"  P({ec.party_b_label} gets majority):     {p_b:.3%}")

        return MonteCarloSummary(
            n_simulations=n_sim,
            median_flips=med,
            mean_flips=mean,
            p95_flips=p95,
            p99_flips=p99,
            max_flips=mx,
            flips_needed=flips_needed,
            p_party_a_majority=p_a,
            p_party_b_majority=p_b,
            raw=mc_df,
        )

    def named_scenarios(self) -> pd.DataFrame:
        """Compute a concise table of results for named scenarios."""
        ec = self.ec
        xc = self.xc
        df = self.df
        a_df = df[df["winner_is_party_a"]].copy()
        a_declared = int(df["winner_is_party_a"].sum())
        b_label = ec.party_b_label
        min_grp = ec.minority_group_name
        maj_grp = ec.majority_group_name

        scenarios = []
        for label, p_min, p_maj, turnout in xc.named_scenarios:
            effective = xc.total_excluded * turnout
            flips_u  = self._count_flips_uniform(a_df, effective, p_min, p_maj)
            flips_nu = self._count_flips_nonuniform(a_df, df, effective, p_min, p_maj)
            scenarios.append({
                "Scenario":            label,
                f"{min_grp}→{b_label}": f"{p_min:.0%}",
                f"{maj_grp}→{b_label}": f"{p_maj:.0%}",
                "Turnout":             f"{turnout:.0%}",
                "Uniform flips":       flips_u,
                "Non-uniform flips":   flips_nu,
                f"{ec.party_a_label} (uniform)":   a_declared - flips_u,
                f"{ec.party_a_label} (non-unif.)": a_declared - flips_nu,
                f"{ec.party_a_label} majority (U)?": "Yes" if a_declared - flips_u >= ec.majority_mark else "NO",
            })

        sdf = pd.DataFrame(scenarios)
        print("\n" + "=" * 60)
        print("SCENARIO SUMMARY TABLE")
        print("=" * 60)
        print(sdf.to_string(index=False))
        sdf.to_csv("scenario_summary.csv", index=False)
        print("\nSaved scenario_summary.csv")
        return sdf

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _net_party_b_gain(
        self,
        n_voters: float,
        minority_pct: float,
        p_min_b: float,
        p_maj_b: float,
    ) -> float:
        """
        Expected net party-B advantage from n_voters additional voters
        in a constituency with given minority_pct.
        """
        p_min_a = max(0.0, 1.0 - p_min_b - self.xc.minority_others)
        p_maj_a = max(0.0, 1.0 - p_maj_b - self.xc.majority_others)
        n_min = n_voters * minority_pct
        n_maj = n_voters * (1 - minority_pct)
        b_gain = n_min * p_min_b + n_maj * p_maj_b
        a_gain = n_min * p_min_a + n_maj * p_maj_a
        return b_gain - a_gain

    def _count_flips_uniform(
        self,
        party_a_df: pd.DataFrame,
        effective_voters: float,
        p_min_b: float,
        p_maj_b: float,
    ) -> int:
        """Count party-A seats that flip under uniform voter distribution."""
        n = effective_voters / len(party_a_df) if len(party_a_df) else 0
        flips = 0
        for _, row in party_a_df.iterrows():
            gain = self._net_party_b_gain(n, row["minority_pct"], p_min_b, p_maj_b)
            if gain > row["margin"]:
                flips += 1
        return flips

    def _count_flips_nonuniform(
        self,
        party_a_df: pd.DataFrame,
        df_all: pd.DataFrame,
        effective_voters: float,
        p_min_b: float,
        p_maj_b: float,
    ) -> int:
        """
        Count party-A seats that flip under non-uniform distribution:
        voters allocated proportional to district minority %.
        """
        weights = df_all["minority_pct"].values
        total_w = weights.sum()
        allocated_all = (weights / total_w) * effective_voters
        alloc_map = dict(zip(df_all["const_no"].values, allocated_all))

        flips = 0
        for _, row in party_a_df.iterrows():
            n = alloc_map.get(row["const_no"], 0)
            gain = self._net_party_b_gain(n, row["minority_pct"], p_min_b, p_maj_b)
            if gain > row["margin"]:
                flips += 1
        return flips

    @staticmethod
    def _print_grid(grid: np.ndarray, row_labels: list, col_labels: list) -> None:
        header = f"{'':>22}" + "  ".join(f"{c:>20}" for c in col_labels)
        print(header)
        for i, rl in enumerate(row_labels):
            row_str = f"{rl:>22}"
            for j in range(len(col_labels)):
                v = grid[i, j]
                row_str += f"  {v:>20}" if v >= 0 else f"  {'(invalid)':>20}"
            print(row_str)
