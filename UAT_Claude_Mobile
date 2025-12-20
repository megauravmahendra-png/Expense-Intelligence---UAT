import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from io import BytesIO
import calendar
from glob import glob
import os

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="Expense Intelligence - UAT",
    page_icon="💳",
    layout="wide"
)

# =========================================================
# MOBILE-OPTIMIZED UI THEME
# =========================================================
st.markdown("""
<style>
body { background:#0b1220; color:#e5e7eb; }

/* Responsive containers */
.section-box {
    background:#0f172a;
    border:1px solid #1e293b;
    border-radius:18px;
    padding:22px;
    margin-bottom:24px;
}

.card {
    background:#111827;
    border:1px solid #1f2937;
    border-radius:16px;
    padding:18px;
    transition:0.25s;
    margin-bottom:16px;
}

.card:hover {
    transform:translateY(-4px);
    box-shadow:0 10px 24px rgba(0,0,0,0.35);
}

.kpi-title {
    font-size:0.75rem;
    letter-spacing:0.08em;
    color:#9ca3af;
    text-transform:uppercase;
    margin-bottom:8px;
}

.kpi-value {
    font-size:1.8rem;
    font-weight:700;
    word-break:break-word;
}

.subtle {
    color:#9ca3af;
    font-size:0.85rem;
}

/* Mobile optimizations */
@media (max-width: 768px) {
    .kpi-title {
        font-size:0.7rem;
    }
    
    .kpi-value {
        font-size:1.5rem;
    }
    
    .card {
        padding:14px;
        margin-bottom:12px;
    }
    
    .section-box {
        padding:16px;
        margin-bottom:16px;
        border-radius:12px;
    }
    
    /* Make text more readable on mobile */
    body {
        font-size:16px !important;
    }
    
    h1, h2, h3, h4 {
        font-size:1.3rem !important;
        line-height:1.4 !important;
    }
    
    /* Increase touch targets */
    button, .stButton button {
        min-height:44px !important;
        padding:12px 20px !important;
        font-size:16px !important;
    }
    
    /* Better input fields */
    input, select, .stSelectbox, .stNumberInput {
        font-size:16px !important;
        min-height:44px !important;
    }
    
    /* Sidebar improvements */
    section[data-testid="stSidebar"] {
        width:85% !important;
        max-width:300px !important;
    }
    
    /* Better spacing for mobile */
    .block-container {
        padding-left:1rem !important;
        padding-right:1rem !important;
        padding-top:1rem !important;
    }
}

/* Better touch targets for all screen sizes */
.stCheckbox {
    min-height:44px;
    display:flex;
    align-items:center;
}

/* Improve popover on mobile */
@media (max-width: 768px) {
    [data-testid="stPopover"] {
        font-size:16px !important;
    }
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# HEADER
# =========================================================
st.markdown("## 💳 Expense Intelligence - UAT")
st.markdown("<div class='subtle'>Designed for awareness, not anxiety</div>", unsafe_allow_html=True)
st.markdown("---")

# =========================================================
# HELPERS
# =========================================================
def detect(df, keys):
    for c in df.columns:
        for k in keys:
            if k.lower() in c.lower():
                return c
    return None

def format_month(m):
    return pd.to_datetime(m + "-01").strftime("%B %y")

WEEK_ORDER = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

# =========================================================
# DATA SOURCE
# =========================================================
with st.sidebar:
    st.markdown("### 📂 Data Source")
    mode = st.radio("", ["Manual Upload", "Local Folder (Auto-sync)"])

dfs = []
if mode == "Manual Upload":
    uploads = st.sidebar.file_uploader(
        "Upload Excel files",
        type=["xlsx"],
        accept_multiple_files=True
    )
    if uploads:
        dfs = [pd.read_excel(f) for f in uploads]
else:
    folder = st.sidebar.text_input(
        "Local Folder Path",
        r"E:\Mahendra\DashBoard\Data"
    )
    all_files = glob(os.path.join(folder, "*.xlsx"))
    # 🔒 IGNORE EXCEL TEMP / LOCK FILES
    valid_files = [
        f for f in all_files
        if not os.path.basename(f).startswith("~$")
    ]
    for f in valid_files:
        try:
            dfs.append(pd.read_excel(f))
        except Exception as e:
            st.warning(f"Skipped file: {os.path.basename(f)}")

if not dfs:
    st.info("Add expense data to begin.")
    st.stop()

df = pd.concat(dfs, ignore_index=True)

# =========================================================
# DATA PREP
# =========================================================
date_col = detect(df, ["date"])
amt_col = detect(df, ["amount"])
cat_col = detect(df, ["category"])
sub_col = detect(df, ["sub"])
desc_col = detect(df, ["merchant","description","name"])

df[date_col] = pd.to_datetime(df[date_col])
df[amt_col] = pd.to_numeric(df[amt_col], errors="coerce").fillna(0)
df["Category"] = df.get(cat_col, "Uncategorized")
df["Sub Category"] = df.get(sub_col, "Uncategorized")
df["Description"] = df.get(desc_col, "Unknown")
df["Month"] = df[date_col].dt.to_period("M").astype(str)
df["Weekday"] = df[date_col].dt.day_name()
df["WeekType"] = np.where(df[date_col].dt.weekday >= 5, "Weekend", "Weekday")

# =========================================================
# FILTERS
# =========================================================
months = sorted(df["Month"].unique())
selected_month = st.sidebar.selectbox(
    "Month",
    months,
    index=len(months)-1,
    format_func=format_month
)

month_df = df[df["Month"] == selected_month]
non_bill_df = month_df[month_df["Category"] != "Bill Payment"]

# =========================================================
# TABS
# =========================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Trends",
    "📅 Monthly",
    "🧠 Intel",
    "📤 Export"
])

# =========================================================
# TAB 1 — TRENDS (RESPONSIVE LAYOUT)
# =========================================================
with tab1:
    st.markdown("### 📈 Long-term Trends")
    
    # Stack on mobile, side-by-side on desktop
    monthly = df.groupby("Month")[amt_col].sum().reset_index()
    fig1 = px.line(monthly, x="Month", y=amt_col, markers=True,
                   template="plotly_dark", title="Total Monthly Spend")
    fig1.update_layout(dragmode=False)
    st.plotly_chart(
        fig1,
        use_container_width=True,
        config={'displayModeBar': False, 'scrollZoom': False, 'doubleClick': False}
    )
    
    cat_trend = df.groupby(["Month","Category"])[amt_col].sum().reset_index()
    fig2 = px.line(cat_trend, x="Month", y=amt_col, color="Category",
                   template="plotly_dark", title="Category-wise Trend")
    fig2.update_layout(dragmode=False)
    st.plotly_chart(
        fig2,
        use_container_width=True,
        config={'displayModeBar': False, 'scrollZoom': False, 'doubleClick': False}
    )

# =========================================================
# TAB 2 — MONTHLY VIEW (MOBILE OPTIMIZED)
# =========================================================
with tab2:
    st.markdown(f"### 📅 {format_month(selected_month)}")
    
    # KPIs - Stack on mobile
    kpis_data = [
        ("Total Spend", month_df[amt_col].sum()),
        ("Excl. Bills", non_bill_df[amt_col].sum()),
        ("Daily Avg", non_bill_df.groupby(date_col)[amt_col].sum().mean()),
        ("Top Category", non_bill_df.groupby("Category")[amt_col].sum().idxmax())
    ]
    
    # Create 2x2 grid for mobile, 4 columns for desktop
    cols = st.columns(2)
    for idx, (title, val) in enumerate(kpis_data):
        col = cols[idx % 2]
        display = f"₹{val:,.0f}" if isinstance(val,(int,float,np.number)) else str(val)
        col.markdown(
            f"<div class='card'><div class='kpi-title'>{title}</div><div class='kpi-value'>{display}</div></div>",
            unsafe_allow_html=True
        )
    
    # Budget Burn-down (full width on mobile)
    st.markdown("#### 📉 Budget Burn-down")
    budget = st.number_input("Monthly Budget", value=30000, step=1000)
    days = calendar.monthrange(
        int(selected_month.split("-")[0]),
        int(selected_month.split("-")[1])
    )[1]
    daily = (
        non_bill_df.groupby(date_col)[amt_col]
        .sum()
        .reindex(pd.date_range(month_df[date_col].min(),
                                month_df[date_col].max()), fill_value=0)
        .cumsum()
        .reset_index()
    )
    daily.columns = ["Date","Actual"]
    ideal = np.linspace(0, budget, days)
    fig = px.line(daily, x="Date", y="Actual", template="plotly_dark")
    fig.add_scatter(
        x=pd.date_range(daily["Date"].min(), periods=days),
        y=ideal, name="Ideal"
    )
    fig.update_layout(height=350, dragmode=False)
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': False, 'doubleClick': False})
    
    # Expense Composition
    st.markdown("#### 🧩 Expense Composition")
    treemap_fig = px.treemap(
        month_df,
        path=["Category","Sub Category"],
        values=amt_col,
        template="plotly_dark"
    )
    treemap_fig.update_layout(height=400, dragmode=False)
    st.plotly_chart(treemap_fig, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': False, 'doubleClick': False})
    
    # Category vs Day (stacked on mobile)
    st.markdown("#### 📆 Spending Pattern")
    fig_cat = px.bar(
        month_df.groupby("Category")[amt_col].sum().reset_index(),
        x="Category", y=amt_col,
        template="plotly_dark", title="Category vs Amount"
    )
    fig_cat.update_layout(height=350, dragmode=False)
    st.plotly_chart(
        fig_cat,
        use_container_width=True,
        config={'displayModeBar': False, 'scrollZoom': False, 'doubleClick': False}
    )
    
    fig_day = px.bar(
        month_df.groupby(date_col)[amt_col].sum().reset_index(),
        x=date_col, y=amt_col,
        template="plotly_dark", title="Amount vs Day"
    )
    fig_day.update_layout(height=350, dragmode=False)
    st.plotly_chart(
        fig_day,
        use_container_width=True,
        config={'displayModeBar': False, 'scrollZoom': False, 'doubleClick': False}
    )
    
    # =====================================================
    # Weekday vs Weekend Behaviour 
    # =====================================================
    st.markdown("### 📅 Weekday vs Weekend")
    
    # Filters (stacked on mobile)
    with st.expander("🔍 Filters", expanded=False):
        st.markdown("**Category Filter**")
        selected_categories = [
            cat for cat in sorted(month_df["Category"].unique())
            if st.checkbox(cat, value=True, key=f"cat_{cat}")
        ]
        
        filtered = month_df[month_df["Category"].isin(selected_categories)]
        
        st.markdown("**Sub Category Filter**")
        selected_subcategories = [
            sub for sub in sorted(filtered["Sub Category"].unique())
            if st.checkbox(sub, value=True, key=f"sub_{sub}")
        ]
        
        filtered = filtered[filtered["Sub Category"].isin(selected_subcategories)]
    
    metric = st.selectbox("Metric", ["Total Spend","Average Spend (per calendar day)"])
    
    if metric == "Total Spend":
        day_metric = filtered.groupby("Weekday")[amt_col].sum()
    else:
        day_metric = (
            filtered.groupby([date_col,"Weekday"])[amt_col].sum()
            .reset_index().groupby("Weekday")[amt_col].mean()
        )
    day_metric = day_metric.reindex(WEEK_ORDER).reset_index()
    
    fig_weekday = px.bar(day_metric, x="Weekday", y=amt_col, template="plotly_dark",
                         title=f"{metric} by Day")
    fig_weekday.update_layout(height=350, dragmode=False)
    st.plotly_chart(
        fig_weekday,
        use_container_width=True,
        config={'displayModeBar': False, 'scrollZoom': False, 'doubleClick': False}
    )
    
    fig_weektype = px.bar(filtered.groupby("WeekType")[amt_col].mean().reset_index(),
                          x="WeekType", y=amt_col, template="plotly_dark",
                          title="Weekday vs Weekend")
    fig_weektype.update_layout(height=350, dragmode=False)
    st.plotly_chart(
        fig_weektype,
        use_container_width=True,
        config={'displayModeBar': False, 'scrollZoom': False, 'doubleClick': False}
    )

# =========================================================
# TAB 3 — INTELLIGENCE
# =========================================================
with tab3:
    st.markdown("### 🧠 Signals & Risks")
    
    st.markdown("#### 🔁 Recurring (Uncategorized)")
    recurring = (
        df[df["Category"]=="Uncategorized"]
        .groupby("Description")[amt_col]
        .agg(["count","mean","std"])
        .reset_index()
    )
    recurring = recurring[(recurring["count"]>=3)&((recurring["std"]/recurring["mean"])<0.1)]
    st.dataframe(recurring, use_container_width=True, height=300)
    
    st.markdown("#### 🚨 Large Expenses (> ₹3000)")
    alerts = df[(df["Category"]!="Bill Payment")&(df[amt_col]>3000)]
    st.dataframe(alerts[[date_col,"Description",amt_col]], use_container_width=True, height=300)

# =========================================================
# TAB 4 — EXPORT
# =========================================================
with tab4:
    st.markdown("### 📤 Export Data")
    buf = BytesIO()
    df.sort_values(date_col).to_excel(buf, index=False)
    buf.seek(0)
    st.download_button(
        "⬇️ Download Clean Excel",
        data=buf,
        file_name="expense_intelligence_clean.xlsx",
        use_container_width=True
    )

st.markdown("---")
st.markdown("<div class='subtle'>Built for thinking, not panic.</div>", unsafe_allow_html=True)
