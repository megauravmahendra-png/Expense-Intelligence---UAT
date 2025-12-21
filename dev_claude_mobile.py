import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from io import BytesIO
import calendar
import gdown
from pathlib import Path
import shutil
import requests

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="Expense Intelligence - UAT",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =========================================================
# AUTHENTICATION
# =========================================================
def load_credentials():
    """Load credentials from Google Sheets"""
    sheet_id = "1Im3g5NNm5962SUA-rd4WBr09n0nX2pLH5yHWc5BlXVA"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    try:
        df = pd.read_csv(url)
        return df
    except Exception as e:
        st.error(f"Error loading credentials: {e}")
        return None

def login_page():
    """Beautiful login page"""
    
    # Custom CSS for login page
    st.markdown("""
    <style>
    .login-container {
        max-width: 450px;
        margin: 100px auto;
        padding: 50px 40px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 24px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    }
    .login-title {
        font-size: 2.5rem;
        font-weight: 800;
        text-align: center;
        color: white;
        margin-bottom: 10px;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    .login-subtitle {
        text-align: center;
        color: rgba(255,255,255,0.9);
        margin-bottom: 40px;
        font-size: 1rem;
    }
    .stTextInput > div > div > input {
        background: rgba(255,255,255,0.2);
        border: 2px solid rgba(255,255,255,0.3);
        border-radius: 12px;
        color: white;
        font-size: 1rem;
        padding: 12px 16px;
    }
    .stTextInput > div > div > input:focus {
        border-color: rgba(255,255,255,0.8);
        box-shadow: 0 0 0 3px rgba(255,255,255,0.1);
    }
    .stTextInput > label {
        color: white !important;
        font-weight: 600;
        font-size: 0.9rem;
    }
    .login-button > button {
        width: 100%;
        background: white;
        color: #667eea;
        font-weight: 700;
        font-size: 1.1rem;
        padding: 14px;
        border-radius: 12px;
        border: none;
        margin-top: 20px;
        transition: all 0.3s;
    }
    .login-button > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 25px rgba(0,0,0,0.2);
    }
    .creator-text {
        text-align: center;
        color: rgba(255,255,255,0.8);
        margin-top: 30px;
        font-size: 0.9rem;
        font-style: italic;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Login container
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<div class="login-title">💳 Expense Intelligence</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-subtitle">Designed for awareness, not anxiety</div>', unsafe_allow_html=True)
        
        username = st.text_input("Username", placeholder="Enter your username", key="login_user")
        password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_pass")
        
        st.markdown('<div class="login-button">', unsafe_allow_html=True)
        login_btn = st.button("🔐 Login", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        if login_btn:
            if username and password:
                credentials = load_credentials()
                
                if credentials is not None:
                    # Check credentials
                    user_match = credentials[
                        (credentials['User Name'].str.strip() == username.strip()) & 
                        (credentials['Password'].astype(str).str.strip() == password.strip())
                    ]
                    
                    if not user_match.empty:
                        st.session_state['authenticated'] = True
                        st.session_state['username'] = username
                        st.rerun()
                    else:
                        st.error("❌ Incorrect username or password")
            else:
                st.warning("⚠️ Please enter both username and password")
        
        st.markdown('<div class="creator-text">Created by Gaurav Mahendra</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# Check authentication
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    login_page()
    st.stop()

# =========================================================
# UI THEME (AFTER LOGIN)
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
.insight-box {
    background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
    border-radius: 16px;
    padding: 20px;
    margin: 10px 0;
    color: white;
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}
.insight-icon {
    font-size: 1.5rem;
    margin-right: 10px;
}
.insight-text {
    font-size: 1rem;
    line-height: 1.6;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# HEADER
# =========================================================
col1, col2 = st.columns([6, 1])
with col1:
    st.markdown("## 💳 Expense Intelligence - UAT")
    st.markdown("<div class='subtle'>Designed for awareness, not anxiety</div>", unsafe_allow_html=True)
with col2:
    st.markdown(f"**👤 {st.session_state['username']}**")
    if st.button("🚪 Logout"):
        st.session_state['authenticated'] = False
        st.rerun()

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
        'displayModeBar': False,
        'scrollZoom': False,
        'doubleClick': False,
        'dragMode': False,
        'staticPlot': False,
        'displaylogo': False,
        'modeBarButtonsToRemove': ['zoom', 'pan', 'select', 'lasso', 'zoomIn', 'zoomOut', 'autoScale', 'resetScale']
    }

def download_from_gdrive_folder(folder_id):
    """Downloads all Excel files from a public Google Drive folder"""
    temp_dir = Path("temp_data")
    
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    
    temp_dir.mkdir(exist_ok=True)
    folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
    
    try:
        gdown.download_folder(folder_url, output=str(temp_dir), quiet=False, use_cookies=False, remaining_ok=True)
        excel_files = list(temp_dir.glob("*.xlsx"))
        return [str(f) for f in excel_files if not f.name.startswith("~$")]
    except Exception as e:
        st.error(f"Error downloading from Google Drive: {e}")
        return []

def generate_insights(current_month_df, previous_month_df, amt_col):
    """Generate intelligent insights comparing current and previous month"""
    insights = []
    
    # Total spend comparison
    current_total = current_month_df[amt_col].sum()
    prev_total = previous_month_df[amt_col].sum() if not previous_month_df.empty else 0
    
    if prev_total > 0:
        pct_change = ((current_total - prev_total) / prev_total) * 100
        if pct_change > 10:
            insights.append(f"💸 Your spending increased by {pct_change:.1f}% compared to last month (₹{current_total:,.0f} vs ₹{prev_total:,.0f})")
        elif pct_change < -10:
            insights.append(f"✅ Great job! You saved {abs(pct_change):.1f}% compared to last month (₹{current_total:,.0f} vs ₹{prev_total:,.0f})")
        else:
            insights.append(f"📊 Your spending is stable at ₹{current_total:,.0f}, similar to last month (₹{prev_total:,.0f})")
    
    # Category analysis
    current_cat = current_month_df.groupby("Category")[amt_col].sum()
    prev_cat = previous_month_df.groupby("Category")[amt_col].sum() if not previous_month_df.empty else pd.Series()
    
    for cat in current_cat.index:
        if cat in prev_cat.index and prev_cat[cat] > 0:
            cat_change = ((current_cat[cat] - prev_cat[cat]) / prev_cat[cat]) * 100
            if cat_change > 25:
                insights.append(f"⚠️ {cat} spending jumped by {cat_change:.1f}% (₹{current_cat[cat]:,.0f} vs ₹{prev_cat[cat]:,.0f})")
    
    # Weekend vs Weekday
    weekend_avg = current_month_df[current_month_df["WeekType"] == "Weekend"].groupby(current_month_df[detect(current_month_df, ["date"])])[amt_col].sum().mean()
    weekday_avg = current_month_df[current_month_df["WeekType"] == "Weekday"].groupby(current_month_df[detect(current_month_df, ["date"])])[amt_col].sum().mean()
    
    if weekend_avg > weekday_avg * 1.3:
        insights.append(f"🎉 You spend {((weekend_avg/weekday_avg - 1) * 100):.0f}% more on weekends (₹{weekend_avg:,.0f} vs ₹{weekday_avg:,.0f} per day)")
    
    # Top expense
    top_expense = current_month_df.nlargest(1, amt_col).iloc[0]
    insights.append(f"🔝 Your largest expense was ₹{top_expense[amt_col]:,.0f} on {top_expense['Description']}")
    
    return insights

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

else:
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

# Get previous month data for insights
current_month_idx = months.index(selected_month)
previous_month_df = df[df["Month"] == months[current_month_idx - 1]] if current_month_idx > 0 else pd.DataFrame()

# =========================================================
# TABS
# =========================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Trends",
    "📅 Monthly View",
    "💡 Insights",
    "🧠 Intelligence",
    "📤 Export"
])

# =========================================================
# TAB 1 — TRENDS
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
    
    with right:
        st.markdown("#### 🧩 Expense Composition")
        
        # Define fixed colors for each category
        category_colors = {
            'Food & Dining': '#ef4444',
            'Shopping': '#f59e0b',
            'Transportation': '#3b82f6',
            'Entertainment': '#8b5cf6',
            'Bills & Utilities': '#10b981',
            'Healthcare': '#ec4899',
            'Education': '#06b6d4',
            'Personal Care': '#f97316',
            'Travel': '#14b8a6',
            'Investments': '#6366f1',
            'Others': '#64748b',
            'Bill Payment': '#059669',
            'Uncategorized': '#6b7280'
        }
        
        # Prepare treemap data
        treemap_data = month_df.copy()
        total_amount = treemap_data[amt_col].sum()
        
        # Calculate category totals and percentages
        cat_totals = treemap_data.groupby('Category')[amt_col].sum()
        
        # Assign colors based on category
        treemap_data['Color'] = treemap_data['Category'].map(
            lambda x: category_colors.get(x, '#64748b')
        )
        
        # Create custom labels with amount and percentage
        def create_label(row):
            cat_total = cat_totals.get(row['Category'], 0)
            cat_pct = (cat_total / total_amount * 100) if total_amount > 0 else 0
            sub_pct = (row[amt_col] / cat_total * 100) if cat_total > 0 else 0
            
            # For category level
            if row['Sub Category'] == row['Category']:
                return f"{row['Category']}<br>₹{cat_total:,.0f}<br>{cat_pct:.1f}% of total"
            # For subcategory level
            else:
                return f"{row['Sub Category']}<br>₹{row[amt_col]:,.0f}<br>{sub_pct:.1f}% of {row['Category']}<br>{(row[amt_col]/total_amount*100):.1f}% of total"
        
        treemap_data['CustomLabel'] = treemap_data.apply(create_label, axis=1)
        
        fig = px.treemap(
            treemap_data,
            path=["Category", "Sub Category"],
            values=amt_col,
            color='Category',
            color_discrete_map=category_colors,
            template="plotly_dark"
        )
        
        fig.update_traces(
            textposition="middle center",
            textfont=dict(size=11, color='white', family='Arial'),
            marker=dict(
                line=dict(width=2.5, color='#0f172a'),
                cornerradius=5
            ),
            hovertemplate='<b>%{label}</b><br>Amount: ₹%{value:,.0f}<br>%{percentParent}<extra></extra>'
        )
        
        fig.update_layout(
            xaxis_fixedrange=True, 
            yaxis_fixedrange=True,
            margin=dict(t=10, b=10, l=10, r=10),
            uniformtext=dict(minsize=8, mode='hide')
        )
        
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
    
    # Weekday vs Weekend Behaviour 
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
# TAB 3 — INSIGHTS
# =========================================================
with tab3:
    st.markdown("### 💡 Smart Insights")
    
    insights = generate_insights(month_df, previous_month_df, amt_col)
    
    for insight in insights:
        st.markdown(f"""
        <div class="insight-box">
            <div class="insight-text">{insight}</div>
        </div>
        """, unsafe_allow_html=True)

# =========================================================
# TAB 4 — INTELLIGENCE
# =========================================================
with tab4:
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
# TAB 5 — EXPORT
# =========================================================
with tab5:
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
