from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

claims_total = Counter(
    "ginja_claims_total",
    "Total claims adjudicated",
    ["decision", "stage", "source_type"],
)

adjudication_duration = Histogram(
    "ginja_adjudication_duration_seconds",
    "Time spent adjudicating a claim in seconds",
    ["decision"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

risk_score_histogram = Histogram(
    "ginja_risk_score",
    "Distribution of ML risk scores",
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)

auth_attempts = Counter(
    "ginja_auth_attempts_total",
    "Total authentication attempts",
    ["method", "outcome"],   # method: credentials|google|microsoft, outcome: success|failure
)

http_requests_total = Counter(
    "ginja_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

active_requests = Gauge(
    "ginja_active_requests",
    "Number of requests currently being processed",
)