from pathlib import Path
from datetime import datetime, timedelta
import random
import pandas as pd
import numpy as np


# ============================================================
# CYBERNOVA IIS WEB SERVER LOG GENERATOR
# Generates:
# 1. Raw IIS-style web logs
# 2. Cleaned web analytics logs
# 3. Web behaviour features by client
# 4. Merged CRM + web analytics dataset
# ============================================================

print("Starting CyberNova IIS web log generator...")

RANDOM_SEED = 42
N_LOGS = 23200

random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

SALES_FILE = DATA_DIR / "Cybernova_Final_Intelligence_v2.csv"

RAW_IIS_FILE = DATA_DIR / "iis_web_logs_raw.csv"
CLEANED_IIS_FILE = DATA_DIR / "iis_web_logs_cleaned.csv"
WEB_FEATURES_FILE = DATA_DIR / "web_features_by_client.csv"
MERGED_OUTPUT_FILE = DATA_DIR / "Cybernova_Final_Intelligence_v3_web.csv"


# ============================================================
# LOAD SALES DATA
# ============================================================

if not SALES_FILE.exists():
    raise FileNotFoundError(
        f"Could not find {SALES_FILE}. "
        "Make sure Cybernova_Final_Intelligence_v2.csv is inside the data folder."
    )

sales_df = pd.read_csv(SALES_FILE)

if "client_id" not in sales_df.columns:
    raise ValueError("Your sales dataset must contain a client_id column.")

sales_df["client_id"] = sales_df["client_id"].astype(str)

print(f"Loaded sales dataset: {len(sales_df):,} rows")


# ============================================================
# ADD SAFE FALLBACK COLUMNS
# ============================================================

fallbacks = {
    "country": "Unknown",
    "city": "Unknown",
    "service_type": "Cyber Security Service",
    "marketing_channel": "Direct",
    "campaign_name": "Organic Visit",
    "current_stage": "Inquiry",
    "converted": 0
}

for col, default in fallbacks.items():
    if col not in sales_df.columns:
        sales_df[col] = default

if "service_type" not in sales_df.columns and "service" in sales_df.columns:
    sales_df["service_type"] = sales_df["service"]


# ============================================================
# WEBSITE EVENT DESIGN
# ============================================================

EVENT_TO_URI = {
    "Homepage Visit": "/",
    "Services Page View": "/services",
    "Pricing Page View": "/pricing",
    "Case Study View": "/case-studies",
    "Schedule Demo Request": "/schedule-demo",
    "AI Assistant Request": "/ai-assistant",
    "Promotional Event Request": "/events/webinar",
    "Proposal Download": "/proposal/download",
    "Contract Confirmation": "/contract/confirm",
    "Contact Form Submit": "/contact"
}

STANDARD_EVENTS = [
    "Homepage Visit",
    "Services Page View",
    "Pricing Page View",
    "Case Study View",
    "Contact Form Submit"
]

HIGH_INTENT_EVENTS = [
    "Schedule Demo Request",
    "AI Assistant Request",
    "Promotional Event Request",
    "Proposal Download",
    "Contract Confirmation"
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) Firefox/126.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Mobile Safari/604.1",
    "Mozilla/5.0 (Android 14; Mobile) Chrome/125.0"
]

REFERRERS = [
    "https://www.google.com/",
    "https://www.linkedin.com/",
    "https://www.facebook.com/",
    "https://www.cybernova.ai/",
    "https://newsletter.cybernova.ai/",
    "-"
]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def safe_value(row, column, default="Unknown"):
    value = row.get(column, default)

    if pd.isna(value) or str(value).strip() == "":
        return default

    return str(value)


def random_ip():
    return ".".join(str(random.randint(1, 254)) for _ in range(4))


def random_datetime():
    start_date = datetime(2025, 1, 1, 8, 0, 0)
    end_date = datetime(2025, 6, 30, 23, 59, 59)
    total_seconds = int((end_date - start_date).total_seconds())
    return start_date + timedelta(seconds=random.randint(0, total_seconds))


def choose_event(row):
    stage = safe_value(row, "current_stage", "Inquiry")

    try:
        converted = int(float(row.get("converted", 0)))
    except Exception:
        converted = 0

    if converted == 1 or stage == "Contract Confirmed":
        events = STANDARD_EVENTS + HIGH_INTENT_EVENTS
        weights = [16, 18, 12, 8, 8, 16, 12, 6, 4, 8]
        return random.choices(events, weights=weights, k=1)[0]

    if stage == "Proposal Sent":
        events = STANDARD_EVENTS + [
            "Schedule Demo Request",
            "AI Assistant Request",
            "Proposal Download"
        ]
        weights = [18, 20, 14, 8, 8, 16, 10, 6]
        return random.choices(events, weights=weights, k=1)[0]

    if stage == "Demo Requested":
        events = STANDARD_EVENTS + [
            "Schedule Demo Request",
            "AI Assistant Request",
            "Promotional Event Request"
        ]
        weights = [20, 22, 14, 9, 8, 16, 8, 3]
        return random.choices(events, weights=weights, k=1)[0]

    events = STANDARD_EVENTS + [
        "AI Assistant Request",
        "Promotional Event Request"
    ]
    weights = [28, 26, 14, 10, 8, 9, 5]
    return random.choices(events, weights=weights, k=1)[0]


def choose_status_code(event_type):
    if event_type in HIGH_INTENT_EVENTS:
        return random.choices(
            [200, 302, 404, 500],
            weights=[88, 7, 4, 1],
            k=1
        )[0]

    return random.choices(
        [200, 304, 404, 500],
        weights=[86, 8, 5, 1],
        k=1
    )[0]


def response_time_for_status(status_code):
    if status_code >= 500:
        return random.randint(900, 3500)

    if status_code == 404:
        return random.randint(300, 1200)

    return random.randint(80, 850)


# ============================================================
# GENERATE RAW IIS LOGS
# ============================================================

log_rows = []

for i in range(N_LOGS):
    row = sales_df.sample(1).iloc[0]

    client_id = safe_value(row, "client_id", f"CL{random.randint(10000, 99999)}")
    country = safe_value(row, "country", "Unknown")
    city = safe_value(row, "city", "Unknown")
    service_type = safe_value(row, "service_type", "Cyber Security Service")
    marketing_channel = safe_value(row, "marketing_channel", "Direct")
    campaign_name = safe_value(row, "campaign_name", "Organic Visit")

    event_time = random_datetime()
    session_id = f"SESS{random.randint(100000, 999999)}"
    event_type = choose_event(row)
    uri = EVENT_TO_URI.get(event_type, "/services")
    status_code = choose_status_code(event_type)
    response_time = response_time_for_status(status_code)

    query = (
        f"client_id={client_id}"
        f"&session_id={session_id}"
        f"&service={service_type.replace(' ', '+')}"
        f"&channel={marketing_channel.replace(' ', '+')}"
    )

    log_rows.append({
        "date": event_time.strftime("%Y-%m-%d"),
        "time": event_time.strftime("%H:%M:%S"),
        "s_ip": "127.0.0.1",
        "cs_method": "POST" if event_type in [
            "Contact Form Submit",
            "Schedule Demo Request",
            "Contract Confirmation"
        ] else "GET",
        "cs_uri_stem": uri,
        "cs_uri_query": query,
        "s_port": 443,
        "cs_username": "-",
        "c_ip": random_ip(),
        "cs_user_agent": random.choice(USER_AGENTS),
        "cs_referer": random.choice(REFERRERS),
        "sc_status": status_code,
        "sc_substatus": 0,
        "sc_win32_status": 0,
        "time_taken_ms": response_time,
        "client_id": client_id,
        "session_id": session_id,
        "country": country,
        "city": city,
        "service_type": service_type,
        "marketing_channel": marketing_channel,
        "campaign_name": campaign_name,
        "event_type": event_type
    })

raw_iis_df = pd.DataFrame(log_rows)
raw_iis_df.to_csv(RAW_IIS_FILE, index=False)

print(f"Raw IIS logs created: {len(raw_iis_df):,} rows")


# ============================================================
# CLEANED IIS LOGS
# ============================================================

cleaned_df = raw_iis_df.copy()

cleaned_df["event_datetime"] = pd.to_datetime(
    cleaned_df["date"] + " " + cleaned_df["time"],
    errors="coerce"
)

cleaned_df["is_error"] = cleaned_df["sc_status"].astype(int).ge(400).astype(int)
cleaned_df["is_success"] = cleaned_df["sc_status"].astype(int).between(200, 399).astype(int)

cleaned_df["is_demo_request"] = cleaned_df["event_type"].eq("Schedule Demo Request").astype(int)
cleaned_df["is_ai_assistant_request"] = cleaned_df["event_type"].eq("AI Assistant Request").astype(int)
cleaned_df["is_promotional_event_request"] = cleaned_df["event_type"].eq("Promotional Event Request").astype(int)
cleaned_df["is_contract_confirmation"] = cleaned_df["event_type"].eq("Contract Confirmation").astype(int)
cleaned_df["is_proposal_download"] = cleaned_df["event_type"].eq("Proposal Download").astype(int)
cleaned_df["is_high_intent"] = cleaned_df["event_type"].isin(HIGH_INTENT_EVENTS).astype(int)

cleaned_df.to_csv(CLEANED_IIS_FILE, index=False)

print(f"Cleaned IIS logs created: {len(cleaned_df):,} rows")


# ============================================================
# WEB FEATURES BY CLIENT
# ============================================================

features_df = cleaned_df.groupby("client_id").agg(
    total_web_requests=("client_id", "size"),
    unique_sessions=("session_id", "nunique"),
    web_visit_count=("client_id", "size"),
    demo_request_count=("is_demo_request", "sum"),
    ai_assistant_request_count=("is_ai_assistant_request", "sum"),
    promotional_event_count=("is_promotional_event_request", "sum"),
    contract_confirmation_count=("is_contract_confirmation", "sum"),
    proposal_download_count=("is_proposal_download", "sum"),
    high_intent_hits=("is_high_intent", "sum"),
    web_error_count=("is_error", "sum"),
    avg_response_time_ms=("time_taken_ms", "mean"),
    first_web_event=("event_datetime", "min"),
    last_web_event=("event_datetime", "max")
).reset_index()

features_df["avg_response_time_ms"] = features_df["avg_response_time_ms"].round(1)

top_pages = (
    cleaned_df.groupby(["client_id", "cs_uri_stem"])
    .size()
    .reset_index(name="page_hits")
    .sort_values(["client_id", "page_hits"], ascending=[True, False])
    .drop_duplicates("client_id")
    .rename(columns={"cs_uri_stem": "top_page"})
)

features_df = features_df.merge(
    top_pages[["client_id", "top_page"]],
    on="client_id",
    how="left"
)

features_df.to_csv(WEB_FEATURES_FILE, index=False)

print(f"Web features created: {len(features_df):,} client rows")


# ============================================================
# MERGE CRM + WEB FEATURES
# ============================================================

overlap_cols = [
    col for col in features_df.columns
    if col in sales_df.columns and col != "client_id"
]

sales_for_merge = sales_df.drop(columns=overlap_cols, errors="ignore")

merged_df = sales_for_merge.merge(
    features_df,
    on="client_id",
    how="left"
)

web_numeric_cols = [
    "total_web_requests",
    "unique_sessions",
    "web_visit_count",
    "demo_request_count",
    "ai_assistant_request_count",
    "promotional_event_count",
    "contract_confirmation_count",
    "proposal_download_count",
    "high_intent_hits",
    "web_error_count",
    "avg_response_time_ms"
]

for col in web_numeric_cols:
    if col in merged_df.columns:
        merged_df[col] = pd.to_numeric(merged_df[col], errors="coerce").fillna(0)

if "top_page" in merged_df.columns:
    merged_df["top_page"] = merged_df["top_page"].fillna("No web activity")
else:
    merged_df["top_page"] = "No web activity"

merged_df.to_csv(MERGED_OUTPUT_FILE, index=False)

print(f"Merged dashboard dataset created: {len(merged_df):,} rows")


# ============================================================
# FINAL SUMMARY
# ============================================================

print("")
print("CyberNova IIS web server log generation complete.")
print(f"Raw IIS logs saved to:      {RAW_IIS_FILE}")
print(f"Cleaned IIS logs saved to:  {CLEANED_IIS_FILE}")
print(f"Web features saved to:      {WEB_FEATURES_FILE}")
print(f"Merged v3 dataset saved to: {MERGED_OUTPUT_FILE}")
print("")
print("Top website events:")
print(cleaned_df["event_type"].value_counts().head(10).to_string())