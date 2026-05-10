"""
West Bengal 2026 Assembly Election — specific configuration instances.

WB_2026_ELECTION  : ElectionConfig for the WB 2026 state assembly election.
WB_2026_SIR_EXCLUSION : VoterExclusionConfig for the SIR-pending voter analysis.

Party aliases, constituency-district mapping, and district Muslim %
are copied verbatim from the original scraper.py / analyzer.py.
"""
from election_analysis.models import ElectionConfig, VoterExclusionConfig

# ---------------------------------------------------------------------------
# Party alias table (from scraper.py PARTY_ALIASES)
# ---------------------------------------------------------------------------
_PARTY_ALIASES = {
    "bharatiya janata party": "BJP",
    "bjp":                    "BJP",
    "all india trinamool congress": "TMC",
    "aitc":                   "TMC",
    "trinamool congress":     "TMC",
    "indian national congress": "INC",
    "inc":                    "INC",
    "communist party of india (marxist)": "CPI(M)",
    "cpi(m)":                 "CPI(M)",
    "cpi-m":                  "CPI(M)",
    "independent":            "IND",
    "none of the above":      "NOTA",
    "aam janata unnayan party": "AJUP",
    "all india secular front": "AISF",
    "socialist unity centre of india (communist)": "SUCI(C)",
}

# ---------------------------------------------------------------------------
# District → approximate Muslim population share (Census 2011)
# (from analyzer.py DISTRICT_MUSLIM_PCT)
# ---------------------------------------------------------------------------
_DISTRICT_MUSLIM_PCT = {
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

# ---------------------------------------------------------------------------
# Constituency number → district mapping
# (from analyzer.py CONSTITUENCY_DISTRICT, copied verbatim)
# ---------------------------------------------------------------------------
_CONSTITUENCY_DISTRICT = {
    # Cooch Behar (1-7)
    **{n: "Cooch Behar" for n in range(1, 8)},
    # Alipurduar (8-14)
    **{n: "Alipurduar" for n in range(8, 15)},
    # Jalpaiguri (15-21)
    **{n: "Jalpaiguri" for n in range(15, 22)},
    # Kalimpong (22)
    22: "Kalimpong",
    # Darjeeling (23-27)
    **{n: "Darjeeling" for n in range(23, 28)},
    # North Dinajpur (28-36)
    **{n: "North Dinajpur" for n in range(28, 37)},
    # South Dinajpur (37-42)
    **{n: "South Dinajpur" for n in range(37, 43)},
    # Malda (43-54)
    **{n: "Malda" for n in range(43, 55)},
    # Murshidabad (55-76)
    **{n: "Murshidabad" for n in range(55, 77)},
    # Nadia (77-93)
    **{n: "Nadia" for n in range(77, 94)},
    # North 24 Parganas (94-126)
    **{n: "North 24 Parganas" for n in range(94, 127)},
    # South 24 Parganas (127-148)
    127: "South 24 Parganas",   # GOSABA
    128: "South 24 Parganas",   # BASANTI
    129: "South 24 Parganas",   # KULTALI
    130: "South 24 Parganas",   # PATHARPRATIMA
    131: "South 24 Parganas",   # KAKDWIP
    132: "South 24 Parganas",   # SAGAR
    133: "South 24 Parganas",   # KULPI
    134: "South 24 Parganas",   # RAIDIGHI
    135: "South 24 Parganas",   # MANDIRBAZAR
    136: "South 24 Parganas",   # JAYNAGAR
    137: "South 24 Parganas",   # BARUIPUR PURBA
    138: "South 24 Parganas",   # CANNING PASCHIM
    139: "South 24 Parganas",   # CANNING PURBA
    140: "South 24 Parganas",   # BARUIPUR PASCHIM
    141: "South 24 Parganas",   # MAGRAHAT PURBA
    142: "South 24 Parganas",   # MAGRAHAT PASCHIM
    143: "South 24 Parganas",   # DIAMOND HARBOUR
    144: "South 24 Parganas",   # FALTA (repoll, excluded from analysis)
    145: "South 24 Parganas",   # SATGACHHIA
    146: "South 24 Parganas",   # BISHNUPUR
    147: "South 24 Parganas",   # SONARPUR DAKSHIN
    148: "South 24 Parganas",   # BHANGAR
    # Kolkata (149-168)
    **{n: "Kolkata" for n in range(149, 169)},
    # Howrah (169-184)
    **{n: "Howrah" for n in range(169, 185)},
    # Hooghly (185-202)
    **{n: "Hooghly" for n in range(185, 203)},
    # East Midnapore (203-219)
    **{n: "East Midnapore" for n in range(203, 220)},
    # West Midnapore / Jhargram (220-237)
    220: "West Midnapore",   # NAYAGRAM
    221: "Jhargram",         # GOPIBALLAVPUR
    222: "Jhargram",         # JHARGRAM
    223: "Jhargram",         # KESHIARY
    224: "West Midnapore",   # KHARAGPUR SADAR
    225: "West Midnapore",   # NARAYANGARH
    226: "West Midnapore",   # SABANG
    227: "West Midnapore",   # PINGLA
    228: "West Midnapore",   # KHARAGPUR
    229: "West Midnapore",   # DEBRA
    230: "West Midnapore",   # DASPUR
    231: "West Midnapore",   # GHATAL
    232: "West Midnapore",   # CHANDRAKONA
    233: "West Midnapore",   # GARBETA
    234: "West Midnapore",   # SALBONI
    235: "West Midnapore",   # KESHPUR
    236: "West Midnapore",   # MEDINIPUR
    237: "Jhargram",         # BINPUR
    238: "Purulia",          # BANDWAN
    # Purulia (239-245)
    **{n: "Purulia" for n in range(239, 246)},
    # Bankura (246-258)
    **{n: "Bankura" for n in range(246, 259)},
    # Paschim Bardhaman / Purba Bardhaman (259-283)
    **{n: "Burdwan" for n in range(259, 266)},
    **{n: "Burdwan" for n in range(266, 273)},
    273: "Burdwan",   # AUSGRAM
    274: "Burdwan",   # GALSI
    275: "Burdwan",   # PANDABESWAR
    276: "Burdwan",   # DURGAPUR PURBA
    277: "Burdwan",   # DURGAPUR PASCHIM
    278: "Burdwan",   # RANIGANJ
    279: "Burdwan",   # JAMURIA
    280: "Burdwan",   # ASANSOL DAKSHIN
    281: "Burdwan",   # ASANSOL UTTAR
    282: "Burdwan",   # KULTI
    283: "Burdwan",   # BARABANI
    # Birbhum (284-294)
    **{n: "Birbhum" for n in range(284, 295)},
}

# ---------------------------------------------------------------------------
# ElectionConfig instance for WB 2026
# ---------------------------------------------------------------------------
WB_2026_ELECTION = ElectionConfig(
    state_name="West Bengal",
    state_code="S25",
    year=2026,
    total_seats=294,
    majority_mark=148,
    statewise_pages=15,
    skip_seats=frozenset({144}),           # Falta — repoll on May 21
    party_a_name="Bharatiya Janata",
    party_a_label="BJP",
    party_b_name="Trinamool",
    party_b_label="TMC",
    party_aliases=_PARTY_ALIASES,
    constituency_district=_CONSTITUENCY_DISTRICT,
    district_minority_pct=_DISTRICT_MUSLIM_PCT,
    wayback_timestamp="20260505010000",
    default_minority_pct=0.15,
    minority_group_name="Muslim",
    majority_group_name="Hindu",
)

# ---------------------------------------------------------------------------
# VoterExclusionConfig instance for WB 2026 SIR analysis
# ---------------------------------------------------------------------------
WB_2026_SIR_EXCLUSION = VoterExclusionConfig(
    total_excluded=2_700_000,        # 27 lakh pending SIR exclusions
    minority_share=0.65,             # ~65% Muslim
    majority_share=0.35,             # ~35% Hindu
    default_turnout=0.80,
    minority_b_grid=[0.50, 0.60, 0.70, 0.80, 0.90],
    majority_b_grid=[0.15, 0.25, 0.35, 0.45, 0.55],
    turnout_grid=[0.60, 0.70, 0.80, 0.90, 1.00],
    minority_others=0.08,
    majority_others=0.10,
    mc_simulations=10_000,
    mc_seed=42,
    named_scenarios=[
        ("BJP-biased",        0.50, 0.15, 0.80),
        ("Mildly BJP-biased", 0.60, 0.25, 0.80),
        ("Midpoint",          0.70, 0.35, 0.80),
        ("Mildly TMC-biased", 0.80, 0.45, 0.80),
        ("TMC-biased",        0.90, 0.55, 0.80),
        ("Max (no discount)", 0.90, 0.55, 1.00),
    ],
)
