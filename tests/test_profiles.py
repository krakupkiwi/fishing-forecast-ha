"""Fishing-style profiles (docs/fishing-knowledge.md, docs/scoring.md §14)."""

from __future__ import annotations

from datetime import timedelta

import pytest

from custom_components.fishing_forecast.entry_data import scoring_from_entry
from custom_components.fishing_forecast.models import AstroDay, Component
from custom_components.fishing_forecast.profiles import (
    DEFAULT_PROFILE,
    PROFILES,
    profile_labels,
    scoring_config_for,
)
from custom_components.fishing_forecast.scoring.sunlight import score as sun_score
from custom_components.fishing_forecast.scoring.swell import score as swell_score
from tests.conftest import utc


def test_every_profile_builds_and_normalises() -> None:
    for name in PROFILES:
        cfg = scoring_config_for(name)
        assert sum(cfg.full_weights.values()) == pytest.approx(1.0)
        assert sum(cfg.outlook_weights.values()) == pytest.approx(1.0)
        assert cfg.swell["height_m_curve"]


def test_unknown_profile_falls_back() -> None:
    fallback = scoring_config_for(DEFAULT_PROFILE)
    assert scoring_config_for("nope").full_weights == fallback.full_weights


def test_labels_cover_all_profiles() -> None:
    assert set(profile_labels()) == set(PROFILES)


def test_big_swell_scores_higher_for_snapper_than_calm_water(mindarie) -> None:
    calm = scoring_config_for("calm_water")
    rock = scoring_config_for("rock_snapper")
    # a 2.5 m groundswell: junk for whiting, prime for rock-wall snapper
    rock_big = swell_score(2.5, 13, 245, mindarie, rock)
    calm_big = swell_score(2.5, 13, 245, mindarie, calm)
    assert rock_big > calm_big + 30
    # and small swell is the other way round
    assert swell_score(0.5, 12, 245, mindarie, calm) > swell_score(0.5, 12, 245, mindarie, rock)


def test_snapper_weights_lean_on_swell_and_pressure() -> None:
    rock = scoring_config_for("rock_snapper")
    calm = scoring_config_for("calm_water")
    assert rock.full_weights[Component.SWELL] > calm.full_weights[Component.SWELL]
    assert rock.full_weights[Component.PRESSURE] > calm.full_weights[Component.PRESSURE]


def test_night_bonus_for_marina_mulloway() -> None:
    day = AstroDay(
        date_local=utc(2026, 9, 13).date(),
        sunrise_utc=utc(2026, 9, 12, 22, 20),
        sunset_utc=utc(2026, 9, 13, 10, 5),
    )
    midnight = day.sunset_utc + timedelta(hours=4)  # deep night
    calm_cfg = scoring_config_for("calm_water")
    calm = sun_score(midnight, day, calm_cfg)
    marina = sun_score(midnight, day, scoring_config_for("estuary_marina"))
    assert calm == pytest.approx(float(calm_cfg.sun["base"]))  # no night bonus
    assert marina and marina > 70  # night_score kicks in


def test_scoring_from_entry_reads_profile_from_data_or_options() -> None:
    from_data = scoring_from_entry({}, {"profile": "rock_snapper"})
    from_opts = scoring_from_entry({"profile": "rock_snapper"}, {"profile": "calm_water"})
    assert from_data.full_weights == scoring_config_for("rock_snapper").full_weights
    # options win over data
    assert from_opts.full_weights == scoring_config_for("rock_snapper").full_weights
