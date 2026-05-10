"""
election_analysis — generic Indian election analysis package.

Exports all dataclasses and the four main classes for convenience.
"""
from .models import (
    ConstituencyResult,
    ElectionConfig,
    VoterExclusionConfig,
    SensitivityGrid,
    MonteCarloSummary,
    UpperBoundResult,
    AnalysisResults,
)
from .scraper import ECIScraper
from .analyzer import VoterExclusionAnalyzer
from .visualizer import ElectionVisualizer
from .reporter import ReportGenerator

__all__ = [
    "ConstituencyResult",
    "ElectionConfig",
    "VoterExclusionConfig",
    "SensitivityGrid",
    "MonteCarloSummary",
    "UpperBoundResult",
    "AnalysisResults",
    "ECIScraper",
    "VoterExclusionAnalyzer",
    "ElectionVisualizer",
    "ReportGenerator",
]
