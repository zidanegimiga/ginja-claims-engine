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


