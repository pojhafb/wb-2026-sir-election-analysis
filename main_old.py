"""
West Bengal 2026 Election — SIR Voter Exclusion Impact Analysis
Entry point: runs scraping, analysis, visualization, and report generation.

Usage:
    python main.py              # Full pipeline
    python main.py --no-scrape  # Skip scraping; use existing wb_2026_results.csv
"""

import sys
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="WB 2026 Election SIR voter exclusion impact analysis"
    )
    parser.add_argument(
        "--no-scrape",
        action="store_true",
        help="Skip scraping; use existing wb_2026_results.csv",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("West Bengal 2026: SIR Voter Exclusion Impact Analysis")
    print("=" * 60)

    if not args.no_scrape:
        from scraper import run_scrape
        df = run_scrape()
    else:
        if not Path("wb_2026_results.csv").exists():
            print("ERROR: wb_2026_results.csv not found. Run without --no-scrape first.")
            sys.exit(1)
        print("Using existing wb_2026_results.csv")

    from analyzer import run_analysis
    results = run_analysis()

    from visualizer import generate_all
    generate_all(results)

    from report import generate_report
    generate_report(results)

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    outputs = [
        "wb_2026_results.csv",
        "candidateswise_raw.csv",
        "statewise_raw.csv",
        "monte_carlo_results.csv",
        "scenario_summary.csv",
        "fig1_margin_distribution.png",
        "fig2_sensitivity_heatmap.png",
        "fig3_scenario_bars.png",
        "fig4_monte_carlo.png",
        "fig5_marginal_seats.png",
        "REPORT.md",
    ]
    print("\nOutput files:")
    for f in outputs:
        exists = "✓" if Path(f).exists() else "✗"
        print(f"  {exists} {f}")


if __name__ == "__main__":
    main()
