"""
Publication-quality visualizations for election voter exclusion analysis.
All labels and colors are driven by ElectionConfig so they work for any election.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from .models import AnalysisResults

# Default color palette
_PARTY_A_COLOR = "#FF6B35"   # warm orange (BJP-ish)
_PARTY_B_COLOR = "#009B72"   # teal green (TMC-ish)
_NEUTRAL       = "#4A4A4A"
_LIGHT_GREY    = "#E8E8E8"

sns.set_theme(style="whitegrid", font_scale=1.1)
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.titlesize": 14,
    "axes.labelsize": 12,
    "figure.dpi": 150,
})


class ElectionVisualizer:
    """
    Generates all charts for the voter exclusion analysis.
    Colors and labels are read from AnalysisResults.election so they adapt
    automatically to any election configuration.
    """

    def __init__(
        self,
        results: AnalysisResults,
        output_dir: Path = Path("."),
    ) -> None:
        self.results    = results
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        ec = results.election
        self._a_label  = ec.party_a_label
        self._b_label  = ec.party_b_label
        self._a_color  = _PARTY_A_COLOR
        self._b_color  = _PARTY_B_COLOR

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_all(self) -> list:
        """Call all five chart methods and return the list of saved Paths."""
        print("\n" + "=" * 60)
        print("PHASE 3: Generating visualizations")
        print("=" * 60)
        paths = [
            self.margin_histogram(),
            self.sensitivity_heatmap(),
            self.scenario_bars(),
            self.monte_carlo_plot(),
            self.marginal_seats_chart(),
        ]
        print("\nAll figures saved.")
        return paths

    def margin_histogram(self) -> Path:
        """Histogram of victory margins, split by winning party."""
        df = self.results.data
        ec = self.results.election

        fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=False)

        a_margins = df[df["winner_is_party_a"]]["margin"].dropna()
        b_margins = df[df["winner_is_party_b"]]["margin"].dropna()
        max_m = max(a_margins.max(), b_margins.max())
        bins  = np.linspace(0, min(max_m + 5000, 200_000), 31)

        for ax, data, color, label in [
            (axes[0], a_margins, self._a_color, f"{self._a_label}-won seats (n={len(a_margins)})"),
            (axes[1], b_margins, self._b_color, f"{self._b_label}-won seats (n={len(b_margins)})"),
        ]:
            ax.hist(data, bins=bins, color=color, alpha=0.85, edgecolor="white", linewidth=0.5)
            for threshold, ls, lbl in [
                (5_000,  "--", f"< 5k: {(data < 5000).sum()} seats"),
                (10_000, ":",  f"< 10k: {(data < 10000).sum()} seats"),
                (20_000, "-.", f"< 20k: {(data < 20000).sum()} seats"),
            ]:
                ax.axvline(threshold, color=_NEUTRAL, linestyle=ls, linewidth=1.2, label=lbl)
            ax.set_title(label, fontweight="bold")
            ax.set_xlabel("Margin of victory (votes)")
            ax.set_ylabel("Number of seats")
            ax.legend(fontsize=9)
            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x/1000:.0f}k"))

        fig.suptitle(
            f"{ec.state_name} {ec.year} — Victory Margin Distribution by Winning Party",
            fontsize=15, fontweight="bold", y=1.02,
        )
        fig.tight_layout()
        return self._save(fig, "fig1_margin_distribution.png")

    def sensitivity_heatmap(self) -> Path:
        """Heatmap of seats flipped across the full probability grid."""
        grid = self.results.sensitivity
        ec   = self.results.election

        uni  = grid.uniform
        nonu = grid.nonuniform
        row_labels = [r.split(" ", 1)[1] if " " in r else r for r in grid.row_labels]
        col_labels = [c.split(" ", 1)[1] if " " in c else c for c in grid.col_labels]
        flips_needed = grid.flips_needed

        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        vmax = max(int(uni.max()), int(nonu.max()))

        for ax, data, title in [
            (axes[0], uni,  f"Uniform distribution"),
            (axes[1], nonu, f"Non-uniform (weighted by district {ec.minority_group_name} %)"),
        ]:
            masked = np.ma.masked_where(data < 0, data)
            im = ax.imshow(masked, cmap="RdYlGn_r", vmin=0, vmax=vmax, aspect="auto")

            ax.set_xticks(range(len(col_labels)))
            ax.set_xticklabels(col_labels)
            ax.set_yticks(range(len(row_labels)))
            ax.set_yticklabels(row_labels)
            ax.set_xlabel(f"{ec.majority_group_name} voters → {ec.party_b_label} (%)")
            ax.set_ylabel(f"{ec.minority_group_name} voters → {ec.party_b_label} (%)")
            ax.set_title(title, fontweight="bold")

            for i in range(data.shape[0]):
                for j in range(data.shape[1]):
                    v = data[i, j]
                    if v < 0:
                        continue
                    color  = "white" if v > vmax * 0.6 else "black"
                    marker = f"★{v}" if v >= flips_needed else str(v)
                    ax.text(j, i, marker, ha="center", va="center",
                            fontsize=11, fontweight="bold", color=color)

            plt.colorbar(im, ax=ax, label=f"Seats flipped ({ec.party_a_label} → {ec.party_b_label})")

        fig.suptitle(
            f"Seats Flipped from {ec.party_a_label} to {ec.party_b_label} Across Full Probability Spectrum\n"
            f"(★ = {ec.party_a_label} loses majority; needs ≥{flips_needed} flips | Turnout = 80%)",
            fontsize=13, fontweight="bold", y=1.03,
        )
        fig.tight_layout()
        return self._save(fig, "fig2_sensitivity_heatmap.png")

    def scenario_bars(self) -> Path:
        """Grouped bar chart of seats flipped and final seat counts per named scenario."""
        scen_df = self.results.scenarios
        ec      = self.results.election

        a_label = ec.party_a_label
        b_label = ec.party_b_label
        a_declared = int(self.results.data["winner_is_party_a"].sum())

        labels = scen_df["Scenario"].tolist()
        x = np.arange(len(labels))
        w = 0.35

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

        flips_u  = scen_df["Uniform flips"].tolist()
        flips_nu = scen_df["Non-uniform flips"].tolist()
        b1 = ax1.bar(x - w/2, flips_u,  w, label="Uniform",     color=self._b_color, alpha=0.85, edgecolor="white")
        b2 = ax1.bar(x + w/2, flips_nu, w, label="Non-uniform", color=self._a_color, alpha=0.70, edgecolor="white")
        ax1.bar_label(b1, fmt="%d", fontsize=10, padding=3, fontweight="bold")
        ax1.bar_label(b2, fmt="%d", fontsize=10, padding=3, fontweight="bold")
        ax1.set_xticks(x)
        ax1.set_xticklabels(labels, rotation=25, ha="right", fontsize=10)
        ax1.set_ylabel(f"{a_label} seats that flip to {b_label}")
        ax1.set_title(f"Seats Flipped per Scenario\n(Uniform vs Non-uniform distribution)", fontweight="bold")
        ax1.legend()
        ax1.set_ylim(0, max(max(flips_u), max(flips_nu)) * 1.4 + 3)

        col_u  = f"{a_label} (uniform)"
        col_nu = f"{a_label} (non-unif.)"
        a_u  = scen_df[col_u].tolist()
        a_nu = scen_df[col_nu].tolist()
        b3 = ax2.bar(x - w/2, a_u,  w, label="Uniform",     color=self._a_color, alpha=0.85, edgecolor="white")
        b4 = ax2.bar(x + w/2, a_nu, w, label="Non-uniform", color="#CC4400",     alpha=0.70, edgecolor="white")
        ax2.bar_label(b3, fmt="%d", fontsize=10, padding=3, fontweight="bold")
        ax2.bar_label(b4, fmt="%d", fontsize=10, padding=3, fontweight="bold")
        ax2.axhline(ec.majority_mark, color="red", linewidth=2, linestyle="--",
                    label=f"Majority ({ec.majority_mark})")
        ax2.set_xticks(x)
        ax2.set_xticklabels(labels, rotation=25, ha="right", fontsize=10)
        ax2.set_ylabel(f"{a_label} final seat count")
        ax2.set_title(f"{a_label} Final Seat Count by Scenario\n(Majority = {ec.majority_mark})", fontweight="bold")
        ax2.legend()
        ax2.set_ylim(0, a_declared * 1.15)

        fig.suptitle(
            f"Impact of {self.results.exclusion.total_excluded:,} SIR-Excluded Voters: Named Scenarios\n"
            f"From {a_label}-biased to {b_label}-biased assumptions",
            fontsize=14, fontweight="bold", y=1.02,
        )
        fig.tight_layout()
        return self._save(fig, "fig3_scenario_bars.png")

    def monte_carlo_plot(self) -> Path:
        """Distribution of seat changes from Monte Carlo simulation."""
        mc  = self.results.monte_carlo
        ec  = self.results.election
        mc_df = mc.raw

        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        flips_needed = mc.flips_needed

        ax = axes[0]
        max_flips = mc_df["seats_flipped"].max()
        bins = range(0, max_flips + 2)
        ax.hist(mc_df["seats_flipped"], bins=bins, color=self._b_color, alpha=0.80, edgecolor="white")
        median_f = mc_df["seats_flipped"].median()
        p95_f    = mc_df["seats_flipped"].quantile(0.95)
        ax.axvline(median_f,      color=_NEUTRAL,      linewidth=2,   linestyle="--",
                   label=f"Median: {median_f:.0f}")
        ax.axvline(p95_f,         color="darkorange",  linewidth=1.5, linestyle=":",
                   label=f"95th pct: {p95_f:.0f}")
        ax.axvline(flips_needed,  color="red",         linewidth=2,   linestyle="-.",
                   label=f"Majority-denial threshold: {flips_needed}")
        ax.set_xlabel(f"{ec.party_a_label} seats flipped to {ec.party_b_label}")
        ax.set_ylabel("Simulation count")
        ax.set_title(f"Distribution of Seat Flips\n({mc.n_simulations:,} Monte Carlo simulations)", fontweight="bold")
        ax.legend(fontsize=9)

        ax2 = axes[1]
        sorted_f = np.sort(mc_df["seats_flipped"])
        cdf = np.arange(1, len(sorted_f) + 1) / len(sorted_f)
        ax2.plot(sorted_f, 1 - cdf, color=self._a_color, linewidth=2.5, label="P(flips ≥ x)")
        ax2.axvline(flips_needed, color="red", linewidth=1.5, linestyle="--",
                    label=f"Majority-denial threshold ({flips_needed})")
        p_loses = (mc_df["seats_flipped"] >= flips_needed).mean()
        ax2.axhline(p_loses, color=_NEUTRAL, linewidth=1.2, linestyle=":",
                    label=f"P({ec.party_a_label} loses majority) = {p_loses:.4%}")
        ax2.set_xlabel("Minimum seats flipped")
        ax2.set_ylabel("Probability")
        ax2.set_title(f"P({ec.party_a_label} Loses Majority)\nas a function of seats flipped", fontweight="bold")
        ax2.legend(fontsize=9)
        ax2.set_ylim(-0.02, 1.05)
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.1%}"))

        xc = self.results.exclusion
        fig.suptitle(
            f"Monte Carlo Simulation: SIR Exclusion Impact Under Full Parameter Uncertainty\n"
            f"({ec.minority_group_name}→{ec.party_b_label} ∈ [{xc.minority_b_grid[0]:.0%},{xc.minority_b_grid[-1]:.0%}], "
            f"{ec.majority_group_name}→{ec.party_b_label} ∈ [{xc.majority_b_grid[0]:.0%},{xc.majority_b_grid[-1]:.0%}], "
            f"Turnout ∈ [60%,90%])",
            fontsize=13, fontweight="bold", y=1.03,
        )
        fig.tight_layout()
        return self._save(fig, "fig4_monte_carlo.png")

    def marginal_seats_chart(self) -> Path:
        """Horizontal bar chart of the 30 most marginal party-A seats."""
        df  = self.results.data
        ub  = self.results.upper_bound
        ec  = self.results.election

        a_df = df[df["winner_is_party_a"]].copy().sort_values("margin").head(30)

        flipped_names = set()
        if ub.flipped_seats:
            flipped_names = {s["const_name"] for s in ub.flipped_seats}

        fig, ax = plt.subplots(figsize=(12, 9))

        colors = [
            self._b_color if row["const_name"] in flipped_names else self._a_color
            for _, row in a_df.iterrows()
        ]

        ax.barh(
            range(len(a_df)),
            a_df["margin"].values,
            color=colors, alpha=0.85, edgecolor="white",
        )

        ax.set_yticks(range(len(a_df)))
        ax.set_yticklabels(
            [f"{r['const_name']} ({str(r.get('district', '?'))[:8]})"
             for _, r in a_df.iterrows()],
            fontsize=8.5,
        )
        ax.set_xlabel(f"{ec.party_a_label} victory margin (votes)")
        ax.set_title(
            f"30 Most Marginal {ec.party_a_label} Seats — {ec.state_name} {ec.year}\n"
            f"(Green = flips under the absolute upper-bound stress test)",
            fontweight="bold",
        )
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))

        a_patch = mpatches.Patch(color=self._a_color, label="Safe under all realistic scenarios")
        b_patch = mpatches.Patch(color=self._b_color, label="Flips under absolute upper-bound only")
        ax.legend(handles=[a_patch, b_patch], loc="lower right")

        fig.tight_layout()
        return self._save(fig, "fig5_marginal_seats.png")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _save(self, fig, filename: str) -> Path:
        path = self.output_dir / filename
        fig.savefig(path, bbox_inches="tight", dpi=150)
        plt.close(fig)
        print(f"Saved {path}")
        return path
