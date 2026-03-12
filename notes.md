## Research sources

1. Applying Machine Learning Fraud Detection to Healthcare Payment Systems: An Adaptation Study 
https://www.preprints.org/manuscript/202510.0409

## Case study paper: 
https://www.researchgate.net/publication/389983406_AI-Powered_Claims_Adjudication_Redefining_Accuracy_and_Speed_in_Healthcare_Reimbursement_Technological_Innovations_in_AI-Powered_Claims_Adjudication

Decision-support feature routing complex claims to human experts while processing simple claims automatically. 
Real time adjudication of healthcare claims model enables healthcare providers to streamline the workflow and guarantee quicker reimbursements to both providers and patients.

AI in healthcare claims adjudication makes the processing faster because it recognizes fraud patterns, predicts claims denial, confirms coverage policies and allows real-time claim verifications. This technology leads to faster payment cycles, a sharp decline in processing errors and better accuracy in medical claim adjudication decisions.

2. Fraud detection in healthcare claims using machine learning: A systematic review
https://www.sciencedirect.com/science/article/pii/S0933365724003038

Fraud committed by healthcare providers was the most prevalent, followed by fraud committed by patients.

### Challenges:
These include inconsistent data, absence of data standardization and integration, privacy concerns, and a limited number of labeled fraudulent cases to train models on.


3. Claims adjudication process
https://sdata.us/2022/08/22/understanding-the-healthcare-claims-adjudication-process/

- checks for accuracy and relevancy
- Claims is ingested. Duplicate claims check is performed. Personal patient data is confirmed.
- Detailed information check which will look for diagnosis and procedure codes, and match patient ID to patient DOB, which is verified by Payer internal records. In this stage, the patient is confirmed to be a participating member of the insurance plan, and their member number is cross-referenced to determine coverage. 
- Decision is made: paid, pending, or denied. Claim adjudication results in an Explanation of Benefits (EOB) or Electronic Remittance Advice that explains how the Payer came to that decision.



## Sample claims forms analysis:

### Document 1: Nairobi Lifecare Hospital Outpatient Invoice 
Format: PDF (digitally typed)
A clean system-generated invoice. Fields:

Hospital name, Invoice number
Full name, Insurance Member number, Hospital number
Visit type (Dental in this case)
Phone, Date
Line items: Service description + Amount in KES
Total amount

### Document 2: ECM Health Insurance Claims Form 
Format: PDF (mixed: printed form + handwritten fill)
Actual Eden Care claim form.

Fields:
### Patient Details:

Visit ID, Membership number
Surname, First name, Date of birth, Gender
Cellphone, Email

### Medical Practitioner Details:

Doctor name, Specialization, RMDC Registration number

### Treatment Details:

Treatment date, Referring doctor, Healthcare facility
Final Diagnosis ICD Code (blank here!), Diagnosis description (handwritten: "Bilateral Breast Cysts")
Pre-authorisation number, Type of care (Outpatient/Optical/Maternity/Inpatient/Dental)

### Services/Items Claimed:

RMPC Procedure Code, Procedure description, Total Billed, Co-pay Amount, Total Claimed
Row 1: Ultrasound (Breast) — 2800, 0, 2800
Row 2: Consultation — 1500, 1500
Totals: 4300, 0, 4300
Patient signature + date, Doctor signature + date

## Critical observations:
1. The ICD code field is blank but the description is handwritten. System needs to handle missing codes gracefully and infer them where possible.
2. The invoice and the claim form are two separate documents that belong together. The invoice comes from the hospital (like a receipt), the claim form is submitted by the patient to the insurer. Together they form one claim.
3. The amounts between the two documents don't always match — the invoice shows 17,000 KES (dental), the claim form shows 4,300 KES (outpatient). These are different patients but in production, amount mismatches between invoice and claim form are a major fraud signal.
The handwriting varies significantly — "Avenue Hospital" is quite clear, "Bilateral Breast Cysts" is readable but messy. This is exactly why we need a vision model rather than just basic text extraction.
This changes our data model slightly. A claim in our system is not one document — it's a pair: claim form + invoice. Our extractor needs to handle both and reconcile them.


# Training Notes
Needed to install OpenMP for MacOS: `brew install libomp`
Precision 0.891 — of every 100 claims the model flagged as fraud, 89 actually were fraud. Only 11 were false accusations against legitimate claims.
Recall 0.950 — of every 100 actual fraud cases, the model caught 95 of them. Only 5 slipped through undetected.
ROC-AUC 0.978 — on a scale of 0.5 (random guessing) to 1.0 (perfect), the model scores 0.978. Extremely strong.

Confusion matrix:

173 legitimate claims correctly approved
57 fraud cases correctly caught
7 legitimate claims wrongly flagged (false positives — minor inconvenience)
3 fraud cases missed (false negatives — the costly ones)

The SHAP rankings tell a clear story:
provider_is_high_risk is the strongest signal — who submits the claim matters most
amount_deviation_pct is second — how much above tariff is the strongest financial signal
code_match is third — mismatched diagnosis and procedure codes are a strong fraud indicator
is_duplicate scored zero — this is because our duplicate detection in synthetic data wasn't frequent enough to create a learnable pattern.

# Prediction model building
Deliberately setting the Pass threshold low (0.3) so borderline cases go to human review rather than being auto-approved. 
In healthcare, false negatives (missed fraud) are more costly than false positives (unnecessary reviews).

Upon running the model, it outputs:
```
(venv) zedane@Zidanes-MacBook-M4 ginja-claims-engine % python model/predict.py
Running prediction on test claim...

Decision : Fail
Risk Score : 0.9994
Confidence : 0.9989

Reasons:
  • Claimed amount is 194.0% above the approved tariff
  • Procedure code does not match the submitted diagnosis code
  • Provider has an elevated risk profile based on historical claim patterns

Feature Contributions (SHAP):
  provider_is_high_risk            2.7582  -> fraud
  code_match                       2.4284  -> fraud
  amount_deviation_pct             2.1954  -> fraud
  amount_ratio                     0.4540  -> fraud
  member_age                      -0.4237  -> legitimate
  provider_claim_frequency        -0.0717  -> legitimate
  member_claim_frequency          -0.0096  -> legitimate
  is_duplicate                     0.0000  -> legitimate
```

The prediction pipeline works exactly as designed. 
The test claim scored 0.9994. Essentially the model is 99.94% certain it's fraud, and the reasons are clear and human-readable.

The SHAP values tell a clear story:
- `member_age` actually pushed the score toward legitimate (-0.4237). That means the model learned that a 45-year-old making claims is slightly less suspicious than younger ages in our synthetic data. That's the model finding subtle patterns, not just obvious ones. 
- `provider_is_high_risk` is the strongest signal — who submits the claim matters most
- `code_match` is second — mismatched diagnosis and procedure codes are a strong fraud indicator
- `amount_deviation_pct` is third — how much above tariff is the strongest financial signal
- `is_duplicate` scored zero — this is because our duplicate detection in synthetic data wasn't frequent enough to create a learnable pattern.


# Building the Rules Engine

CURATED VALID CODE SETS
In production these would be loaded from a medical codes database. For the prototype we use curated subsets of real ICD-10 and CPT codes.

Maximum claim age: claims older than this are rejected. 90 days is standard in most insurance markets

Created hard override thresholds 
If claimed amount exceeds tariff by this much, auto-fail regardless of ML score (3x tariff)

Stage 1:
Performing basic validation. Basically fast checks that require no machine learning. A failure here stops processing immediately.

STAGE 2:
Detailed validation. Clinical and financial checks. Only reached if Stage 1 passes.


# Adjucator Engine snapshot
`CLM-TEST-001` — Passed cleanly. Risk score 0.0297 (nearly zero), confidence 94%. The model is certain this is legitimate.
`CLM-TEST-002` — Failed at Stage 2 in 0ms. Never even reached the ML model. The hard rule caught it instantly — 50,000 KES against a 4,000 KES tariff is 12.5x the approved rate. Hard override, immediate Fail. This is exactly how a real adjudication system works — don't waste compute on obvious cases.
`CLM-TEST-003` — Failed at Stage 3 via ML scoring. Risk score 0.9991. Three clear reasons: amount above tariff, mismatched codes, high-risk provider with suspicious volume. The model caught all three signals simultaneously.

```
(venv) zedane@Zidanes-MacBook-M4 ginja-claims-engine % python -m scripts.test_adjudicator

=======================================================
Testing claim: CLM-TEST-001
Decision     : Pass
Risk Score   : 0.0297
Confidence   : 0.9406
Stage        : 3
Reasons:
  • Claim meets all validation criteria
Processing   : 554ms

=======================================================
Testing claim: CLM-TEST-002
Decision     : Fail
Risk Score   : 1.0
Confidence   : 1.0
Stage        : 2
Reasons:
  • Claimed amount (50000 KES) exceeds 3.0x the approved tariff (4000 KES)
Processing   : 0ms

=======================================================
Testing claim: CLM-TEST-003
Decision     : Fail
Risk Score   : 0.9991
Confidence   : 0.9982
Stage        : 3
Reasons:
  • Claimed amount is 45.0% above the approved tariff
  • Procedure code does not match the submitted diagnosis code
  • Provider has an elevated risk profile based on historical claim patterns
  • Provider has submitted 35 claims — significantly above average
Processing   : 8ms
```
