import html
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
from datetime import timedelta
from textwrap import dedent


# ============================================================
# COLOUR TOKENS - MARKETING PURPLE THEME
# ============================================================
PURPLE = "#7c3aed"
PURPLE_DEEP = "#5b05f5"
PURPLE_DARK = "#25006e"
PURPLE_SOFT = "#c084fc"
LAVENDER = "#d8b4fe"
TEAL = "#7ef9d6"
PINK = "#ec4899"
GREEN = "#22c55e"
BLUE = "#60a5fa"
ORANGE = "#f59e0b"
RED = "#ef4444"
TEXT_LIGHT = "#f8fafc"
TEXT_MUTED = "#b5a7e8"
CARD_BORDER = "rgba(216, 180, 254, 0.20)"


# ============================================================
# BASIC HELPERS
# ============================================================
def render_html(markup: str) -> None:
    st.markdown(dedent(markup).strip(), unsafe_allow_html=True)


def compact_money(value):
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
    try:
        denominator = float(denominator)

        if denominator == 0:
            return 0.0

        return float(numerator) / denominator * 100

    except Exception:
        return 0.0


def go_to_overview():
    st.session_state.active_page = "Overview"
    st.rerun()


# ============================================================
# DATA CLEANING
# ============================================================
def clean_marketing_data(df):
    df = df.copy()

    if "marketing_channel" not in df.columns:
        if "lead_source" in df.columns:
            df["marketing_channel"] = df["lead_source"]
        elif "channel" in df.columns:
            df["marketing_channel"] = df["channel"]
        elif "acquisition_channel" in df.columns:
            df["marketing_channel"] = df["acquisition_channel"]
        else:
            df["marketing_channel"] = "Direct"

    if "service_type" not in df.columns and "service" in df.columns:
        df["service_type"] = df["service"]

    if "service" not in df.columns and "service_type" in df.columns:
        df["service"] = df["service_type"]

    text_defaults = {
        "client_id": "Unknown",
        "country": "Unknown",
        "city": "Unknown",
        "industry": "General Market",
        "service_type": "CyberNova Service",
        "service": "CyberNova Service",
        "current_stage": "Inquiry",
        "marketing_channel": "Direct",
        "campaign_name": "Organic Campaign",
    }

    for col, default in text_defaults.items():
        if col not in df.columns:
            df[col] = default

        df[col] = df[col].fillna(default).astype(str)

    numeric_cols = [
        "actual_revenue",
        "forecast_revenue",
        "target_revenue",
        "converted",
        "lead_score",
        "conversion_probability",
        "web_visit_count",
        "total_web_requests",
        "total_web_events",
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

    for col in numeric_cols:
        if col not in df.columns:
            df[col] = 0

        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    date_cols = [
        "inquiry_date",
        "demo_date",
        "proposal_date",
        "close_date",
        "first_web_event",
        "last_web_event",
    ]

    for col in date_cols:
        if col not in df.columns:
            df[col] = pd.NaT

        df[col] = pd.to_datetime(df[col], errors="coerce")

    if df["conversion_probability"].max() > 1:
        df["conversion_probability"] = df["conversion_probability"] / 100

    if df["conversion_probability"].sum() == 0 and "lead_score" in df.columns:
        df["conversion_probability"] = (df["lead_score"] / 100).clip(0, 1)

    df["converted"] = (df["converted"] > 0).astype(int)
    df["converted_revenue"] = df["actual_revenue"] * df["converted"]

    return df


# ============================================================
# HISTORICAL DATA LOADING AND DATE REFERENCE HELPERS
# ============================================================
@st.cache_data(show_spinner=False)
def load_historical_marketing_dataset() -> pd.DataFrame:
    """Load the stable historical marketing dataset used by the Marketing page."""
    paths = [
        Path("data/Cybernova_Final_Intelligence_v2.csv"),
        Path("data/Cybernova_Final_Intelligence_v3_web.csv"),
    ]

    for path in paths:
        if path.exists():
            try:
                return pd.read_csv(path)
            except Exception:
                continue

    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_date_reference_dataset() -> pd.DataFrame:
    """Load the stable historical file used only for date limits."""
    paths = [
        Path("data/Cybernova_Final_Intelligence_v2.csv"),
        Path("data/Cybernova_Final_Intelligence_v3_web.csv"),
    ]

    for path in paths:
        if path.exists():
            try:
                return pd.read_csv(path)
            except Exception:
                continue

    return pd.DataFrame()


def get_reference_date_limits():
    """Return the true historical inquiry_date range from the stable CSV."""
    reference_df = load_date_reference_dataset()

    if reference_df.empty or "inquiry_date" not in reference_df.columns:
        return None, None

    reference_dates = pd.to_datetime(reference_df["inquiry_date"], errors="coerce").dropna()

    if reference_dates.empty:
        return None, None

    return reference_dates.min().date(), reference_dates.max().date()


def keep_records_inside_reference_window(df: pd.DataFrame, start_date, end_date) -> pd.DataFrame:
    """Remove accidental live/simulation rows outside the historical range."""
    if df is None or df.empty:
        return pd.DataFrame()

    if start_date is None or end_date is None or "inquiry_date" not in df.columns:
        return df.copy()

    cleaned = df.copy()
    dates = pd.to_datetime(cleaned["inquiry_date"], errors="coerce")
    keep_mask = dates.isna() | ((dates.dt.date >= start_date) & (dates.dt.date <= end_date))

    return cleaned.loc[keep_mask].copy()


def build_marketing_source(incoming_df: pd.DataFrame) -> pd.DataFrame:
    """Build Marketing data from historical data plus valid incoming rows.

    The live API may pass 2026/current-date records. Those should not replace
    the historical CyberNova marketing dataset used for this assessed dashboard.
    """
    incoming_df = incoming_df.copy() if incoming_df is not None else pd.DataFrame()
    historical_df = load_historical_marketing_dataset()

    reference_start, reference_end = get_reference_date_limits()

    historical_df = keep_records_inside_reference_window(
        historical_df,
        reference_start,
        reference_end,
    )

    incoming_df = keep_records_inside_reference_window(
        incoming_df,
        reference_start,
        reference_end,
    )

    frames = []

    if not historical_df.empty:
        frames.append(historical_df)

    if not incoming_df.empty:
        frames.append(incoming_df)

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True, sort=False)
    combined = clean_marketing_data(combined)

    if "client_id" in combined.columns:
        combined["_sort_date"] = combined["last_web_event"].fillna(combined["inquiry_date"])
        combined = combined.sort_values("_sort_date")
        combined = combined.drop_duplicates(subset=["client_id"], keep="last")
        combined = combined.drop(columns=["_sort_date"], errors="ignore")

    return combined


def get_date_limits(valid_dates: pd.Series):
    """Return date limits for the filter without forcing a selected range."""
    reference_start, reference_end = get_reference_date_limits()

    if reference_start is not None and reference_end is not None:
        return reference_start, reference_end

    if valid_dates.empty:
        return None, None

    return valid_dates.min().date(), valid_dates.max().date()


def normalise_date_range(date_range):
    """Keep the date filter empty unless the user selects a complete range."""
    if date_range is None:
        return None, None

    if isinstance(date_range, (tuple, list)):
        if len(date_range) == 2 and date_range[0] is not None and date_range[1] is not None:
            start_date = date_range[0]
            end_date = date_range[1]

            if start_date > end_date:
                start_date, end_date = end_date, start_date

            return start_date, end_date

    return None, None


# ============================================================
# PERIOD / TIMELINE HELPERS
# ============================================================
def get_previous_period(start_date, end_date):
    if start_date is None or end_date is None:
        return None, None

    number_of_days = (end_date - start_date).days + 1
    previous_end = start_date - timedelta(days=1)
    previous_start = previous_end - timedelta(days=number_of_days - 1)

    return previous_start, previous_end


def date_label(start_date, end_date):
    if start_date is None or end_date is None:
        return "Full available timeline"

    return f"{start_date.strftime('%d %b %Y')} → {end_date.strftime('%d %b %Y')}"


def filter_date(df, start_date, end_date, date_col="inquiry_date"):
    if start_date is None or end_date is None or date_col not in df.columns:
        return df.copy()

    dates = pd.to_datetime(df[date_col], errors="coerce")

    return df[
        (dates.dt.date >= start_date)
        & (dates.dt.date <= end_date)
    ].copy()


# ============================================================
# MARKETING KPI HELPERS
# ============================================================
def web_active_mask(df):
    mask = pd.Series(False, index=df.index)

    web_cols = [
        "web_visit_count",
        "total_web_requests",
        "total_web_events",
        "unique_sessions",
        "high_intent_hits",
        "demo_request_count",
        "ai_assistant_request_count",
        "contract_confirmation_count",
        "proposal_download_count",
    ]

    for col in web_cols:
        if col in df.columns:
            mask = mask | (
                pd.to_numeric(df[col], errors="coerce").fillna(0) > 0
            )

    return mask


def funnel_counts(df):
    if df.empty:
        return 0, 0, 0, 0

    inquiry_count = len(df)
    stage = df["current_stage"].str.lower()

    demo_count = int(
        (
            (df["demo_date"].notna())
            | (df["demo_request_count"] > 0)
            | stage.str.contains("demo|proposal|contract|closed|won", na=False)
        ).sum()
    )

    proposal_count = int(
        (
            (df["proposal_date"].notna())
            | (df["proposal_download_count"] > 0)
            | stage.str.contains("proposal|contract|closed|won", na=False)
        ).sum()
    )

    contract_count = int(
        (
            (df["close_date"].notna())
            | (df["contract_confirmation_count"] > 0)
            | (df["converted"] == 1)
            | stage.str.contains("contract|closed|won", na=False)
        ).sum()
    )

    return inquiry_count, demo_count, proposal_count, contract_count


def delta_badge(
    current,
    previous,
    higher_is_good=True,
    mode="percent",
    context="change"
):
    try:
        current = float(current)
        previous = float(previous)
    except Exception:
        return '<span class="marketing-kpi-delta neutral">● No comparison available</span>'

    if abs(previous) < 1e-9:
        return '<span class="marketing-kpi-delta neutral">● Baseline period</span>'

    if mode == "points":
        change = current - previous
        arrow = "↑" if change >= 0 else "↓"
        good = change >= 0 if higher_is_good else change <= 0
        css_class = "good" if good else "bad"

        return (
            f'<span class="marketing-kpi-delta {css_class}">'
            f'{arrow} {abs(change):.1f} pts vs previous period'
            f'</span>'
        )

    change = ((current - previous) / abs(previous)) * 100
    arrow = "↑" if change >= 0 else "↓"
    good = change >= 0 if higher_is_good else change <= 0
    css_class = "good" if good else "bad"

    if context == "money":
        meaning = "revenue gain" if good else "revenue loss"
    elif context == "risk":
        meaning = "risk reduced" if good else "risk increased"
    else:
        meaning = "improved" if good else "declined"

    return (
        f'<span class="marketing-kpi-delta {css_class}">'
        f'{arrow} {abs(change):.1f}% {meaning}'
        f'</span>'
    )


# ============================================================
# CSS - MARKETING DASHBOARD
# ============================================================
def marketing_css():
    render_html(f"""
    <style>
        .stApp {{
            background:
                radial-gradient(circle at 15% 15%, rgba(124, 58, 237, 0.24), transparent 28%),
                radial-gradient(circle at 82% 18%, rgba(216, 180, 254, 0.18), transparent 30%),
                radial-gradient(circle at 55% 85%, rgba(91, 5, 245, 0.16), transparent 34%),
                linear-gradient(135deg, #090015 0%, #15002b 50%, #05000d 100%) !important;
            color: {TEXT_LIGHT} !important;
        }}

        .block-container {{
            max-width: 1450px !important;
            padding-top: 1.2rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }}

        .marketing-page-title {{
            font-size: 38px;
            color: {TEXT_LIGHT};
            font-weight: 950;
            letter-spacing: -1px;
            margin: 6px 0 4px 2px;
        }}

        .marketing-page-sub {{
            color: {TEXT_MUTED};
            font-size: 14px;
            margin: 0 0 16px 2px;
        }}

        .marketing-timeline {{
            background: rgba(124, 58, 237, 0.13);
            border: 1px solid {CARD_BORDER};
            border-radius: 16px;
            padding: 12px 16px;
            margin: 0 0 22px 2px;
            color: {LAVENDER};
            font-size: 12px;
            font-weight: 800;
        }}

        .marketing-section-heading {{
            color: {TEXT_LIGHT};
            font-size: 17px;
            font-weight: 850;
            margin: 8px 0 14px 2px;
        }}

        .marketing-filter-label {{
            color: {TEXT_MUTED};
            font-size: 12px;
            font-weight: 900;
            letter-spacing: 0.8px;
            text-transform: uppercase;
            margin: 4px 0 8px 2px;
        }}

        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] {{
            background: rgba(24, 13, 49, 0.96) !important;
            border: 1px solid rgba(216, 180, 254, 0.24) !important;
            border-radius: 14px !important;
            min-height: 44px !important;
            color: {TEXT_LIGHT} !important;
            box-shadow: none !important;
        }}

        div[data-baseweb="select"] span,
        div[data-baseweb="input"] input,
        input {{
            color: {TEXT_LIGHT} !important;
        }}

        label {{
            color: {TEXT_MUTED} !important;
            font-size: 12px !important;
            font-weight: 700 !important;
        }}

        div.stButton > button {{
            background:
                radial-gradient(circle at 90% 0%, rgba(216, 180, 254, 0.18), transparent 36%),
                linear-gradient(135deg, rgba(28, 13, 55, 0.98), rgba(91, 5, 245, 0.96)) !important;
            color: {TEXT_LIGHT} !important;
            border: 1px solid rgba(216, 180, 254, 0.26) !important;
            border-radius: 14px !important;
            font-weight: 850 !important;
            box-shadow: 0 12px 32px rgba(0,0,0,0.22) !important;
        }}

        div.stButton > button:hover {{
            background:
                radial-gradient(circle at 90% 0%, rgba(216, 180, 254, 0.24), transparent 36%),
                linear-gradient(135deg, #310083, #7c3aed) !important;
            color: #ffffff !important;
            border: 1px solid rgba(216, 180, 254, 0.50) !important;
            transform: translateY(-1px);
        }}

        div.stButton > button p {{
            color: #ffffff !important;
            font-weight: 850 !important;
        }}

        .marketing-kpi-card {{
            background:
                radial-gradient(circle at 85% 0%, rgba(124, 58, 237, 0.36), transparent 42%),
                linear-gradient(135deg, rgba(16, 8, 34, 0.98), rgba(13, 8, 31, 0.98));
            border: 1px solid {CARD_BORDER};
            border-radius: 22px;
            padding: 22px 24px;
            min-height: 166px;
            box-shadow: 0 18px 55px rgba(0,0,0,0.30);
        }}

        .marketing-kpi-card.featured {{
            background:
                radial-gradient(circle at 82% 72%, rgba(216, 180, 254, 0.28), transparent 34%),
                linear-gradient(135deg, #25006e 0%, #5b05f5 46%, #7c3aed 100%);
            border: 1px solid rgba(216, 180, 254, 0.36);
        }}

        .marketing-kpi-label {{
            color: {TEXT_MUTED};
            font-size: 12px;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            margin-bottom: 10px;
        }}

        .marketing-kpi-value {{
            color: {TEXT_LIGHT};
            font-size: 27px;
            font-weight: 950;
            line-height: 1.15;
            margin-bottom: 8px;
        }}

        .marketing-kpi-note {{
            color: {TEXT_MUTED};
            font-size: 11px;
            margin-top: 8px;
            line-height: 1.35;
        }}

        .marketing-kpi-delta {{
            display: inline-flex;
            align-items: center;
            gap: 4px;
            border-radius: 999px;
            padding: 4px 10px;
            font-size: 11px;
            font-weight: 850;
            border: 1px solid transparent;
        }}

        .marketing-kpi-delta.good {{
            color: #bbf7d0;
            background: rgba(34,197,94,0.13);
            border-color: rgba(34,197,94,0.22);
        }}

        .marketing-kpi-delta.bad {{
            color: #fecaca;
            background: rgba(239,68,68,0.13);
            border-color: rgba(239,68,68,0.22);
        }}

        .marketing-kpi-delta.neutral {{
            color: #d8b4fe;
            background: rgba(196,181,253,0.13);
            border-color: rgba(196,181,253,0.22);
        }}

        .marketing-chart-card {{
            background:
                radial-gradient(circle at 85% 0%, rgba(124, 58, 237, 0.20), transparent 50%),
                rgba(16, 8, 34, 0.96);
            border: 1px solid {CARD_BORDER};
            border-radius: 22px;
            padding: 22px 24px 12px 24px;
            box-shadow: 0 18px 55px rgba(0,0,0,0.30);
            margin-bottom: 20px;
        }}

        .marketing-chart-title {{
            color: {TEXT_LIGHT};
            font-size: 18px;
            font-weight: 850;
            margin-bottom: 4px;
        }}

        .marketing-chart-sub {{
            color: {TEXT_MUTED};
            font-size: 12px;
            margin-bottom: 16px;
        }}

        .marketing-insight-card {{
            background:
                radial-gradient(circle at 90% 0%, rgba(126, 249, 214, 0.14), transparent 36%),
                linear-gradient(135deg, rgba(16, 8, 34, 0.98), rgba(34, 13, 70, 0.94));
            border: 1px solid rgba(126, 249, 214, 0.18);
            border-radius: 22px;
            padding: 20px 24px;
            margin-bottom: 20px;
            color: #d8b4fe;
            font-size: 13px;
            line-height: 1.6;
            box-shadow: 0 18px 55px rgba(0,0,0,0.28);
        }}

        .marketing-insight-card b {{
            color: #ffffff;
        }}


        /* ------------------------------------------------------------
           Marketing evidence table - same dark style as Web Analytics
        ------------------------------------------------------------ */
        .marketing-table-wrap {{
            background:
                radial-gradient(circle at 90% 0%, rgba(124,58,237,0.20), transparent 45%),
                rgba(13, 10, 28, 0.96);
            border: 1px solid rgba(168, 85, 247, 0.24);
            border-radius: 18px;
            padding: 12px;
            margin-top: 10px;
            box-shadow: 0 18px 45px rgba(0,0,0,0.26);
            overflow-x: auto;
        }}

        table.marketing-evidence-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
            color: #cbd5e1;
            overflow: hidden;
            border-radius: 12px;
        }}

        table.marketing-evidence-table thead tr {{
            background: linear-gradient(135deg, rgba(91,5,255,0.55), rgba(168,85,247,0.32));
            color: #ffffff;
        }}

        table.marketing-evidence-table th {{
            padding: 11px 10px;
            text-align: left;
            font-weight: 950;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-size: 10px;
            border-bottom: 1px solid rgba(196,181,253,0.20);
            white-space: nowrap;
        }}

        table.marketing-evidence-table td {{
            padding: 10px;
            border-bottom: 1px solid rgba(148, 163, 184, 0.10);
            vertical-align: middle;
            white-space: nowrap;
        }}

        table.marketing-evidence-table tbody tr:nth-child(even) {{
            background: rgba(255,255,255,0.025);
        }}

        table.marketing-evidence-table tbody tr:hover {{
            background: rgba(168, 85, 247, 0.10);
        }}

        .marketing-table-badge {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 4px 8px;
            border-radius: 999px;
            font-size: 10px;
            font-weight: 900;
            color: #ddd6fe;
            background: rgba(196,181,253,0.14);
            border: 1px solid rgba(196,181,253,0.25);
        }}

        .marketing-table-money {{
            color: #7ef9d6;
            font-weight: 900;
        }}

        div[data-testid="stDataFrame"] {{
            border: 1px solid {CARD_BORDER};
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 18px 55px rgba(0,0,0,0.18);
        }}

        /* Date input visibility fix */
        div[data-testid="stDateInput"] label {{
            color: #cbd5e1 !important;
            font-weight: 800 !important;
        }}

        div[data-testid="stDateInput"] div[data-baseweb="input"] {{
            background: rgba(24, 13, 49, 0.96) !important;
            border: 1px solid rgba(216, 180, 254, 0.34) !important;
            border-radius: 14px !important;
        }}

        div[data-testid="stDateInput"] input {{
            color: #f8fafc !important;
            -webkit-text-fill-color: #f8fafc !important;
            background: transparent !important;
            opacity: 1 !important;
        }}

        div[data-testid="stDateInput"] input::placeholder {{
            color: #e2e8f0 !important;
            -webkit-text-fill-color: #e2e8f0 !important;
            opacity: 1 !important;
        }}

        div[data-baseweb="popover"] {{
            z-index: 999999 !important;
        }}
    </style>
    """)


# ============================================================
# PLOTLY THEME
# ============================================================
def apply_dark_chart_layout(fig, height=250):
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="Inter, system-ui",
            color=TEXT_MUTED,
            size=12,
        ),
        margin=dict(l=10, r=10, t=10, b=10),
        hoverlabel=dict(
            bgcolor="rgba(16,8,34,0.98)",
            bordercolor=PURPLE,
            font_color=TEXT_LIGHT,
        ),
        legend=dict(
            font=dict(color=TEXT_MUTED),
            orientation="h",
            yanchor="top",
            y=-0.18,
            xanchor="left",
            x=0,
        ),
    )

    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        tickfont=dict(color=TEXT_MUTED),
    )

    fig.update_yaxes(
        showgrid=True,
        gridcolor="rgba(216,180,254,0.10)",
        zeroline=False,
        tickfont=dict(color=TEXT_MUTED),
    )

    return fig


# ============================================================
# MARKETING EVIDENCE TABLE HELPER
# ============================================================
def render_marketing_evidence_table(evidence_table: pd.DataFrame) -> None:
    """Render the bottom evidence table using the same dark style as Web Analytics."""
    if evidence_table.empty:
        st.info("No marketing evidence table available.")
        return

    headers = evidence_table.columns.tolist()
    html_rows = []

    for _, row in evidence_table.iterrows():
        cells = []

        for col in headers:
            value = html.escape(str(row[col]))

            if col == "Conversion Rate":
                cells.append(
                    f'<td><span class="marketing-table-badge">{value}</span></td>'
                )
            elif col == "Converted Revenue":
                cells.append(
                    f'<td><span class="marketing-table-money">{value}</span></td>'
                )
            else:
                cells.append(f"<td>{value}</td>")

        html_rows.append("<tr>" + "".join(cells) + "</tr>")

    html_head = "".join(
        f"<th>{html.escape(str(col))}</th>"
        for col in headers
    )

    table_html = f"""
    <div class="marketing-table-wrap">
        <table class="marketing-evidence-table">
            <thead>
                <tr>{html_head}</tr>
            </thead>
            <tbody>
                {''.join(html_rows)}
            </tbody>
        </table>
    </div>
    """

    render_html(table_html)


# ============================================================
# MAIN MARKETING PAGE
# ============================================================
def show(df):
    marketing_css()

    # Clear old Streamlit date-state that used to force-select the live date range.
    date_filter_version = "historical_marketing_combined_window_v2"

    if st.session_state.get("_market_date_filter_version") != date_filter_version:
        st.session_state.pop("market_date_range", None)
        st.session_state["_market_date_filter_version"] = date_filter_version

    if st.session_state.pop("_market_reset_filters", False):
        for key in (
            "market_date_range",
            "market_channel_filter",
            "market_country_filter",
            "market_industry_filter",
        ):
            st.session_state.pop(key, None)

    df = build_marketing_source(df)

    if df.empty:
        st.warning(
            "No marketing data is available. Check that data/Cybernova_Final_Intelligence_v2.csv "
            "exists and contains inquiry_date records."
        )
        return

    nav_left, spacer, nav_right = st.columns([1.6, 4.4, 1.4])

    with nav_left:
        if st.button(
            "← Back to Overview",
            use_container_width=True,
            key="market_back_btn",
        ):
            go_to_overview()

    with nav_right:
        if st.button(
            "↺ Reset Filters",
            use_container_width=True,
            key="market_reset_btn",
        ):
            st.session_state["_market_reset_filters"] = True
            st.rerun()

    render_html("""
    <div class="marketing-page-title">Marketing Dashboard</div>
    <div class="marketing-page-sub">
        Demand generation • Channel performance • Web-to-contract conversion
    </div>
    """)

    render_html('<div class="marketing-filter-label">Filters</div>')

    f1, f2, f3, f4 = st.columns(4)

    with f1:
        valid_dates = df["inquiry_date"].dropna()
        min_date, max_date = get_date_limits(valid_dates)

        if min_date is not None:
            raw_date_range = st.date_input(
                "Date Range",
                value=(),
                min_value=min_date,
                max_value=max_date,
                format="YYYY/MM/DD",
                key="market_date_range",
            )
            start_date, end_date = normalise_date_range(raw_date_range)
        else:
            st.date_input(
                "Date Range",
                value=None,
                key="market_date_range",
                disabled=True,
            )
            start_date, end_date = None, None

    with f2:
        channel_options = ["All"] + sorted(
            df["marketing_channel"].dropna().astype(str).unique().tolist()
        )

        selected_channel = st.selectbox(
            "Marketing Channel",
            channel_options,
            key="market_channel_filter",
        )

    with f3:
        country_options = ["All"] + sorted(
            df["country"].dropna().astype(str).unique().tolist()
        )

        selected_country = st.selectbox(
            "Country",
            country_options,
            key="market_country_filter",
        )

    with f4:
        industry_options = ["All"] + sorted(
            df["industry"].dropna().astype(str).unique().tolist()
        )

        selected_industry = st.selectbox(
            "Industry",
            industry_options,
            key="market_industry_filter",
        )

    market_base = df.copy()

    if selected_channel != "All":
        market_base = market_base[
            market_base["marketing_channel"].astype(str) == selected_channel
        ]

    if selected_country != "All":
        market_base = market_base[
            market_base["country"].astype(str) == selected_country
        ]

    if selected_industry != "All":
        market_base = market_base[
            market_base["industry"].astype(str) == selected_industry
        ]

    prev_start, prev_end = get_previous_period(start_date, end_date)

    market_df = filter_date(market_base, start_date, end_date)

    if start_date is None or end_date is None:
        previous_df = pd.DataFrame(columns=market_base.columns)
    else:
        previous_df = filter_date(market_base, prev_start, prev_end)

    render_html(f"""
    <div class="marketing-timeline">
        Current period: {date_label(start_date, end_date)}
        &nbsp; | &nbsp;
        KPI movement compares against: {date_label(prev_start, prev_end)}
    </div>
    """)

    if market_df.empty:
        st.warning("No records match the current filters. Try widening the filters above.")
        return

    total_inquiries, demo_count, proposal_count, contract_count = funnel_counts(market_df)
    previous_inquiries, previous_demo, previous_proposal, previous_contract = funnel_counts(previous_df)

    converted_revenue = float(market_df["converted_revenue"].sum())
    previous_converted_revenue = float(previous_df["converted_revenue"].sum())

    funnel_conversion_rate = safe_rate(contract_count, total_inquiries)
    previous_funnel_conversion_rate = safe_rate(previous_contract, previous_inquiries)

    current_web_mask = web_active_mask(market_df)

    if previous_df.empty:
        previous_web_mask = pd.Series(False, index=previous_df.index)
    else:
        previous_web_mask = web_active_mask(previous_df)

    web_leads = int(current_web_mask.sum())
    previous_web_leads = int(previous_web_mask.sum()) if not previous_df.empty else 0

    web_contracts = int(market_df.loc[current_web_mask, "converted"].sum()) if web_leads > 0 else 0

    previous_web_contracts = (
        int(previous_df.loc[previous_web_mask, "converted"].sum())
        if previous_web_leads > 0
        else 0
    )

    web_to_contract_rate = safe_rate(web_contracts, web_leads)
    previous_web_to_contract_rate = safe_rate(previous_web_contracts, previous_web_leads)

    channel_performance = market_df.groupby(
        "marketing_channel",
        as_index=False,
    ).agg(
        converted_revenue=("converted_revenue", "sum"),
        leads=("client_id", "count"),
        conversions=("converted", "sum"),
        high_intent_hits=("high_intent_hits", "sum"),
    )

    channel_performance["conversion_rate"] = channel_performance.apply(
        lambda row: safe_rate(row["conversions"], row["leads"]),
        axis=1,
    )

    channel_performance = channel_performance.sort_values(
        "converted_revenue",
        ascending=False,
    )

    previous_channel_performance = previous_df.groupby(
        "marketing_channel",
        as_index=False,
    ).agg(
        converted_revenue=("converted_revenue", "sum"),
    )

    if not channel_performance.empty:
        top_channel_name = channel_performance.iloc[0]["marketing_channel"]
        top_channel_revenue = float(channel_performance.iloc[0]["converted_revenue"])
    else:
        top_channel_name = "N/A"
        top_channel_revenue = 0.0

    if not previous_channel_performance.empty:
        previous_top_channel_revenue = float(
            previous_channel_performance["converted_revenue"].max()
        )
    else:
        previous_top_channel_revenue = 0.0

    geographic_demand = market_df.groupby(
        "country",
        as_index=False,
    ).agg(
        inquiries=("client_id", "count"),
        converted_revenue=("converted_revenue", "sum"),
        high_intent_hits=("high_intent_hits", "sum"),
    ).sort_values(
        "inquiries",
        ascending=False,
    )

    top_market = geographic_demand.iloc[0]["country"] if not geographic_demand.empty else "N/A"

    render_html('<div class="marketing-section-heading">Key Marketing Indicators</div>')

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        render_html(f"""
        <div class="marketing-kpi-card featured">
            <div class="marketing-kpi-label">Marketing Inquiries</div>
            <div class="marketing-kpi-value">{total_inquiries:,}</div>
            {delta_badge(total_inquiries, previous_inquiries, True)}
            <div class="marketing-kpi-note">
                Top demand market: {top_market}.
            </div>
        </div>
        """)

    with c2:
        render_html(f"""
        <div class="marketing-kpi-card">
            <div class="marketing-kpi-label">Converted Revenue</div>
            <div class="marketing-kpi-value">{compact_money(converted_revenue)}</div>
            {delta_badge(converted_revenue, previous_converted_revenue, True, context="money")}
            <div class="marketing-kpi-note">
                Green means revenue gain; red means revenue loss.
            </div>
        </div>
        """)

    with c3:
        render_html(f"""
        <div class="marketing-kpi-card">
            <div class="marketing-kpi-label">Best Channel</div>
            <div class="marketing-kpi-value">{top_channel_name}</div>
            {delta_badge(top_channel_revenue, previous_top_channel_revenue, True, context="money")}
            <div class="marketing-kpi-note">
                {compact_money(top_channel_revenue)} converted revenue.
            </div>
        </div>
        """)

    with c4:
        render_html(f"""
        <div class="marketing-kpi-card">
            <div class="marketing-kpi-label">Web-to-Contract</div>
            <div class="marketing-kpi-value">{web_to_contract_rate:.1f}%</div>
            {delta_badge(web_to_contract_rate, previous_web_to_contract_rate, True, mode="points")}
            <div class="marketing-kpi-note">
                Contracts from leads with visible IIS/web behaviour.
            </div>
        </div>
        """)

    with c5:
        render_html(f"""
        <div class="marketing-kpi-card">
            <div class="marketing-kpi-label">Funnel Conversion</div>
            <div class="marketing-kpi-value">{funnel_conversion_rate:.1f}%</div>
            {delta_badge(funnel_conversion_rate, previous_funnel_conversion_rate, True, mode="points")}
            <div class="marketing-kpi-note">
                Inquiry-to-contract conversion across the full funnel.
            </div>
        </div>
        """)

    st.markdown("<br>", unsafe_allow_html=True)

    render_html(f"""
    <div class="marketing-insight-card">
        <b>Marketing intelligence summary:</b>
        The strongest channel is <b>{top_channel_name}</b>, generating
        <b>{compact_money(top_channel_revenue)}</b> in converted revenue.
        The current web-to-contract rate is <b>{web_to_contract_rate:.1f}%</b>,
        which means marketing should prioritise campaigns that produce demo requests,
        high-intent website actions, and contract-confirmation behaviour rather than
        only measuring traffic volume.
    </div>
    """)

    row1_col1, row1_col2 = st.columns([1.35, 1.2])

    with row1_col1:
        render_html("""
        <div class="marketing-chart-card">
            <div class="marketing-chart-title">
                Inquiry → Demo → Proposal → Contract Funnel
            </div>
            <div class="marketing-chart-sub">
                Shows where marketing demand converts or leaks before contract.
            </div>
        """)

        funnel_df = pd.DataFrame(
            {
                "stage": ["Inquiry", "Demo", "Proposal", "Contract"],
                "value": [total_inquiries, demo_count, proposal_count, contract_count],
            }
        )

        fig_funnel = go.Figure(
            go.Funnel(
                y=funnel_df["stage"],
                x=funnel_df["value"],
                textinfo="value+percent initial",
                marker=dict(
                    color=[PURPLE_DARK, PURPLE_DEEP, PURPLE_SOFT, TEAL]
                ),
                connector={
                    "line": {
                        "color": LAVENDER,
                        "width": 2,
                    }
                },
                hovertemplate="<b>%{y}</b><br>Leads: %{x:,}<extra></extra>",
            )
        )

        fig_funnel = apply_dark_chart_layout(fig_funnel, height=250)
        fig_funnel.update_layout(showlegend=False)

        st.plotly_chart(
            fig_funnel,
            use_container_width=True,
            key="market_funnel_chart",
            config={"displayModeBar": False},
        )

        render_html("</div>")

    with row1_col2:
        render_html("""
        <div class="marketing-chart-card">
            <div class="marketing-chart-title">
                Top Marketing Channels by Converted Revenue
            </div>
            <div class="marketing-chart-sub">
                Shows which channels generate business value, not just traffic.
            </div>
        """)

        top_channels = channel_performance.head(6).copy()

        fig_channel = go.Figure(
            go.Bar(
                y=top_channels["marketing_channel"][::-1],
                x=top_channels["converted_revenue"][::-1],
                orientation="h",
                text=[
                    compact_money(value)
                    for value in top_channels["converted_revenue"][::-1]
                ],
                textposition="outside",
                marker=dict(
                    color=top_channels["converted_revenue"][::-1],
                    colorscale=[
                        [0.0, PURPLE_DARK],
                        [0.5, PURPLE],
                        [1.0, LAVENDER],
                    ],
                ),
                hovertemplate="<b>%{y}</b><br>Converted revenue: BWP %{x:,.0f}<extra></extra>",
            )
        )

        fig_channel = apply_dark_chart_layout(fig_channel, height=250)
        fig_channel.update_layout(showlegend=False)
        fig_channel.update_xaxes(title="Converted Revenue", tickprefix="BWP ")
        fig_channel.update_yaxes(title="")

        st.plotly_chart(
            fig_channel,
            use_container_width=True,
            key="market_channel_chart",
            config={"displayModeBar": False},
        )

        render_html("</div>")

    row2_col1, row2_col2 = st.columns([1.1, 1.3])

    with row2_col1:
        render_html("""
        <div class="marketing-chart-card">
            <div class="marketing-chart-title">
                Geographic Demand Heat Map
            </div>
            <div class="marketing-chart-sub">
                Shows countries generating marketing demand and web interest.
            </div>
        """)

        if geographic_demand.empty:
            st.info("No geographic demand data available.")
        else:
            fig_geo = px.choropleth(
                geographic_demand,
                locations="country",
                locationmode="country names",
                color="inquiries",
                hover_name="country",
                hover_data={
                    "inquiries": True,
                    "converted_revenue": ":,.0f",
                    "high_intent_hits": True,
                },
                color_continuous_scale=[
                    [0.0, PURPLE_DARK],
                    [0.5, PURPLE],
                    [1.0, LAVENDER],
                ],
            )

            fig_geo.update_geos(
                bgcolor="rgba(0,0,0,0)",
                lakecolor="rgba(0,0,0,0)",
                landcolor="rgba(255,255,255,0.03)",
                showframe=False,
                showcoastlines=True,
                coastlinecolor="rgba(216,180,254,0.25)",
                projection_type="natural earth",
            )

            fig_geo.update_layout(
                height=250,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color=TEXT_MUTED),
                margin=dict(l=0, r=0, t=0, b=0),
                coloraxis_colorbar=dict(
                    title=dict(text="Inquiries", font=dict(color=TEXT_MUTED)),
                    tickfont=dict(color=TEXT_MUTED),
                ),
            )

            st.plotly_chart(
                fig_geo,
                use_container_width=True,
                key="market_geo_heatmap",
                config={"displayModeBar": False},
            )

        render_html("</div>")

    with row2_col2:
        render_html("""
        <div class="marketing-chart-card">
            <div class="marketing-chart-title">
                Marketing Growth Trend
            </div>
            <div class="marketing-chart-sub">
                Monthly inquiries, conversions, and converted revenue.
            </div>
        """)

        trend_df = market_df.dropna(subset=["inquiry_date"]).copy()

        if trend_df.empty:
            st.info("No date data available for growth trend.")
        else:
            trend_df["month"] = trend_df["inquiry_date"].dt.to_period("M").astype(str)

            monthly = trend_df.groupby(
                "month",
                as_index=False,
            ).agg(
                inquiries=("client_id", "count"),
                conversions=("converted", "sum"),
                converted_revenue=("converted_revenue", "sum"),
            )

            fig_growth = go.Figure()

            fig_growth.add_trace(
                go.Scatter(
                    x=monthly["month"],
                    y=monthly["inquiries"],
                    mode="lines+markers",
                    name="Inquiries",
                    line=dict(color=LAVENDER, width=3, shape="spline"),
                    hovertemplate="Inquiries: %{y:,}<extra></extra>",
                )
            )

            fig_growth.add_trace(
                go.Scatter(
                    x=monthly["month"],
                    y=monthly["conversions"],
                    mode="lines+markers",
                    name="Conversions",
                    line=dict(color=TEAL, width=3, shape="spline"),
                    hovertemplate="Conversions: %{y:,}<extra></extra>",
                )
            )

            fig_growth.add_trace(
                go.Bar(
                    x=monthly["month"],
                    y=monthly["converted_revenue"],
                    name="Converted Revenue",
                    marker=dict(color="rgba(124, 58, 237, 0.38)"),
                    yaxis="y2",
                    hovertemplate="Revenue: BWP %{y:,.0f}<extra></extra>",
                )
            )

            fig_growth.update_layout(
                yaxis=dict(
                    title=dict(text="Lead Count", font=dict(color=TEXT_MUTED)),
                    showgrid=True,
                    gridcolor="rgba(216,180,254,0.10)",
                    tickfont=dict(color=TEXT_MUTED),
                ),
                yaxis2=dict(
                    title=dict(text="Revenue", font=dict(color=TEXT_MUTED)),
                    overlaying="y",
                    side="right",
                    showgrid=False,
                    tickprefix="BWP ",
                    tickfont=dict(color=TEXT_MUTED),
                ),
            )

            fig_growth = apply_dark_chart_layout(fig_growth, height=250)

            st.plotly_chart(
                fig_growth,
                use_container_width=True,
                key="market_growth_trend",
                config={"displayModeBar": False},
            )

        render_html("</div>")

    row3_col1, row3_col2 = st.columns([1.2, 1.2])

    with row3_col1:
        render_html("""
        <div class="marketing-chart-card">
            <div class="marketing-chart-title">
                Industry Segmentation
            </div>
            <div class="marketing-chart-sub">
                Shows which industries produce the strongest demand and revenue.
            </div>
        """)

        industry_df = market_df.groupby(
            "industry",
            as_index=False,
        ).agg(
            inquiries=("client_id", "count"),
            converted_revenue=("converted_revenue", "sum"),
            conversions=("converted", "sum"),
            avg_lead_score=("lead_score", "mean"),
        )

        industry_df["conversion_rate"] = industry_df.apply(
            lambda row: safe_rate(row["conversions"], row["inquiries"]),
            axis=1,
        )

        industry_df = industry_df.sort_values(
            "converted_revenue",
            ascending=False,
        ).head(8)

        if industry_df.empty:
            st.info("No industry segmentation data available.")
        else:
            fig_industry = go.Figure(
                go.Bar(
                    y=industry_df["industry"][::-1],
                    x=industry_df["converted_revenue"][::-1],
                    orientation="h",
                    text=[
                        compact_money(value)
                        for value in industry_df["converted_revenue"][::-1]
                    ],
                    textposition="outside",
                    marker=dict(
                        color=industry_df["avg_lead_score"][::-1],
                        colorscale=[
                            [0.0, PURPLE_DARK],
                            [0.5, PURPLE],
                            [1.0, TEAL],
                        ],
                    ),
                    hovertemplate=(
                        "<b>%{y}</b><br>"
                        "Revenue: BWP %{x:,.0f}<br>"
                        "Avg lead score: %{marker.color:.1f}"
                        "<extra></extra>"
                    ),
                )
            )

            fig_industry = apply_dark_chart_layout(fig_industry, height=250)
            fig_industry.update_layout(showlegend=False)
            fig_industry.update_xaxes(title="Converted Revenue", tickprefix="BWP ")
            fig_industry.update_yaxes(title="")

            st.plotly_chart(
                fig_industry,
                use_container_width=True,
                key="market_industry_segmentation",
                config={"displayModeBar": False},
            )

        render_html("</div>")

    with row3_col2:
        render_html("""
        <div class="marketing-chart-card">
            <div class="marketing-chart-title">
                Cross-Sell Opportunity Matrix
            </div>
            <div class="marketing-chart-sub">
                Higher values show stronger industry-service opportunity.
            </div>
        """)

        matrix_df = market_df.copy()

        matrix_df["opportunity_score"] = (
            matrix_df["conversion_probability"] * 45
            + matrix_df["lead_score"] * 0.35
            + matrix_df["high_intent_hits"] * 4
            + matrix_df["demo_request_count"] * 5
            + matrix_df["proposal_download_count"] * 4
        )

        matrix_summary = matrix_df.groupby(
            ["industry", "service_type"],
            as_index=False,
        ).agg(
            opportunity_score=("opportunity_score", "mean"),
        )

        if matrix_summary.empty:
            st.info("No cross-sell matrix data available.")
        else:
            pivot = matrix_summary.pivot_table(
                index="industry",
                columns="service_type",
                values="opportunity_score",
                aggfunc="mean",
                fill_value=0,
            )

            fig_matrix = go.Figure(
                data=go.Heatmap(
                    z=pivot.values,
                    x=pivot.columns,
                    y=pivot.index,
                    colorscale=[
                        [0.0, PURPLE_DARK],
                        [0.5, PURPLE],
                        [1.0, TEAL],
                    ],
                    colorbar=dict(
                        title=dict(text="Opportunity", font=dict(color=TEXT_MUTED)),
                        tickfont=dict(color=TEXT_MUTED),
                    ),
                    hovertemplate=(
                        "<b>Industry:</b> %{y}<br>"
                        "<b>Service:</b> %{x}<br>"
                        "<b>Opportunity Score:</b> %{z:.1f}"
                        "<extra></extra>"
                    ),
                )
            )

            fig_matrix = apply_dark_chart_layout(fig_matrix, height=250)
            fig_matrix.update_layout(showlegend=False)
            fig_matrix.update_xaxes(tickangle=-30)

            st.plotly_chart(
                fig_matrix,
                use_container_width=True,
                key="market_cross_sell_matrix",
                config={"displayModeBar": False},
            )

        render_html("</div>")

    render_html("""
    <div class="marketing-chart-card">
        <div class="marketing-chart-title">
            Campaign and Web-to-Contract Evidence Table
        </div>
        <div class="marketing-chart-sub">
            Shows which campaigns/channels created revenue, intent, and contracts.
        </div>
    """)

    evidence = channel_performance.copy()

    if evidence.empty:
        st.info("No marketing evidence table available.")

    else:
        evidence["Converted Revenue"] = evidence["converted_revenue"].apply(compact_money)
        evidence["Conversion Rate"] = evidence["conversion_rate"].apply(percent)

        evidence = evidence[
            [
                "marketing_channel",
                "leads",
                "conversions",
                "Conversion Rate",
                "high_intent_hits",
                "Converted Revenue",
            ]
        ].rename(
            columns={
                "marketing_channel": "Marketing Channel",
                "leads": "Leads",
                "conversions": "Conversions",
                "high_intent_hits": "High-Intent Hits",
            }
        )

        render_marketing_evidence_table(evidence)

    render_html("</div>")