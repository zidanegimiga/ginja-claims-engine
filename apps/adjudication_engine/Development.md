# Development journal: Ginja Claims Engine

A full account of building the Ginja Claims Engine from scratch in a single session. This document covers every significant technical decision, the reasoning behind it, the bugs encountered, and what the production version of this system would look like differently.

-----------

## Table of contents

1. [Project brief and constraints](#project-brief-and-constraints)
2. [Understanding the domain](#understanding-the-domain)
3. [Architecture decisions](#architecture-decisions)
4. [Data and feature engineering](#data-and-feature-engineering)
5. [The machine learning model](#the-machine-learning-model)
6. [The rules engine](#the-rules-engine)
7. [The adjudication pipeline](#the-adjudication-pipeline)
8. [PDF extraction](#pdf-extraction)
9. [Cross-reference validation](#cross-reference-validation)
10. [API design](#api-design)
11. [Security implementation](#security-implementation)
12. [MLOps infrastructure](#mlops-infrastructure)
13. [Testing](#testing)
14. [Docker and deployment](#docker-and-deployment)
15. [Bugs encountered and fixed](#bugs-encountered-and-fixed)
16. [What would change in production](#what-would-change-in-production)
17. [Approach explanation and model decisions](#approach-explanation-and-model-decisions)

--------------

## Project brief and constraints

The brief asked for an AI-powered healthcare claims adjudication system with XGBoost as the core model, SHAP for explainability, a FastAPI backend, and a Streamlit dashboard. Sample PDF claim forms from real Eden Care submissions were provided.

The constraint that shaped every decision was this: it was a case study to be completed in one day, demo-recorded, and presented in a technical interview. That meant making deliberate choices about where to invest time and where to acknowledge gaps honestly.

The approach was to build production-grade infrastructure (auth, logging, drift detection, model registry, tests) around a model trained on synthetic data, then be transparent about what changes before real deployment. A clean architecture with honest documentation is more valuable to an interviewer than a model with impressive metrics built on shaky foundations.

---

## Understanding the domain

Before writing a line of code, the sample claim forms were analysed carefully. This changed the architecture.

The Nairobi Lifecare Hospital invoice is a clean system-generated PDF with line items, amounts in KES, and a hospital reference number. The ECM Health Insurance claim form is a mix of printed fields and handwriting, including a handwritten diagnosis description and blank ICD code fields.

This is the reality of East African healthcare claims. Two separate documents from two separate parties (hospital and patient) must be reconciled. Codes are frequently absent. Handwriting quality varies.

Three critical insights came from the forms analysis.

First, a claim in this system is not one document. It is a pair: the patient submits a claim form, the hospital issues an invoice. Both belong to the same claim event. The data model had to reflect this from the start.

Second, the absence of ICD-10 and CPT codes on paper forms is not an edge case. It is the common case. A system that hard-fails on missing codes would reject the majority of legitimate submissions from smaller clinics and private practitioners. The system needed to treat missing codes as soft flags routed to human review, not as hard failures.

Third, the amounts between the two documents do not always match. In the samples provided, the invoice showed 17,000 KES and the claim form showed 4,300 KES. These were different patients, but in production this kind of mismatch is a primary fraud signal. The cross-reference validator had to catch it.

---------------

## Architecture decisions

### Why FastAPI over Django or Flask?

FastAPI gives async support, automatic OpenAPI documentation, Pydantic validation, and a dependency injection system out of the box. For an ML service that will have concurrent requests and needs clear API documentation for a frontend consumer, it was the right choice. Flask requires too much assembly. Django is too heavy for an API-only service.

### Why MongoDB over PostgreSQL?

Claims data is semi-structured and variable. A claim from a paper form will have different fields present compared to a claim submitted as structured JSON. MongoDB's document model handles this naturally. Schema migrations are not needed when a new field appears in extracted data.

The trade-off: no ACID transactions across documents. For claims processing where you need guaranteed atomicity across updates (for example, marking a claim paid while updating a member's balance), PostgreSQL would be the right choice. For the scope of this system, MongoDB was appropriate.

### Why XGBoost over a neural network?

Three reasons. XGBoost works well on tabular data with engineered features, which is exactly what structured claims data is. Neural networks on tabular data rarely outperform gradient boosting without significantly more data. XGBoost is also fast at inference, which matters for real-time adjudication. And SHAP integration with XGBoost is mature and well-supported.

The deeper reason: explainability is not optional in healthcare adjudication. Every decision must be auditable. A black-box neural network that says "this claim is fraud because of latent features in layer 7" is not acceptable to an insurance regulator or a provider disputing a denial. SHAP values that say "the claimed amount was 194% above tariff, and the procedure code does not match the diagnosis" are.

### Why Streamlit over a custom frontend?

Time constraint. Streamlit lets you build a functional data dashboard without writing React components. The roadmap explicitly calls for a Next.js frontend. Streamlit is the right prototype tool when the priority is demonstrating the backend logic rather than polishing the UI.

### The provider abstraction for PDF extraction

Vision model APIs change frequently. Google has renamed and deprecated models multiple times in the past year alone. Building against a concrete implementation means every model change breaks production. The `BaseVisionProvider` abstract class means the extraction logic is completely decoupled from the specific API being called. Swapping from Gemini to Claude Vision to Ollama requires implementing one class and changing one environment variable.

----------------

## Data and feature engineering

The training dataset was generated synthetically with 1,200 claims at a 25% fraud rate. The fraud rate reflects estimates from the healthcare fraud literature, which places provider-committed fraud as the most prevalent category.

The features engineered from raw claim fields are:

`amount_deviation_pct` — the percentage difference between the claimed amount and the approved tariff. This is the most directly interpretable financial signal. A claim for 194% above tariff warrants immediate scrutiny.

`amount_ratio` — claimed amount divided by tariff. Captures non-linear relationships that percentage deviation misses at extreme values.

`provider_is_high_risk` — a binary flag based on a curated list of provider IDs with known elevated risk profiles. In production this would be derived from historical claim patterns rather than a static list.

`code_match` — binary flag indicating whether the procedure code is clinically consistent with the diagnosis code. Built from a curated mapping of valid ICD-10 to CPT code pairs. This catches a common fraud pattern where providers bill expensive procedures against minor diagnoses.

`provider_claim_frequency` — the number of claims submitted by this provider in the dataset. Unusually high frequency is a fraud signal, particularly for providers whose claim volume far exceeds patient population norms.

`member_claim_frequency` — equivalent metric for the member. Patients submitting claims at abnormally high frequency may indicate claim farming or identity fraud.

`is_duplicate` — binary flag for claims with matching member, provider, procedure, and date. This feature scored zero in SHAP importance, which revealed a gap in the synthetic data: duplicates were not frequent enough to create a learnable pattern. In real data this would be among the strongest signals.

One constraint deserves its own mention: training and serving parity. The `engineer_features()` function in `features/engineer.py` is used in both the training pipeline and the prediction pipeline. This is not optional. If features are computed differently at training time versus serving time, the model will produce incorrect predictions on real data. This class of bug is called training-serving skew and it is one of the most common causes of ML model degradation in production.

---

## The machine learning model

### Why a 0.3 fraud threshold?

The default binary classification threshold is 0.5. Claims with a fraud probability above 0.5 are flagged, below 0.5 are passed. We set the threshold at 0.3.

The reasoning is asymmetric cost. In healthcare fraud detection, two types of errors exist: false positives (flagging a legitimate claim) and false negatives (passing a fraudulent claim). A false positive inconveniences a legitimate provider and delays payment. A false negative costs the insurer money, potentially thousands of dollars per missed case, and may enable ongoing fraud patterns.

At 0.3, a claim with a 31% predicted fraud probability goes to human review rather than being auto-approved. The cost of routing 31%-probability claims to review is low. The cost of auto-approving genuinely fraudulent claims that score 31-49% is high.

### Model performance in context

The ROC-AUC of 0.978 is strong but reflects synthetic data. Synthetic data is cleaner, more balanced, and has less noise than real claims data. Real-world performance on East African healthcare claims would realistically fall in the 0.85 to 0.92 range based on comparable insurance fraud detection systems in the literature.

The confusion matrix on the test set:
- 173 legitimate claims correctly approved
- 57 fraud cases correctly caught
- 7 legitimate claims wrongly flagged (false positives)
- 3 fraud cases missed (false negatives)

The 3 missed fraud cases are the costly ones. The 7 wrongly flagged legitimate claims are routed to human review, which resolves them.

### SHAP values in practice

On the test claim with a 0.9994 fraud score, SHAP values showed:

```
provider_is_high_risk     2.7582  -> fraud
code_match                2.4284  -> fraud
amount_deviation_pct      2.1954  -> fraud
amount_ratio              0.4540  -> fraud
member_age               -0.4237  -> legitimate
provider_claim_frequency -0.0717  -> legitimate
```

The negative SHAP value for `member_age` is the most interesting signal. The model learned that a 45-year-old submitting a claim is slightly less suspicious than younger claimants in the synthetic data. This is not a manually encoded rule. The model found this pattern from the data. This kind of learned pattern is what distinguishes a gradient boosting model from a simple rule engine.

-------------

## The rules engine

### Why have rules at all if you have a model?

The model should not be asked to score claims that violate basic validity constraints. A claim dated ten years in the future, or with a negative claimed amount, or from a non-existent provider type, should not consume model inference time. Hard rules at Stage 1 and Stage 2 act as fast filters that stop obviously invalid claims before they reach the ML layer.

More importantly, some rules are regulatory requirements rather than statistical patterns. An insurer may be legally required to reject claims older than 90 days. That is a compliance rule, not a fraud signal. It does not belong in a machine learning model.

### The three-stage design

Stage 1 validates existence and basic logic: are required fields present, is the date valid, is the amount positive, is the provider type recognised?

Stage 2 validates clinical and financial consistency: do the codes make sense together, does the line item total match the claimed amount, does the claimed amount exceed the tariff by an unreasonable multiple?

The hard override at Stage 2 is important. If a claim is for 12.5x the approved tariff, the ML model does not need to score it. It fails immediately. In the test suite, CLM-TEST-002 (50,000 KES against a 4,000 KES tariff) failed at Stage 2 in 0ms without ever reaching the ML layer. This is how production adjudication systems work: do not waste compute on obvious cases.

Stage 3 runs the XGBoost model and combines its output with the cross-reference score from PDF validation using a 70/30 weighted blend.

### The soft flag escalation logic

A claim that passes all hard rules but accumulates soft flags (missing codes, minor discrepancies) is escalated from Pass to Flag rather than being auto-approved. This ensures borderline claims reach human review without hard-failing claims that are merely incomplete.

------------

## PDF extraction

### The vision model approach

Tesseract OCR extracts text but cannot understand form structure. It does not know that a string appearing after the label "Member Number:" is the member's ID. It returns raw text and the caller must parse it.

Vision models with multimodal capability can understand both the visual layout and the semantic meaning of what they see. Gemini Vision returns structured field extractions: it understands that "1538500" is a member ID because it is in the membership number field of a claim form, not because of a regex pattern.

This matters enormously for handwritten forms. "Bilateral Breast Cysts" written by hand in the diagnosis description field is extracted correctly by Gemini. A traditional OCR and parsing pipeline would either miss it or require extensive regular expression engineering.

### The fallback chain

The extraction pipeline attempts each provider in sequence and returns the first successful result. In practice: Gemini is fast, accurate on handwriting, and returns structured JSON. Tesseract is available offline, requires no API key, and works reliably on clean typed documents. The chain means the system continues functioning if the Gemini API is unavailable.

### What Gemini extracted from the real forms

From the ECM Health Insurance claim form: claim ID, member ID, patient name, amount (4,300 KES), date of service, location, provider type, patient age. Additionally, Gemini noted a date discrepancy between the treatment date (2025) and the signature date (2026), without being explicitly instructed to check for this.

What was missing: provider ID (the form does not have one, it uses a provider name), ICD-10 diagnosis code (the field was blank, only a handwritten description was present), and procedure code (the form used free text "Ultrasound (Breast)" rather than a code).

This was the expected result. East African claim forms at small and medium clinics frequently omit structured codes. The system handles this gracefully.

-------------

## Cross-reference validation

When both a claim form and an invoice are uploaded together, the cross-reference validator compares them across five dimensions: claimed amount, patient name (fuzzy matched to handle word order differences), date of service (within a 3-day tolerance for billing delays), member ID, and line item sum.

Each check produces either a confirmation or a mismatch. Mismatches are weighted by severity and aggregated into a cross-reference score between 0 and 1. This score is blended with the ML fraud score at Stage 3.

### The fuzzy name matching logic

Name matching cannot be exact. Names appear in different word orders on different forms. "Sharma Siddharth" and "Siddharth Sharma" are the same person. "S. Sharma" and "Siddharth Sharma" are the same person.

The initial matching implementation was too permissive: "John Doe" and "Jane Doe" shared the word "Doe" and were incorrectly identified as a match. This was caught by the test suite (`test_patient_name_mismatch_detected`), and the matching function was tightened to require a majority of the shorter name's words to overlap, with a minimum of two matching words. Single-word overlap is no longer sufficient.

This is an example of a test that caught a real production bug rather than simply confirming existing behaviour.

-------------

## API design

### Versioning from day one

All routes are prefixed with `/api/v1/`. This is not premature optimisation. Once a frontend or third-party integration is consuming the API, changing endpoint paths breaks those consumers. The version prefix means `/api/v2/` can be introduced without removing `/api/v1/`, allowing gradual migration.

### The dependency injection pattern for authentication

The initial authentication implementation called `require_write(request)` at the start of each route handler function. This was incorrect: FastAPI validated the request body against the Pydantic schema before executing the handler, which meant an unauthenticated request with an invalid body would receive a 422 validation error rather than a 401 authentication error. The order of operations was wrong.

The fix is FastAPI's `Depends()` system. When authentication is declared as a dependency parameter (`auth: dict = Depends(require_write)`), FastAPI guarantees it runs before schema validation. Unauthenticated requests now receive 401 before the body is inspected.

### Why not JWT for authentication?

JWT is the right choice for end-user authentication: a user logs in with credentials and receives a short-lived token that identifies them across requests. API key authentication is the right choice for service-to-service communication: a frontend application or a batch processing system authenticates with a stable key that identifies the service.

This system's current consumers are services (the Streamlit dashboard, the CLI test scripts). API keys are appropriate. The roadmap calls for JWT when end-user login is introduced.

-------------

## Security implementation

### API key storage

API keys are stored as SHA-256 hashes. The plaintext key is shown exactly once at creation and never stored. If a key is lost, it must be regenerated. This mirrors the pattern used by Stripe, GitHub, and most production API platforms.

The key format is `ginja_<32 random bytes as hex>`. The `ginja_` prefix makes keys identifiable in logs and error messages without revealing the secret. If a key is accidentally committed to a Git repository, the prefix allows automated scanning tools to detect and alert on the exposure.

### MongoDB indexes for authentication performance

Without an index on `key_hash`, every API request requires a full collection scan of all API keys. This is acceptable with 10 keys. It is catastrophic with 10,000 keys at high request volume. The `setup_db.py` script creates a unique index on `key_hash` so key lookup is always O(log n) regardless of how many keys exist.

### Authentication failure logging

Every failed authentication attempt is logged to a separate `auth_failures` collection with the client IP, the reason (missing key, invalid key, expired key, insufficient scope), and a timestamp. This creates an audit trail for security monitoring. A spike in failures from a single IP indicates a brute force attempt.

### Rate limiting

The current rate limiter is in-memory with a 60 requests per minute limit per IP. Its limitation is that it resets on server restart and is not shared across multiple server instances. For the prototype this is acceptable. For production horizontal scaling, this must be Redis-backed.

### Input validation

Pydantic validates every request body before it reaches business logic. Type coercion, field presence, and value constraints are enforced at the boundary. The adjudication engine never receives a claim with a negative amount or a non-string claim ID.

------------------------

## MLOps infrastructure

### Model registry

Every trained model is registered in MongoDB with a content hash, training metrics, the training dataset path, and a lifecycle status (staging, production, retired). Promoting a model from staging to production is an explicit action, not an implicit side effect of training.

The content hash prevents a subtle failure mode: a model file that is silently corrupted or overwritten will have a different hash than the registered version, and the mismatch will be detected at load time.

### PSI-based drift detection

Population Stability Index measures how much the distribution of a feature has shifted between the training population and recent production data. A PSI above 0.2 on any feature triggers a drift alert.

The intuition is straightforward: if the model was trained when the average claimed amount was 5,000 KES, and recent claims average 15,000 KES, the model's learned relationship between amount deviation and fraud risk may no longer be calibrated correctly. It needs retraining on current data.

### Retraining pipeline

The `scripts/retrain.py` script runs drift detection, triggers retraining if drift is detected (or unconditionally if forced), evaluates the new model against minimum performance thresholds (ROC-AUC >= 0.85, Recall >= 0.80), and registers the new model in staging. Promotion to production is a separate manual step to allow human review of new model behaviour before it affects live decisions.

### Structured logging

Every log line is JSON with consistent fields: timestamp, level, logger name, message, and any additional context. This format is directly ingestible by log aggregation platforms without custom parsing. The key insight: logs are written for machines to read, not humans. Human-readable logs are a debugging convenience; machine-parseable logs are a production necessity.

---------------------

## Testing

27 tests across three modules.

`test_features.py` covers feature engineering edge cases: what happens when `approved_tariff` is None, when `member_age` is None, when a provider appears on the high-risk list. These tests verified that the `or default` defensive patterns in `engineer_features()` worked correctly.

`test_rules.py` covers Stage 1 and Stage 2 rule logic: valid claims pass, missing required fields fail, negative amounts fail, future dates fail, stale claims fail, hard overrides trigger at 3x tariff, missing codes are soft flags rather than hard failures.

`test_cross_reference.py` covers document reconciliation: consistent documents pass, amount mismatches are detected, patient name mismatches are detected (including the word order case), line item sum mismatches are flagged.

Two tests failed on first run and both caught real production bugs.

`test_future_date_fails` failed because the date validation code checked for stale claims (older than 90 days) but not for future dates. A claim dated 10 days in the future passed Stage 1 validation. The fix added a future-date check before the staleness check.

`test_patient_name_mismatch_detected` failed because the fuzzy name matching was too permissive. "John Doe" and "Jane Doe" shared the surname "Doe" and were incorrectly matched. The fix tightened the matching function to require a majority of words to overlap rather than any single word.

Both failures represent claims that would have behaved incorrectly in production: claims dated in the future would have been accepted, and cross-reference validation would have failed to catch a name mismatch when only the first name differed.

--------------------

## Docker and deployment

### Why two containers share one image

The API and the Streamlit dashboard are built from the same Dockerfile. They run different commands (uvicorn for the API, streamlit for the dashboard) but share identical dependencies. A single image means one build, one set of security patches, one dependency lock. In production you would likely split these as the frontend grows in complexity, but for the current scope it is the correct approach.

### The build context size problem

The initial Docker build attempted to copy 1.05GB into the container build context. The cause: the `venv/` directory was not properly excluded by `.dockerignore`. At 1.05GB, this caused Docker's BuildKit to run out of disk space when attempting to write the layer metadata.

The fix: correcting `.dockerignore` to explicitly exclude `venv/` and `**/__pycache__/`, and running `docker system prune` to reclaim disk space before rebuilding.

### The NVIDIA GPU library problem

XGBoost pulled `nvidia-nccl-cu12` as an optional dependency, adding 293MB of NVIDIA GPU communication libraries to a container that runs on CPU-only infrastructure (the M4 Mac and any standard cloud VM). The fix: uninstall `nvidia-nccl-cu12` explicitly after the main pip install step in the Dockerfile.

--------------------

## Bugs encountered and fixed

**XGBoost and OpenMP on Apple M4:** XGBoost requires OpenMP for multi-threaded training. On Apple Silicon Macs, OpenMP is not installed by default. The symptom was an import error mentioning `libgomp`. The fix: `brew install libomp`.

**The `google-generativeai` deprecation:** The original Gemini integration used the `google-generativeai` package. This package was deprecated and replaced with `google-genai`. The new package has a different API surface. The provider implementation was rewritten against the new package.

**`int(None)` crash in feature engineering:** When `approved_tariff` or `member_age` was missing from a claim, the feature engineering function crashed attempting to compute numerical features. The fix: replace direct type conversions with `or default` patterns that substitute zero or a reasonable default when values are absent.

**`str.startswith()` on None in rules engine:** The rules engine called `.startswith()` on provider type and diagnosis code fields without null-checking first. When these fields were absent (common in partially extracted PDF claims), the function crashed. The fix: add `if field and field.startswith(...)` null guards throughout the rules engine.

**Reserved logging field name collision:** Python's logging system reserves the field name `name` for the logger's own name. Passing `name` as a key in the `extra` dictionary raises a `KeyError`. The fix: rename the field to `key_name` in all logger calls in `api/auth.py`.

**FastAPI dependency order for authentication:** As described in the API design section, calling authentication manually inside a route handler allows FastAPI to validate the request body before authentication runs. The fix: declare authentication as a `Depends()` parameter to guarantee it runs first.

**Python parameter ordering with defaults:** FastAPI route functions that mix parameters with defaults (`Depends()`, `Query()`) and parameters without defaults (`Request`) must place parameters without defaults before parameters with defaults. Violating this order produces a `SyntaxError: parameter without a default follows parameter with a default`.

--------------------

## What would change in production

**Data.** The most important change is retraining on real labelled claims from actual Eden Care submissions. The synthetic training data gave the model a foundation, but real fraud patterns in East African claims will differ from synthetic assumptions in ways that only surface at scale. Alongside that, the provider risk database needs to be built from historical claim patterns rather than a static curated list, and member eligibility checks need to run against a live policy database. The curated ICD-10/CPT code subsets would be replaced with the full code databases.

**Infrastructure.** The in-memory rate limiter needs to move to Redis for horizontal scaling. Logs should be shipped to a dedicated aggregation platform (Datadog or ELK) rather than stored in MongoDB alongside business data. Secrets need to move from `.env` files to a proper manager like AWS Secrets Manager or HashiCorp Vault. And the system needs HTTPS with TLS termination at the load balancer, plus database connection pooling for high-concurrency workloads.

**Security.** Claims officers logging in via the frontend should authenticate with JWT. API keys stay, but only for service-to-service communication (the frontend backend, batch processors). Keys should rotate on a schedule. Given the sensitivity of healthcare data, penetration testing is a prerequisite for launch, not an afterthought.

**Model.** The model should be retrained on real data after 3 to 6 months of production claims. The feedback loop is the most important mechanism: human reviewers' accept/reject decisions become training labels, which means every manual review improves the next model version. Feature drift should be monitored monthly, with automated retraining triggered when PSI exceeds the threshold. New model versions should be A/B tested on a small percentage of traffic before full rollout.

**Compliance.** Claims data falls under Kenya's Data Protection Act 2019 and Rwanda's Law No. 058/2021. A data protection impact assessment is required before launch. Every adjudication decision and every model retrain needs a complete audit trail. Data retention and deletion policies for claims records need to be defined and enforced.

--------------------

## Approach explanation and model decisions

The core question the system answers is: given a healthcare claim, should it be paid automatically, sent to human review, or rejected outright?

The answer sits at the intersection of rules (compliance requirements and clinical logic), machine learning (fraud pattern recognition), and human judgment (borderline cases). The three-stage pipeline reflects this: hard rules first, then soft rules, then ML scoring. The escalation logic ensures that claims which pass all automated checks but accumulate soft flags still reach a human reviewer.

XGBoost was chosen over a neural network because the problem is tabular, the data volume is modest, inference speed matters, and explainability is non-negotiable. Every claim decision must be auditable. SHAP values provide that audit trail in a format that is interpretable to a non-technical claims officer: "the provider has submitted 35 claims, significantly above average" is understandable. "Feature activation in layer 4 node 237" is not.

The threshold of 0.3 reflects the asymmetric cost of errors in healthcare fraud. The system is designed to be conservative: when in doubt, route to review. This accepts a higher false positive rate in exchange for a lower false negative rate. In practice, human review of borderline cases also generates labelled training data for the next model version, which is a meaningful long-term benefit.

The most important potential improvement is the feedback loop. A model that never receives feedback from reviewers will drift over time as fraud patterns evolve. Building the human review queue and the reviewer feedback mechanism is the highest-priority next step after the Next.js frontend.

