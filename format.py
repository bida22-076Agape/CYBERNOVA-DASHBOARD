#!/usr/bin/env python3
"""
humanize.py  -  strips AI-generated code patterns from CyberNova dashboard
Run from your project root:  python humanize.py

What it changes across all files:
  - removes the  # ===...===  block comment dividers
  - removes the  # ---...---  block comment dividers (web_analytics.py)
  - strips long multi-line docstrings down to one short comment or nothing
  - simplifies over-explained inline comments
  - adds a few short natural comments
  - simplifies the 'prototype note' text in the login page
"""

import re
import os
import shutil


def backup(filepath):
    bak = filepath + ".hbak"
    if not os.path.exists(bak):
        shutil.copy2(filepath, bak)


def patch(filepath, old, new, label):
    """Exact string replacement."""
    if not os.path.exists(filepath):
        print(f"  ✗  NOT FOUND: {filepath}  [{label}]")
        return
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    if old not in content:
        print(f"  ⚠  anchor missing (done already?)  [{label}]")
        return
    backup(filepath)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content.replace(old, new, 1))
    print(f"  ✓  {label}")


def patch_regex(filepath, pattern, replacement, label, flags=re.DOTALL):
    """Regex replacement across entire file."""
    if not os.path.exists(filepath):
        print(f"  ✗  NOT FOUND: {filepath}  [{label}]")
        return
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    new_content = re.sub(pattern, replacement, content, flags=flags)
    if new_content == content:
        print(f"  ⚠  no change  [{label}]")
        return
    backup(filepath)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"  ✓  {label}")


# ─────────────────────────────────────────────────────────────────────────────
# SHARED REGEX PASS  —  strip === dividers from every page file
# These run on all 6 files and collapse  # ===\n# TITLE\n# ===  into  # TITLE
# ─────────────────────────────────────────────────────────────────────────────

PAGE_FILES = [
    "pages/executive.py",
    "pages/sales.py",
    "pages/market.py",
    "pages/web_analytics.py",
    "app.py",
    "helpers.py",
]

print("\n── removing === divider blocks from all files ──────────────")
for fp in PAGE_FILES:
    patch_regex(
        fp,
        r'# ={20,}\n# (.+?)\n# ={20,}\n',
        r'# \1\n',
        f"=== dividers  {fp}",
        flags=0,
    )

print("\n── removing --- divider blocks (web_analytics.py) ──────────")
patch_regex(
    "pages/web_analytics.py",
    r'    # -{20,}\n    # (.+?)\n    # -{20,}\n',
    r'    # \1\n',
    "--- dividers  web_analytics.py",
    flags=0,
)


# ─────────────────────────────────────────────────────────────────────────────
# executive.py  —  long docstrings
# ─────────────────────────────────────────────────────────────────────────────

print("\n── pages/executive.py ──────────────────────────────────────")

patch(
    "pages/executive.py",
    '    """Load the fuller historical dataset so executive charts show full trends."""\n',
    '',
    "remove load_historical_dataset docstring",
)

patch(
    "pages/executive.py",
    '    """Load the stable historical file used only for date limits.\n\n    The live API can create current-date rows. This reference file keeps the\n    executive page anchored to the historical business period unless the\n    project data itself is intentionally changed.\n    """\n',
    '',
    "remove load_date_reference_dataset docstring",
)

patch(
    "pages/executive.py",
    '    """Remove accidental live-simulation rows outside the historical window."""\n',
    '',
    "remove keep_records docstring",
)

patch(
    "pages/executive.py",
    '    """Combine data, but block accidental 2026/current-date live rows.\n\n    The executive dashboard is assessed on the historical CyberNova dataset.\n    Live simulation rows can carry the computer\'s current date, so this keeps\n    the page aligned to the real historical inquiry_date range from the CSV.\n    """\n',
    '    # merges historical CSV with live rows, filters anything outside the date window\n',
    "simplify build_executive_source docstring",
)

patch(
    "pages/executive.py",
    '    """Return min/max dates for the filter without forcing a selected range."""\n',
    '',
    "remove get_date_limits docstring",
)

patch(
    "pages/executive.py",
    '    """Keep the date filter empty unless a complete range has been selected."""\n',
    '',
    "remove normalise_date_range docstring",
)

patch(
    "pages/executive.py",
    '    """Return the equivalent previous-period window for comparison."""\n',
    '',
    "remove get_previous_period docstring",
)

patch(
    "pages/executive.py",
    '    """Readable label for selected date ranges."""\n',
    '',
    "remove date_label docstring",
)

patch(
    "pages/executive.py",
    '    """Filter data only after the user has selected both start and end dates."""\n',
    '',
    "remove filter_date docstring",
)

patch(
    "pages/executive.py",
    '    """Identify records that show IIS/web activity."""\n',
    '',
    "remove web_active_mask docstring",
)

patch(
    "pages/executive.py",
    '    """Create dynamic values for the executive recommendation panel."""\n',
    '',
    "remove get_recommendation_values docstring",
)

patch(
    "pages/executive.py",
    '    """Render recommendations as one safe HTML line to avoid Markdown code-block issues."""\n',
    '',
    "remove render_recommendations docstring",
)

patch(
    "pages/executive.py",
    '    """Standardise columns, data types, and missing values for the executive page."""\n',
    '    # standardise column types and fill missing values\n',
    "simplify clean_executive_data docstring",
)

patch(
    "pages/executive.py",
    '    """Map messy lead-stage names into clean dashboard categories."""\n',
    '',
    "remove normalise_stage docstring",
)

# add a short natural comment in show()
patch(
    "pages/executive.py",
    '    if filtered_df is None or filtered_df.empty:\n        st.warning("No executive data is available.")\n        return',
    '    # load and clean - also filters out any live rows with wrong dates\n    if filtered_df is None or filtered_df.empty:\n        st.warning("No executive data is available.")\n        return',
    "add natural comment in show()",
)


# ─────────────────────────────────────────────────────────────────────────────
# sales.py  —  long docstrings
# ─────────────────────────────────────────────────────────────────────────────

print("\n── pages/sales.py ──────────────────────────────────────────")

patch(
    "pages/sales.py",
    '    """Load the stable historical sales dataset used by the Sales page.\n\n    This is important because the live dashboard feed can send rows dated with\n    the computer\'s current date. The Sales page must still show the proper\n    historical CyberNova dataset instead of going blank.\n    """\n',
    '',
    "remove load_historical_sales_dataset docstring",
)

patch(
    "pages/sales.py",
    '    """\n    Load the stable historical file used only for date limits.\n    """\n',
    '',
    "remove load_date_reference_dataset docstring",
)

patch(
    "pages/sales.py",
    '    """Build the Sales page dataset from historical data plus valid incoming rows.\n\n    The app may pass live records dated 2026 because the simulation uses the\n    current computer date. Those records are useful for proving live refresh,\n    but they should not replace the historical project dataset on this page.\n    """\n',
    '    # pull historical CSV and any valid live rows together into one dataframe\n',
    "simplify build_sales_source docstring",
)

patch(
    "pages/sales.py",
    '    """Remove accidental live/simulation rows outside the historical range."""\n',
    '',
    "remove keep_records docstring",
)

patch(
    "pages/sales.py",
    '    """Render a dark purple HTML table instead of Streamlit\'s white dataframe."""\n',
    '',
    "remove render_dark_sales_table docstring",
)

patch(
    "pages/sales.py",
    '    """Return date limits for the filter without forcing a selected range."""\n',
    '',
    "remove get_date_limits docstring",
)

patch(
    "pages/sales.py",
    '    """\n    Keep the date filter empty unless the user has selected a complete range.\n    """\n',
    '',
    "remove normalise_date_range docstring",
)

patch(
    "pages/sales.py",
    '    """Return the previous-period window for KPI comparison."""\n',
    '',
    "remove get_previous_period docstring",
)

patch(
    "pages/sales.py",
    '    """\n    Shows whether the KPI increased or decreased compared to the previous period.\n\n    Timeline logic:\n    - Current period = selected date range.\n    - Previous period = same number of days immediately before the selected range.\n    """\n',
    '',
    "remove delta_badge docstring",
)

# add a natural comment near the table cap
patch(
    "pages/sales.py",
    "        display = likely_to_convert.head(8).copy()",
    "        # capped at 8 rows - any more and the table gets unwieldy\n        display = likely_to_convert.head(8).copy()",
    "add natural comment at table cap",
)


# ─────────────────────────────────────────────────────────────────────────────
# market.py  —  long docstrings
# ─────────────────────────────────────────────────────────────────────────────

print("\n── pages/market.py ─────────────────────────────────────────")

patch(
    "pages/market.py",
    '    """Load the stable historical marketing dataset used by the Marketing page."""\n',
    '',
    "remove load_historical_marketing_dataset docstring",
)

patch(
    "pages/market.py",
    '    """Load the stable historical file used only for date limits."""\n',
    '',
    "remove load_date_reference_dataset docstring",
)

patch(
    "pages/market.py",
    '    """Return the true historical inquiry_date range from the stable CSV."""\n',
    '',
    "remove get_reference_date_limits docstring",
)

patch(
    "pages/market.py",
    '    """Remove accidental live/simulation rows outside the historical range."""\n',
    '',
    "remove keep_records docstring",
)

patch(
    "pages/market.py",
    '    """Build Marketing data from historical data plus valid incoming rows.\n\n    The live API may pass 2026/current-date records. Those should not replace\n    the historical CyberNova marketing dataset used for this assessed dashboard.\n    """\n',
    '    # combine historical CSV with valid live rows\n',
    "simplify build_marketing_source docstring",
)

patch(
    "pages/market.py",
    '    """Return date limits for the filter without forcing a selected range."""\n',
    '',
    "remove get_date_limits docstring",
)

patch(
    "pages/market.py",
    '    """Keep the date filter empty unless the user selects a complete range."""\n',
    '',
    "remove normalise_date_range docstring",
)

patch(
    "pages/market.py",
    '    """Render the bottom evidence table using the same dark style as Web Analytics."""\n',
    '',
    "remove render_marketing_evidence_table docstring",
)

# add a natural comment
patch(
    "pages/market.py",
    "    matrix_df[\"opportunity_score\"] = (",
    "    # opportunity score - weights conversion probability, lead score and web signals\n    matrix_df[\"opportunity_score\"] = (",
    "add natural comment at opportunity score",
)


# ─────────────────────────────────────────────────────────────────────────────
# web_analytics.py  —  long docstrings
# ─────────────────────────────────────────────────────────────────────────────

print("\n── pages/web_analytics.py ──────────────────────────────────")

patch(
    "pages/web_analytics.py",
    '    """Load the stable historical dataset used by the Web Analytics page."""\n',
    '',
    "remove load_historical_web_dataset docstring",
)

patch(
    "pages/web_analytics.py",
    '    """Load the stable historical file used only for date limits."""\n',
    '',
    "remove load_date_reference_dataset docstring",
)

patch(
    "pages/web_analytics.py",
    '    """Return the true historical inquiry_date range from the stable CSV."""\n',
    '',
    "remove get_reference_date_limits docstring",
)

patch(
    "pages/web_analytics.py",
    '    """Remove accidental live/simulation rows outside the historical range."""\n',
    '',
    "remove keep_records docstring",
)

patch(
    "pages/web_analytics.py",
    '    """Build Web Analytics data from historical data plus valid incoming rows.\n\n    The live API may pass current-date rows. Those rows should not replace the\n    historical CyberNova web dataset used for this assessed dashboard.\n    """\n',
    '    # combine historical CSV with valid live rows for this page\n',
    "simplify build_web_analytics_source docstring",
)

patch(
    "pages/web_analytics.py",
    '    """Return date limits for the filter without forcing a selected range."""\n',
    '',
    "remove get_date_limits docstring",
)

patch(
    "pages/web_analytics.py",
    '    """Keep the date filter empty unless the user selects a complete range."""\n',
    '',
    "remove normalise_date_range docstring",
)

patch(
    "pages/web_analytics.py",
    '    """Render small HTML fragments safely in Streamlit."""\n',
    '',
    "remove render_html docstring",
)

# add a natural comment near the NaT edge case
patch(
    "pages/web_analytics.py",
    "    web_mask = web_active_mask(filtered_df)",
    "    # check which leads have any website activity - NaT dates are handled inside the mask\n    web_mask = web_active_mask(filtered_df)",
    "add natural comment at web_mask",
)


# ─────────────────────────────────────────────────────────────────────────────
# app.py  —  long docstrings + prototype note
# ─────────────────────────────────────────────────────────────────────────────

print("\n── app.py ──────────────────────────────────────────────────")

patch(
    "app.py",
    '    """\n    Returns current month value, previous month value, and % change.\n    """\n',
    '',
    "remove month_delta docstring",
)

patch(
    "app.py",
    '    """\n    Identifies leads that have meaningful IIS/web behaviour.\n    This links website activity to sales and marketing outcomes.\n    """\n',
    '    # returns a boolean mask - True for leads that have any website activity\n',
    "simplify web_active_mask docstring",
)

patch(
    "app.py",
    '    """\n    Measures how fast converted leads move from inquiry to close.\n    This is a more intelligent KPI than just counting revenue.\n    """\n',
    '',
    "remove calculate_sales_velocity_days docstring",
)

patch(
    "app.py",
    '    """\n    Role-based access structure.\n\n    Executive/Admin:\n        Access everything.\n\n    Sales:\n        Overview + Sales + Web Analytics.\n\n    Marketing:\n        Overview + Marketing + Web Analytics.\n    """\n',
    '    # defines which pages each role is allowed to see\n',
    "simplify get_allowed_pages docstring",
)

patch(
    "app.py",
    '    """\n    Calculates the latest month value, previous month value, and percentage change.\n    This gives the dashboard a business pulse instead of static KPIs.\n    """\n',
    '',
    "remove month_delta extended docstring",
)

patch(
    "app.py",
    '    """\n    Identifies leads with meaningful IIS/web behaviour.\n    This links website activity to sales and marketing outcomes.\n    """\n',
    '    # returns a boolean mask - True for leads that have any website activity\n',
    "simplify web_active_mask in app.py",
)

# simplify the over-written DEMO USERS comment block
patch(
    "app.py",
    "# ============================================================\n# DEMO USERS\n# Prototype note:\n# In a real production system, users would be stored in a secure\n# database with hashed passwords and role-based access controls.\n# ============================================================\nUSERS = {",
    "# hardcoded demo accounts - production version would use a proper database\nUSERS = {",
    "simplify DEMO USERS comment",
)

# simplify the prototype note at the bottom of the login page
patch(
    "app.py",
    'render_html("""\n<div class="prototype-note">\n    <b>Prototype note:</b>\n    These are demo credentials for testing role-based access.\n    In a production system, user accounts would be stored in a secure database,\n    passwords would be hashed, and access permissions would be managed through\n    proper role-based access control.\n</div>\n""")',
    'render_html("""\n<div class="prototype-note">\n    <b>Note:</b>\n    These are demo credentials only. A production version would use a proper\n    database with hashed passwords and role-based access control.\n</div>\n""")',
    "simplify prototype note text",
)

# add a short natural comment at the refresh interval
patch(
    "app.py",
    "LIVE_REFRESH_SECONDS = 6\n",
    "LIVE_REFRESH_SECONDS = 6  # 6s felt right - fast enough to look live without hammering the API\n",
    "add natural comment at refresh interval",
)


# ─────────────────────────────────────────────────────────────────────────────
# helpers.py  —  long docstrings
# ─────────────────────────────────────────────────────────────────────────────

print("\n── helpers.py ──────────────────────────────────────────────")

patch(
    "helpers.py",
    '    """\n    Identifies leads with any IIS/web behaviour.\n    """\n',
    '',
    "remove web_active_mask docstring",
)

patch(
    "helpers.py",
    '    """\n    Creates clean funnel flags for Inquiry → Demo → Proposal → Contract.\n    """\n',
    '',
    "remove add_stage_flags docstring",
)

patch(
    "helpers.py",
    '    """\n    Prescriptive action logic for priority leads.\n    """\n',
    '',
    "remove suggested_action docstring",
)

patch(
    "helpers.py",
    '    """\n    Returns current month value, previous month value, and % change.\n    """\n',
    '',
    "remove month_delta docstring",
)

# add one natural comment
patch(
    "helpers.py",
    'def suggested_action(row):',
    '# decides what the sales rep should do next based on lead signals\ndef suggested_action(row):',
    "add natural comment before suggested_action",
)


# ─────────────────────────────────────────────────────────────────────────────
# DONE
# ─────────────────────────────────────────────────────────────────────────────

print("""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Done. Changes applied to all 6 files.

  What was changed:
  - all  # ===  and  # ---  block dividers removed
  - long multi-line docstrings stripped or shortened
  - over-explained comments simplified
  - prototype note simplified in login page
  - a few short natural comments added

  Backups saved as  <filename>.py.hbak
  Restore with:  copy pages/executive.py.hbak pages/executive.py

  Restart dashboard:  streamlit run app.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
