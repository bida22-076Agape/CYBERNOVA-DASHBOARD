#!/usr/bin/env python3
"""
apply_fixes.py  —  CyberNova Dashboard Auto-Patcher
=====================================================
Automatically applies all three requirement fixes to your existing page files.
  CR11 — Export Report button on every page
  CR03 — Next-Quarter Revenue Forecast on Executive page
  CR12 — WHAT → WHY → NEXT storytelling box on every page

HOW TO USE:
  1. Make sure fixes.py is in the same folder as app.py (your project root).
  2. Open a terminal in that folder.
  3. Run:  python apply_fixes.py
  4. The script will patch pages/executive.py, pages/sales.py,
     pages/market.py, pages/web_analytics.py, and app.py.
  5. Backups of each file are saved as <filename>.py.bak before patching.

Run it again safely — it skips any patch already applied.
"""

import os
import shutil

# ─────────────────────────────────────────────────────────────────────────────
# CORE PATCH UTILITY
# ─────────────────────────────────────────────────────────────────────────────

def patch(filepath: str, old: str, new: str, label: str) -> None:
    """Replace `old` with `new` inside `filepath` exactly once."""
    if not os.path.exists(filepath):
        print(f"  ✗  FILE NOT FOUND: {filepath}  [{label}]")
        return

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if old not in content:
        print(f"  ⚠  Anchor not found — already patched or file changed  [{label}]")
        return

    if new in content:
        print(f"  ✓  Already applied — skipping  [{label}]")
        return

    # Backup once (don't overwrite an existing backup)
    bak = filepath + ".bak"
    if not os.path.exists(bak):
        shutil.copy2(filepath, bak)
        print(f"     Backup saved → {bak}")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content.replace(old, new, 1))

    print(f"  ✓  Patched  [{label}]")


# ─────────────────────────────────────────────────────────────────────────────
# EXECUTIVE PAGE  (pages/executive.py)
# ─────────────────────────────────────────────────────────────────────────────

print("\n── pages/executive.py ──────────────────────────────────────")

# 1. Import
patch(
    "pages/executive.py",
    "import streamlit as st\n",
    "import streamlit as st\nfrom fixes import render_export_button, render_next_quarter_forecast, render_storytelling_box\n",
    "CR11/CR03/CR12  import",
)

# 2. CR12 Storytelling — insert before the Charts section
patch(
    "pages/executive.py",
    '    st.markdown("<br>", unsafe_allow_html=True)\n\n    # Charts\n    chart_col1, chart_col2 = st.columns([3, 2])',
    '''    st.markdown("<br>", unsafe_allow_html=True)

    # CR12 — Data Storytelling Box
    _exec_what = (
        f"CyberNova has generated {compact_money(total_revenue)} in actual revenue — "
        f"{target_achievement:.1f}% of the revenue target — with a conversion rate of "
        f"{conversion_rate:.1f}% across {total_leads:,} leads."
    )
    _exec_why = (
        f"Actual revenue is {'ahead of' if revenue_vs_forecast >= 100 else 'below'} "
        f"forecast at {revenue_vs_forecast:.1f}%. "
        f"Web-influenced revenue accounts for {compact_money(web_influenced_revenue)}, "
        f"reflecting the impact of digital channels on closed deals."
    )
    _exec_next = (
        "Protect the strongest markets and scale the top service line."
        if target_achievement >= 100
        else
        "Close the revenue gap by accelerating high-probability pipeline "
        "and improving follow-up speed on web-active leads."
    )
    render_storytelling_box(_exec_what, _exec_why, _exec_next)

    # Charts
    chart_col1, chart_col2 = st.columns([3, 2])''',
    "CR12  storytelling box",
)

# 3. CR03 Next-Quarter Forecast — insert before Strategic Recommendations
patch(
    "pages/executive.py",
    "    # Strategic Recommendations\n    render_html('<div class=\"exec-section-heading\">Strategic Recommendations</div>')",
    '''    # CR03 — Next-Quarter Revenue Forecast
    render_next_quarter_forecast(df)

    # Strategic Recommendations
    render_html('<div class="exec-section-heading">Strategic Recommendations</div>')''',
    "CR03  next-quarter forecast",
)

# 4. CR11 Export — insert before the footer caption
patch(
    "pages/executive.py",
    "    # Footer\n    render_html(\"\"\"\n        <div class=\"exec-caption\">",
    '''    # CR11 — Export Report
    render_export_button(df, "cybernova_executive_report")

    # Footer
    render_html("""
        <div class="exec-caption">''',
    "CR11  export button",
)


# ─────────────────────────────────────────────────────────────────────────────
# SALES PAGE  (pages/sales.py)
# ─────────────────────────────────────────────────────────────────────────────

print("\n── pages/sales.py ──────────────────────────────────────────")

# 1. Import
patch(
    "pages/sales.py",
    "import streamlit as st\n",
    "import streamlit as st\nfrom fixes import render_export_button, render_storytelling_box\n",
    "CR11/CR12  import",
)

# 2. CR12 Storytelling — insert before Chart Row 1
patch(
    "pages/sales.py",
    '    st.markdown("<div style=\\"height:4px\\"></div>", unsafe_allow_html=True)\n\n    # ============================================================\n    # CHART ROW 1\n    # ============================================================',
    '''    st.markdown("<div style=\\"height:4px\\"></div>", unsafe_allow_html=True)

    # CR12 — Data Storytelling Box
    _sales_what = (
        f"The pipeline holds {total_leads:,} leads with {won_deals:,} converted — "
        f"a {conversion_rate:.1f}% conversion rate. "
        f"Actual revenue stands at {compact_money(total_revenue)}."
    )
    _sales_why = (
        f"The weighted pipeline value is {compact_money(active_pipeline)}, meaning "
        f"significant forecast value remains unconverted. "
        f"Sales velocity averages {velocity:.0f} days from inquiry to close."
    )
    _sales_next = (
        f"Focus on the {web_hot_leads:,} web hot leads showing demo requests or "
        "high-intent signals — these are the most likely to convert in the next cycle."
    )
    render_storytelling_box(_sales_what, _sales_why, _sales_next)

    # ============================================================
    # CHART ROW 1
    # ============================================================''',
    "CR12  storytelling box",
)

# 3. CR11 Export — append after the closing div of the Priority Leads card
patch(
    "pages/sales.py",
    "        render_dark_sales_table(display)\n\n    render_html(\"</div>\")",
    '''        render_dark_sales_table(display)

    render_html("</div>")

    # CR11 — Export Report
    render_export_button(sales_df, "cybernova_sales_report")''',
    "CR11  export button",
)


# ─────────────────────────────────────────────────────────────────────────────
# MARKETING PAGE  (pages/market.py)
# ─────────────────────────────────────────────────────────────────────────────

print("\n── pages/market.py ─────────────────────────────────────────")

# 1. Import
patch(
    "pages/market.py",
    "import streamlit as st\n",
    "import streamlit as st\nfrom fixes import render_export_button, render_storytelling_box\n",
    "CR11/CR12  import",
)

# 2. CR12 Storytelling — insert before the row1 charts
patch(
    "pages/market.py",
    "    st.markdown(\"<br>\", unsafe_allow_html=True)\n\n    row1_col1, row1_col2 = st.columns([1.35, 1.2])",
    '''    st.markdown("<br>", unsafe_allow_html=True)

    # CR12 — Data Storytelling Box
    _mkt_what = (
        f"Marketing has generated {total_inquiries:,} inquiries with "
        f"{contract_count:,} contracts — a {funnel_conversion_rate:.1f}% "
        f"funnel conversion rate. Converted revenue is {compact_money(converted_revenue)}."
    )
    _mkt_why = (
        f"The strongest channel is {top_channel_name}, contributing "
        f"{compact_money(top_channel_revenue)} in converted revenue. "
        f"Web-to-contract rate is {web_to_contract_rate:.1f}%, showing how "
        "digital behaviour connects to commercial outcomes."
    )
    _mkt_next = (
        f"Invest in campaigns that replicate {top_channel_name} behaviour — "
        "prioritise demo requests and high-intent web actions over raw traffic volume."
    )
    render_storytelling_box(_mkt_what, _mkt_why, _mkt_next)

    row1_col1, row1_col2 = st.columns([1.35, 1.2])''',
    "CR12  storytelling box",
)

# 3. CR11 Export — append after the closing div of the Evidence Table card
patch(
    "pages/market.py",
    "        render_marketing_evidence_table(evidence)\n\n    render_html(\"</div>\")",
    '''        render_marketing_evidence_table(evidence)

    render_html("</div>")

    # CR11 — Export Report
    render_export_button(market_df, "cybernova_marketing_report")''',
    "CR11  export button",
)


# ─────────────────────────────────────────────────────────────────────────────
# WEB ANALYTICS PAGE  (pages/web_analytics.py)
# ─────────────────────────────────────────────────────────────────────────────

print("\n── pages/web_analytics.py ──────────────────────────────────")

# 1. Import  (web_analytics imports from helpers, so anchor on that import block)
patch(
    "pages/web_analytics.py",
    "from helpers import (\n    clean_dashboard_data,\n",
    "from helpers import (\n    clean_dashboard_data,\n",  # unchanged — real patch below
    "import check only",
)

patch(
    "pages/web_analytics.py",
    "import streamlit as st\nimport plotly.graph_objects as go\n\nfrom helpers import",
    "import streamlit as st\nimport plotly.graph_objects as go\nfrom fixes import render_export_button, render_storytelling_box\n\nfrom helpers import",
    "CR11/CR12  import",
)

# 2. CR12 Storytelling — insert after the insight box, before funnel data
patch(
    "pages/web_analytics.py",
    "    # -------------------------------------------------------------------------\n    # Funnel data\n    # -------------------------------------------------------------------------",
    '''    # CR12 — Data Storytelling Box
    _web_what = (
        f"There are {web_active_leads:,} web-active leads generating "
        f"{total_web_events:,} IIS events. "
        f"{web_contracts:,} contracts trace directly to web behaviour — "
        f"{money_short(web_influenced_revenue)} in web-influenced revenue."
    )
    _web_why = (
        f"The strongest web signal comes from {top_channel}, concentrated in "
        f"{top_country}. High-intent hits total {high_intent_hits:,}, with "
        f"{demo_requests:,} demo requests captured from website activity."
    )
    _web_next = (
        "Sales should prioritise leads with 3 or more high-intent hits and at least "
        "one demo request — these show the strongest digital buying signals and are "
        "most likely to convert in the next sales cycle."
    )
    render_storytelling_box(_web_what, _web_why, _web_next)

    # -------------------------------------------------------------------------
    # Funnel data
    # -------------------------------------------------------------------------''',
    "CR12  storytelling box",
)

# 3. CR11 Export — insert before the web footer
patch(
    "pages/web_analytics.py",
    '    render_html(\n        """\n        <div class="web-footer">\n            CyberNova Web Analytics',
    '''    # CR11 — Export Report
    render_export_button(filtered_df, "cybernova_web_analytics_report")

    render_html(
        """
        <div class="web-footer">
            CyberNova Web Analytics''',
    "CR11  export button",
)


# ─────────────────────────────────────────────────────────────────────────────
# OVERVIEW PAGE  (app.py  →  show_overview function)
# ─────────────────────────────────────────────────────────────────────────────

print("\n── app.py (Overview) ───────────────────────────────────────")

# 1. Import — add after the existing helpers import
patch(
    "app.py",
    "from helpers import load_data\n",
    "from helpers import load_data\nfrom fixes import render_export_button, render_storytelling_box\n",
    "CR11/CR12  import",
)

# 2. CR12 Storytelling + CR11 Export — insert after the dashboard buttons block
#    and before the final `return` in show_overview()
patch(
    "app.py",
    "    # Important:\n    # The Overview page ends here. It must not render Executive/Sales/Marketing content below it.\n    return",
    '''    # CR12 — Data Storytelling Box (Overview)
    _ov_what = (
        f"CyberNova has converted {percent(conversion_rate)} of its pipeline, "
        f"generating {money_short(total_revenue)} in closed revenue from {total_leads:,} leads. "
        f"The weighted forecast stands at {money_short(forecasted_value)}."
    )
    _ov_why = (
        f"Web-influenced revenue is {money_short(web_influenced_revenue)} "
        f"({percent(web_revenue_share)} of total). "
        f"{high_intent_hits:,} high-intent web actions and {demo_requests:,} demo requests "
        "are the strongest current buying signals in the pipeline."
    )
    _ov_next = (
        f"{sales_velocity_text}. "
        "To improve revenue performance, prioritise high-intent web leads before "
        "low-engagement pipeline records and review the Sales and Executive dashboards for detail."
    )
    render_storytelling_box(_ov_what, _ov_why, _ov_next)

    # CR11 — Export full dataset
    render_export_button(df, "cybernova_overview_report")

    # Important:
    # The Overview page ends here. It must not render Executive/Sales/Marketing content below it.
    return''',
    "CR12/CR11  overview storytelling + export",
)


# ─────────────────────────────────────────────────────────────────────────────
# DONE
# ─────────────────────────────────────────────────────────────────────────────

print("""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  All patches applied!

  What was added:
  ✓ CR11 — Export CSV button on every page
  ✓ CR03 — Next-quarter revenue forecast (Executive)
  ✓ CR12 — WHAT → WHY → NEXT storytelling on every page

  Backups saved as  <filename>.py.bak

  Start your dashboard normally:
    streamlit run app.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
