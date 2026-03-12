# ABOUT
This is a system that receives a healthcare claim (from a PDF, CSV, JSON, or API call), understands what's in it, decides whether it should be paid, flagged for review, or rejected, and explains why. That's the entire brief.

We have PDF forms that are sample inputs, they're showing the kind of messy real-world documents the system needs to handle. 
The system's extractor will use a vision model that reads whatever it sees.



# ARCHITECTURE

```
ginja-claims-engine/
├── data/
│   ├── synthetic/          # generated training claims
│   └── samples/            # sample PDFs
├── extraction/
│   ├── providers/
│   │   ├── base.py         # shared interface all providers implement
│   │   ├── gemini.py       # Google Gemini Vision
│   │   ├── ollama.py       # Ollama (offline, e.g. llama vision)
│   │   └── qwen.py         # Qwen vision via Ollama
│   ├── factory.py          # picks provider based on .env or param
│   └── validator.py        # validates extracted fields
├── features/
│   └── engineer.py         # computes all ML features
├── model/
│   ├── train.py            # trains XGBoost, saves model
│   ├── evaluate.py         # precision, recall, F1, confusion matrix
│   ├── predict.py          # loads model, scores a claim
│   └── artifacts/          # saved model file lives here
├── engine/
│   ├── rules.py            # hard deterministic rules (Stage 1 + 2)
│   ├── adjudicator.py      # combines rules + ML + reason generation
│   └── explainer.py        # SHAP values + LLM reason generation
├── api/
│   ├── main.py             # FastAPI app
│   ├── routes/
│   │   ├── claims.py       # claim submission endpoints
│   │   └── health.py       # health check endpoint
│   └── schemas.py          # Pydantic request/response models
├── dashboard/
│   └── app.py              # Streamlit demo dashboard
├── monitoring/
│   └── logger.py           # structured logging + audit trail
├── db/
│   ├── mongo.py            # MongoDB connection
│   └── models.py           # MongoDB document schemas
├── tests/
│   ├── test_extraction.py
│   ├── test_features.py
│   ├── test_model.py
│   ├── test_engine.py
│   └── test_api.py
├── scripts/
│   ├── generate_data.py    # synthetic data generator
│   └── retrain.py          # retraining script scaffold
├── .env
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

# ADJUCATION STAGES
Stage 1 lives in engine/rules.py — fast, deterministic checks:

- Is this a duplicate claim
- Are all required fields present
- Is the member ID valid format
- Is the date of service within an acceptable range
- Does the plan ID exist

If Stage 1 fails -> immediate Fail, no need to go further.

Stage 2 lives in features/engineer.py + model/predict.py:

- Compute all features (amount deviation, frequency anomaly etc.)
- XGBoost scores the claim and outputs a probability 0–1
- SHAP tells us which features drove that score

Stage 3 lives in engine/adjudicator.py:

- Rules can override the ML score (e.g. 3x tariff = auto Fail regardless)
- Final decision mapped: 0–0.3 Pass, 0.3–0.7 Flag, 0.7–1.0 Fail
- LLM generates a plain English Explanation of Benefits


# EXAMS OUTPUT FOR EVERY CLAIM
```
{
  "claim_id": "CLM-2024-001",
  "member_id": "MEM-00123",
  "decision": "Flag",
  "risk_score": 0.61,
  "confidence": 0.87,
  "adjudication_stage": 2,
  "reasons": [
    "Claimed amount is 94% above approved tariff",
    "Provider has 3 similar claims flagged this month",
    "Diagnosis code does not typically match procedure code"
  ],
  "explanation": "This claim has been flagged for manual review. The billed amount significantly exceeds the approved tariff for this procedure, and the provider has a elevated risk profile based on recent claim history. A benefits coordinator should verify the supporting invoice before approval.",
  "feature_contributions": {
    "amount_deviation_pct": 0.38,
    "provider_risk_score": 0.29,
    "code_mismatch": 0.21,
    "claim_frequency_anomaly": 0.12
  },
  "timestamp": "2024-03-12T10:23:45Z",
  "processing_time_ms": 342
}
```


# MongoDB document design
```
{
  "_id": "CLM-2024-001",
  "raw_input": {},
  "extracted_data": {},
  "features": {},
  "adjudication": {},
  "audit_trail": [
    {
      "stage": 1,
      "timestamp": "",
      "result": "",
      "checks_run": []
    }
  ],
  "status": "flagged",
  "created_at": "",
  "updated_at": ""
}
```


# EXTRA
1. Swappable vision providers — Gemini, Ollama, Qwen, Tesseract, switchable via a single parameter
2. Full audit trail — every decision recorded with which stage stopped it and why
3. Explanation of Benefits generation — LLM produces a human-readable EOB per claim, mimicking real insurance workflows
4. Model confidence alongside risk score — two separate numbers, risk score is the fraud probability, confidence is how certain the model is about that score
5. Retraining script — when enough new labelled claims accumulate in MongoDB, retrain automatically
6. Prometheus monitoring hooks — latency, decision distribution, extraction failures


# SYNTHETIC DATA GENERATION
Real healthcare fraud in East Africa typically looks like:
- Upcoding — billing for a more expensive procedure than was performed
- Phantom billing — billing for services never rendered
- Duplicate claims — submitting the same claim multiple times
- Unbundling — splitting one procedure into multiple claims to increase payout
- Tariff inflation — billing significantly above the approved rate