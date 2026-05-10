"""
Data models for election analysis.
All structures use @dataclass for clean, type-safe data representation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import numpy as np
import pandas as pd


@dataclass
class ConstituencyResult:
    const_no: int
    const_name: str
    winner_name: str
    winner_party: str
    runner_name: str
    runner_party: str
    margin: Optional[int]
    status: str
    party_a_votes: int = 0      # e.g. BJP votes
    party_b_votes: int = 0      # e.g. TMC votes
    total_votes: int = 0
    district: str = ""
    minority_pct: float = 0.15  # district minority group % (e.g. Muslim)


@dataclass
class ElectionConfig:
    state_name: str             # "West Bengal"
    state_code: str             # ECI state code "S25"
    year: int                   # 2026
    total_seats: int            # 294
    majority_mark: int          # 148
    statewise_pages: int        # 15
    skip_seats: frozenset       # {144} — seats with no result yet
    party_a_name: str           # substring to match in winner_party for party A, e.g. "Bharatiya Janata"
    party_a_label: str          # "BJP"
    party_b_name: str           # "Trinamool"
    party_b_label: str          # "TMC"
    party_aliases: dict         # {"bharatiya janata party": "BJP", ...} for candidateswise parsing
    constituency_district: dict # {const_no: district_name}
    district_minority_pct: dict # {district_name: float} e.g. Muslim %
    wayback_timestamp: str      # "20260505010000"
    default_minority_pct: float = 0.15   # fallback when district unknown
    minority_group_name: str = "Muslim"
    majority_group_name: str = "Hindu"


@dataclass
class VoterExclusionConfig:
    total_excluded: int         # 2_700_000
    minority_share: float       # 0.65
    majority_share: float       # 0.35
    default_turnout: float      # 0.80
    minority_b_grid: list       # [0.50, 0.60, 0.70, 0.80, 0.90] minority → party_b vote shares
    majority_b_grid: list       # [0.15, 0.25, 0.35, 0.45, 0.55]
    turnout_grid: list          # [0.60, 0.70, 0.80, 0.90, 1.00]
    minority_others: float = 0.08
    majority_others: float = 0.10
    mc_simulations: int = 10_000
    mc_seed: int = 42
    # Named scenarios for the comparison chart
    named_scenarios: list = field(default_factory=lambda: [
        ("BJP-biased",        0.50, 0.15, 0.80),
        ("Mildly BJP-biased", 0.60, 0.25, 0.80),
        ("Midpoint",          0.70, 0.35, 0.80),
        ("Mildly TMC-biased", 0.80, 0.45, 0.80),
        ("TMC-biased",        0.90, 0.55, 0.80),
        ("Max (no discount)", 0.90, 0.55, 1.00),
    ])


@dataclass
class SensitivityGrid:
    uniform: np.ndarray           # shape (len(minority_b_grid), len(majority_b_grid))
    nonuniform: np.ndarray
    row_labels: list              # e.g. ["Muslim→TMC 50%", ...]
    col_labels: list              # e.g. ["Hindu→TMC 15%", ...]
    flips_needed: int


@dataclass
class MonteCarloSummary:
    n_simulations: int
    median_flips: float
    mean_flips: float
    p95_flips: int
    p99_flips: int
    max_flips: int
    flips_needed: int
    p_party_a_majority: float
    p_party_b_majority: float
    raw: pd.DataFrame  # full sim results


@dataclass
class UpperBoundResult:
    p_minority_b: float    # 0.95
    p_majority_b: float    # 0.60
    seats_flipped: int
    party_a_final: int
    party_b_final: int
    party_a_majority: bool
    voter_budget_for_party_b_majority: float
    seats_needed_for_party_b_majority: int
    flipped_seats: list  # list of dicts with const_name, district, margin, voters_needed


@dataclass
class AnalysisResults:
    election: ElectionConfig
    exclusion: VoterExclusionConfig
    data: pd.DataFrame          # full constituency data with derived columns
    sensitivity: SensitivityGrid
    scenarios: pd.DataFrame     # named scenario summary
    upper_bound: UpperBoundResult
    monte_carlo: MonteCarloSummary
