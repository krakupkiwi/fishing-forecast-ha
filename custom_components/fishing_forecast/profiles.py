"""Fishing-style presets that reshape the scoring for what you actually target.

The V1 defaults suit calm-water bait fishing (herring, whiting, squid). Perth
land-based knowledge (see ``docs/fishing-knowledge.md``) says tailor, salmon and
pink snapper off the rock walls and beaches want the rough, post-front, dirty-water
conditions the generic curve penalises. Each preset here is a partial override
applied on top of :func:`const.default_scoring_config`.
"""

from __future__ import annotations

import copy
from dataclasses import replace
from typing import Any

from .const import default_scoring_config
from .models import Component, ScoringConfig

DEFAULT_PROFILE = "beach_sport"

# label + partial overrides. Weight dicts are merged key-by-key then re-normalised;
# component sub-tables (swell/wind/tide/sun) are shallow-merged.
PROFILES: dict[str, dict[str, Any]] = {
    "calm_water": {
        "label": "Calm water (herring, whiting, squid, garfish)",
        # The V1 defaults already model this style; nudge tide toward the run-in.
        "tide": {"early_rise_score": 75},
    },
    "beach_sport": {
        "label": "Beach sport (tailor, Australian salmon)",
        "full_weights": {
            Component.WIND: 0.24,
            Component.SWELL: 0.20,
            Component.TIDE: 0.13,
            Component.SOLUNAR: 0.12,
            Component.SUN: 0.16,
            Component.RAIN: 0.04,
            Component.PRESSURE: 0.11,
        },
        "outlook_weights": {
            Component.WIND: 0.44,
            Component.SOLUNAR: 0.16,
            Component.SUN: 0.20,
            Component.RAIN: 0.05,
            Component.PRESSURE: 0.15,
        },
        "swell": {
            "height_m_curve": [
                (0.0, 55),
                (0.4, 75),
                (0.8, 92),
                (1.2, 100),
                (2.5, 100),
                (3.0, 85),
                (3.5, 55),
                (4.5, 12),
                (5.5, 0),
            ],
            "ideal_swell_min_m": 1.0,
            "ideal_swell_max_m": 3.0,
        },
        "wind": {
            # onshore is only mildly bad; a NW blow before a front fires tailor up
            "direction_multiplier": {"0": 1.0, "45": 0.95, "90": 0.85, "135": 0.75, "180": 0.6},
        },
        "sun": {"night_score": 55},
    },
    "rock_snapper": {
        "label": "Rock wall / groyne (pink snapper, mulloway, after storms)",
        "full_weights": {
            Component.WIND: 0.18,
            Component.SWELL: 0.24,
            Component.TIDE: 0.15,
            Component.SOLUNAR: 0.12,
            Component.SUN: 0.13,
            Component.RAIN: 0.03,
            Component.PRESSURE: 0.15,
        },
        "outlook_weights": {
            Component.WIND: 0.40,
            Component.SOLUNAR: 0.16,
            Component.SUN: 0.16,
            Component.RAIN: 0.04,
            Component.PRESSURE: 0.24,
        },
        "swell": {
            "height_m_curve": [
                (0.0, 45),
                (0.5, 62),
                (1.0, 80),
                (1.5, 95),
                (2.0, 100),
                (3.0, 100),
                (3.5, 90),
                (4.0, 60),
                (5.0, 15),
                (6.0, 0),
            ],
            "period_clamp": [0.9, 1.15],  # short-period storm swell is fine here
            "ideal_swell_min_m": 1.5,
            "ideal_swell_max_m": 3.5,
        },
        "wind": {
            "direction_multiplier": {"0": 1.0, "45": 1.0, "90": 0.9, "135": 0.85, "180": 0.8},
        },
        "sun": {"night_score": 65},
    },
    "estuary_marina": {
        "label": "Inside the marina / estuary (mulloway, bream — sheltered)",
        "full_weights": {
            Component.WIND: 0.08,
            Component.SWELL: 0.05,
            Component.TIDE: 0.30,
            Component.SOLUNAR: 0.15,
            Component.SUN: 0.19,
            Component.RAIN: 0.05,
            Component.PRESSURE: 0.18,
        },
        "outlook_weights": {
            Component.WIND: 0.20,
            Component.SOLUNAR: 0.24,
            Component.SUN: 0.28,
            Component.RAIN: 0.08,
            Component.PRESSURE: 0.20,
        },
        "wind": {
            "direction_multiplier": {"0": 1.0, "45": 1.0, "90": 0.97, "135": 0.93, "180": 0.9},
        },
        "tide": {
            "relative_to_high_curve": [
                (-3.0, 82),
                (-2.0, 96),
                (-1.0, 100),
                (0.0, 90),
                (1.0, 68),
                (2.5, 45),
            ],
            "early_rise_score": 80,
            "generic_rising_score": 72,
        },
        "sun": {"night_score": 78},
    },
}


def profile_labels() -> dict[str, str]:
    return {key: spec["label"] for key, spec in PROFILES.items()}


def _renormalise(weights: dict[Component, float]) -> dict[Component, float]:
    total = sum(weights.values())
    return {c: w / total for c, w in weights.items()} if total > 0 else weights


def scoring_config_for(profile: str | None) -> ScoringConfig:
    """Return a :class:`ScoringConfig` for ``profile`` (falls back to the default)."""

    base = default_scoring_config()
    spec = PROFILES.get(profile or DEFAULT_PROFILE) or PROFILES[DEFAULT_PROFILE]

    kwargs: dict[str, Any] = {}
    for key, current in (
        ("full_weights", base.full_weights),
        ("outlook_weights", base.outlook_weights),
    ):
        if key in spec:
            kwargs[key] = _renormalise({**current, **spec[key]})
    for table in ("wind", "swell", "tide", "solunar", "sun", "rain", "pressure"):
        if table in spec:
            merged = copy.deepcopy(getattr(base, table))
            merged.update(spec[table])
            kwargs[table] = merged

    return replace(base, **kwargs)
