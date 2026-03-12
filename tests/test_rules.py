"""
Unit tests for the adjudication rules engine
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from engine.rules import run_stage_one, run_stage_two
from datetime import datetime, timedelta


def valid_claim(**overrides) -> dict:
    claim = {
        "claim_id": "CLM-TEST-001",
        "member_id": "MEM-00001",
        "provider_id": "PRV-00001",
        "diagnosis_code": "B50.9",
        "procedure_code": "99214",
        "claimed_amount": 4000,
        "approved_tariff": 4000,
        "date_of_service": datetime.now().isoformat(),
        "provider_type":  "hospital",
        "location": "Nairobi",
    }
    claim.update(overrides)
    return claim


class TestStageOne:

    def test_valid_claim_passes(self):
        result = run_stage_one(valid_claim())
        assert result["passed"] is True
        assert result["failures"] == []

    def test_missing_member_id_fails(self):
        result = run_stage_one(valid_claim(member_id=None))
        assert result["passed"] is False

    def test_negative_amount_fails(self):
        result = run_stage_one(valid_claim(claimed_amount=-100))
        assert result["passed"] is False

    def test_future_date_fails(self):
        future = (datetime.now() + timedelta(days=10)).isoformat()
        result = run_stage_one(valid_claim(date_of_service=future))
        assert result["passed"] is False

    def test_stale_claim_fails(self):
        old_date = (datetime.now() - timedelta(days=100)).isoformat()
        result = run_stage_one(valid_claim(date_of_service=old_date))
        assert result["passed"] is False

    def test_none_provider_id_does_not_crash(self):
        result = run_stage_one(valid_claim(provider_id=None))
        # Should not raise — provider_id is soft requirement
        assert isinstance(result, dict)


class TestStageTwo:

    def test_valid_claim_passes(self):
        result = run_stage_two(valid_claim())
        assert result["passed"] is True
        assert result["hard_overrides"] == []

    def test_amount_three_times_tariff_triggers_hard_override(self):
        result = run_stage_two(valid_claim(
            claimed_amount=13000,
            approved_tariff=4000,
        ))
        assert len(result["hard_overrides"]) > 0

    def test_missing_diagnosis_code_is_soft_flag(self):
        result = run_stage_two(valid_claim(diagnosis_code=None))
        assert result["passed"] is True
        assert len(result["soft_flags"]) > 0

    def test_line_items_mismatch_flagged(self):
        result = run_stage_two(valid_claim(
            claimed_amount=5000,
            line_items=[
                {"description": "Consultation", "total": 2000},
                {"description": "Test", "total": 2000},
            ]
        ))
        assert any("line item" in f.lower() for f in result["soft_flags"])