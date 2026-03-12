import os
import random
import uuid
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from faker import Faker
from pymongo import MongoClient

load_dotenv()

# Faker generates realistic fake names, addresses, dates etc
fake = Faker()
random.seed(42)
np.random.seed(42)


# REFERENCE DATA
# These are realistic codes and values used in
# East African / Kenyan healthcare claims


# ICD-10 diagnosis codes common in East Africa
# Format: { code: (description, typical_procedure_codes) }
DIAGNOSIS_CODES = {
    "J06.9":  ("Acute upper respiratory infection", ["99213", "99214"]),
    "A09":    ("Diarrhoea and gastroenteritis", ["99213", "99214", "43239"]),
    "B50.9":  ("Malaria", ["99214", "99215", "87798"]),
    "J18.9":  ("Pneumonia", ["99215", "71046", "94640"]),
    "E11.9":  ("Type 2 diabetes", ["99214", "83036", "82947"]),
    "I10":    ("Hypertension", ["99213", "93000", "83036"]),
    "K29.7":  ("Gastritis", ["99213", "43239"]),
    "N39.0":  ("Urinary tract infection", ["99213", "81003"]),
    "A01.0":  ("Typhoid fever", ["99214", "87998"]),
    "Z34.00": ("Normal pregnancy supervision", ["99212", "76805", "59400"]),
}

# CPT procedure codes with approved tariff amounts in KES
# Format: { code: (description, base_tariff_kes) }
PROCEDURE_TARIFFS = {
    "99212": ("Office visit - minimal", 1500),
    "99213": ("Office visit - low complexity",  2500),
    "99214": ("Office visit - moderate", 4000),
    "99215": ("Office visit - high complexity", 6000),
    "71046": ("Chest X-ray", 3500),
    "83036": ("HbA1c blood test", 1800),
    "82947": ("Glucose blood test", 800),
    "93000": ("Electrocardiogram", 2500),
    "81003": ("Urinalysis", 600),
    "87798": ("Malaria rapid test", 1200),
    "87998": ("Typhoid test", 1500),
    "76805": ("Obstetric ultrasound",  4500),
    "43239": ("Upper GI endoscopy", 18000),
    "94640": ("Nebulisation treatment", 2000),
    "59400": ("Routine obstetric care", 35000),
}

PROVIDER_TYPES = [
    "hospital",
    "clinic",
    "pharmacy",
    "laboratory",
    "specialist",
]

# Kenyan counties for location
LOCATIONS = [
    "Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret",
    "Thika", "Malindi", "Kitale", "Garissa", "Kakamega",
]

# Pre-generate a pool of members and providers
# This lets us simulate repeat claims from the same people
NUM_MEMBERS   = 200
NUM_PROVIDERS = 50

MEMBER_IDS   = [f"MEM-{str(i).zfill(5)}" for i in range(1, NUM_MEMBERS + 1)]
PROVIDER_IDS = [f"PRV-{str(i).zfill(5)}" for i in range(1, NUM_PROVIDERS + 1)]

# Some providers are pre-designated as high risk
# This simulates real-world known bad actors
HIGH_RISK_PROVIDERS = set(random.sample(PROVIDER_IDS, 8))


# FEATURE HELPERS
# These compute the same features our ML model will use at prediction time


def compute_amount_deviation(claimed: float, tariff: float) -> float:
    """
    How much more than the approved tariff was claimed, as a percentage.
    e.g. claimed=5000, tariff=2500 -> deviation = 1.0 (100% above tariff)
    Fraud often shows large positive deviations.
    """
    if tariff == 0:
        return 0.0
    return round((claimed - tariff) / tariff, 4)


def compute_code_match(diagnosis_code: str, procedure_code: str) -> int:
    """
    Returns 1 if the procedure code is a valid match for the diagnosis.
    Returns 0 if they don't match — a common fraud signal called
    'upcoding' or 'unbundling'.
    """
    if diagnosis_code not in DIAGNOSIS_CODES:
        return 0
    valid_procedures = DIAGNOSIS_CODES[diagnosis_code][1]
    return 1 if procedure_code in valid_procedures else 0


# CLAIM GENERATORS
# We generate two kinds of claims:
#   - Legitimate: realistic amounts, matching codes
#   - Fraudulent: one or more fraud patterns applied

def generate_legitimate_claim(
    claim_date: datetime,
    member_claim_counts: dict,
    provider_claim_counts: dict,
) -> dict:
    """
    Generates a single realistic legitimate claim.
    Amounts are close to tariff (±15%).
    Diagnosis and procedure codes match.
    """
    diagnosis_code = random.choice(list(DIAGNOSIS_CODES.keys()))
    description, valid_procedures = DIAGNOSIS_CODES[diagnosis_code]
    procedure_code = random.choice(valid_procedures)

    _, base_tariff = PROCEDURE_TARIFFS.get(
        procedure_code, ("Unknown", 2000)
    )

    # Legitimate claims vary slightly from tariff due to
    # hospital-specific pricing, consumables, etc.
    variation   = random.uniform(-0.15, 0.15)
    claimed_amt = round(base_tariff * (1 + variation))

    member_id   = random.choice(MEMBER_IDS)
    provider_id = random.choice(
        [p for p in PROVIDER_IDS if p not in HIGH_RISK_PROVIDERS]
    )

    member_claim_counts[member_id]     = member_claim_counts.get(member_id, 0) + 1
    provider_claim_counts[provider_id] = provider_claim_counts.get(provider_id, 0) + 1

    return {
        "claim_id":              f"CLM-{uuid.uuid4().hex[:8].upper()}",
        "member_id":             member_id,
        "provider_id":           provider_id,
        "diagnosis_code":        diagnosis_code,
        "diagnosis_description": description,
        "procedure_code":        procedure_code,
        "procedure_description": PROCEDURE_TARIFFS[procedure_code][0],
        "claimed_amount":        claimed_amt,
        "approved_tariff":       base_tariff,
        "date_of_service":       claim_date.isoformat(),
        "provider_type":         random.choice(PROVIDER_TYPES),
        "location":              random.choice(LOCATIONS),
        "member_age":            random.randint(18, 75),
        "is_fraud":              0,
        "fraud_type":            None,
    }


def generate_fraudulent_claim(
    claim_date: datetime,
    member_claim_counts: dict,
    provider_claim_counts: dict,
) -> dict:
    """
    Generates a single fraudulent claim with one of five
    real-world fraud patterns applied.

    Fraud patterns:
    1. Upcoding       — billing for more expensive procedure than performed
    2. Tariff inflate — claiming far above approved tariff
    3. Phantom        — billing for service never rendered (mismatched codes)
    4. Duplicate      — same member, provider, date, procedure
    5. Unbundling     — abnormally high frequency from one provider
    """
    fraud_type = random.choice([
        "upcoding",
        "tariff_inflation",
        "phantom_billing",
        "duplicate",
        "unbundling",
    ])

    diagnosis_code = random.choice(list(DIAGNOSIS_CODES.keys()))
    description, valid_procedures = DIAGNOSIS_CODES[diagnosis_code]

    if fraud_type == "upcoding":
        # Bill for expensive procedure regardless of diagnosis
        procedure_code = random.choice(["43239", "59400", "99215"])
        _, base_tariff = PROCEDURE_TARIFFS.get(procedure_code, ("", 2000))
        claimed_amt    = round(base_tariff * random.uniform(1.0, 1.3))

    elif fraud_type == "tariff_inflation":
        procedure_code = random.choice(valid_procedures)
        _, base_tariff = PROCEDURE_TARIFFS.get(procedure_code, ("", 2000))
        # Inflate claim by 80%–300% above tariff
        claimed_amt    = round(base_tariff * random.uniform(1.8, 4.0))

    elif fraud_type == "phantom_billing":
        # Mismatched codes — procedure doesn't match diagnosis
        all_codes      = list(PROCEDURE_TARIFFS.keys())
        procedure_code = random.choice(
            [c for c in all_codes if c not in valid_procedures]
        )
        _, base_tariff = PROCEDURE_TARIFFS.get(procedure_code, ("", 2000))
        claimed_amt    = round(base_tariff * random.uniform(0.9, 1.2))

    elif fraud_type == "duplicate":
        procedure_code = random.choice(valid_procedures)
        _, base_tariff = PROCEDURE_TARIFFS.get(procedure_code, ("", 2000))
        claimed_amt    = round(base_tariff * random.uniform(0.95, 1.05))

    else:  # unbundling
        procedure_code = random.choice(valid_procedures)
        _, base_tariff = PROCEDURE_TARIFFS.get(procedure_code, ("", 2000))
        claimed_amt    = round(base_tariff * random.uniform(1.1, 1.5))

    # Fraudulent claims more likely from high risk providers
    provider_id = random.choice(
        list(HIGH_RISK_PROVIDERS) if random.random() < 0.7
        else PROVIDER_IDS
    )
    member_id = random.choice(MEMBER_IDS)

    member_claim_counts[member_id]     = member_claim_counts.get(member_id, 0) + 1
    provider_claim_counts[provider_id] = provider_claim_counts.get(provider_id, 0) + 1

    proc_info = PROCEDURE_TARIFFS.get(procedure_code, ("Unknown procedure", base_tariff))

    return {
        "claim_id":              f"CLM-{uuid.uuid4().hex[:8].upper()}",
        "member_id":             member_id,
        "provider_id":           provider_id,
        "diagnosis_code":        diagnosis_code,
        "diagnosis_description": description,
        "procedure_code":        procedure_code,
        "procedure_description": proc_info[0],
        "claimed_amount":        claimed_amt,
        "approved_tariff":       base_tariff,
        "date_of_service":       claim_date.isoformat(),
        "provider_type":         random.choice(PROVIDER_TYPES),
        "location":              random.choice(LOCATIONS),
        "member_age":            random.randint(18, 75),
        "is_fraud":              1,
        "fraud_type":            fraud_type,
    }


# FEATURE ENGINEERING
# Adds computed features to each raw claim.
# These are the inputs our ML model will learn from.

def add_features(
    claims: list[dict],
    member_claim_counts: dict,
    provider_claim_counts: dict,
) -> list[dict]:
    """
    Adds engineered features to every claim in the list.
    These features are what the XGBoost model will actually
    learn from — not the raw fields.
    """
    # Build a lookup of claim fingerprints for duplicate detection
    # A fingerprint is: member + provider + date + procedure
    seen_fingerprints: dict[str, int] = {}

    for claim in claims:
        proc   = claim["procedure_code"]
        tariff = claim["approved_tariff"]

        # 1. Amount deviation from approved tariff
        # High positive values = potential fraud
        claim["amount_deviation_pct"] = compute_amount_deviation(
            claim["claimed_amount"], tariff
        )

        # 2. Does the procedure code match the diagnosis?
        # Mismatch = potential phantom billing or upcoding
        claim["code_match"] = compute_code_match(
            claim["diagnosis_code"], proc
        )

        # 3. How many claims has this member submitted historically?
        # Very high frequency = potential abuse
        claim["member_claim_frequency"] = member_claim_counts.get(
            claim["member_id"], 1
        )

        # 4. How many claims has this provider submitted?
        # High provider frequency = potential mill fraud
        claim["provider_claim_frequency"] = provider_claim_counts.get(
            claim["provider_id"], 1
        )

        # 5. Is this provider flagged as high risk?
        claim["provider_is_high_risk"] = (
            1 if claim["provider_id"] in HIGH_RISK_PROVIDERS else 0
        )

        # 6. Duplicate detection
        # Same member + provider + date + procedure seen before?
        date_str     = claim["date_of_service"][:10]
        fingerprint  = f"{claim['member_id']}_{claim['provider_id']}_{date_str}_{proc}"
        is_duplicate = 1 if fingerprint in seen_fingerprints else 0
        seen_fingerprints[fingerprint] = 1
        claim["is_duplicate"] = is_duplicate

        # 7. Amount ratio (claimed vs tariff as a simple ratio)
        # Easier for the model to use than raw amounts
        claim["amount_ratio"] = round(
            claim["claimed_amount"] / tariff if tariff > 0 else 1.0, 4
        )

    return claims


# MAIN GENERATOR

def generate_dataset(
    num_claims: int = 1200,
    fraud_rate: float = 0.25,
) -> list[dict]:
    """
    Generates a full synthetic dataset of claims.

    num_claims : total number of claims to generate
    fraud_rate : proportion that are fraudulent (0.25 = 25%)

    We use 25% fraud rate — higher than real world (typically 5–10%)
    but necessary for training since we need enough fraud examples
    for the model to learn from. We document this assumption
    in the README.
    """
    num_fraud      = int(num_claims * fraud_rate)
    num_legitimate = num_claims - num_fraud

    print(f"Generating {num_legitimate} legitimate claims...")
    print(f"Generating {num_fraud} fraudulent claims...")

    # Track claim counts per member and provider across all claims
    # so frequency features are accurate
    member_claim_counts:   dict[str, int] = {}
    provider_claim_counts: dict[str, int] = {}

    # Generate claims spread across the last 12 months
    end_date   = datetime.now()
    start_date = end_date - timedelta(days=365)

    def random_date() -> datetime:
        delta = end_date - start_date
        return start_date + timedelta(days=random.randint(0, delta.days))

    claims = []

    for _ in range(num_legitimate):
        claims.append(generate_legitimate_claim(
            random_date(), member_claim_counts, provider_claim_counts
        ))

    for _ in range(num_fraud):
        claims.append(generate_fraudulent_claim(
            random_date(), member_claim_counts, provider_claim_counts
        ))

    # Shuffle so fraud and legitimate are mixed
    random.shuffle(claims)

    # Add engineered features to every claim
    claims = add_features(claims, member_claim_counts, provider_claim_counts)

    print(f"Total claims generated: {len(claims)}")
    return claims


def save_to_csv(claims: list[dict], path: str) -> None:
    dataframe = pd.DataFrame(claims)
    dataframe.to_csv(path, index=False)
    print(f"Saved {len(claims)} claims to {path}")


def save_to_mongodb(claims: list[dict]) -> None:
    uri     = os.getenv("MONGODB_URI")
    db_name = os.getenv("MONGODB_DB_NAME")

    client     = MongoClient(uri)
    db         = client[db_name]
    collection = db["training_claims"]

    # Clear existing training data before inserting fresh batch
    collection.delete_many({})
    collection.insert_many(claims)

    print(f"Saved {len(claims)} claims to MongoDB collection: training_claims")
    client.close()


if __name__ == "__main__":
    claims = generate_dataset(num_claims=1200, fraud_rate=0.25)

    # Save as CSV for model training
    os.makedirs("data/synthetic", exist_ok=True)
    save_to_csv(claims, "data/synthetic/claims_training.csv")

    # Save to MongoDB
    save_to_mongodb(claims)

    # Print a summary
    dataframe  = pd.DataFrame(claims)
    fraud_count = dataframe["is_fraud"].sum()
    print(f"\nDataset summary:")
    print(f"  Total claims    : {len(dataframe)}")
    print(f"  Legitimate      : {len(dataframe) - fraud_count}")
    print(f"  Fraudulent      : {fraud_count}")
    print(f"  Fraud rate      : {fraud_count / len(dataframe):.1%}")
    print(f"\nFraud type breakdown:")
    print(dataframe[dataframe["is_fraud"] == 1]["fraud_type"].value_counts())
    print(f"\nSample claim:")
    print(dataframe.iloc[0].to_dict())