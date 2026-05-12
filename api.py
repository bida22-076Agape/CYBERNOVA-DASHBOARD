from flask import Flask, jsonify
from pathlib import Path
from datetime import datetime, timedelta
import random
import pandas as pd
import numpy as np


# ============================================================
# CYBERNOVA LIVE API
# Purpose:
# - Runs separately from Streamlit.
# - Feeds live CRM/sales data into app.py.
# - Adds matching IIS web server log rows.
# - Supports Web Analytics, Sales, Marketing, and Executive pages.
# ============================================================

app = Flask(__name__)


# ============================================================
# FILE PATHS
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"

SALES_FILE_V3 = DATA_DIR / "Cybernova_Final_Intelligence_v3_web.csv"
SALES_FILE_V2 = DATA_DIR / "Cybernova_Final_Intelligence_v2.csv"

RAW_IIS_FILE = DATA_DIR / "iis_web_logs_raw.csv"
CLEANED_IIS_FILE = DATA_DIR / "iis_web_logs_cleaned.csv"


# ============================================================
# SETTINGS
# ============================================================
MAX_STORED_ROWS = 3000
RETURN_ROWS = 800


SERVICE_REVENUE_RANGES = {
    "Fraud Monitoring Solution": (8000, 45000),
    "Threat Detection Platform": (6000, 38000),
    "Executive Cyber Training": (3000, 22000),
    "SME Security Package": (2500, 18000),
    "Cloud Security Analytics": (7000, 32000),
    "AI Security Audit": (9000, 48000),
}


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
    "Contact Form Submit": "/contact",
}


HIGH_INTENT_EVENTS = [
    "Schedule Demo Request",
    "AI Assistant Request",
    "Promotional Event Request",
    "Proposal Download",
    "Contract Confirmation",
]


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) Firefox/126.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Mobile Safari/604.1",
    "Mozilla/5.0 (Android 14; Mobile) Chrome/125.0",
]


REFERRERS = [
    "https://www.google.com/",
    "https://www.linkedin.com/",
    "https://www.facebook.com/",
    "https://www.cybernova.ai/",
    "https://newsletter.cybernova.ai/",
    "-",
]


# ============================================================
# SAFE VALUE HELPERS
# ============================================================
def safe_value(row, column, default="Unknown"):
    try:
        value = row.get(column, default)

        if pd.isna(value) or str(value).strip() == "":
            return default

        return str(value)

    except Exception:
        return default


def safe_int(row, column, default=0):
    try:
        value = row.get(column, default)

        if pd.isna(value):
            return default

        return int(float(value))

    except Exception:
        return default


def random_ip():
    return ".".join(str(random.randint(1, 254)) for _ in range(4))


# ============================================================
# LOAD STARTING DATASET
# ============================================================
def load_initial_data():
    if SALES_FILE_V3.exists():
        data_file = SALES_FILE_V3
        print(f"Loaded web-enhanced dataset: {data_file}", flush=True)

    elif SALES_FILE_V2.exists():
        data_file = SALES_FILE_V2
        print(f"Loaded original dataset: {data_file}", flush=True)

    else:
        raise FileNotFoundError(
            "No CyberNova dataset found. Expected either "
            "data/Cybernova_Final_Intelligence_v3_web.csv or "
            "data/Cybernova_Final_Intelligence_v2.csv"
        )

    df = pd.read_csv(data_file)

    if "service_type" not in df.columns and "service" in df.columns:
        df["service_type"] = df["service"]

    date_columns = [
        "inquiry_date",
        "close_date",
        "demo_date",
        "proposal_date",
        "first_web_event",
        "last_web_event",
    ]

    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    fallback_columns = {
        "client_id": "Unknown",
        "country": "Unknown",
        "country_group": "Unknown",
        "city": "Unknown",
        "industry": "Unknown",
        "company_size": "Unknown",
        "service_type": "Cyber Security Service",
        "service_category": "Cyber Security",
        "marketing_channel": "Direct",
        "campaign_name": "Live Website Visit",
        "current_stage": "Inquiry",
        "sales_rep_name": "Unassigned",
        "sales_team": "Unassigned",
        "converted": 0,
        "lead_score": 50,
        "intent_score": 50,
        "commercial_readiness_score": 50,
        "actual_revenue": 0,
        "forecast_revenue": 0,
        "target_revenue": 0,
        "revenue_gap": 0,
        "conversion_probability": 0.25,
        "web_visit_count": 0,
        "total_web_requests": 0,
        "unique_sessions": 0,
        "demo_request_count": 0,
        "ai_assistant_request_count": 0,
        "promotional_event_count": 0,
        "contract_confirmation_count": 0,
        "proposal_download_count": 0,
        "high_intent_hits": 0,
        "web_error_count": 0,
        "avg_response_time_ms": 0,
        "top_page": "No web activity",
    }

    for col, default in fallback_columns.items():
        if col not in df.columns:
            df[col] = default

        df[col] = df[col].fillna(default)

    numeric_columns = [
        "converted",
        "lead_score",
        "intent_score",
        "commercial_readiness_score",
        "actual_revenue",
        "forecast_revenue",
        "target_revenue",
        "revenue_gap",
        "conversion_probability",
        "web_visit_count",
        "total_web_requests",
        "unique_sessions",
        "demo_request_count",
        "ai_assistant_request_count",
        "promotional_event_count",
        "contract_confirmation_count",
        "proposal_download_count",
        "high_intent_hits",
        "web_error_count",
        "avg_response_time_ms",
    ]

    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    if "conversion_probability" in df.columns and df["conversion_probability"].max() > 1:
        df["conversion_probability"] = df["conversion_probability"] / 100

    return df


# ============================================================
# INITIAL LIVE DATA STORE
# ============================================================
base_df = load_initial_data()
current_data = base_df.tail(1500).copy().reset_index(drop=True)


# ============================================================
# LIVE CRM RECORD GENERATION
# ============================================================
def choose_live_stage(converted):
    if converted == 1:
        return random.choice(["Proposal Sent", "Contract Confirmed"])

    return random.choice([
        "Inquiry",
        "Demo Requested",
        "Proposal Sent",
    ])


def choose_live_events(stage, converted):
    events = [
        "Homepage Visit",
        "Services Page View",
        "Pricing Page View",
    ]

    if random.random() < 0.55:
        events.append("AI Assistant Request")

    if random.random() < 0.35:
        events.append("Contact Form Submit")

    if stage in ["Demo Requested", "Proposal Sent", "Contract Confirmed"]:
        events.append("Schedule Demo Request")

    if random.random() < 0.25:
        events.append("Promotional Event Request")

    if stage in ["Proposal Sent", "Contract Confirmed"]:
        events.append("Proposal Download")

    if converted == 1 or stage == "Contract Confirmed":
        events.append("Contract Confirmation")

    return events


def generate_live_crm_records(records_to_add):
    new_records = []

    for _ in range(records_to_add):
        base_row = current_data.sample(1).iloc[0].copy()

        service = safe_value(base_row, "service_type", "Fraud Monitoring Solution")
        min_rev, max_rev = SERVICE_REVENUE_RANGES.get(service, (3000, 25000))

        converted = 1 if random.random() < 0.28 else 0
        stage = choose_live_stage(converted)

        new_row = base_row.copy()

        new_row["client_id"] = f"CL{random.randint(100000, 999999)}"
        new_row["inquiry_date"] = datetime.now() - timedelta(minutes=random.randint(0, 30))
        new_row["last_web_event"] = datetime.now()
        new_row["first_web_event"] = datetime.now() - timedelta(minutes=random.randint(1, 90))

        new_row["converted"] = converted
        new_row["current_stage"] = stage

        new_row["actual_revenue"] = round(random.uniform(min_rev, max_rev), 2) if converted == 1 else 0.0
        new_row["forecast_revenue"] = round(random.uniform(min_rev, max_rev), 2)
        new_row["target_revenue"] = round(random.uniform(max_rev, max_rev * 1.7), 2)
        new_row["revenue_gap"] = float(new_row["target_revenue"]) - float(new_row["actual_revenue"])

        new_row["lead_score"] = random.randint(35, 94)
        new_row["intent_score"] = random.randint(30, 96)
        new_row["commercial_readiness_score"] = random.randint(35, 95)
        new_row["conversion_probability"] = round(random.uniform(0.12, 0.88), 4)

        web_visit_count = random.randint(3, 9)
        demo_count = 1 if stage in ["Demo Requested", "Proposal Sent", "Contract Confirmed"] else 0
        ai_count = random.randint(0, 2)
        promo_count = random.randint(0, 1)
        proposal_count = 1 if stage in ["Proposal Sent", "Contract Confirmed"] else 0
        contract_count = 1 if stage == "Contract Confirmed" else 0

        new_row["web_visit_count"] = web_visit_count
        new_row["total_web_requests"] = web_visit_count
        new_row["unique_sessions"] = random.randint(1, 3)
        new_row["demo_request_count"] = demo_count
        new_row["ai_assistant_request_count"] = ai_count
        new_row["promotional_event_count"] = promo_count
        new_row["proposal_download_count"] = proposal_count
        new_row["contract_confirmation_count"] = contract_count
        new_row["high_intent_hits"] = demo_count + ai_count + promo_count + proposal_count + contract_count
        new_row["web_error_count"] = random.randint(0, 1)
        new_row["avg_response_time_ms"] = random.randint(120, 850)

        top_pages = [
            "/",
            "/services",
            "/pricing",
            "/schedule-demo",
            "/ai-assistant",
            "/events/webinar",
            "/proposal/download",
            "/contract/confirm",
        ]

        new_row["top_page"] = random.choice(top_pages)

        new_records.append(new_row)

    return new_records


# ============================================================
# IIS LOG GENERATION
# ============================================================
def status_code_for_event(event_type):
    if event_type in HIGH_INTENT_EVENTS:
        return random.choices(
            [200, 302, 404, 500],
            weights=[88, 7, 4, 1],
            k=1,
        )[0]

    return random.choices(
        [200, 304, 404, 500],
        weights=[86, 8, 5, 1],
        k=1,
    )[0]


def response_time_for_status(status_code):
    if status_code >= 500:
        return random.randint(900, 3500)

    if status_code == 404:
        return random.randint(300, 1200)

    return random.randint(80, 850)


def build_iis_log_rows(new_records):
    log_rows = []
    now = datetime.now()

    for row in new_records:
        client_id = safe_value(row, "client_id", f"CL{random.randint(100000, 999999)}")
        stage = safe_value(row, "current_stage", "Inquiry")
        converted = safe_int(row, "converted", 0)

        country = safe_value(row, "country", "Unknown")
        city = safe_value(row, "city", "Unknown")
        service_type = safe_value(row, "service_type", "Cyber Security Service")
        service_category = safe_value(row, "service_category", "Cyber Security")
        marketing_channel = safe_value(row, "marketing_channel", "Direct")
        campaign_name = safe_value(row, "campaign_name", "Live Website Visit")

        session_id = f"SESSLIVE{random.randint(100000, 999999)}"
        events = choose_live_events(stage, converted)

        for event_type in events:
            event_time = now - timedelta(seconds=random.randint(0, 25))
            status_code = status_code_for_event(event_type)
            uri = EVENT_TO_URI.get(event_type, "/services")

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
                    "Contract Confirmation",
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
                "time_taken_ms": response_time_for_status(status_code),
                "client_id": client_id,
                "session_id": session_id,
                "country": country,
                "city": city,
                "service_type": service_type,
                "service_category": service_category,
                "marketing_channel": marketing_channel,
                "campaign_name": campaign_name,
                "event_type": event_type,
            })

    return log_rows


def engineer_cleaned_iis_logs(raw_log_rows):
    cleaned_rows = []

    for row in raw_log_rows:
        cleaned_row = row.copy()

        event_datetime = pd.to_datetime(
            f"{row['date']} {row['time']}",
            errors="coerce",
        )

        status_code = int(row.get("sc_status", 0))
        event_type = row.get("event_type", "")

        cleaned_row["event_datetime"] = event_datetime.strftime("%Y-%m-%d %H:%M:%S")
        cleaned_row["is_error"] = 1 if status_code >= 400 else 0
        cleaned_row["is_success"] = 1 if 200 <= status_code <= 399 else 0
        cleaned_row["is_demo_request"] = 1 if event_type == "Schedule Demo Request" else 0
        cleaned_row["is_ai_assistant_request"] = 1 if event_type == "AI Assistant Request" else 0
        cleaned_row["is_promotional_event_request"] = 1 if event_type == "Promotional Event Request" else 0
        cleaned_row["is_contract_confirmation"] = 1 if event_type == "Contract Confirmation" else 0
        cleaned_row["is_proposal_download"] = 1 if event_type == "Proposal Download" else 0
        cleaned_row["is_high_intent"] = 1 if event_type in HIGH_INTENT_EVENTS else 0

        cleaned_rows.append(cleaned_row)

    return cleaned_rows


def append_csv_aligned(file_path, new_df):
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if file_path.exists():
        existing_columns = pd.read_csv(file_path, nrows=0).columns.tolist()

        for col in existing_columns:
            if col not in new_df.columns:
                new_df[col] = None

        new_df = new_df[existing_columns]

        new_df.to_csv(
            file_path,
            mode="a",
            header=False,
            index=False,
        )

    else:
        new_df.to_csv(
            file_path,
            mode="w",
            header=True,
            index=False,
        )


def append_live_iis_logs(new_records):
    raw_log_rows = build_iis_log_rows(new_records)

    if not raw_log_rows:
        return 0

    raw_logs_df = pd.DataFrame(raw_log_rows)
    cleaned_logs_df = pd.DataFrame(engineer_cleaned_iis_logs(raw_log_rows))

    append_csv_aligned(RAW_IIS_FILE, raw_logs_df)
    append_csv_aligned(CLEANED_IIS_FILE, cleaned_logs_df)

    return len(raw_logs_df)


# ============================================================
# JSON PREPARATION
# ============================================================
def prepare_json_data(dataframe):
    latest_df = dataframe.copy()

    date_columns = [
        "inquiry_date",
        "close_date",
        "demo_date",
        "proposal_date",
        "first_web_event",
        "last_web_event",
    ]

    for col in date_columns:
        if col in latest_df.columns:
            latest_df[col] = pd.to_datetime(
                latest_df[col],
                errors="coerce",
            ).dt.strftime("%Y-%m-%d %H:%M:%S")

    latest_df = latest_df.replace({np.nan: None})

    return latest_df.to_dict(orient="records")


# ============================================================
# ROUTES
# ============================================================
@app.route("/")
def home():
    return jsonify({
        "status": "running",
        "message": "CyberNova live API is active",
        "live_endpoint": "/live-data",
        "current_records": len(current_data),
    })


@app.route("/live-data")
def live_data():
    global current_data

    records_to_add = random.randint(1, 3)

    new_records = generate_live_crm_records(records_to_add)
    iis_logs_added = append_live_iis_logs(new_records)

    if new_records:
        new_df = pd.DataFrame(new_records)
        current_data = pd.concat([current_data, new_df], ignore_index=True)

    if len(current_data) > MAX_STORED_ROWS:
        current_data = current_data.tail(MAX_STORED_ROWS).reset_index(drop=True)

    latest_records = prepare_json_data(current_data.tail(RETURN_ROWS))
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(
        f"[LIVE API POLL] {timestamp} | "
        f"crm_added={len(new_records)} | "
        f"iis_logs_added={iis_logs_added} | "
        f"stored_total={len(current_data)} | "
        f"returned={len(latest_records)}",
        flush=True,
    )

    return jsonify({
        "timestamp": timestamp,
        "new_records_added": len(new_records),
        "iis_logs_added": iis_logs_added,
        "total_records": len(current_data),
        "returned_records": len(latest_records),
        "data": latest_records,
    })


# ============================================================
# RUN API
# ============================================================
if __name__ == "__main__":
    print("CyberNova Flask API starting...", flush=True)
    print("API endpoint: http://127.0.0.1:5001/live-data", flush=True)

    app.run(
        host="127.0.0.1",
        port=5001,
        debug=False,
        use_reloader=False,
    )