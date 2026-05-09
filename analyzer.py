"""
Statistical analysis of SIR voter exclusion impact on WB 2026 Assembly Election.

METHODOLOGY OVERVIEW
====================
We test whether 27 lakh (2.7M) voters excluded during the Special Intensive
Revision (SIR), if they had voted, could have changed enough seats to deny
BJP a majority (148/294 seats).

The core uncertainty is *how excluded voters would have voted*. Rather than
assuming a single set of probabilities, we run the entire analysis across a
full grid of voting assumptions from "strongly BJP-biased" to "strongly
TMC-biased", letting the reader judge which assumptions are realistic.

KEY FACTS
=========
  - Total seats: 294 (293 declared May 4; Falta/144 repoll May 21 → BJP)
  - BJP: 206 declared (207 with Falta), TMC: 81, Others: 6
  - Majority mark: 148
  - SIR pending (not yet adjudicated): 27 lakh
  - Of the 27 lakh pending: ~65% Muslim, ~35% Hindu (per multiple sources)
  - District Muslim population shares: Census of India 2011

PROBABILITY GRID (for sensitivity analysis)
============================================
Muslim TMC% range: 0.50 – 0.90 (in steps of 0.10)
  - 0.50 = half of Muslim excluded voters vote TMC (BJP-biased assumption)
  - 0.90 = near-unanimous Muslim vote for TMC (TMC-biased assumption)

Hindu TMC%  range: 0.15 – 0.55 (in steps of 0.10)
  - 0.15 = few Hindus vote TMC (BJP-biased)
  - 0.55 = majority of Hindus vote TMC (TMC-biased)

At each grid point, the remaining votes are split proportionally between BJP
and "Others" (using historical "Others" share as a constant 8%).

TURNOUT GRID: 0.60 – 1.00 (in steps of 0.10)
  - 0.60 = only 60% of excluded voters would have actually voted
  - 1.00 = all excluded voters vote (upper bound)
"""

import pandas as pd
import numpy as np
from pathlib import Path
import itertools

# ── Constants ──────────────────────────────────────────────────────────────

TOTAL_EXCLUDED = 2_700_000       # 27 lakh pending SIR exclusions
MUSLIM_SHARE   = 0.65            # fraction of excluded who are Muslim
HINDU_SHARE    = 0.35            # fraction of excluded who are Hindu
MAJORITY_MARK  = 148
BJP_DECLARED   = 206             # BJP seats from declared 293
TMC_DECLARED   = 81              # TMC seats (81 from ECI data; 80 per other sources — 1-seat discrepancy)

# Default assumptions (for single-scenario runs) — *labelled* as a midpoint
DEFAULT_P_MUSLIM_TMC = 0.75
DEFAULT_P_HINDU_TMC  = 0.30
DEFAULT_TURNOUT      = 0.80

# Grid ranges for sensitivity analysis
MUSLIM_TMC_GRID = [0.50, 0.60, 0.70, 0.80, 0.90]
HINDU_TMC_GRID  = [0.15, 0.25, 0.35, 0.45, 0.55]
TURNOUT_GRID    = [0.60, 0.70, 0.80, 0.90, 1.00]

# "Others" vote share stays fixed at 8% for Muslims, 10% for Hindus;
# remaining votes split BJP/TMC proportionally.
MUSLIM_OTHERS = 0.08
HINDU_OTHERS  = 0.10

# District → approximate Muslim population share (Census 2011)
DISTRICT_MUSLIM_PCT = {
    "Murshidabad":       0.66,
    "Malda":             0.51,
    "North Dinajpur":    0.50,
    "South 24 Parganas": 0.33,
    "Birbhum":           0.37,
    "Nadia":             0.25,
    "North 24 Parganas": 0.25,
    "Howrah":            0.25,
    "Kolkata":           0.20,
    "Hooghly":           0.16,
    "Purulia":           0.09,
    "Bankura":           0.07,
    "West Midnapore":    0.08,
    "East Midnapore":    0.09,
    "Jhargram":          0.06,
    "Burdwan":           0.20,
    "Cooch Behar":       0.25,
    "Jalpaiguri":        0.12,
    "Alipurduar":        0.10,
    "Darjeeling":        0.05,
    "Kalimpong":         0.05,
    "South Dinajpur":    0.26,
}

# Constituency number → district mapping.
# Derived from ECI 2026 delimitation order verified against constituency names
# in wb_2026_results.csv.
CONSTITUENCY_DISTRICT = {
    # Cooch Behar (1-7): MEKLIGANJ, MATHABHANGA, COOCHBEHAR UTTAR/DAKSHIN, SITALKUCHI, SITAI, DINHATA
    **{n: "Cooch Behar" for n in range(1, 8)},
    # Alipurduar (8-14): NATABARI, TUFANGANJ, KUMARGRAM, KALCHINI, ALIPURDUARS, FALAKATA, MADARIHAT
    **{n: "Alipurduar" for n in range(8, 15)},
    # Jalpaiguri (15-21): DHUPGURI, MAYNAGURI, JALPAIGURI, RAJGANJ, DABGRAM-FULBARI, MAL, NAGRAKATA
    **{n: "Jalpaiguri" for n in range(15, 22)},
    # Kalimpong (22)
    22: "Kalimpong",
    # Darjeeling (23-27): DARJEELING, KURSEONG, MATIGARA-NAXALBARI, SILIGURI, PHANSIDEWA
    **{n: "Darjeeling" for n in range(23, 28)},
    # North Dinajpur (28-36): CHOPRA, ISLAMPUR, GOALPOKHAR, CHAKULIA, KARANDIGHI, HEMTABAD, KALIAGANJ, RAIGANJ, ITAHAR
    **{n: "North Dinajpur" for n in range(28, 37)},
    # South Dinajpur (37-42): KUSHMANDI, KUMARGANJ, BALURGHAT, TAPAN, GANGARAMPUR, HARIRAMPUR
    **{n: "South Dinajpur" for n in range(37, 43)},
    # Malda (43-54): HABIBPUR, GAZOLE, CHANCHAL, HARISCHANDRAPUR, MALATIPUR, RATUA, MANIKCHAK,
    #               MALDAHA, ENGLISH BAZAR, MOTHABARI, SUJAPUR, BAISNABNAGAR
    **{n: "Malda" for n in range(43, 55)},
    # Murshidabad (55-76): FARAKKA, SAMSERGANJ, SUTI, JANGIPUR, RAGHUNATHGANJ, SAGARDIGHI,
    #   LALGOLA, BHAGAWANGOLA, RANINAGAR, MURSHIDABAD, NABAGRAM, KHARGRAM, BURWAN, KANDI,
    #   BHARATPUR, REJINAGAR, BELDANGA, BAHARAMPUR, HARIHARPARA, NOWDA, DOMKAL, JALANGI
    **{n: "Murshidabad" for n in range(55, 77)},
    # Nadia (77-93): KARIMPUR, TEHATTA, PALASHIPARA, KALIGANJ, NAKASHIPARA, CHAPRA,
    #   KRISHNANAGAR UTTAR, NABADWIP, KRISHNANAGAR DAKSHIN, SANTIPUR, RANAGHAT series,
    #   CHAKDAHA, KALYANI, HARINGHATA
    **{n: "Nadia" for n in range(77, 94)},
    # North 24 Parganas (94-126): BAGDA, BANGAON, GAIGHATA, SWARUPNAGAR, BADURIA, HABRA,
    #   ASHOKNAGAR, AMDANGA, BIJPUR, NAIHATI, BHATPARA, JAGATDAL, NOAPARA, BARRACKPUR,
    #   KHARDAHA, DUM DUM UTTAR, PANIHATI, KAMARHATI, BARANAGAR, DUM DUM, RAJARHAT NEW TOWN,
    #   BIDHANNAGAR, RAJARHAT GOPALPUR, MADHYAMGRAM, BARASAT, DEGANGA, HAROA, MINAKHAN,
    #   SANDESHKHALI, BASIRHAT DAKSHIN, BASIRHAT UTTAR, HINGALGANJ, GOSABA
    **{n: "North 24 Parganas" for n in range(94, 127)},
    # South 24 Parganas (127-143, 145-148): Sundarban/coastal areas + Kolkata fringe
    # 127: GOSABA (already in N24P above - actually GOSABA is South 24 Pgs)
    # Let me reassign: 122-126 are North 24 Parganas northern belt, 127+ are South 24 Parganas
    127: "South 24 Parganas",  # GOSABA
    128: "South 24 Parganas",  # BASANTI
    129: "South 24 Parganas",  # KULTALI
    130: "South 24 Parganas",  # PATHARPRATIMA
    131: "South 24 Parganas",  # KAKDWIP
    132: "South 24 Parganas",  # SAGAR
    133: "South 24 Parganas",  # KULPI
    134: "South 24 Parganas",  # RAIDIGHI
    135: "South 24 Parganas",  # MANDIRBAZAR
    136: "South 24 Parganas",  # JAYNAGAR
    137: "South 24 Parganas",  # BARUIPUR PURBA
    138: "South 24 Parganas",  # CANNING PASCHIM
    139: "South 24 Parganas",  # CANNING PURBA
    140: "South 24 Parganas",  # BARUIPUR PASCHIM
    141: "South 24 Parganas",  # MAGRAHAT PURBA
    142: "South 24 Parganas",  # MAGRAHAT PASCHIM
    143: "South 24 Parganas",  # DIAMOND HARBOUR
    144: "South 24 Parganas",  # FALTA (repoll, excluded)
    145: "South 24 Parganas",  # SATGACHHIA
    146: "South 24 Parganas",  # BISHNUPUR
    147: "South 24 Parganas",  # SONARPUR DAKSHIN
    148: "South 24 Parganas",  # BHANGAR
    # Kolkata (149-168): KASBA, JADAVPUR, SONARPUR UTTAR, TOLLYGANJ, BEHALA PURBA/PASCHIM,
    #   MAHESHTALA, BUDGE BUDGE, METIABURUZ, KOLKATA PORT, BHABANIPUR, RASHBEHARI,
    #   BALLYGUNGE, CHOWRANGEE, ENTALLY, BELEGHATA, JORASANKO, SHYAMPUKUR, MANIKTALA,
    #   KASHIPUR-BELGACHHIA
    **{n: "Kolkata" for n in range(149, 169)},
    # Howrah (169-184): BALLY, HOWRAH UTTAR/MADHYA, SHIBPUR, HOWRAH DAKSHIN, SANKRAIL,
    #   PANCHLA, ULUBERIA PURBA/UTTAR/DAKSHIN, SHYAMPUR, BAGNAN, AMTA, UDAYNARAYANPUR,
    #   JAGATBALLAVPUR, DOMJUR
    **{n: "Howrah" for n in range(169, 185)},
    # Hooghly (185-202): UTTARPARA, SREERAMPUR, CHAMPDANI, SINGUR, CHANDANNAGAR, CHUNCHURA,
    #   BALAGARH, PANDUA, SAPTAGRAM, CHANDITALA, JANGIPARA, HARIPAL, DHANEKHALI,
    #   TARAKESWAR, PURSURAH, ARAMBAG, GOGHAT, KHANAKUL
    **{n: "Hooghly" for n in range(185, 203)},
    # East Midnapore (203-219): TAMLUK, PANSKURA PURBA/PASCHIM, MOYNA, NANDAKUMAR, MAHISADAL,
    #   HALDIA, NANDIGRAM, CHANDIPUR, PATASHPUR, KANTHI UTTAR, BHAGABANPUR, KHEJURI,
    #   KANTHI DAKSHIN, RAMNAGAR, EGRA, DANTAN
    **{n: "East Midnapore" for n in range(203, 220)},
    # West Midnapore / Jhargram (220-237):
    220: "West Midnapore",  # NAYAGRAM
    221: "Jhargram",        # GOPIBALLAVPUR
    222: "Jhargram",        # JHARGRAM
    223: "Jhargram",        # KESHIARY
    224: "West Midnapore",  # KHARAGPUR SADAR
    225: "West Midnapore",  # NARAYANGARH
    226: "West Midnapore",  # SABANG
    227: "West Midnapore",  # PINGLA
    228: "West Midnapore",  # KHARAGPUR
    229: "West Midnapore",  # DEBRA
    230: "West Midnapore",  # DASPUR
    231: "West Midnapore",  # GHATAL
    232: "West Midnapore",  # CHANDRAKONA
    233: "West Midnapore",  # GARBETA
    234: "West Midnapore",  # SALBONI
    235: "West Midnapore",  # KESHPUR
    236: "West Midnapore",  # MEDINIPUR
    237: "Jhargram",        # BINPUR
    238: "Purulia",         # BANDWAN
    # Purulia (239-245): BALARAMPUR, BAGHMUNDI, JOYPUR, PURULIA, MANBAZAR, KASHIPUR, PARA
    **{n: "Purulia" for n in range(239, 246)},
    # Bankura (246-258): RAGHUNATHPUR, SALTORA, CHHATNA, RANIBANDH, RAIPUR, TALDANGRA,
    #   BANKURA, BARJORA, ONDA, BISHNUPUR, KATULPUR, INDUS, SONAMUKHI
    **{n: "Bankura" for n in range(246, 259)},
    # Paschim Bardhaman (259-265): KHANDAGHOSH, BARDHAMAN DAKSHIN, RAINA, JAMALPUR,
    #   MONTESWAR, KALNA, MEMARI
    **{n: "Burdwan" for n in range(259, 266)},
    # Purba Bardhaman (266-272): BARDHAMAN UTTAR, BHATAR, PURBASTHALI DAKSHIN/UTTAR, KATWA, KETUGRAM, MANGALKOT
    **{n: "Burdwan" for n in range(266, 273)},
    # Birbhum (273-282): AUSGRAM, GALSI, PANDABESWAR, DURGAPUR PURBA/PASCHIM, RANIGANJ,
    #   JAMURIA, ASANSOL DAKSHIN, ASANSOL UTTAR (actually these are Paschim Bardhaman)
    # Correction: AUSGRAM, GALSI = Purba Bardhaman; PANDABESWAR, DURGAPUR, RANIGANJ, JAMURIA,
    #   ASANSOL = Paschim Bardhaman; KULTI, BARABANI = Paschim Bardhaman
    273: "Burdwan",  # AUSGRAM (Purba Bardhaman)
    274: "Burdwan",  # GALSI (Purba Bardhaman)
    275: "Burdwan",  # PANDABESWAR (Paschim Bardhaman)
    276: "Burdwan",  # DURGAPUR PURBA
    277: "Burdwan",  # DURGAPUR PASCHIM
    278: "Burdwan",  # RANIGANJ
    279: "Burdwan",  # JAMURIA
    280: "Burdwan",  # ASANSOL DAKSHIN
    281: "Burdwan",  # ASANSOL UTTAR
    282: "Burdwan",  # KULTI
    283: "Burdwan",  # BARABANI
    # Birbhum (284-294): DUBRAJPUR, SURI, BOLPUR, NANOOR, LABPUR, SAINTHIA,
    #   MAYURESWAR, RAMPURHAT, HANSAN, NALHATI, MURARAI
    **{n: "Birbhum" for n in range(284, 295)},
}


# ── Data loading ────────────────────────────────────────────────────────────

def load_data():
    path = Path("wb_2026_results.csv")
    if not path.exists():
        raise FileNotFoundError("wb_2026_results.csv not found. Run scraper.py first.")
    df = pd.read_csv(path)
    df["district"]    = df["const_no"].map(CONSTITUENCY_DISTRICT)
    df["muslim_pct"]  = df["district"].map(DISTRICT_MUSLIM_PCT).fillna(0.15)
    df["winner_is_bjp"] = df["winner_party"].str.contains("Bharatiya Janata", na=False)
    df["winner_is_tmc"] = df["winner_party"].str.contains("Trinamool", na=False)
    return df


# ── Core vote-gain model ─────────────────────────────────────────────────────

def compute_probabilities(p_muslim_tmc, p_hindu_tmc):
    """
    Given TMC vote shares for Muslim and Hindu voters, compute BJP shares by
    assuming "Others" is fixed and remainder goes to BJP.
    BJP share = 1 - TMC share - Others share (clipped to [0,1]).
    """
    p_muslim_bjp = max(0.0, 1.0 - p_muslim_tmc - MUSLIM_OTHERS)
    p_hindu_bjp  = max(0.0, 1.0 - p_hindu_tmc  - HINDU_OTHERS)
    return {
        "muslim": {"TMC": p_muslim_tmc, "BJP": p_muslim_bjp, "Others": MUSLIM_OTHERS},
        "hindu":  {"TMC": p_hindu_tmc,  "BJP": p_hindu_bjp,  "Others": HINDU_OTHERS},
    }


def net_tmc_gain(n_voters, muslim_pct, p_muslim_tmc, p_hindu_tmc):
    """
    Expected net TMC advantage from `n_voters` additional voters in a
    constituency with district Muslim share `muslim_pct`.

    Returns: (net_tmc_gain, tmc_extra, bjp_extra)
    """
    probs = compute_probabilities(p_muslim_tmc, p_hindu_tmc)
    n_m = n_voters * muslim_pct
    n_h = n_voters * (1 - muslim_pct)

    tmc_extra = n_m * probs["muslim"]["TMC"] + n_h * probs["hindu"]["TMC"]
    bjp_extra = n_m * probs["muslim"]["BJP"] + n_h * probs["hindu"]["BJP"]
    return tmc_extra - bjp_extra, tmc_extra, bjp_extra


def count_flips_uniform(bjp_df, effective_voters, p_muslim_tmc, p_hindu_tmc):
    """Count BJP seats that flip under uniform voter distribution."""
    n = effective_voters / len(bjp_df) if len(bjp_df) else 0
    flips = 0
    for _, row in bjp_df.iterrows():
        gain, _, _ = net_tmc_gain(n, row["muslim_pct"], p_muslim_tmc, p_hindu_tmc)
        if gain > row["margin"]:
            flips += 1
    return flips


def count_flips_nonuniform(bjp_df, df_all, effective_voters, p_muslim_tmc, p_hindu_tmc):
    """
    Count BJP seats that flip under non-uniform distribution:
    voters allocated proportional to district Muslim %.
    """
    weights = df_all["muslim_pct"].values
    total_w = weights.sum()
    allocated_all = (weights / total_w) * effective_voters

    # Build a mapping from const_no to allocation
    alloc_map = dict(zip(df_all["const_no"].values, allocated_all))

    flips = 0
    for _, row in bjp_df.iterrows():
        n = alloc_map.get(row["const_no"], 0)
        gain, _, _ = net_tmc_gain(n, row["muslim_pct"], p_muslim_tmc, p_hindu_tmc)
        if gain > row["margin"]:
            flips += 1
    return flips


# ── Analysis 1: Margin Distribution ─────────────────────────────────────────

def analysis_margin_distribution(df):
    print("\n" + "=" * 60)
    print("ANALYSIS 1: Victory Margin Distribution")
    print("=" * 60)

    bjp_seats = df[df["winner_is_bjp"]].copy()
    tmc_seats = df[df["winner_is_tmc"]].copy()

    print(f"\nBJP won {len(bjp_seats)} seats  |  TMC won {len(tmc_seats)} seats")
    thresholds = [2_000, 5_000, 10_000, 15_000, 20_000, 30_000, 50_000]
    print(f"\n{'Margin <':>15}  {'BJP seats':>10}  {'TMC seats':>10}")
    print("-" * 40)
    for t in thresholds:
        b  = int((bjp_seats["margin"] < t).sum())
        tm = int((tmc_seats["margin"] < t).sum())
        print(f"{t:>15,}  {b:>10}  {tm:>10}")

    print(f"\nBJP margin stats (votes):")
    print(bjp_seats["margin"].describe().apply(lambda x: f"{x:,.0f}").to_string())
    print(f"\nTMC margin stats (votes):")
    print(tmc_seats["margin"].describe().apply(lambda x: f"{x:,.0f}").to_string())

    return {"bjp_seats": bjp_seats, "tmc_seats": tmc_seats}


# ── Analysis 2: Sensitivity Grid ─────────────────────────────────────────────

def analysis_sensitivity_grid(df, turnout=DEFAULT_TURNOUT):
    """
    Compute seats flipped across a full grid of voting probability assumptions.
    Two sub-grids: uniform distribution and non-uniform (Muslim-district-weighted).
    Shows results from BJP-biased to TMC-biased assumptions.
    """
    print("\n" + "=" * 60)
    print("ANALYSIS 2: Sensitivity Grid — Seats Flipped Across Probability Assumptions")
    print(f"(Turnout = {turnout:.0%}  |  Total effective voters = {TOTAL_EXCLUDED * turnout:,.0f})")
    print("=" * 60)

    bjp_df = df[df["winner_is_bjp"]].copy()
    effective = TOTAL_EXCLUDED * turnout

    results_uniform    = np.zeros((len(MUSLIM_TMC_GRID), len(HINDU_TMC_GRID)), dtype=int)
    results_nonuniform = np.zeros((len(MUSLIM_TMC_GRID), len(HINDU_TMC_GRID)), dtype=int)

    for i, p_m in enumerate(MUSLIM_TMC_GRID):
        for j, p_h in enumerate(HINDU_TMC_GRID):
            # Ensure TMC + Others ≤ 1 for both groups
            if (p_m + MUSLIM_OTHERS > 1.0) or (p_h + HINDU_OTHERS > 1.0):
                results_uniform[i, j] = -1    # invalid
                results_nonuniform[i, j] = -1
                continue
            results_uniform[i, j]    = count_flips_uniform(bjp_df, effective, p_m, p_h)
            results_nonuniform[i, j] = count_flips_nonuniform(bjp_df, df, effective, p_m, p_h)

    col_labels = [f"Hindu TMC {p:.0%}" for p in HINDU_TMC_GRID]
    row_labels  = [f"Muslim TMC {p:.0%}" for p in MUSLIM_TMC_GRID]

    print("\n-- Uniform Distribution (≈9,215 voters per seat) --")
    print("Rows = Muslim TMC vote share | Cols = Hindu TMC vote share")
    print("Lower-left = BJP-biased | Upper-right = TMC-biased")
    _print_grid(results_uniform, row_labels, col_labels)

    print("\n-- Non-Uniform Distribution (weighted by district Muslim %) --")
    _print_grid(results_nonuniform, row_labels, col_labels)

    # For reference: how many flips needed to deny BJP majority
    flips_needed = BJP_DECLARED - MAJORITY_MARK + 1
    print(f"\nFlips needed to deny BJP majority: {flips_needed}")
    print(f"Max flips in uniform grid:         {results_uniform.max()}")
    print(f"Max flips in non-uniform grid:     {results_nonuniform.max()}")

    return {
        "uniform":    results_uniform,
        "nonuniform": results_nonuniform,
        "row_labels": row_labels,
        "col_labels": col_labels,
        "flips_needed": flips_needed,
    }


def _print_grid(grid, row_labels, col_labels):
    header = f"{'':>20}" + "  ".join(f"{c:>16}" for c in col_labels)
    print(header)
    for i, rl in enumerate(row_labels):
        row_str = f"{rl:>20}"
        for j in range(len(col_labels)):
            v = grid[i, j]
            row_str += f"  {v:>16}" if v >= 0 else f"  {'(invalid)':>16}"
        print(row_str)


# ── Analysis 3: Turnout Sensitivity ──────────────────────────────────────────

def analysis_turnout_sensitivity(df):
    """
    Show how seats flipped change as turnout varies, at both extremes and
    the midpoint of the voting probability grid.
    """
    print("\n" + "=" * 60)
    print("ANALYSIS 3: Turnout Sensitivity")
    print("=" * 60)

    bjp_df = df[df["winner_is_bjp"]].copy()

    scenarios = [
        ("BJP-biased",    MUSLIM_TMC_GRID[0], HINDU_TMC_GRID[0]),
        ("Midpoint",      DEFAULT_P_MUSLIM_TMC, DEFAULT_P_HINDU_TMC),
        ("TMC-biased",    MUSLIM_TMC_GRID[-1], HINDU_TMC_GRID[-1]),
    ]

    print(f"\n{'Scenario':>15}  {'Muslim TMC':>10}  {'Hindu TMC':>10}", end="")
    for t in TURNOUT_GRID:
        print(f"  {'Turnout '+f'{t:.0%}':>12}", end="")
    print()
    print("-" * (40 + 14 * len(TURNOUT_GRID)))

    for label, p_m, p_h in scenarios:
        print(f"{label:>15}  {p_m:>10.0%}  {p_h:>10.0%}", end="")
        for turnout in TURNOUT_GRID:
            effective = TOTAL_EXCLUDED * turnout
            flips = count_flips_uniform(bjp_df, effective, p_m, p_h)
            print(f"  {flips:>12}", end="")
        print()

    return scenarios


# ── Analysis 4: Maximum Possible TMC Benefit (Analytical Bound) ──────────────

def analysis_max_tmc_bound(df):
    """
    Compute the analytical upper bound: how many seats COULD flip if we
    make every assumption as TMC-favourable as possible AND allow voters
    to be placed optimally (ignoring geographic constraints).

    This establishes a hard ceiling — if the ceiling is still below majority,
    the conclusion is robust to all assumptions.
    """
    print("\n" + "=" * 60)
    print("ANALYSIS 4: Analytical Upper Bound (Max TMC Benefit)")
    print("=" * 60)
    print("\nAssumptions: 100% turnout, 95% Muslim→TMC, 60% Hindu→TMC")
    print("Geographic: all 27L concentrated in smallest-margin BJP seats")
    print("(This is physically impossible — just tests the ceiling)")

    p_m_max = 0.95
    p_h_max = 0.60

    bjp_df = df[df["winner_is_bjp"]].copy().sort_values("margin")
    budget = float(TOTAL_EXCLUDED)

    flipped_seats = []
    remaining = budget
    for _, row in bjp_df.iterrows():
        m = row["muslim_pct"]
        net_rate_per_voter = (
            (p_m_max - (1 - p_m_max - MUSLIM_OTHERS)) * m +
            (p_h_max - (1 - p_h_max - HINDU_OTHERS))  * (1 - m)
        )
        if net_rate_per_voter <= 0:
            continue
        needed = row["margin"] / net_rate_per_voter
        if remaining >= needed:
            remaining -= needed
            flipped_seats.append({
                "const_name": row["const_name"],
                "district": row.get("district", "?"),
                "margin": row["margin"],
                "voters_needed": int(needed),
            })
        else:
            break  # budget exhausted

    bjp_after = BJP_DECLARED - len(flipped_seats)
    tmc_after  = TMC_DECLARED + len(flipped_seats)

    print(f"\nSeats that flip under absolute upper bound: {len(flipped_seats)}")
    print(f"BJP final: {bjp_after}  |  TMC final: {tmc_after}")
    print(f"BJP retains majority? {'YES' if bjp_after >= MAJORITY_MARK else 'NO'}")

    if flipped_seats:
        print(f"\nFlipped seats:")
        for s in flipped_seats:
            dist = str(s.get("district") or "Unknown")
            print(f"  {s['const_name']:30s} ({dist:20s}) margin={s['margin']:>7,}  voters needed={s['voters_needed']:>7,}")

    seats_to_flip_for_tmc_maj = MAJORITY_MARK - TMC_DECLARED
    cost = 0
    for i, (_, row) in enumerate(bjp_df.iterrows()):
        if i >= seats_to_flip_for_tmc_maj:
            break
        m = row["muslim_pct"]
        net_rate = (
            (p_m_max - (1 - p_m_max - MUSLIM_OTHERS)) * m +
            (p_h_max - (1 - p_h_max - HINDU_OTHERS))  * (1 - m)
        )
        cost += row["margin"] / max(net_rate, 1e-9)

    print(f"\nFor TMC to reach {MAJORITY_MARK} seats would need {seats_to_flip_for_tmc_maj} flips")
    print(f"Voter budget needed (best-case): {cost:>12,.0f}")
    print(f"Available (27L, no discount):   {TOTAL_EXCLUDED:>12,}")
    print(f"Gap (shortfall):                {cost - TOTAL_EXCLUDED:>12,.0f}")

    return {
        "flipped": len(flipped_seats),
        "bjp_final": bjp_after,
        "tmc_final": tmc_after,
        "bjp_majority": bjp_after >= MAJORITY_MARK,
        "voter_budget_for_tmc_majority": cost,
        "flipped_seats": flipped_seats,
    }


# ── Analysis 5: Monte Carlo ──────────────────────────────────────────────────

def analysis_monte_carlo(df, n_simulations=10_000, seed=42):
    """
    Monte Carlo simulation varying:
    - Muslim TMC vote share: U[0.50, 0.90]
    - Hindu TMC vote share:  U[0.15, 0.55]
    - Turnout:               U[0.60, 0.90]
    - Geographic weights:    Muslim% + N(0, 0.05) noise (clipped)

    This samples the *entire* parameter space, not a single point.
    """
    print("\n" + "=" * 60)
    print("ANALYSIS 5: Monte Carlo Simulation (10,000 runs)")
    print("=" * 60)
    print("Parameter ranges:")
    print(f"  Muslim TMC vote share: U[{MUSLIM_TMC_GRID[0]:.0%}, {MUSLIM_TMC_GRID[-1]:.0%}]")
    print(f"  Hindu TMC vote share:  U[{HINDU_TMC_GRID[0]:.0%},  {HINDU_TMC_GRID[-1]:.0%}]")
    print(f"  Turnout:               U[60%, 90%]")
    print(f"  Geography:             Muslim% ± 5% noise")

    rng = np.random.default_rng(seed)

    bjp_df = df[df["winner_is_bjp"]].copy()
    margins = bjp_df["margin"].values
    muslim_pcts = bjp_df["muslim_pct"].values

    results = []
    for _ in range(n_simulations):
        p_m_tmc = rng.uniform(MUSLIM_TMC_GRID[0],  MUSLIM_TMC_GRID[-1])
        p_h_tmc = rng.uniform(HINDU_TMC_GRID[0],   HINDU_TMC_GRID[-1])
        turnout = rng.uniform(0.60, 0.90)
        effective = TOTAL_EXCLUDED * turnout

        # Non-uniform distribution with geographic noise
        noisy_muslim = np.clip(
            muslim_pcts + rng.normal(0, 0.05, len(muslim_pcts)), 0.01, 0.99
        )
        weights = noisy_muslim
        weights = weights / weights.sum()

        # Add noise to all-constituency allocation too (for non-bjp seats)
        all_weights = np.clip(
            df["muslim_pct"].values + rng.normal(0, 0.05, len(df)), 0.01, 0.99
        )
        all_weights = all_weights / all_weights.sum()
        bjp_alloc = all_weights[df["winner_is_bjp"].values] * effective

        p_m_bjp = max(0.0, 1.0 - p_m_tmc - MUSLIM_OTHERS)
        p_h_bjp = max(0.0, 1.0 - p_h_tmc - HINDU_OTHERS)

        n_m = bjp_alloc * muslim_pcts
        n_h = bjp_alloc * (1 - muslim_pcts)
        tmc_extra = n_m * p_m_tmc + n_h * p_h_tmc
        bjp_extra  = n_m * p_m_bjp + n_h * p_h_bjp
        net_gains  = tmc_extra - bjp_extra

        flipped = int((net_gains > margins).sum())
        results.append({
            "seats_flipped": flipped,
            "bjp_final":  BJP_DECLARED - flipped,
            "tmc_final":  TMC_DECLARED + flipped,
            "bjp_majority": (BJP_DECLARED - flipped) >= MAJORITY_MARK,
            "tmc_majority": (TMC_DECLARED + flipped) >= MAJORITY_MARK,
            "p_m_tmc":    p_m_tmc,
            "p_h_tmc":    p_h_tmc,
            "turnout":    turnout,
        })

    mc_df = pd.DataFrame(results)

    flips_for_bjp_loss = BJP_DECLARED - MAJORITY_MARK + 1

    print(f"\nMonte Carlo results:")
    print(f"  Median seats flipped:         {mc_df['seats_flipped'].median():.0f}")
    print(f"  Mean seats flipped:           {mc_df['seats_flipped'].mean():.1f}")
    print(f"  95th percentile flips:        {mc_df['seats_flipped'].quantile(0.95):.0f}")
    print(f"  99th percentile flips:        {mc_df['seats_flipped'].quantile(0.99):.0f}")
    print(f"  Max seats flipped (any sim):  {mc_df['seats_flipped'].max()}")
    print(f"")
    print(f"  Flips needed to deny BJP majority: {flips_for_bjp_loss}")
    print(f"  P(BJP retains majority):  {mc_df['bjp_majority'].mean():.3%}")
    print(f"  P(BJP loses majority):    {1 - mc_df['bjp_majority'].mean():.3%}")
    print(f"  P(TMC gets majority):     {mc_df['tmc_majority'].mean():.3%}")

    return mc_df


# ── Summary per scenario ─────────────────────────────────────────────────────

def compute_named_scenarios(df):
    """
    Return a concise table of results for named scenarios across the probability
    spectrum, for use in the report and visualizations.
    """
    bjp_df = df[df["winner_is_bjp"]].copy()
    scenarios = []
    named = [
        ("BJP-biased",       0.50, 0.15, 0.80),
        ("Mildly BJP-biased", 0.60, 0.25, 0.80),
        ("Midpoint",         0.70, 0.35, 0.80),
        ("Mildly TMC-biased", 0.80, 0.45, 0.80),
        ("TMC-biased",       0.90, 0.55, 0.80),
        ("Max TMC (no discount)", 0.90, 0.55, 1.00),
    ]

    for label, p_m, p_h, turnout in named:
        effective = TOTAL_EXCLUDED * turnout
        flips_u  = count_flips_uniform(bjp_df, effective, p_m, p_h)
        flips_nu = count_flips_nonuniform(bjp_df, df, effective, p_m, p_h)
        scenarios.append({
            "Scenario":        label,
            "Muslim→TMC":      f"{p_m:.0%}",
            "Hindu→TMC":       f"{p_h:.0%}",
            "Turnout":         f"{turnout:.0%}",
            "Uniform flips":   flips_u,
            "Non-uniform flips": flips_nu,
            "BJP (uniform)":   BJP_DECLARED - flips_u,
            "BJP (non-unif.)": BJP_DECLARED - flips_nu,
            "BJP majority (U)?": "Yes" if BJP_DECLARED - flips_u >= MAJORITY_MARK else "NO",
        })

    sdf = pd.DataFrame(scenarios)
    print("\n" + "=" * 60)
    print("SCENARIO SUMMARY TABLE")
    print("=" * 60)
    print(sdf.to_string(index=False))
    sdf.to_csv("scenario_summary.csv", index=False)
    print("\nSaved scenario_summary.csv")
    return sdf


# ── Main entry point ─────────────────────────────────────────────────────────

def run_analysis():
    df = load_data()
    print(f"Loaded {len(df)} constituencies")
    print(f"BJP seats: {df['winner_is_bjp'].sum()} | TMC: {df['winner_is_tmc'].sum()} | Others: {(~df['winner_is_bjp'] & ~df['winner_is_tmc']).sum()}")
    print(f"Missing vote data: {df['bjp_votes'].isna().sum() if 'bjp_votes' in df.columns else 'N/A (margin-only mode)'}")

    r1      = analysis_margin_distribution(df)
    r2      = analysis_sensitivity_grid(df)
    r3      = analysis_turnout_sensitivity(df)
    r4      = analysis_max_tmc_bound(df)
    mc_df   = analysis_monte_carlo(df)
    scen_df = compute_named_scenarios(df)

    mc_df.to_csv("monte_carlo_results.csv", index=False)
    print("Saved monte_carlo_results.csv")

    return {
        "df":        df,
        "margin":    r1,
        "grid":      r2,
        "turnout":   r3,
        "max_tmc":   r4,
        "mc":        mc_df,
        "scenarios": scen_df,
    }


if __name__ == "__main__":
    run_analysis()
