"""
Entry point — uses the new election_analysis package.

Usage:
    python main.py              # Full pipeline (scrape + analyze + visualize + report)
    python main.py --no-scrape  # Skip scraping; use existing wb_2026_results.csv
"""

import argparse
from pathlib import Path

import pandas as pd

from configs.wb_2026_sir import WB_2026_ELECTION, WB_2026_SIR_EXCLUSION
from election_analysis.scraper import ECIScraper
from election_analysis.analyzer import VoterExclusionAnalyzer
from election_analysis.visualizer import ElectionVisualizer
from election_analysis.reporter import ReportGenerator
from election_analysis.pdf_report import PDFReportGenerator


def main() -> None:
    parser = argparse.ArgumentParser(
        description=f"Election voter exclusion impact analysis"
    )
    parser.add_argument(
        "--no-scrape",
        action="store_true",
        help="Skip scraping; use existing wb_2026_results.csv",
    )
    parser.add_argument(
        "--csv",
        default="wb_2026_results.csv",
        help="CSV path to use with --no-scrape (default: wb_2026_results.csv)",
    )
    args = parser.parse_args()

    ec = WB_2026_ELECTION
    print("=" * 60)
    print(f"{ec.state_name} {ec.year}: SIR Voter Exclusion Impact Analysis")
    print("=" * 60)

    if not args.no_scrape:
        scraper = ECIScraper(WB_2026_ELECTION)
        df = scraper.scrape()
    else:
        csv_path = Path(args.csv)
        if not csv_path.exists():
            print(f"ERROR: {csv_path} not found. Run without --no-scrape first.")
            raise SystemExit(1)
        print(f"Using existing {csv_path}")
        df = pd.read_csv(csv_path)

    analyzer = VoterExclusionAnalyzer(df, WB_2026_ELECTION, WB_2026_SIR_EXCLUSION)
    results = analyzer.run_all()

    # Save Monte Carlo results CSV
    results.monte_carlo.raw.to_csv("monte_carlo_results.csv", index=False)
    print("Saved monte_carlo_results.csv")

    visualizer = ElectionVisualizer(results)
    visualizer.generate_all()

    reporter = ReportGenerator(results)
    reporter.generate()

    pdf_gen = PDFReportGenerator(results, output_dir=Path("."))
    pdf_gen.generate("WB_2026_SIR_Analysis.pdf")

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
        "WB_2026_SIR_Analysis.pdf",
    ]
    print("\nOutput files:")
    for f in outputs:
        marker = "OK" if Path(f).exists() else "MISSING"
        print(f"  [{marker}] {f}")


if __name__ == "__main__":
    main()
