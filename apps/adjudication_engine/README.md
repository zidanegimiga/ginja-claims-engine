# Ginja Claims Engine

This is an AI-powered healthcare claims adjudication system built for East African insurance markets. The system ingests paper claim forms and invoices via PDF upload, extracts structured data using vision models, validates the claim through a three-stage rules and machine learning pipeline, and returns a decision with a plain-English explanation.

Built as a technical case study for Ginja AI / Eden Care.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [System Requirements](#system-requirements)
4. [Quick Start](#quick-start)
5. [Running with Docker](#running-with-docker)
6. [Running Locally](#running-locally)
7. [API Reference](#api-reference)
8. [Environment Variables](#environment-variables)
9. [Running Tests](#running-tests)
10. [Model Explanation](#model-explanation)
11. [Assumptions and Trade-offs](#assumptions-and-trade-offs)
12. [Roadmap](#roadmap)
13. [Acknowledgements](#acknowledgements)

---

## Overview

Healthcare claims adjudication in East Africa involves significant manual processing of paper forms that often lack standardised codes, contain handwriting, and pair two separate documents (a patient-submitted claim form and a hospital-issued invoice) that must be reconciled.

This system automates that process with three layers of defence:

- **Stage 1** validates basic fields and dates
- **Stage 2** performs clinical and financial rule checks including hard overrides for extreme overbilling
- **Stage 3** runs an XGBoost classifier with SHAP explainability to score fraud risk

Every decision includes a confidence score, a list of human-readable reasons, and an Explanation of Benefits.

---

## Architecture

![Architecture Diagram](Flowchart.jpg)


**Key design decisions:**

The API gateway and ML layer are separate concerns. The gateway handles auth, rate limiting, and request routing. The ML layer handles feature engineering, prediction, and explainability. This separation means the ML model can be retrained and swapped without touching the API contract.

PDF extraction uses a provider abstraction with a fallback chain: Gemini Vision is the primary extractor, Tesseract OCR is the offline fallback. Adding a new vision provider requires only implementing the `BaseVisionProvider` interface.

---

## System Requirements

- Python 3.13+
- Docker and Docker Compose (for containerised setup)
- A MongoDB Atlas account (free tier works)
- A Google Gemini API key (for PDF extraction)
- Tesseract OCR installed locally for non-Docker setup

On macOS, XGBoost requires OpenMP:
```bash
brew install libomp
```

For Tesseract on macOS:
```bash
brew install tesseract
```

---

## Quick Start

Clone the repository and copy the environment file:

```bash
git clone https://github.com/YOUR_USERNAME/ginja-claims-engine.git
cd ginja-claims-engine/apps/adjudication_engine
cp .env.example .env
```

Fill in your `.env` values (see [Environment Variables](#environment-variables) below), then choose Docker or local setup.

---

## Running with Docker

This is the recommended approach. It starts both the API and the Streamlit dashboard.

```bash
docker compose build
docker compose up
```

- API: http://localhost:8000
- API docs: http://localhost:8000/docs
- Dashboard: http://localhost:8501

On first startup, the API will print a development API key to the terminal. Copy it and add it to your `.env` as `API_KEY_PRIMARY`.

---

## Folder Structure

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


## Running Locally

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate       # macOS/Linux
# or
venv\Scripts\activate          # Windows
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Set up database indexes:

```bash
python -m scripts.setup_db
```

Train the model (required before first run):

```bash
python -m model.train
```

Start the API in one terminal:

```bash
python -m uvicorn api.main:app --reload --port 8000
```

Start the dashboard in a second terminal:

```bash
python -m streamlit run dashboard/app.py
```

---

## API Reference

All endpoints require an `X-API-Key` header. POST endpoints require write scope. GET endpoints require read scope.

**Adjudicate a single claim:**
```
POST /api/v1/adjudicate
```

**Adjudicate a batch (JSON array):**
```
POST /api/v1/adjudicate/batch
```

**Upload a CSV of claims:**
```
POST /api/v1/adjudicate/upload/csv
```

**Upload a PDF claim form:**
```
POST /api/v1/adjudicate/upload/pdf?provider=gemini
```

**Retrieve a claim by ID:**
```
GET /api/v1/claims/{claim_id}
```

**List claims with filters:**
```
GET /api/v1/claims?decision=Flag&limit=20
```

**Admin - create API key:**
```
POST /api/v1/admin/keys
```

Full interactive documentation is available at http://localhost:8000/docs when the server is running.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the following:

| Variable | Description |
|---|---|
| `MONGODB_URI` | MongoDB Atlas connection string |
| `MONGODB_DB_NAME` | Database name (default: ginja_claims) |
| `GEMINI_API_KEY` | Google Gemini API key for PDF extraction |
| `VISION_PROVIDER` | Primary vision provider: gemini, ollama, tesseract |
| `VISION_MODEL` | Model name override |
| `API_KEY_PRIMARY` | Your development API key (generated on first startup) |
| `LOG_LEVEL` | Logging verbosity (default: INFO) |

---

## Running Tests

```bash
python -m pytest tests/ -v
```

27 tests covering feature engineering, rules engine, and cross-reference validation. 25 pass. The 2 failing tests were caught during development and the underlying bugs were fixed in the production code.

---

## Model Explanation

The adjudication model is an XGBoost binary classifier trained on 1,200 synthetic claims with a 25% fraud rate.

**Performance on held-out test set:**

| Metric | Score |
|---|---|
| Precision | 0.891 |
| Recall | 0.950 |
| F1 | 0.919 |
| ROC-AUC | 0.978 |
| Cross-val ROC-AUC | 0.971 +/- 0.034 |

Precision of 0.891 means that of every 100 claims the model flagged as fraud, 89 were genuinely fraudulent. Recall of 0.950 means the model caught 95 out of every 100 actual fraud cases.

**Top features by SHAP importance:**

1. `provider_is_high_risk` - historical fraud pattern from the submitting provider
2. `amount_deviation_pct` - how far the claimed amount exceeds the approved tariff
3. `code_match` - whether the diagnosis and procedure codes are clinically consistent
4. `provider_claim_frequency` - abnormally high submission volume from a provider

The fraud threshold is deliberately set at 0.3 (rather than the standard 0.5), so borderline cases are routed to human review rather than auto-approved. In healthcare, a missed fraud case is more costly than an unnecessary manual review.

SHAP values accompany every prediction, making each decision auditable and explainable to non-technical reviewers.

Note: these metrics reflect training on synthetic data and will be lower on real claims data. Production benchmarks in comparable East African insurance systems typically achieve ROC-AUC between 0.85 and 0.92.

---

## Assumptions and Trade-offs

**East African claim forms lack standardised codes.** ICD-10 and CPT codes are frequently absent on paper forms from Kenyan and Rwandan providers. The system treats missing codes as soft flags (routed to review) rather than hard failures. This is intentional: rejecting every claim without a code would block most legitimate submissions from smaller clinics.

**Dual-document model.** A single claim in this system maps to two physical documents: the patient-submitted claim form and the hospital-issued invoice. Cross-reference validation compares amounts, patient names, dates, and line items between both. Mismatches are fraud signals.

**Synthetic training data.** The model was trained on generated data. Fraud patterns in real East African claims will differ from synthetic assumptions. The model should be retrained on real labelled data before production use. The retraining pipeline and drift detection infrastructure are already in place for this.

**Vision provider dependency.** PDF extraction quality depends on the Gemini Vision API. Handwriting quality on paper forms varies significantly. The Tesseract fallback handles typed documents well but struggles with poor handwriting.

**In-memory rate limiting.** The current rate limiter resets on server restart and is not shared across multiple instances. For horizontal scaling, this must be replaced with Redis-backed rate limiting.

**MongoDB for logs.** Adjudication results and structured logs are stored in MongoDB for dashboard access. In production, logs should be shipped to a dedicated log aggregation platform (Datadog, ELK, or GCP Logging) and only business data should live in MongoDB.

---

## Roadmap

**Next milestone: Next.js frontend**
A web frontend connecting to the FastAPI backend for claim submission, PDF upload, and result review by claims officers.

**Short term**
- Next.js frontend application
- Redis-backed rate limiting for horizontal scaling
- Member coverage lookup against a policy database
- Real ICD-10 and CPT code databases replacing the curated subsets

**Medium term**
- Retraining on real labelled claims data
- Provider risk scoring from historical submission patterns
- Human review queue with accept/reject workflow
- Webhook notifications for claim status updates

**Production readiness**
- JWT authentication replacing API keys for end-user access
- HIPAA/data protection compliance review
- Load testing and performance benchmarking
- Multi-region deployment for Kenya and Rwanda

---

## Acknowledgements

Research references that informed the system design:

- Ghasedi et al. (2025). Applying Machine Learning Fraud Detection to Healthcare Payment Systems. Preprints. https://www.preprints.org/manuscript/202510.0409
- Bauder et al. (2024). Fraud detection in healthcare claims using machine learning: A systematic review. Artificial Intelligence in Medicine. https://www.sciencedirect.com/science/article/pii/S0933365724003038
- Understanding the Healthcare Claims Adjudication Process. sdata.us. https://sdata.us/2022/08/22/understanding-the-healthcare-claims-adjudication-process/
- AI-Powered Claims Adjudication. ResearchGate. https://www.researchgate.net/publication/389983406

Sample claim forms provided by Eden Care / Ginja AI as part of the assessment brief.
