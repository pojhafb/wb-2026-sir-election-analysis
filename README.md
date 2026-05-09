# West Bengal 2026 Election: Statistical Analysis of SIR Voter Exclusion Impact

A rigorous constituency-level analysis of whether the 27 lakh (2.7 million) voters excluded during the Special Intensive Revision (SIR) of West Bengal's electoral rolls could have changed the outcome of the May 2026 Assembly Election.

## Background

An article (Nilanjan Mukhopadhyay, Rediff, May 7 2026) juxtaposes the ~32 lakh aggregate vote gap between BJP and TMC with the 27 lakh voters whose appeals are still pending adjudication, implying the election's legitimacy is questionable. This project tests that claim rigorously using actual ECI constituency-level data.

## Key Findings

| Scenario | Seats flipped | BJP final | Majority? |
|---|---|---|---|
| Actual result | 0 | 206 | ✅ Yes |
| BJP-biased (Muslim 50%→TMC, Hindu 15%→TMC, 80% turnout) | 0 | 206 | ✅ Yes |
| Midpoint (Muslim 70%→TMC, Hindu 35%→TMC, 80% turnout) | 0 | 206 | ✅ Yes |
| TMC-biased (Muslim 90%→TMC, Hindu 55%→TMC, 80% turnout) | 9–10 | 196–197 | ✅ Yes |
| Max TMC, 100% turnout, geographic constraint | 13 | 193 | ✅ Yes |
| **Absolute upper bound (geographic constraint removed)** | **92** | **114** | ❌ No* |

*\*The 92-flip scenario requires teleporting voters to strategic seats — physically impossible.*

**P(BJP retains majority) = 100.000% across 10,000 Monte Carlo simulations** varying all parameters simultaneously.

## Methodology

- **Data**: All 293 declared constituencies from ECI results website (via Internet Archive)
- **Probability sensitivity**: Full grid from BJP-biased to TMC-biased assumptions (no cherry-picking)
- **Geographic realism**: Voters distributed by district-level Muslim population % (Census 2011)
- **Monte Carlo**: 10,000 simulations varying Muslim TMC% ∈ [50%,90%], Hindu TMC% ∈ [15%,55%], turnout ∈ [60%,90%]

## Why the Original Argument Fails

1. **Ecological fallacy**: Aggregate vote gaps don't translate to seat changes in FPTP
2. **Geographic mismatch**: 65% of excluded voters are Muslim, concentrated in districts (Murshidabad, Malda, North Dinajpur) that TMC was already winning by large margins
3. **Distributional impossibility**: Average of ~9,215 excluded voters per seat produces a net swing far smaller than the median BJP margin of 26,042 votes

## Project Structure

```
.
├── scraper.py          # Data collection (ECI via Wayback Machine)
├── analyzer.py         # Statistical analysis (5 analyses)
├── visualizer.py       # Publication-quality charts
├── report.py           # Markdown report generator
├── main.py             # Pipeline entry point
├── requirements.txt    # Python dependencies
├── REPORT.md           # Full analysis report (generated)
├── wb_2026_results.csv     # Final merged dataset (generated)
├── scenario_summary.csv    # Named scenario results (generated)
├── monte_carlo_results.csv # 10,000 simulation results (generated)
└── fig*.png                # Visualizations (generated)
```

## Usage

```bash
pip install -r requirements.txt

# Full pipeline (scrape + analyse + visualize + report)
python main.py

# If you already have wb_2026_results.csv
python main.py --no-scrape
```

**Note**: Scraping fetches ~308 pages from the Internet Archive (Wayback Machine) with 2.5s delays. Expect ~15–20 minutes for initial scrape. Results are cached in `cache/`.

## Data Sources

| Source | Details |
|---|---|
| ECI Results | `results.eci.gov.in/ResultAcGenMay2026/` via Internet Archive (May 4–5 2026) |
| SIR exclusion data | Multiple Indian news sources; Wikipedia (2026 WB Assembly election article) |
| Muslim population % | Census of India 2011, district-level (Office of the Registrar General) |

## Figures

| Figure | Description |
|---|---|
| `fig1_margin_distribution.png` | Histogram of BJP and TMC victory margins |
| `fig2_sensitivity_heatmap.png` | Seats flipped across full probability grid (5×5 heatmap) |
| `fig3_scenario_bars.png` | BJP/TMC seat counts for 6 named scenarios |
| `fig4_monte_carlo.png` | Monte Carlo distribution and survival function |
| `fig5_marginal_seats.png` | 30 most marginal BJP seats |

## Limitations

- District mapping based on ECI 2026 delimitation; minor boundary-constituency assignments may differ
- Muslim% from Census 2011; 2026 may differ marginally
- The 27 lakh "pending" figure comes from news sources; ECI has not published a constituency-level breakdown
- Falta (seat 144) excluded — repoll held May 21, won by BJP (included in 207 final tally)
- One seat discrepancy between our ECI scrape (81 TMC) and some news sources (80 TMC)

## License

MIT License. All code and analysis are for research/educational purposes. The analysis is politically neutral — it tests a specific statistical claim using publicly available data.
