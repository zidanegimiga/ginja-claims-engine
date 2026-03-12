"""
Unit tests for feature engineering.

Every test follows the Arrange-Act-Assert pattern:
- Arrange: set up the input
- Act: call the function
- Assert: verify the output
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from features.engineer import engineer_features


def base_claim(**overrides) -> dict:
    claim = {
        "claimed_amount":          4000,
        "approved_tariff":         4000,
        "diagnosis_code":          "B50.9",
        "procedure_code":          "99214",
        "provider_id":             "PRV-00001",
        "member_claim_frequency":  2,
        "provider_claim_frequency": 5,
        "is_duplicate":            0,
        "member_age":              35,
    }
    claim.update(overrides)
    return claim


def test_amount_deviation_zero_when_equal():
    features = engineer_features(base_claim())
    assert features["amount_deviation_pct"] == 0.0


def test_amount_deviation_positive_when_overclaimed():
    features = engineer_features(base_claim(claimed_amount=6000, approved_tariff=4000))
    assert features["amount_deviation_pct"] == pytest.approx(0.5, rel=1e-3)


def test_amount_deviation_negative_when_underclaimed():
    features = engineer_features(base_claim(claimed_amount=3000, approved_tariff=4000))
    assert features["amount_deviation_pct"] == pytest.approx(-0.25, rel=1e-3)


def test_code_match_valid_pair():
    features = engineer_features(base_claim(
        diagnosis_code="B50.9",
        procedure_code="99214",
    ))
    assert features["code_match"] == 1


def test_code_match_invalid_pair():
    features = engineer_features(base_claim(
        diagnosis_code="B50.9",
        procedure_code="59400",  # obstetric care does not match malaria
    ))
    assert features["code_match"] == 0


def test_high_risk_provider_flagged():
    features = engineer_features(base_claim(provider_id="PRV-00003"))
    assert features["provider_is_high_risk"] == 1


def test_normal_provider_not_flagged():
    features = engineer_features(base_claim(provider_id="PRV-00001"))
    assert features["provider_is_high_risk"] == 0


def test_none_member_age_uses_default():
    features = engineer_features(base_claim(member_age=None))
    assert features["member_age"] == 35


def test_none_approved_tariff_uses_procedure_tariff():
    features = engineer_features(base_claim(
        approved_tariff=None,
        procedure_code="99214",
    ))
    assert features["amount_ratio"] > 0


def test_duplicate_flag_passed_through():
    features = engineer_features(base_claim(is_duplicate=1))
    assert features["is_duplicate"] == 1