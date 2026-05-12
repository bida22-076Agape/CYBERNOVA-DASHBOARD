# fixes.py
# helper functions added to meet the remaining dashboard requirements
# - export button for each page
# - next quarter revenue forecast for executive page
# - insight summary panel shown below KPI cards

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go


def _render(markup):
    st.markdown(markup.strip(), unsafe_allow_html=True)


def _fmt(value):
    try:
        v = float(value)
        if abs(v) >= 1_000_000:
            return f"BWP {v / 1_000_000:.1f}M"
        if abs(v) >= 1_000:
            return f"BWP {v / 1_000:.1f}K"
        return f"BWP {v:,.0f}"
    except Exception:
        return "BWP 0"


# export button - lets users download the current filtered data as a CSV file
def render_export_button(df, filename="cybernova_report"):
    if df is None or df.empty:
        return

    out = df.copy()
    for col in ["inquiry_date", "close_date", "demo_date", "proposal_date",
                "first_web_event", "last_web_event"]:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce").dt.strftime("%Y-%m-%d")

    csv_bytes = out.to_csv(index=False).encode("utf-8")

    _render("""
    <style>
        div[data-testid="stDownloadButton"] > button {
            background: linear-gradient(135deg, rgba(16,8,34,0.98), rgba(37,0,110,0.96)) !important;
            color: #f8fafc !important;
            border: 1px solid rgba(196,181,253,0.38) !important;
            border-radius: 14px !important;
            font-weight: 850 !important;
            padding: 0.65rem 1.3rem !important;
        }
        div[data-testid="stDownloadButton"] > button:hover {
            background: linear-gradient(135deg, #25006e, #7c3aed) !important;
        }
        div[data-testid="stDownloadButton"] > button p {
            color: #f8fafc !important;
            font-weight: 850 !important;
        }
    </style>
    """)

    st.download_button(
        label="⬇  Export as CSV",
        data=csv_bytes,
        file_name=f"{filename}.csv",
        mime="text/csv",
        key=f"dl_{filename}_{len(df)}",
    )


# projects revenue 3 months forward using a linear trend fitted on monthly history
def render_next_quarter_forecast(df):
    TEXT_LIGHT  = "#f8fafc"
    TEXT_MUTED  = "#94a3b8"
    PURPLE      = "#a855f7"
    PURPLE_DEEP = "#6d28d9"
    LILAC       = "#c4b5fd"
    GREEN       = "#22c55e"
    RED         = "#ef4444"
    CARD_BG     = "rgba(14,13,30,0.96)"
    CARD_BORDER = "rgba(148,113,255,0.22)"

    if df is None or df.empty or "inquiry_date" not in df.columns:
        return

    tmp = df.copy()
    tmp["inquiry_date"] = pd.to_datetime(tmp["inquiry_date"], errors="coerce")
    tmp = tmp.dropna(subset=["inquiry_date"])

    if tmp.empty:
        return

    tmp["month"] = tmp["inquiry_date"].dt.to_period("M").dt.to_timestamp()

    monthly = (
        tmp.groupby("month", as_index=False)
        .agg(revenue=("actual_revenue", "sum"))
        .sort_values("month")
    )

    if len(monthly) < 3:
        return

    # fit a straight line through the monthly totals
    t = np.arange(len(monthly), dtype=float)
    slope, intercept = np.polyfit(t, monthly["revenue"].values, 1)

    last_month = monthly["month"].iloc[-1]
    next_months = pd.date_range(
        start=last_month + pd.offsets.MonthBegin(1),
        periods=3, freq="MS"
    )

    future_t = np.arange(len(monthly), len(monthly) + 3, dtype=float)
    projected = np.maximum(slope * future_t + intercept, 0.0)
    q_total = float(projected.sum())

    all_t = np.arange(len(monthly) + 3, dtype=float)
    trend_y = slope * all_t + intercept
    all_dates = list(monthly["month"]) + list(next_months)

    up = slope > 0
    col = GREEN if up else RED
    arrow = "↑" if up else "↓"

    _render(f"""
    <div style="
        background: radial-gradient(circle at 85% 0%, rgba(109,40,217,0.18), transparent 50%), {CARD_BG};
        border: 1px solid {CARD_BORDER};
        border-radius: 16px;
        padding: 14px 16px 4px 16px;
        box-shadow: 0 16px 40px rgba(0,0,0,0.24);
        margin-bottom: 12px;
    ">
        <div style="color:{TEXT_LIGHT}; font-size:14px; font-weight:850; margin-bottom:3px;">
            Next-Quarter Revenue Forecast
        </div>
        <div style="color:{TEXT_MUTED}; font-size:10px; margin-bottom:8px;">
            Linear trend projection from historical monthly revenue.
        </div>
        <div style="
            display:inline-block;
            background:rgba(168,85,247,0.14);
            border:1px solid rgba(168,85,247,0.30);
            border-radius:999px;
            padding:5px 14px;
            font-size:12px;
            font-weight:900;
            color:{LILAC};
            margin-bottom:10px;
        ">
            {arrow} Projected next quarter: <b style="color:{col}">{_fmt(q_total)}</b>
        </div>
    """)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=monthly["month"], y=monthly["revenue"],
        name="Historical",
        marker=dict(color="rgba(109,40,217,0.45)", line=dict(color=PURPLE_DEEP, width=1)),
        hovertemplate="Actual: BWP %{y:,.0f}<extra></extra>",
    ))

    fig.add_trace(go.Bar(
        x=next_months, y=projected,
        name="Forecast",
        marker=dict(color="rgba(34,197,94,0.35)", line=dict(color=GREEN, width=1.5)),
        hovertemplate="Forecast: BWP %{y:,.0f}<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=all_dates, y=trend_y,
        mode="lines", name="Trend",
        line=dict(color=LILAC, width=2, dash="dot"),
        hoverinfo="skip",
    ))

    fig.add_vline(
        x=last_month.timestamp() * 1000,
        line_width=1, line_dash="dash",
        line_color="rgba(196,181,253,0.40)",
        annotation_text="  Forecast →",
        annotation_font_color=LILAC,
        annotation_font_size=10,
        annotation_position="top right",
    )

    fig.update_layout(
        height=240,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, system-ui", color=TEXT_MUTED, size=10),
        margin=dict(l=6, r=6, t=8, b=6),
        hoverlabel=dict(bgcolor=CARD_BG, bordercolor=PURPLE, font_color=TEXT_LIGHT),
        legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="left", x=0,
                    font=dict(color=TEXT_MUTED, size=9)),
        barmode="overlay",
    )
    fig.update_xaxes(showgrid=False, zeroline=False, tickfont=dict(color=TEXT_MUTED, size=9))
    fig.update_yaxes(showgrid=True, gridcolor="rgba(148,113,255,0.10)",
                     zeroline=False, tickfont=dict(color=TEXT_MUTED, size=9), tickprefix="BWP ")

    st.plotly_chart(fig, use_container_width=True,
                    key="forecast_chart", config={"displayModeBar": False})
    _render("</div>")


# short insight summary shown below KPI cards - plain language description of current state
def render_storytelling_box(what, why, next_action):
    summary = f"{what} {why} {next_action}"
    _render(f"""
    <div style="
        background: rgba(14,13,30,0.96);
        border: 1px solid rgba(196,181,253,0.22);
        border-radius: 12px;
        padding: 14px 18px;
        margin: 10px 0 18px 0;
        box-shadow: 0 12px 30px rgba(0,0,0,0.20);
    ">
        <p style="color:#94a3b8; font-size:11px; font-weight:700;
                  text-transform:uppercase; letter-spacing:0.5px; margin:0 0 6px 0;">
            Page Summary
        </p>
        <p style="color:#cbd5e1; font-size:13px; margin:0; line-height:1.6;">
            {summary}
        </p>
    </div>
    """)
