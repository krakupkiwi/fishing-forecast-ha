"""Tide derivation + score — Phase 2 (not implemented). See docs/scoring.md §5.

    derive(samples: list[TideSample], cfg) -> list[TideState]
        robust local-extrema detection (min prominence + min spacing); returns
        direction=None when it cannot decide (micro-tidal / smooth model output).
    score(state: TideState, cfg) -> float | None

Kept provider-independent so an EOT20 / official source can replace Open-Meteo's
sea_level_height_msl later (Phase 6).
"""

from __future__ import annotations

from ..models import ScoringConfig, TideSample, TideState


def derive(samples: list[TideSample], cfg: ScoringConfig) -> list[TideState]:
    raise NotImplementedError("Phase 2")


def score(state: TideState, cfg: ScoringConfig) -> float | None:
    raise NotImplementedError("Phase 2")
