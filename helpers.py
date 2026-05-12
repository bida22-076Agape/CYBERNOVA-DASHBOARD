import pandas as pd
import streamlit as st
from pathlib import Path

DATA_DIR = Path("data")


@st.cache_data(ttl=6)
def load_data():
    """
    Loads the best available CyberNova dataset.
    Uses the IIS-enhanced v3 dataset first, then falls back to v2.
    """
    possible_files = [
        DATA_DIR / "Cybernova_Final_Intelligence_v3_web.csv",
        DATA_DIR / "Cybernova_Final_Intelligence_v2.csv"
    ]

    for file_path in possible_files:
        if file_path.exists():
            df = pd.read_csv(file_path)
            return clean_dashboard_data(df)

    st.error("No CyberNova dataset found inside the data folder.")
    return pd.DataFrame()


def clean_dashboard_data(df):
    df = df.copy()

    # ------------------------------------------------------------
    # Column compatibility
    # ------------------------------------------------------------
    if "service_type" not in df.columns and "service" in df.columns:
        df["service_type"] = df["service"]

    if "service" not in df.columns and "service_type" in df.columns:
        df["service"] = df["service_type"]

    if "marketing_channel" not in df.columns:
        df["marketing_channel"] = "Unknown"

    # ------------------------------------------------------------
    # Dates
    # ------------------------------------------------------------
    date_columns = [
        "inquiry_date",
        "demo_date",
        "proposal_date",
        "close_date",
        "first_web_event",
        "last_web_event"
    ]

    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # ------------------------------------------------------------
    # Numeric columns
    # ------------------------------------------------------------
    numeric_columns = [
        "actual_revenue",
        "forecast_revenue",
        "target_revenue",
        "revenue_gap",
        "converted",
        "lead_score",
        "intent_score",
        "conversion_probability",
        "web_visit_count",
        "total_web_events",
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
        "avg_response_ms",
        "total_page_views",
        "unique_pages_visited",
        "web_discount_count"
    ]

    for col in numeric_columns:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Normalise probability
    if "conversion_probability" in df.columns:
        if df["conversion_probability"].max() > 1:
            df["conversion_probability"] = df["conversion_probability"] / 100

    if df["conversion_probability"].sum() == 0 and "lead_score" in df.columns:
        df["conversion_probability"] = (df["lead_score"] / 100).clip(0, 1)

    # ------------------------------------------------------------
    # Text columns
    # ------------------------------------------------------------
    text_columns = [
        "client_id",
        "country",
        "country_group",
        "city",
        "industry",
        "service_type",
        "service",
        "current_stage",
        "sales_rep_name",
        "sales_team",
        "marketing_channel",
        "campaign_name",
        "lead_quality",
        "market_priority"
    ]

    for col in text_columns:
        if col not in df.columns:
            df[col] = "Unknown"
        df[col] = df[col].fillna("Unknown").astype(str)

    return df


def money(value):
    try:
        return f"BWP {float(value):,.0f}"
    except Exception:
        return "BWP 0"


def money_short(value):
    try:
        value = float(value)

        if abs(value) >= 1_000_000:
            return f"BWP {value / 1_000_000:.1f}M"

        if abs(value) >= 1_000:
            return f"BWP {value / 1_000:.1f}K"

        return f"BWP {value:,.0f}"

    except Exception:
        return "BWP 0"


def percent(value):
    try:
        return f"{float(value):.1f}%"
    except Exception:
        return "0.0%"


def safe_rate(numerator, denominator):
    if denominator == 0:
        return 0
    return (float(numerator) / float(denominator)) * 100


def month_delta(df, value_col, date_col="inquiry_date"):
    """
    Returns current month value, previous month value, and % change.
    """
    if df.empty or value_col not in df.columns or date_col not in df.columns:
        return 0, 0, 0

    temp = df[[date_col, value_col]].copy()
    temp[date_col] = pd.to_datetime(temp[date_col], errors="coerce")
    temp = temp.dropna(subset=[date_col])

    if temp.empty:
        return 0, 0, 0

    temp["month"] = temp[date_col].dt.to_period("M").astype(str)

    monthly = (
        temp.groupby("month")[value_col]
        .sum()
        .sort_index()
    )

    if len(monthly) == 0:
        return 0, 0, 0

    current_value = float(monthly.iloc[-1])
    previous_value = float(monthly.iloc[-2]) if len(monthly) > 1 else 0

    if previous_value == 0:
        delta = 0
    else:
        delta = ((current_value - previous_value) / previous_value) * 100

    return current_value, previous_value, delta


def web_active_mask(df):
    """
    Identifies leads with any IIS/web behaviour.
    """
    web_columns = [
        "web_visit_count",
        "total_web_events",
        "total_web_requests",
        "unique_sessions",
        "demo_request_count",
        "ai_assistant_request_count",
        "promotional_event_count",
        "contract_confirmation_count",
        "proposal_download_count",
        "high_intent_hits"
    ]

    mask = pd.Series(False, index=df.index)

    for col in web_columns:
        if col in df.columns:
            mask = mask | (pd.to_numeric(df[col], errors="coerce").fillna(0) > 0)

    return mask


def add_stage_flags(df):
    """
    Creates clean funnel flags for Inquiry → Demo → Proposal → Contract.
    """
    df = df.copy()

    if "current_stage" in df.columns:
        stage = df["current_stage"].str.lower()
    else:
        stage = pd.Series("", index=df.index)

    df["has_inquiry"] = 1

    df["has_demo"] = (
        (df["demo_request_count"] > 0) |
        stage.str.contains("demo", na=False)
    ).astype(int)

    df["has_proposal"] = (
        (df["proposal_download_count"] > 0) |
        stage.str.contains("proposal", na=False)
    ).astype(int)

    df["has_contract"] = (
        (df["contract_confirmation_count"] > 0) |
        (df["converted"] > 0) |
        stage.str.contains("contract|won", na=False)
    ).astype(int)

    return df


def suggested_action(row):
    """
    Prescriptive action logic for priority leads.
    """
    lead_score = row.get("lead_score", 0)
    probability = row.get("conversion_probability", 0)
    demo_requests = row.get("demo_request_count", 0)
    high_intent = row.get("high_intent_hits", 0)

    if demo_requests > 0 or high_intent >= 3:
        return "Call + reference website interest"

    if lead_score >= 80 or probability >= 0.80:
        return "Immediate call required"

    if lead_score >= 60:
        return "Send proposal follow-up"

    return "Nurture via email"


def priority_label(row):
    action = suggested_action(row)

    if "Call" in action or "Immediate" in action:
        return "High"

    if "proposal" in action.lower():
        return "Medium"

    return "Low"