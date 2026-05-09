"""
Publication-quality visualizations for the WB 2026 SIR voter exclusion analysis.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from pathlib import Path

BJP_COLOR  = "#FF6B35"
TMC_COLOR  = "#009B72"
NEUTRAL    = "#4A4A4A"
LIGHT_GREY = "#E8E8E8"

sns.set_theme(style="whitegrid", font_scale=1.1)
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.titlesize": 14,
    "axes.labelsize": 12,
    "figure.dpi": 150,
})

MAJORITY_MARK = 148
BJP_DECLARED  = 206
TMC_DECLARED  = 81


def fig1_margin_histogram(df):
    """Histogram of victory margins, split by winning party."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=False)

    bjp = df[df["winner_is_bjp"]]["margin"].dropna()
    tmc = df[df["winner_is_tmc"]]["margin"].dropna()
    max_m = max(bjp.max(), tmc.max())
    bins = np.linspace(0, min(max_m + 5000, 200_000), 31)

    for ax, data, color, label in [
        (axes[0], bjp, BJP_COLOR, f"BJP-won seats (n={len(bjp)})"),
        (axes[1], tmc, TMC_COLOR, f"TMC-won seats (n={len(tmc)})"),
    ]:
        ax.hist(data, bins=bins, color=color, alpha=0.85, edgecolor="white", linewidth=0.5)
        for threshold, ls, lbl in [
            (5_000,  "--", f"< 5k: {(data < 5000).sum()} seats"),
            (10_000, ":",  f"< 10k: {(data < 10000).sum()} seats"),
            (20_000, "-.", f"< 20k: {(data < 20000).sum()} seats"),
        ]:
            ax.axvline(threshold, color=NEUTRAL, linestyle=ls, linewidth=1.2, label=lbl)
        ax.set_title(label, fontweight="bold")
        ax.set_xlabel("Margin of victory (votes)")
        ax.set_ylabel("Number of seats")
        ax.legend(fontsize=9)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x/1000:.0f}k"))

    fig.suptitle(
        "West Bengal 2026 — Victory Margin Distribution by Winning Party",
        fontsize=15, fontweight="bold", y=1.02,
    )
    fig.tight_layout()
    _save(fig, "fig1_margin_distribution.png")


def fig2_sensitivity_heatmap(grid_results):
    """
    Heatmap of seats flipped across the full probability grid.
    Two panels: uniform distribution and non-uniform (Muslim-weighted).
    """
    uni  = grid_results["uniform"]
    nonu = grid_results["nonuniform"]
    row_labels = [r.replace("Muslim TMC ", "") for r in grid_results["row_labels"]]
    col_labels = [c.replace("Hindu TMC ", "") for c in grid_results["col_labels"]]
    flips_needed = grid_results["flips_needed"]

    fig, axes = plt.subplots(1, 2, figsize=(15, 6))

    # Find common colour range
    vmax = max(uni.max(), nonu.max())

    for ax, data, title in [
        (axes[0], uni,  "Uniform distribution\n(~9,215 voters per seat)"),
        (axes[1], nonu, "Non-uniform distribution\n(weighted by district Muslim %)"),
    ]:
        # Mask invalid cells
        masked = np.ma.masked_where(data < 0, data)
        im = ax.imshow(masked, cmap="RdYlGn_r", vmin=0, vmax=vmax, aspect="auto")

        ax.set_xticks(range(len(col_labels)))
        ax.set_xticklabels(col_labels)
        ax.set_yticks(range(len(row_labels)))
        ax.set_yticklabels(row_labels)
        ax.set_xlabel("Hindu voters → TMC (%)")
        ax.set_ylabel("Muslim voters → TMC (%)")
        ax.set_title(title, fontweight="bold")

        # Annotate cells with seat counts; highlight cells that deny BJP majority
        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                v = data[i, j]
                if v < 0:
                    continue
                color = "white" if v > vmax * 0.6 else "black"
                marker = f"★{v}" if v >= flips_needed else str(v)
                ax.text(j, i, marker, ha="center", va="center",
                        fontsize=11, fontweight="bold", color=color)

        plt.colorbar(im, ax=ax, label="Seats flipped (BJP → TMC)")

    fig.suptitle(
        "Seats Flipped from BJP to TMC Across Full Probability Spectrum\n"
        f"(★ = BJP loses majority; needs ≥{flips_needed} flips | Turnout = 80%)",
        fontsize=13, fontweight="bold", y=1.03,
    )
    fig.tight_layout()
    _save(fig, "fig2_sensitivity_heatmap.png")


def fig3_scenario_bars(scen_df):
    """
    Grouped bar chart showing BJP and TMC seat counts for each named scenario.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

    labels = scen_df["Scenario"].tolist()
    x = np.arange(len(labels))
    w = 0.35

    # Left: seats flipped
    flips_u  = scen_df["Uniform flips"].tolist()
    flips_nu = scen_df["Non-uniform flips"].tolist()
    b1 = ax1.bar(x - w/2, flips_u,  w, label="Uniform",      color=TMC_COLOR,  alpha=0.85, edgecolor="white")
    b2 = ax1.bar(x + w/2, flips_nu, w, label="Non-uniform",  color=BJP_COLOR,  alpha=0.70, edgecolor="white")
    ax1.bar_label(b1, fmt="%d", fontsize=10, padding=3, fontweight="bold")
    ax1.bar_label(b2, fmt="%d", fontsize=10, padding=3, fontweight="bold")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=25, ha="right", fontsize=10)
    ax1.set_ylabel("BJP seats that flip to TMC")
    ax1.set_title("Seats Flipped per Scenario\n(Uniform vs Non-uniform distribution)", fontweight="bold")
    ax1.legend()
    ax1.set_ylim(0, max(max(flips_u), max(flips_nu)) * 1.4 + 3)

    # Right: final BJP seat count
    bjp_u  = scen_df["BJP (uniform)"].tolist()
    bjp_nu = scen_df["BJP (non-unif.)"].tolist()
    b3 = ax2.bar(x - w/2, bjp_u,  w, label="Uniform",     color=BJP_COLOR,  alpha=0.85, edgecolor="white")
    b4 = ax2.bar(x + w/2, bjp_nu, w, label="Non-uniform", color="#CC4400",  alpha=0.70, edgecolor="white")
    ax2.bar_label(b3, fmt="%d", fontsize=10, padding=3, fontweight="bold")
    ax2.bar_label(b4, fmt="%d", fontsize=10, padding=3, fontweight="bold")
    ax2.axhline(MAJORITY_MARK, color="red", linewidth=2, linestyle="--", label=f"Majority ({MAJORITY_MARK})")
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, rotation=25, ha="right", fontsize=10)
    ax2.set_ylabel("BJP final seat count")
    ax2.set_title("BJP Final Seat Count by Scenario\n(Majority = 148)", fontweight="bold")
    ax2.legend()
    ax2.set_ylim(0, BJP_DECLARED * 1.15)

    fig.suptitle(
        "Impact of 27 Lakh SIR-Excluded Voters: Named Scenarios\n"
        "From BJP-biased to TMC-biased assumptions",
        fontsize=14, fontweight="bold", y=1.02,
    )
    fig.tight_layout()
    _save(fig, "fig3_scenario_bars.png")


def fig4_monte_carlo(mc_df):
    """Distribution of seat changes from Monte Carlo simulation."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    flips_for_loss = BJP_DECLARED - MAJORITY_MARK + 1

    # Left: histogram of flips
    ax = axes[0]
    max_flips = mc_df["seats_flipped"].max()
    bins = range(0, max_flips + 2)
    ax.hist(mc_df["seats_flipped"], bins=bins, color=TMC_COLOR, alpha=0.80, edgecolor="white")
    median_f = mc_df["seats_flipped"].median()
    p95_f    = mc_df["seats_flipped"].quantile(0.95)
    ax.axvline(median_f,     color=NEUTRAL,    linewidth=2,   linestyle="--",
               label=f"Median: {median_f:.0f}")
    ax.axvline(p95_f,        color="darkorange", linewidth=1.5, linestyle=":",
               label=f"95th pct: {p95_f:.0f}")
    ax.axvline(flips_for_loss, color="red", linewidth=2, linestyle="-.",
               label=f"Majority-denial threshold: {flips_for_loss}")
    ax.set_xlabel("BJP seats flipped to TMC")
    ax.set_ylabel("Simulation count")
    ax.set_title("Distribution of Seat Flips\n(10,000 Monte Carlo simulations)", fontweight="bold")
    ax.legend(fontsize=9)

    # Right: survival function P(flips ≥ x)
    ax2 = axes[1]
    sorted_f = np.sort(mc_df["seats_flipped"])
    cdf = np.arange(1, len(sorted_f) + 1) / len(sorted_f)
    ax2.plot(sorted_f, 1 - cdf, color=BJP_COLOR, linewidth=2.5, label="P(flips ≥ x)")
    ax2.axvline(flips_for_loss, color="red", linewidth=1.5, linestyle="--",
                label=f"Majority-denial threshold ({flips_for_loss})")
    p_loses = (mc_df["seats_flipped"] >= flips_for_loss).mean()
    ax2.axhline(p_loses, color=NEUTRAL, linewidth=1.2, linestyle=":",
                label=f"P(BJP loses majority) = {p_loses:.4%}")
    ax2.set_xlabel("Minimum seats flipped")
    ax2.set_ylabel("Probability")
    ax2.set_title("P(BJP Loses Majority)\nas a function of seats flipped", fontweight="bold")
    ax2.legend(fontsize=9)
    ax2.set_ylim(-0.02, 1.05)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.1%}"))

    fig.suptitle(
        "Monte Carlo Simulation: SIR Exclusion Impact Under Full Parameter Uncertainty\n"
        f"(Muslim TMC% ∈ [50%,90%], Hindu TMC% ∈ [15%,55%], Turnout ∈ [60%,90%])",
        fontsize=13, fontweight="bold", y=1.03,
    )
    fig.tight_layout()
    _save(fig, "fig4_monte_carlo.png")


def fig5_marginal_seats(df, max_tmc_data):
    """Waterfall-style view of 30 most marginal BJP seats."""
    bjp_df = df[df["winner_is_bjp"]].copy().sort_values("margin").head(30)

    flipped_names = set()
    if max_tmc_data and max_tmc_data.get("flipped_seats"):
        flipped_names = {s["const_name"] for s in max_tmc_data["flipped_seats"]}

    fig, ax = plt.subplots(figsize=(12, 9))

    colors = [
        TMC_COLOR if row["const_name"] in flipped_names else BJP_COLOR
        for _, row in bjp_df.iterrows()
    ]

    bars = ax.barh(
        range(len(bjp_df)),
        bjp_df["margin"].values,
        color=colors, alpha=0.85, edgecolor="white",
    )

    ax.set_yticks(range(len(bjp_df)))
    ax.set_yticklabels(
        [f"{r['const_name']} ({r.get('district', '?')[:8]})"
         for _, r in bjp_df.iterrows()],
        fontsize=8.5,
    )
    ax.set_xlabel("BJP victory margin (votes)")
    ax.set_title(
        "30 Most Marginal BJP Seats — WB 2026\n"
        "(Green = flips under the absolute upper-bound stress test)",
        fontweight="bold",
    )
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    bjp_patch = mpatches.Patch(color=BJP_COLOR, label="Safe under all realistic scenarios")
    tmc_patch = mpatches.Patch(color=TMC_COLOR, label="Flips under absolute upper-bound only")
    ax.legend(handles=[bjp_patch, tmc_patch], loc="lower right")

    fig.tight_layout()
    _save(fig, "fig5_marginal_seats.png")


def _save(fig, path):
    fig.savefig(path, bbox_inches="tight", dpi=150)
    plt.close(fig)
    print(f"Saved {path}")


def generate_all(results):
    print("\n" + "=" * 60)
    print("PHASE 3: Generating visualizations")
    print("=" * 60)

    df      = results["df"]
    fig1_margin_histogram(df)
    fig2_sensitivity_heatmap(results["grid"])
    fig3_scenario_bars(results["scenarios"])
    fig4_monte_carlo(results["mc"])
    fig5_marginal_seats(df, results["max_tmc"])

    print("\nAll figures saved.")


if __name__ == "__main__":
    from analyzer import run_analysis
    results = run_analysis()
    generate_all(results)
