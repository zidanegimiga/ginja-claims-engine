"""
Unit tests for the cross-reference validator
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from extraction.cross_reference import cross_reference, merge_documents


def make_claim_form(**overrides) -> dict:
    doc = {
        "claim_id": "CLM-001",
        "member_id": "1536500",
        "patient_name": "Siddharth Sharma",
        "claimed_amount": 17000,
        "date_of_service": "2025-08-28T00:00:00",
        "hospital_name":  "Nairobi Lifecare Hospital",
    }
    doc.update(overrides)
    return doc


def make_invoice(**overrides) -> dict:
    doc = {
        "member_id": "1536500",
        "patient_name": "Siddharth Sharma",
        "claimed_amount": 17000,
        "date_of_service": "2025-08-28T00:00:00",
        "hospital_name":  "Nairobi Lifecare Hospital",
        "line_items": [
            {"description": "Consultation", "total": 5000},
            {"description": "X-Ray", "total": 12000},
        ]
    }
    doc.update(overrides)
    return doc


class TestCrossReference:

    def test_consistent_documents_pass(self):
        result = cross_reference(make_claim_form(), make_invoice())
        assert result["is_consistent"] is True
        assert result["cross_ref_score"] == 0.0

    def test_amount_mismatch_detected(self):
        result = cross_reference(
            make_claim_form(claimed_amount=17000),
            make_invoice(claimed_amount=12000),
        )
        assert not result["is_consistent"]
        assert any("amount" in m["field"] for m in result["mismatches"])

    def test_patient_name_mismatch_detected(self):
        result = cross_reference(
            make_claim_form(patient_name="John Doe"),
            make_invoice(patient_name="Jane Doe"),
        )
        assert not result["is_consistent"]

    def test_name_match_handles_word_order(self):
        result = cross_reference(
            make_claim_form(patient_name="Sharma Siddharth"),
            make_invoice(patient_name="Siddharth Sharma"),
        )
        assert result["is_consistent"]

    def test_line_items_sum_mismatch_flagged(self):
        result = cross_reference(
            make_claim_form(),
            make_invoice(
                claimed_amount=17000,
                line_items=[
                    {"description": "Consultation", "total": 5000},
                    {"description": "X-Ray", "total": 5000},
                ]
            )
        )
        assert any("line item" in s.lower() for s in result["fraud_signals"])

    def test_high_severity_mismatch_raises_score(self):
        result = cross_reference(
            make_claim_form(claimed_amount=17000),
            make_invoice(claimed_amount=5000),
        )
        assert result["cross_ref_score"] > 0

    def test_merge_prefers_claim_form_for_identity(self):
        merged = merge_documents(
            make_claim_form(member_id="FORM-ID"),
            make_invoice(member_id="INV-ID"),
            cross_reference(make_claim_form(), make_invoice()),
        )
        assert merged["member_id"] == "FORM-ID"