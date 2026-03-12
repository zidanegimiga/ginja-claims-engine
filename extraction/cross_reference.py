"""
Cross-reference validator for multi-document claim submissions.

In real healthcare adjudication, a claim packet often contains:
- A claim form (submitted by the member or employer)
- A supporting invoice (issued by the hospital or provider)

Cross-referencing these two documents is a powerful fraud
detection technique because fabricated claims often contain
subtle inconsistencies between documents that were created
separately.

This module compares extracted data from both documents
and produces a set of consistency signals used by the
decision engine.
"""

from datetime import datetime


def cross_reference(
    claim_form: dict,
    invoice:    dict,
) -> dict:
    """
    Compares extracted fields from a claim form and invoice.

    Returns a cross-reference report with:
    - is_consistent:     bool — whether documents agree on key fields
    - mismatches:        list of specific field conflicts
    - confirmations:     list of fields that matched correctly
    - fraud_signals:     list of signals to feed into adjudication
    - cross_ref_score:   float 0–1, higher = more suspicious
    """
    mismatches   = []
    confirmations = []
    fraud_signals = []

    # ── 1. Amount consistency ──
    # The single most important cross-reference check.
    # A claim form showing a different amount than the invoice
    # is a strong indicator of fraud or billing error.
    claim_amount   = _to_float(claim_form.get("claimed_amount"))
    invoice_amount = _to_float(invoice.get("claimed_amount"))

    if claim_amount and invoice_amount:
        discrepancy = abs(claim_amount - invoice_amount)
        pct         = discrepancy / max(claim_amount, invoice_amount)

        if pct > 0.05:  # more than 5% difference
            mismatches.append({
                "field":      "claimed_amount",
                "claim_form": claim_amount,
                "invoice":    invoice_amount,
                "difference": round(discrepancy, 2),
                "severity":   "high" if pct > 0.20 else "medium",
            })
            fraud_signals.append(
                f"Amount mismatch: claim form shows {claim_amount} "
                f"but invoice shows {invoice_amount} "
                f"({pct:.1%} discrepancy)"
            )
        else:
            confirmations.append(
                f"Amounts consistent: {claim_amount} KES on both documents"
            )

    # ── 2. Patient name consistency ──
    claim_name   = _normalise_name(claim_form.get("patient_name"))
    invoice_name = _normalise_name(invoice.get("patient_name"))

    if claim_name and invoice_name:
        if not _names_match(claim_name, invoice_name):
            mismatches.append({
                "field":      "patient_name",
                "claim_form": claim_name,
                "invoice":    invoice_name,
                "severity":   "high",
            })
            fraud_signals.append(
                f"Patient name mismatch: '{claim_name}' on claim form "
                f"vs '{invoice_name}' on invoice"
            )
        else:
            confirmations.append(f"Patient name consistent: {claim_name}")

    # ── 3. Date of service consistency ──
    claim_date   = _to_date(claim_form.get("date_of_service"))
    invoice_date = _to_date(invoice.get("date_of_service"))

    if claim_date and invoice_date:
        delta = abs((claim_date - invoice_date).days)
        if delta > 3:  # allow 3 days tolerance for admin lag
            mismatches.append({
                "field":      "date_of_service",
                "claim_form": str(claim_date.date()),
                "invoice":    str(invoice_date.date()),
                "days_apart": delta,
                "severity":   "medium",
            })
            fraud_signals.append(
                f"Date mismatch: claim form dated {claim_date.date()} "
                f"but invoice dated {invoice_date.date()} "
                f"({delta} days apart)"
            )
        else:
            confirmations.append(
                f"Service dates consistent: within {delta} day(s)"
            )

    # ── 4. Member ID consistency ──
    claim_member   = str(claim_form.get("member_id") or "").strip()
    invoice_member = str(invoice.get("member_id") or "").strip()

    if claim_member and invoice_member:
        if claim_member != invoice_member:
            mismatches.append({
                "field":      "member_id",
                "claim_form": claim_member,
                "invoice":    invoice_member,
                "severity":   "high",
            })
            fraud_signals.append(
                f"Member ID mismatch: '{claim_member}' on claim form "
                f"vs '{invoice_member}' on invoice"
            )
        else:
            confirmations.append(f"Member ID consistent: {claim_member}")

    # ── 5. Provider/hospital name consistency ──
    claim_provider   = _normalise_name(
        claim_form.get("hospital_name") or claim_form.get("provider_name")
    )
    invoice_provider = _normalise_name(
        invoice.get("hospital_name") or invoice.get("provider_name")
    )

    if claim_provider and invoice_provider:
        if not _names_match(claim_provider, invoice_provider):
            mismatches.append({
                "field":      "provider",
                "claim_form": claim_provider,
                "invoice":    invoice_provider,
                "severity":   "medium",
            })
            fraud_signals.append(
                f"Provider name mismatch: '{claim_provider}' on claim form "
                f"vs '{invoice_provider}' on invoice"
            )
        else:
            confirmations.append(
                f"Provider consistent: {claim_provider}"
            )

    # ── 6. Line items vs claimed amount ──
    # If the invoice has line items, verify they sum to
    # the claimed amount. A discrepancy suggests manipulation.
    line_items = invoice.get("line_items") or []
    if line_items and invoice_amount:
        try:
            line_total = sum(
                float(item.get("total") or 0)
                for item in line_items
                if isinstance(item, dict)
            )
            if line_total > 0:
                discrepancy = abs(line_total - invoice_amount)
                pct         = discrepancy / invoice_amount
                if pct > 0.05:
                    fraud_signals.append(
                        f"Invoice line items total {line_total} KES "
                        f"but invoice claims {invoice_amount} KES "
                        f"({pct:.1%} discrepancy)"
                    )
                else:
                    confirmations.append(
                        f"Line items sum ({line_total} KES) matches "
                        f"invoice total ({invoice_amount} KES)"
                    )
        except (TypeError, ValueError):
            pass

    # ── Compute cross-reference score ──
    # Each high-severity mismatch contributes 0.3
    # Each medium-severity mismatch contributes 0.15
    # Capped at 1.0
    score = 0.0
    for m in mismatches:
        score += 0.3 if m.get("severity") == "high" else 0.15
    score = min(round(score, 2), 1.0)

    return {
        "is_consistent":   len(mismatches) == 0,
        "mismatches":      mismatches,
        "confirmations":   confirmations,
        "fraud_signals":   fraud_signals,
        "cross_ref_score": score,
        "documents_used":  2,
        "summary": (
            f"{len(confirmations)} fields consistent, "
            f"{len(mismatches)} mismatches detected"
        ),
    }


def merge_documents(
    claim_form: dict,
    invoice:    dict,
    cross_ref:  dict,
) -> dict:
    """
    Merges extracted data from both documents into a single
    claim record for adjudication.

    Priority: claim_form fields take precedence over invoice
    fields for identity data (member_id, dates).
    Invoice fields take precedence for financial data
    (line_items, hospital_name, amounts).

    Cross-reference fraud signals are added to the merged
    claim so the decision engine can use them.
    """
    merged = {}

    # Start with invoice data as base
    merged.update({
        k: v for k, v in invoice.items()
        if v is not None and k not in ("raw_text", "provider_name")
    })

    # Overlay claim form data — takes precedence for identity fields
    identity_fields = [
        "claim_id", "member_id", "diagnosis_code",
        "diagnosis_description", "procedure_code",
        "date_of_service", "member_age",
    ]
    for field in identity_fields:
        value = claim_form.get(field)
        if value is not None:
            merged[field] = value

    # Use the higher claimed amount if both present
    # (claim form amount is the one being adjudicated)
    if claim_form.get("claimed_amount"):
        merged["claimed_amount"] = claim_form["claimed_amount"]

    # Add cross-reference results
    merged["cross_reference"]          = cross_ref
    merged["cross_ref_fraud_signals"]  = cross_ref["fraud_signals"]
    merged["cross_ref_score"]          = cross_ref["cross_ref_score"]
    merged["documents_used"]           = 2

    # Merge extraction warnings from both documents
    warnings = (
        list(claim_form.get("extraction_warnings") or []) +
        list(invoice.get("extraction_warnings") or [])
    )
    if cross_ref["fraud_signals"]:
        warnings += [f"⚡ Cross-ref: {s}" for s in cross_ref["fraud_signals"]]
    merged["extraction_warnings"] = warnings

    return merged


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _to_float(value) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _to_date(value) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", ""))
    except (ValueError, TypeError):
        return None


def _normalise_name(name: str | None) -> str | None:
    if not name:
        return None
    return " ".join(str(name).lower().split())


def _names_match(a: str, b: str) -> bool:
    """
    Fuzzy name matching — handles minor spelling differences,
    initials, and word order variations.

    Examples that should match:
    - "wanjiku kamau" vs "kamau wanjiku"
    - "siddharth sharma" vs "s. sharma"
    """
    if a == b:
        return True

    # Check if all words in shorter name appear in longer name
    words_a = set(a.split())
    words_b = set(b.split())
    overlap = words_a & words_b

    # If more than half the words match, consider it a match
    min_words = min(len(words_a), len(words_b))
    return len(overlap) >= max(1, min_words - 1)
