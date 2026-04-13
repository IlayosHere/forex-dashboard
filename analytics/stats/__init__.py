"""
analytics/stats — Univariate statistical analysis for enriched trading signals.

Provides functions to bucket signals by parameter value, compute win rates
with confidence intervals, and run significance tests (chi-squared,
point-biserial) to identify which parameters correlate with winning trades.
"""
from __future__ import annotations
