import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from io import BytesIO
import calendar
import gdown
from pathlib import Path
import shutil

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="Expense Intelligence - UAT",
    page_icon="💳",
    layout="wide"
)

# =========================================================
# UI THEME
# =========================================================
st.markdown("""
<style>
body { background:#0b1220; color:#e5e7eb; }
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
}
.card:hover {
    transform:translateY(-4px);
    box-shadow:0 10px 24px rgba(0,0,0,0.35);
}
.kpi-title {
    font-size:0.7rem;
    letter-spacing:0.08em;
    color:#9ca3af;
    text-transform:uppercase;
}
.kpi-value {
    font-size:1.8rem;
    font-weight:700;
}
.subtle {
    color:#9ca3af;
    font-size:0.85rem;
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

def get_chart_config():
    """Returns Plotly config optimized for mobile touch screens"""
    return {
        'displayModeBar': False,     # Hide the toolbar
        'scrollZoom': False,         # Disable zoom on scroll/pinch
        'doubleClick': False,        # Disable double-click zoom
        'dragMode': False,           # Disable pan/drag
        'staticPlot': False,         # Keep interactivity for tooltips
        'displaylogo': False,        # Remove Plotly logo
        'modeBarButtonsToRemove': ['zoom', 'pan', 'select', 'lasso', 'zoomIn', 'zoomOut', 'autoScale', 'resetScale']
    }

def download_from_gdrive_folder(folder_id):
    """Downloads all Excel files from a public Google Drive folder"""
    
    # Create temp directory
    temp_dir = Path("temp_data")
    
    # Clean up old temp directory if exists
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    
    temp_dir.mkdir(exist_ok=True)
    
    # Google Drive folder URL
    folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
    
    try:
        # Download all files from folder
        gdown.download_folder(folder_url, output=str(temp_dir), quiet=False, use_cookies=False, remaining_ok=True)
        
        # Get all Excel files
        excel_files = list(temp_dir.glob("*.xlsx"))
        
        return [str(f) for f in excel_files if not f.name.startswith("~$")]
    
    except Exception as e:
        st.error(f"Error downloading from Google Drive: {e}")
        return []

WEEK_ORDER = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

# =========================================================
# DATA SOURCE
# =========================================================
with st.sidebar:
    st.markdown("### 📂 Data Source")
    mode = st.radio("", ["Google Drive (Auto-sync)", "Manual Upload"])

dfs = []

if mode == "Manual Upload":
    uploads = st.sidebar.file_uploader(
        "Upload Excel files",
        type=["xlsx"],
        accept_multiple_files=True
    )
    if uploads:
        dfs = [pd.read_excel(f) for f in uploads]

else:  # Google Drive mode
    # Your Google Drive folder ID (extracted from the link)
    folder_id = "10PQWwwCbKU5Y9EsZ12HYXGe67Y0CaEIY"
    
    st.sidebar.info("📁 Syncing from your Google Drive folder")
    
    if st.sidebar.button("🔄 Sync Now") or 'gdrive_loaded' not in st.session_state:
        with st.spinner("Downloading files from Google Drive..."):
            files = download_from_gdrive_folder(folder_id)
            
            if files:
                for f in files:
                    try:
                        dfs.append(pd.read_excel(f))
                    except Exception as e:
                        st.warning(f"Skipped file: {Path(f).name}")
                
                st.session_state['gdrive_loaded'] = True
                st.session_state['gdrive_dfs'] = dfs
                st.sidebar.success(f"✅ Loaded {len(dfs)} files")
            else:
                st.sidebar.error("No files found or error occurred")
    
    # Use cached data if available
    if 'gdrive_dfs' in st.session_state:
        dfs = st.session_state['gdrive_dfs']

if not dfs:
    st.info("📁 Click 'Sync Now' to load data from Google Drive, or switch to Manual Upload")
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
    "📅 Monthly View",
    "🧠 Intelligence",
    "📤 Export"
])

# =========================================================
# TAB 1 — TRENDS (SIDE-BY-SIDE)
# =========================================================
with tab1:
    st.markdown("### 📈 Long-term Trends")
    c1, c2 = st.columns(2)
    
    with c2:
        monthly = df.groupby("Month")[amt_col].sum().reset_index()
        fig = px.line(monthly, x="Month", y=amt_col, markers=True,
                template="plotly_dark", title="Total Monthly Spend")
        fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
        st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
    
    with c1:
        cat_trend = df.groupby(["Month","Category"])[amt_col].sum().reset_index()
        fig = px.line(cat_trend, x="Month", y=amt_col, color="Category",
                template="plotly_dark", title="Category-wise Trend")
        fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
        st.plotly_chart(fig, use_container_width=True, config=get_chart_config())

# =========================================================
# TAB 2 — MONTHLY VIEW
# =========================================================
with tab2:
    st.markdown(f"### 📅 {format_month(selected_month)} Overview")
    
    # KPIs
    k1,k2,k3,k4 = st.columns(4)
    kpis = [
        (k1,"Total Spend",month_df[amt_col].sum()),
        (k2,"Excl. Bills",non_bill_df[amt_col].sum()),
        (k3,"Daily Avg",non_bill_df.groupby(date_col)[amt_col].sum().mean()),
        (k4,"Top Category",non_bill_df.groupby("Category")[amt_col].sum().idxmax())
    ]
    for col,title,val in kpis:
        display = f"₹{val:,.0f}" if isinstance(val,(int,float,np.number)) else str(val)
        col.markdown(
            f"<div class='card'><div class='kpi-title'>{title}</div><div class='kpi-value'>{display}</div></div>",
            unsafe_allow_html=True
        )
    
    # Budget + Composition
    left,right = st.columns([1.4,1])
    
    with left:
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
        fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
        st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
    
    # with right:
    #     st.markdown("#### 🧩 Expense Composition")
    #     fig = px.treemap(
    #         month_df,
    #         path=["Category","Sub Category"],
    #         values=amt_col,
    #         template="plotly_dark"
    #     )

    #   # # NEW: Update traces to show Label, Formatted Amount, and Percentage
    #   #   fig.update_traces(
    #   #       textinfo="label+value+percent parent",
    #   #       texttemplate="%{label}<br>₹%{value:,.0f}<br>%{percentParent:.1%}"
    #   #   )
    #     # CHANGED: Used percentRoot instead of percentParent
    #     fig.update_traces(
    #         textinfo="label+value+percent root",
    #         texttemplate="%{label}<br>₹%{value:,.0f}<br>%{percentRoot:.1%}"
    #     )
      
    #     fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
    #     st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
    with right:
        st.markdown("#### 🧩 Expense Composition")
        
        # 1. Prepare data: Create specific labels for Parent Categories
        chart_df = month_df.copy() # Work on a copy to avoid warnings
        total_monthly = chart_df[amt_col].sum()
        
        # Calculate spend per category to derive the % for the parent label
        cat_sums = chart_df.groupby("Category")[amt_col].sum()
        
        # Create a new column "Category Label" that looks like: "Bill Payment (40.8%)"
        chart_df["Category Label"] = chart_df["Category"].apply(
            lambda x: f"{x} ({cat_sums.get(x, 0) / total_monthly:.1%})" if total_monthly > 0 else x
        )

        # 2. Build the Treemap using the NEW "Category Label" as the parent
        fig = px.treemap(
            chart_df,
            path=["Category Label", "Sub Category"], # Use the custom label here
            values=amt_col,
            template="plotly_dark"
        )
        
        # 3. Formatting: This applies to the boxes (Sub Categories)
        # Shows: Name, Amount (₹), and Percentage of Total
        fig.update_traces(
            textinfo="label+value+percent root",
            texttemplate="%{label}<br>₹%{value:,.0f}<br>%{percentRoot:.1%}"
        )
        
        fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
        st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
    
    # Category vs Day
    st.markdown("#### 📆 Spending Pattern")
    c1,c2 = st.columns(2)
    
    with c1:
        fig = px.bar(
            month_df.groupby("Category")[amt_col].sum().reset_index(),
            x="Category", y=amt_col,
            template="plotly_dark", title="Category vs Amount"
        )
        fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
        st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
    
    with c2:
        fig = px.bar(
            month_df.groupby(date_col)[amt_col].sum().reset_index(),
            x=date_col, y=amt_col,
            template="plotly_dark", title="Amount vs Day"
        )
        fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
        st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
    
    # =====================================================
    # Weekday vs Weekend Behaviour 
    # =====================================================
    
    st.markdown("### 📅 Weekday vs Weekend Behaviour")
    f1,f2,f3 = st.columns([1.2,1.2,1])
    
    with f1:
        with st.popover("Filter Category"):
            selected_categories = [
                cat for cat in sorted(month_df["Category"].unique())
                if st.checkbox(cat, value=True, key=f"cat_{cat}")
            ]
    
    filtered = month_df[month_df["Category"].isin(selected_categories)]
    
    with f2:
        with st.popover("Filter Sub Category"):
            selected_subcategories = [
                sub for sub in sorted(filtered["Sub Category"].unique())
                if st.checkbox(sub, value=True, key=f"sub_{sub}")
            ]
    
    filtered = filtered[filtered["Sub Category"].isin(selected_subcategories)]
    
    with f3:
        metric = st.selectbox("Metric", ["Total Spend","Average Spend (per calendar day)"])
    
    if metric == "Total Spend":
        day_metric = filtered.groupby("Weekday")[amt_col].sum()
    else:
        day_metric = (
            filtered.groupby([date_col,"Weekday"])[amt_col].sum()
            .reset_index().groupby("Weekday")[amt_col].mean()
        )
    
    day_metric = day_metric.reindex(WEEK_ORDER).reset_index()
    
    c1,c2 = st.columns([2.2,1])
    
    with c1:
        fig = px.bar(day_metric, x="Weekday", y=amt_col, template="plotly_dark",
               title=f"{metric} by Day")
        fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
        st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
    
    with c2:
        fig = px.bar(filtered.groupby("WeekType")[amt_col].mean().reset_index(),
               x="WeekType", y=amt_col, template="plotly_dark",
               title="Weekday vs Weekend")
        fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
        st.plotly_chart(fig, use_container_width=True, config=get_chart_config())

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
    st.dataframe(recurring, use_container_width=True)
    
    st.markdown("#### 🚨 Large Expenses (> ₹3000)")
    alerts = df[(df["Category"]!="Bill Payment")&(df[amt_col]>3000)]
    st.dataframe(alerts[[date_col,"Description",amt_col]], use_container_width=True)

# =========================================================
# TAB 4 — EXPORT
# =========================================================
with tab4:
    buf = BytesIO()
    df.sort_values(date_col).to_excel(buf, index=False)
    buf.seek(0)
    st.download_button(
        "Download Clean Excel",
        data=buf,
        file_name="expense_intelligence_clean.xlsx"
    )

st.markdown("---")
st.markdown("<div class='subtle'>Built for thinking, not panic.</div>", unsafe_allow_html=True)
