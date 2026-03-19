#adjudication_engine/dashboard/app.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
import tempfile
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# PAGE CONFIG
st.set_page_config(
    page_title = "Ginja Claims Adjudication Engine",
    page_icon  = "🏥",
    layout     = "wide",
    initial_sidebar_state = "expanded",
)

# STYLING
st.markdown("""
<style>
    .decision-pass  { background:#d4edda; color:#155724; padding:8px 16px; border-radius:6px; font-weight:bold; display:inline-block; }
    .decision-flag  { background:#fff3cd; color:#856404; padding:8px 16px; border-radius:6px; font-weight:bold; display:inline-block; }
    .decision-fail  { background:#f8d7da; color:#721c24; padding:8px 16px; border-radius:6px; font-weight:bold; display:inline-block; }
    .metric-card    { background:#f8f9fa; border-radius:8px; padding:16px; border-left:4px solid #0066cc; }
    .section-header { font-size:1.1rem; font-weight:600; color:#333; margin-bottom:8px; }
</style>
""", unsafe_allow_html=True)


# HELPERS

def decision_badge(decision: str) -> str:
    icons = {"Pass": "✅", "Flag": "⚠️", "Fail": "❌"}
    css   = {"Pass": "pass", "Flag": "flag", "Fail": "fail"}
    icon  = icons.get(decision, "")
    cls   = css.get(decision, "flag")
    return f'<span class="decision-{cls}">{icon} {decision}</span>'


def format_risk_score(score: float) -> str:
    if score < 0.3:
        color = "#28a745"
    elif score < 0.7:
        color = "#ffc107"
    else:
        color = "#dc3545"
    return f'<span style="color:{color}; font-weight:bold; font-size:1.3rem;">{score:.4f}</span>'


@st.cache_resource
def load_model_artifacts():
    """
    Loads model artifacts once and caches them.
    st.cache_resource means this only runs on first load —
    not on every page interaction.
    """
    import xgboost as xgb
    import pickle
    model = xgb.XGBClassifier()
    model.load_model("model/artifacts/xgboost_model.json")
    with open("model/artifacts/shap_explainer.pkl", "rb") as f:
        explainer = pickle.load(f)
    with open("model/artifacts/metrics.json") as f:
        metrics = json.load(f)
    with open("model/artifacts/feature_importance.json") as f:
        importance = json.load(f)
    return model, explainer, metrics, importance


def get_mongo_claims(limit: int = 200) -> list[dict]:
    """Fetches adjudicated claims from MongoDB for the dashboard."""
    try:
        from pymongo import MongoClient
        client = MongoClient(os.getenv("MONGODB_URI"))
        db     = client[os.getenv("MONGODB_DB_NAME", "ginja_claims")]
        claims = list(
            db["claims"].find({}, {"_id": 0}).sort(
                "adjudicated_at", -1
            ).limit(limit)
        )
        client.close()
        return claims
    except Exception as e:
        st.warning(f"Could not connect to MongoDB: {e}")
        return []


# SIDEBAR

with st.sidebar:
    st.image("https://img.icons8.com/color/96/medical-history.png", width=60)
    st.title("Ginja AI")
    st.caption("Claims Adjudication Engine v1.0")
    st.divider()

    page = st.radio(
        "Navigation",
        ["Dashboard", "Adjudicate Claim", "Upload PDF", "Batch Upload", 
        # "Model Insights"
        ],
        label_visibility="collapsed"
    )

    st.divider()
    st.caption("Vision Provider")
    vision_provider = st.selectbox(
        "Provider",
        ["gemini", "ollama", "qwen", "tesseract"],
        label_visibility="collapsed"
    )
    vision_model = st.text_input(
        "Model override (optional)",
        placeholder="e.g. qwen2-vl, llava",
    )
    st.divider()
    # st.caption("Built for Ginja AI · Eden Care")


# PAGE: DASHBOARD

if page == "Dashboard":
    st.title("Claims Adjudication Dashboard")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    claims = get_mongo_claims()

    if not claims:
        st.info("No adjudicated claims yet. Submit a claim to get started.")
    else:
        df = pd.DataFrame(claims)

        # KPI Metrics
        total = len(df)
        passed = len(df[df["decision"] == "Pass"])
        flagged = len(df[df["decision"] == "Flag"])
        failed = len(df[df["decision"] == "Fail"])
        avg_risk = df["risk_score"].mean() if "risk_score" in df.columns else 0

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Total Claims", total)
        col2.metric("Passed", passed, f"{passed/total:.0%}")
        col3.metric("Flagged", flagged, f"{flagged/total:.0%}")
        col4.metric("Failed", failed, f"{failed/total:.0%}")
        col5.metric("Avg Risk Score", f"{avg_risk:.3f}")

        st.divider()

        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("Decision Distribution")
            decision_counts = df["decision"].value_counts().reset_index()
            decision_counts.columns = ["Decision", "Count"]
            colors = {"Pass": "#28a745", "Flag": "#ffc107", "Fail": "#dc3545"}
            fig = px.pie(
                decision_counts,
                values  = "Count",
                names   = "Decision",
                color   = "Decision",
                color_discrete_map = colors,
                hole    = 0.4,
            )
            fig.update_layout(margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig, width="stretch")

        with col_right:
            st.subheader("Risk Score Distribution")
            if "risk_score" in df.columns:
                fig2 = px.histogram(
                    df,
                    x = "risk_score",
                    nbins  = 30,
                    color  = "decision",
                    color_discrete_map = colors,
                    labels = {"risk_score": "Risk Score", "count": "Claims"},
                )
                fig2.update_layout(margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig2, width="stretch")

        # Recent Claims Table
        st.subheader("Recent Adjudications")
        display_cols = [
            c for c in
            ["claim_id", "member_id", "decision", "risk_score", "confidence", "adjudicated_at"]
            if c in df.columns
        ]
        if display_cols:
            st.dataframe(
                df[display_cols].head(20),
                width="stretch",
                hide_index=True,
            )


# PAGE: ADJUDICATE CLAIM

elif page == "Adjudicate Claim":
    st.title("Adjudicate a Claim")
    st.caption("Submit a claim payload for real-time adjudication")

    with st.form("claim_form"):
        st.subheader("Member & Provider")
        col1, col2, col3 = st.columns(3)
        claim_id    = col1.text_input("Claim ID", value="CLM-DEMO-001")
        member_id   = col2.text_input("Member ID", value="MEM-00001")
        provider_id = col3.text_input("Provider ID", value="PRV-00001")

        st.subheader("Clinical Codes")
        col4, col5 = st.columns(2)
        diagnosis_code  = col4.selectbox("Diagnosis Code (ICD-10)", [
            "B50.9 - Malaria", "J06.9 - Upper Respiratory Infection",
            "E11.9 - Type 2 Diabetes", "I10 - Hypertension",
            "J18.9 - Pneumonia", "N39.0 - UTI", "A01.0 - Typhoid",
            "K29.7 - Gastritis", "A09 - Diarrhoea", "Z34.00 - Pregnancy",
        ])
        procedure_code = col5.selectbox("Procedure Code (CPT)", [
            "99214 - Office visit moderate", "99213 - Office visit low",
            "99215 - Office visit high", "71046 - Chest X-ray",
            "83036 - HbA1c test", "87798 - Malaria rapid test",
            "43239 - Upper GI endoscopy", "59400 - Obstetric care",
            "81003 - Urinalysis", "93000 - ECG",
        ])

        st.subheader("Financial & Administrative")
        col6, col7, col8 = st.columns(3)
        claimed_amount = col6.number_input("Claimed Amount (KES)", min_value=1, value=4200)
        approved_tariff = col7.number_input("Approved Tariff (KES)", min_value=1, value=4000)
        date_of_service = col8.date_input("Date of Service")

        col9, col10, col11 = st.columns(3)
        provider_type = col9.selectbox("Provider Type", ["hospital", "clinic", "pharmacy", "laboratory", "specialist"])
        location = col10.selectbox("Location", ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret", "Kigali", "Kampala"])
        member_age = col11.number_input("Member Age", min_value=0, max_value=120, value=35)

        col12, col13 = st.columns(2)
        member_freq = col12.number_input("Member Claim Frequency", min_value=0, value=2)
        provider_freq = col13.number_input("Provider Claim Frequency", min_value=0, value=8)

        submitted = st.form_submit_button("  Adjudicate", width="stretch")

    if submitted:
        from engine.adjudicator import adjudicate
        import asyncio
        from db.mongo import save_adjudication_result

        diag_code = diagnosis_code.split(" - ")[0]
        proc_code = procedure_code.split(" - ")[0]

        raw_claim = {
            "claim_id": claim_id,
            "member_id":  member_id,
            "provider_id": provider_id,
            "diagnosis_code": diag_code,
            "procedure_code": proc_code,
            "claimed_amount": claimed_amount,
            "approved_tariff": approved_tariff,
            "date_of_service": date_of_service.isoformat() + "T00:00:00",
            "provider_type": provider_type,
            "location": location,
            "member_age": member_age,
            "member_claim_frequency":  member_freq,
            "provider_claim_frequency": provider_freq,
            "is_duplicate": 0,
        }

        with st.spinner("Adjudicating..."):
            result = adjudicate(raw_claim)
            asyncio.run(save_adjudication_result(result))

        st.divider()
        st.subheader("Adjudication Result")

        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.markdown(
            f"**Decision**<br>{decision_badge(result['decision'])}",
            unsafe_allow_html=True
        )
        col_b.metric("Risk Score", f"{result['risk_score']:.4f}")
        col_c.metric("Confidence", f"{result['confidence']:.4f}")
        col_d.metric("Stage", f"Stage {result['adjudication_stage']}")

        st.info(f"📋 **Explanation of Benefits**\n\n{result['explanation_of_benefits']}")

        if result["reasons"]:
            st.subheader("Decision Reasons")
            for reason in result["reasons"]:
                icon = "🔴" if result["decision"] == "Fail" else "🟡" if result["decision"] == "Flag" else "🟢"
                st.write(f"{icon} {reason}")

        if result.get("feature_contributions"):
            st.subheader("Feature Contributions (SHAP)")
            contrib_df = pd.DataFrame([
                {
                    "Feature": k,
                    "Contribution": v,
                    "Direction": "-> Fraud" if v > 0 else "-> Legitimate"
                }
                for k, v in result["feature_contributions"].items()
            ]).sort_values("Contribution", key=abs, ascending=True)

            fig3 = px.bar(
                contrib_df,
                x     = "Contribution",
                y     = "Feature",
                color = "Direction",
                color_discrete_map = {
                    "-> Fraud": "#dc3545",
                    "-> Legitimate": "#28a745"
                },
                orientation = "h",
                title = "Which features drove this decision",
            )
            st.plotly_chart(fig3, width="stretch")

        with st.expander("Full Result JSON"):
            display = {k: v for k, v in result.items() if k != "audit_trail"}
            st.json(display)


# PAGE: UPLOAD PDF

elif page == "Upload PDF":
    st.title("PDF Claim Extraction & Adjudication")
    st.caption(
        "Upload a claim form, invoice, or both together. "
        "When both are provided the system cross-references them "
        "for additional fraud signals."
    )

    # col_info1, col_info2, col_info3 = st.columns(3)
    # col_info1.info("**Gemini** — Best for handwritten forms")
    # col_info2.info("**Ollama/Qwen** — Fully offline, privacy-first")
    # col_info3.info("**Tesseract** — Digital PDFs, no API needed")

    st.subheader("Document Upload")
    col_up1, col_up2 = st.columns(2)

    with col_up1:
        st.caption("Claim Form (required or optional)")
        claim_form_file = st.file_uploader(
            "Upload claim form PDF",
            type = ["pdf"],
            key = "claim_form_upload",
        )

    with col_up2:
        st.caption("Supporting Invoice (optional)")
        invoice_file = st.file_uploader(
            "Upload invoice PDF",
            type = ["pdf"],
            key = "invoice_upload",
        )

    col_prov, col_mod = st.columns(2)
    selected_provider = col_prov.selectbox(
        "Vision Provider",
        ["gemini", "ollama", "qwen", "tesseract"],
        index = 0,
        key = "pdf_provider",
    )
    selected_model = col_mod.text_input(
        "Model override (optional)",
        placeholder = "Leave blank to use default",
        key = "pdf_model",
    )

    # Determine what was uploaded
    has_claim_form = claim_form_file is not None
    has_invoice = invoice_file is not None
    has_both = has_claim_form and has_invoice

    if has_both:
        st.success(
            "Both documents uploaded — cross-reference validation will run"
        )
    elif has_claim_form:
        st.info("📋 Claim form uploaded — single document adjudication")
    elif has_invoice:
        st.info("🧾 Invoice uploaded — single document adjudication")

    if has_claim_form or has_invoice:
        if st.button(" Extract & Adjudicate", width="stretch"):
            from extraction.fallback import extract_with_fallback
            from extraction.cross_reference import cross_reference, merge_documents
            from engine.adjudicator import adjudicate
            from extraction.validator import validate_extracted_claim
            import asyncio
            from db.mongo import save_adjudication_result

            extracted_form = None
            extracted_invoice = None

            # Extract claim form
            if has_claim_form:
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".pdf"
                ) as tmp:
                    tmp.write(claim_form_file.read())
                    tmp_path = tmp.name
                with st.spinner("Extracting claim form..."):
                    extracted_form = extract_with_fallback(
                        tmp_path,
                        provider = selected_provider,
                        model    = selected_model or None,
                    )
                os.unlink(tmp_path)
                st.success("Claim form extracted")

            # Extract invoice
            if has_invoice:
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".pdf"
                ) as tmp:
                    tmp.write(invoice_file.read())
                    tmp_path = tmp.name
                with st.spinner("Extracting invoice..."):
                    extracted_invoice = extract_with_fallback(
                        tmp_path,
                        provider = selected_provider,
                        model = selected_model or None,
                    )
                os.unlink(tmp_path)
                st.success("Invoice extracted")

            # Cross-reference if both present
            if has_both:
                st.subheader("Cross-Reference Analysis")
                cross_ref = cross_reference(extracted_form, extracted_invoice)
                merged = merge_documents(
                    extracted_form, extracted_invoice, cross_ref
                )

                col_cr1, col_cr2, col_cr3 = st.columns(3)
                col_cr1.metric(
                    "Documents Consistent",
                    "Yes" if cross_ref["is_consistent"] else "No"
                )
                col_cr2.metric(
                    "Cross-Ref Score",
                    f"{cross_ref['cross_ref_score']:.2f}"
                )
                col_cr3.metric(
                    "Summary",
                    cross_ref["summary"]
                )

                if cross_ref["confirmations"]:
                    with st.expander("Confirmed matches"):
                        for c in cross_ref["confirmations"]:
                            st.write(f"✓ {c}")

                if cross_ref["mismatches"]:
                    with st.expander(
                        f"{len(cross_ref['mismatches'])} mismatches detected",
                        expanded=True
                    ):
                        for m in cross_ref["mismatches"]:
                            severity_color = (
                                "X" if m["severity"] == "high" else "OK"
                            )
                            st.write(
                                f"{severity_color} **{m['field']}**: "
                                f"claim form=`{m.get('claim_form')}` "
                                f"vs invoice=`{m.get('invoice')}`"
                            )

                final_claim = merged

            else:
                # Single document
                final_claim = extracted_form or extracted_invoice

            # Show extraction summary
            st.subheader("Extracted Data")
            skip = {
                "raw_text", "extraction_warnings", "validation_errors",
                "is_valid", "fallback_attempts", "provider_used",
                "cross_reference", "cross_ref_fraud_signals",
            }
            display_data = {
                k: v for k, v in final_claim.items()
                if k not in skip and v is not None
            }
            st.json(display_data)

            if final_claim.get("extraction_warnings"):
                with st.expander("Extraction warnings"):
                    for w in final_claim["extraction_warnings"]:
                        st.warning(f"WARNING: {w}")

            # Adjudicate
            st.subheader("Adjudication Result")
            with st.spinner("Adjudicating..."):
                result = adjudicate(final_claim)
                asyncio.run(save_adjudication_result(result))

            col_r1, col_r2, col_r3, col_r4 = st.columns(4)
            col_r1.markdown(
                f"**Decision**<br>{decision_badge(result['decision'])}",
                unsafe_allow_html=True
            )
            col_r2.metric("Risk Score",  f"{result['risk_score']:.4f}")
            col_r3.metric("Confidence",  f"{result['confidence']:.4f}")
            col_r4.metric("Stage",       f"Stage {result['adjudication_stage']}")

            st.info(f"📋 {result['explanation_of_benefits']}")

            if result.get("reasons"):
                st.subheader("Decision Reasons")
                for reason in result["reasons"]:
                    icon = (
                        "🔴" if result["decision"] == "Fail"
                        else "🟡" if result["decision"] == "Flag"
                        else "🟢"
                    )
                    st.write(f"{icon} {reason}")

            if result.get("feature_contributions"):
                contrib_df = pd.DataFrame([
                    {
                        "Feature":      k,
                        "Contribution": v,
                        "Direction":    "-> Fraud" if v > 0 else "-> Legitimate"
                    }
                    for k, v in result["feature_contributions"].items()
                ]).sort_values("Contribution", key=abs, ascending=True)

                fig = px.bar(
                    contrib_df,
                    x = "Contribution",
                    y = "Feature",
                    color = "Direction",
                    color_discrete_map = {
                        "-> Fraud": "#dc3545",
                        "-> Legitimate": "#28a745",
                    },
                    orientation = "h",
                    title       = "Feature contributions to this decision",
                )
                st.plotly_chart(fig, width="stretch")

            with st.expander("Full Result JSON"):
                st.json({
                    k: v for k, v in result.items()
                    if k != "audit_trail"
                })



# PAGE: BATCH UPLOAD
elif page == "Batch Upload":
    st.title("Batch Claims Processing")
    st.caption("Upload a CSV file to adjudicate multiple claims at once")

    st.download_button(
        "⬇️ Download Sample CSV Template",
        data = pd.DataFrame([{
            "claim_id": "CLM-001", "member_id": "MEM-00001",
            "provider_id": "PRV-00001", "diagnosis_code": "B50.9",
            "procedure_code": "99214", "claimed_amount": 4200,
            "approved_tariff": 4000, "date_of_service": "2026-01-15T10:00:00",
            "provider_type": "hospital", "location": "Nairobi",
            "member_age": 34, "member_claim_frequency": 2,
            "provider_claim_frequency": 8, "is_duplicate": 0,
        }]).to_csv(index=False),
        file_name = "sample_claims.csv",
        mime = "text/csv",
    )

    uploaded_csv = st.file_uploader("Upload CSV file", type=["csv"])

    if uploaded_csv:
        df = pd.read_csv(uploaded_csv)
        st.write(f"Loaded {len(df)} claims")
        st.dataframe(df.head(5), width="stretch")

        if st.button("  Process All Claims", width="stretch"):
            from engine.adjudicator import adjudicate
            import asyncio
            from db.mongo import save_adjudication_result

            results  = []
            progress = st.progress(0)
            status = st.empty()

            for i, (_, row) in enumerate(df.iterrows()):
                raw = {
                    k: (None if pd.isna(v) else v)
                    for k, v in row.to_dict().items()
                }
                try:
                    result = adjudicate(raw)
                    asyncio.run(save_adjudication_result(result))
                    results.append(result)
                except Exception as e:
                    results.append({
                        "claim_id": raw.get("claim_id"),
                        "decision": "Error",
                        "error":    str(e)
                    })

                progress.progress((i + 1) / len(df))
                status.text(f"Processing {i+1}/{len(df)}: {raw.get('claim_id')}")

            st.success(f"Processed {len(results)} claims")

            results_df = pd.DataFrame(results)
            display    = [c for c in ["claim_id", "decision", "risk_score", "confidence"] if c in results_df.columns]
            st.dataframe(results_df[display], width="stretch")

            decision_counts = results_df["decision"].value_counts()
            col1, col2, col3 = st.columns(3)
            col1.metric("Passed", decision_counts.get("Pass", 0))
