import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from io import BytesIO
import calendar
import gdown
from pathlib import Path
import shutil
import re

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
        margin: 50px auto;
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
        
        with st.form(key="login_form"):
            username = st.text_input("Username", placeholder="Enter your username", key="login_user")
            password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_pass")
            
            st.markdown('<div class="login-button">', unsafe_allow_html=True)
            login_btn = st.form_submit_button("🔐 Login", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        if login_btn:
            if username and password:
                credentials = load_credentials()
                
                if credentials is not None:
                    user_match = credentials[
                        (credentials['User Name'].str.strip() == username.strip()) & 
                        (credentials['Password'].astype(str).str.strip() == password.strip())
                    ]
                    
                    if not user_match.empty:
                        drive_link = user_match.iloc[0].get('Google Drive Data Link', '')
                        
                        st.session_state['authenticated'] = True
                        st.session_state['username'] = username
                        st.session_state['user_drive_link'] = str(drive_link).strip() if pd.notna(drive_link) else ''
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
.section-box { background:#0f172a; border:1px solid #1e293b; border-radius:18px; padding:22px; margin-bottom:24px; }
.card { background:#111827; border:1px solid #1f2937; border-radius:16px; padding:18px; transition:0.25s; }
.card:hover { transform:translateY(-4px); box-shadow:0 10px 24px rgba(0,0,0,0.35); }
.kpi-title { font-size:0.7rem; letter-spacing:0.08em; color:#9ca3af; text-transform:uppercase; }
.kpi-value { font-size:1.8rem; font-weight:700; }
.subtle { color:#9ca3af; font-size:0.85rem; }
.insight-box { background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); border-radius: 16px; padding: 20px; margin: 10px 0; color: white; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3); }
.insight-icon { font-size: 1.5rem; margin-right: 10px; }
.insight-text { font-size: 1rem; line-height: 1.6; }
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
    st.markdown(f"👤 {st.session_state['username']}")
    if st.button("🚪 Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

st.markdown("---")

# =========================================================
# HELPERS
# =========================================================
def detect(df, keys):
    """Detect column names based on keywords"""
    for c in df.columns:
        for k in keys:
            if k.lower() in c.lower():
                return c
    return None

def format_month(m):
    try:
        return pd.to_datetime(m + "-01").strftime("%B %y")
    except:
        return m

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
    """Downloads all data files from a public Google Drive folder"""
    temp_dir = Path("temp_data")
    
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    
    temp_dir.mkdir(exist_ok=True)
    folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
    
    try:
        gdown.download_folder(folder_url, output=str(temp_dir), quiet=False, use_cookies=False, remaining_ok=True)
        
        # Get all supported file types
        excel_files = list(temp_dir.glob("*.xlsx")) + list(temp_dir.glob("*.xls"))
        csv_files = list(temp_dir.glob("*.csv"))
        
        all_files = []
        
        for f in excel_files:
            if not f.name.startswith("~$"):
                all_files.append(("excel", str(f)))
        
        for f in csv_files:
            if not f.name.startswith("~$"):
                all_files.append(("csv", str(f)))
        
        return all_files
    except Exception as e:
        st.error(f"Download error: {e}")
        return None

def extract_folder_id_from_link(link):
    """Extract folder ID from various Google Drive link formats"""
    if not link or pd.isna(link):
        return None
    
    link = str(link).strip()
    
    if '/folders/' in link:
        try:
            folder_id = link.split('/folders/')[1].split('?')[0].split('/')[0].strip()
            return folder_id
        except:
            return None
    
    if len(link) > 20 and '/' not in link:
        return link
    
    return None

def parse_time_to_hour(time_val):
    """Parse various time formats and return hour (0-23)"""
    if pd.isna(time_val):
        return 12  # Default to noon
    
    time_str = str(time_val).strip().upper()
    
    # Check for AM/PM format (e.g., "8:51 PM", "12:30 PM")
    am_pm_match = re.match(r'(\d{1,2}):(\d{2})(?::\d{2})?\s*(AM|PM)', time_str)
    if am_pm_match:
        hour = int(am_pm_match.group(1))
        am_pm = am_pm_match.group(3)
        
        if am_pm == 'PM' and hour != 12:
            hour += 12
        elif am_pm == 'AM' and hour == 12:
            hour = 0
        
        return hour
    
    # Check for 24-hour format (e.g., "20:51", "20:51:30")
    time_24_match = re.match(r'(\d{1,2}):(\d{2})(?::\d{2})?', time_str)
    if time_24_match:
        hour = int(time_24_match.group(1))
        if 0 <= hour <= 23:
            return hour
    
    return 12  # Default to noon if parsing fails

def determine_weekend(row, date_col):
    """
    Determine if a transaction is during weekend.
    Weekend = Friday after 7:00 PM + Saturday + Sunday
    """
    try:
        day_of_week = row[date_col].weekday()
        
        if day_of_week >= 5:  # Saturday or Sunday
            return "Weekend"
        
        if day_of_week == 4:  # Friday
            hour = row.get("Hour", 12)
            if pd.notna(hour) and hour >= 19:
                return "Weekend"
        
        return "Weekday"
    except:
        return "Weekday"

def get_time_period(hour):
    """Categorize hour into time periods"""
    try:
        hour = int(hour)
        if 5 <= hour < 12:
            return "Morning (5AM-12PM)"
        elif 12 <= hour < 17:
            return "Afternoon (12PM-5PM)"
        elif 17 <= hour < 21:
            return "Evening (5PM-9PM)"
        else:
            return "Night (9PM-5AM)"
    except:
        return "Afternoon (12PM-5PM)"

def generate_insights(current_month_df, previous_month_df, amt_col, date_col):
    """Generate intelligent insights comparing current and previous month"""
    insights = []
    
    try:
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
        if "Category" in current_month_df.columns:
            current_cat = current_month_df.groupby("Category")[amt_col].sum()
            prev_cat = previous_month_df.groupby("Category")[amt_col].sum() if not previous_month_df.empty else pd.Series()
            
            for cat in current_cat.index:
                if cat in prev_cat.index and prev_cat[cat] > 0:
                    cat_change = ((current_cat[cat] - prev_cat[cat]) / prev_cat[cat]) * 100
                    if cat_change > 25:
                        insights.append(f"⚠️ {cat} spending jumped by {cat_change:.1f}% (₹{current_cat[cat]:,.0f} vs ₹{prev_cat[cat]:,.0f})")
        
        # Weekend vs Weekday
        if "WeekType" in current_month_df.columns:
            weekend_data = current_month_df[current_month_df["WeekType"] == "Weekend"]
            weekday_data = current_month_df[current_month_df["WeekType"] == "Weekday"]
            
            if not weekend_data.empty and not weekday_data.empty:
                weekend_avg = weekend_data.groupby(date_col)[amt_col].sum().mean()
                weekday_avg = weekday_data.groupby(date_col)[amt_col].sum().mean()
                
                if pd.notna(weekend_avg) and pd.notna(weekday_avg) and weekday_avg > 0:
                    if weekend_avg > weekday_avg * 1.3:
                        insights.append(f"🎉 You spend {((weekend_avg/weekday_avg - 1) * 100):.0f}% more on weekends (₹{weekend_avg:,.0f} vs ₹{weekday_avg:,.0f} per day)")
        
        # Top expense
        if not current_month_df.empty and "Description" in current_month_df.columns:
            top_expense = current_month_df.nlargest(1, amt_col).iloc[0]
            insights.append(f"🔝 Your largest expense was ₹{top_expense[amt_col]:,.0f} on {top_expense['Description']}")
        
        # Peak spending hour
        if "Hour" in current_month_df.columns:
            hour_spend = current_month_df.groupby("Hour")[amt_col].sum()
            if not hour_spend.empty:
                peak_hour = hour_spend.idxmax()
                insights.append(f"⏰ Your peak spending hour is {int(peak_hour)}:00 - {int(peak_hour)+1}:00")
    
    except Exception as e:
        insights.append(f"📊 Analysis in progress...")
    
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
        "Upload Excel/CSV files",
        type=["xlsx", "xls", "csv"],
        accept_multiple_files=True
    )
    if uploads:
        for f in uploads:
            try:
                if f.name.endswith('.csv'):
                    dfs.append(pd.read_csv(f))
                else:
                    dfs.append(pd.read_excel(f))
            except Exception as e:
                st.warning(f"Could not read {f.name}: {e}")

else:  # Google Drive Auto-sync
    user_drive_link = st.session_state.get('user_drive_link', '')
    
    if not user_drive_link:
        st.sidebar.error("📁 Drive link is missing.")
        st.info("📁 Drive link is missing. Please switch to Manual Upload mode.")
        st.stop()
    
    folder_id = extract_folder_id_from_link(user_drive_link)
    
    if not folder_id:
        st.sidebar.error("⚠️ Invalid Google Drive link format")
        st.error("⚠️ Kindly check the Google Drive link\n\n📞 Contact Mahendra: 7627068716 for help")
        st.stop()
    
    st.sidebar.info(f"📁 Syncing from your Google Drive folder")
    
    if st.sidebar.button("🔄 Sync Now") or 'gdrive_loaded' not in st.session_state:
        with st.spinner("Downloading files from Google Drive..."):
            files = download_from_gdrive_folder(folder_id)
            
            if files is None:
                st.sidebar.error("❌ Could not access Google Drive folder")
                st.error("⚠️ Kindly make link visible for all (Anyone with the link can view)\n\n📞 Contact Mahendra: 7627068716 for help")
                st.stop()
            
            if not files:
                st.sidebar.warning("📂 No data files found in folder")
                st.warning("📂 No Excel/CSV files found. Please upload data to your Google Drive folder.")
                st.stop()
            
            for file_type, f in files:
                try:
                    if file_type == "csv":
                        dfs.append(pd.read_csv(f))
                    else:
                        dfs.append(pd.read_excel(f))
                except Exception as e:
                    st.warning(f"Skipped file: {Path(f).name} - {e}")
            
            if dfs:
                st.session_state['gdrive_loaded'] = True
                st.session_state['gdrive_dfs'] = dfs
                st.sidebar.success(f"✅ Loaded {len(dfs)} files")
            else:
                st.sidebar.error("❌ Could not load any files")
                st.error("❌ Could not load data files. Please check file format.")
                st.stop()
    
    if 'gdrive_dfs' in st.session_state:
        dfs = st.session_state['gdrive_dfs']

if not dfs:
    st.info("📁 Click 'Sync Now' to load data, or switch to Manual Upload")
    st.stop()

df = pd.concat(dfs, ignore_index=True)

# =========================================================
# DATA PREP
# =========================================================
# Detect columns
date_col = detect(df, ["date"])
time_col = detect(df, ["time"])
amt_col = detect(df, ["amount"])
cat_col = detect(df, ["category"])
sub_col = detect(df, ["sub-category", "sub category", "subcategory", "sub_category"])
desc_col = detect(df, ["merchant", "person", "description", "name"])
type_col = detect(df, ["paid", "received", "type"])

# Debug: Show detected columns
with st.expander("🔍 Debug: Detected Columns"):
    st.write(f"All columns: {list(df.columns)}")
    st.write(f"Date: {date_col}")
    st.write(f"Time: {time_col}")
    st.write(f"Amount: {amt_col}")
    st.write(f"Category: {cat_col}")
    st.write(f"Sub-category: {sub_col}")
    st.write(f"Description: {desc_col}")

# Validate required columns
if not date_col:
    st.error("❌ Could not find a Date column. Please ensure your data has a column with 'date' in the name.")
    st.stop()

if not amt_col:
    st.error("❌ Could not find an Amount column. Please ensure your data has a column with 'amount' in the name.")
    st.stop()

# Parse Date
try:
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
except Exception as e:
    st.error(f"Error parsing dates: {e}")
    st.stop()

# Parse Amount
df[amt_col] = pd.to_numeric(df[amt_col], errors="coerce").fillna(0)

# Parse Time and extract Hour
if time_col:
    df["Hour"] = df[time_col].apply(parse_time_to_hour)
else:
    df["Hour"] = 12

# Create standardized columns
df["Category"] = df[cat_col].fillna("Uncategorized") if cat_col else "Uncategorized"
df["Sub Category"] = df[sub_col].fillna("Uncategorized") if sub_col else "Uncategorized"
df["Description"] = df[desc_col].fillna("Unknown") if desc_col else "Unknown"
df["Transaction Type"] = df[type_col].fillna("Paid") if type_col else "Paid"

# Create derived columns
df["Month"] = df[date_col].dt.to_period("M").astype(str)
df["Weekday"] = df[date_col].dt.day_name()
df["WeekType"] = df.apply(lambda row: determine_weekend(row, date_col), axis=1)
df["TimePeriod"] = df["Hour"].apply(get_time_period)

# Remove rows with invalid dates
df = df.dropna(subset=[date_col])

if df.empty:
    st.error("❌ No valid data found after processing. Please check your data format.")
    st.stop()

# =========================================================
# FILTERS
# =========================================================
months = sorted(df["Month"].unique())

if not months:
    st.error("❌ No valid months found in data.")
    st.stop()

selected_month = st.sidebar.selectbox(
    "Month",
    months,
    index=len(months)-1,
    format_func=format_month
)

month_df = df[df["Month"] == selected_month]
non_bill_df = month_df[month_df["Category"] != "Bill Payment"]

# Get previous month data
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
    
    total_spend = month_df[amt_col].sum()
    excl_bills = non_bill_df[amt_col].sum()
    daily_avg = non_bill_df.groupby(date_col)[amt_col].sum().mean() if not non_bill_df.empty else 0
    
    if not non_bill_df.empty:
        top_cat = non_bill_df.groupby("Category")[amt_col].sum().idxmax()
    else:
        top_cat = "N/A"
    
    kpis = [
        (k1, "Total Spend", total_spend),
        (k2, "Excl. Bills", excl_bills),
        (k3, "Daily Avg", daily_avg if pd.notna(daily_avg) else 0),
        (k4, "Top Category", top_cat)
    ]
    
    for col, title, val in kpis:
        display = f"₹{val:,.0f}" if isinstance(val, (int, float, np.number)) else str(val)
        col.markdown(
            f"<div class='card'><div class='kpi-title'>{title}</div><div class='kpi-value'>{display}</div></div>",
            unsafe_allow_html=True
        )
    
    # Budget + Composition
    left, right = st.columns([1.4, 1])
    
    with left:
        st.markdown("#### 📉 Budget Burn-down")
        budget = st.number_input("Monthly Budget", value=30000, step=1000)
        
        try:
            year = int(selected_month.split("-")[0])
            month = int(selected_month.split("-")[1])
            days = calendar.monthrange(year, month)[1]
            
            if not non_bill_df.empty:
                daily = (
                    non_bill_df.groupby(date_col)[amt_col]
                    .sum()
                    .reindex(pd.date_range(month_df[date_col].min(),
                                            month_df[date_col].max()), fill_value=0)
                    .cumsum()
                    .reset_index()
                )
                daily.columns = ["Date", "Actual"]
                ideal = np.linspace(0, budget, days)
                
                fig = px.line(daily, x="Date", y="Actual", template="plotly_dark")
                fig.add_scatter(
                    x=pd.date_range(daily["Date"].min(), periods=days),
                    y=ideal, name="Ideal"
                )
                fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
                st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
            else:
                st.info("No data for burn-down chart")
        except Exception as e:
            st.warning(f"Could not create burn-down chart: {e}")
    
    with right:
        st.markdown("#### 🧩 Expense Composition")
        
        if not month_df.empty:
            chart_df = month_df.copy()
            total_monthly = chart_df[amt_col].sum()
            
            if total_monthly > 0:
                cat_sums = chart_df.groupby("Category")[amt_col].sum()
                chart_df["Category Label"] = chart_df["Category"].apply(
                    lambda x: f"{x} ({cat_sums.get(x, 0) / total_monthly:.1%})"
                )
                
                fig = px.treemap(
                    chart_df,
                    path=["Category Label", "Sub Category"],
                    values=amt_col,
                    template="plotly_dark"
                )
                
                fig.update_traces(
                    textinfo="label+value+percent root",
                    texttemplate="%{label}<br>₹%{value:,.0f}<br>%{percentRoot:.1%}"
                )
                
                fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
                st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
            else:
                st.info("No spending data for treemap")
        else:
            st.info("No data for composition chart")
    
    # Category vs Day
    st.markdown("#### 📆 Spending Pattern")
    c1, c2 = st.columns(2)
    
    with c1:
        cat_data = month_df.groupby("Category")[amt_col].sum().reset_index()
        fig = px.bar(
            cat_data,
            x="Category", y=amt_col,
            template="plotly_dark", title="Category vs Amount"
        )
        fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
        st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
    
    with c2:
        day_data = month_df.groupby(date_col)[amt_col].sum().reset_index()
        fig = px.bar(
            day_data,
            x=date_col, y=amt_col,
            template="plotly_dark", title="Amount vs Day"
        )
        fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
        st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
    
    # =========================================================
    # TIME-BASED ANALYSIS
    # =========================================================
    st.markdown("#### ⏰ Time-based Analysis")
    h1, h2 = st.columns(2)
    
    with h1:
        # Spending by Time of Day (Clubbed)
        period_order = ["Morning (5AM-12PM)", "Afternoon (12PM-5PM)", "Evening (5PM-9PM)", "Night (9PM-5AM)"]
        period_spend = month_df.groupby("TimePeriod")[amt_col].sum().reindex(period_order).fillna(0).reset_index()
        
        fig = px.bar(
            period_spend,
            x="TimePeriod", y=amt_col,
            template="plotly_dark",
            title="Spending by Time of Day (Grouped)",
            labels={"TimePeriod": "Time Period", amt_col: "Total Amount (₹)"},
            color="TimePeriod",
            color_discrete_sequence=["#FFD700", "#FF8C00", "#FF4500", "#4169E1"]
        )
        fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True, showlegend=False)
        st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
    
    with h2:
        # Spending by Hour (Individual hours)
        hourly_spend = month_df.groupby("Hour")[amt_col].sum().reset_index()
        all_hours = pd.DataFrame({"Hour": range(24)})
        hourly_spend = all_hours.merge(hourly_spend, on="Hour", how="left").fillna(0)
        hourly_spend["Hour_Label"] = hourly_spend["Hour"].apply(lambda x: f"{int(x):02d}:00")
        
        fig = px.bar(
            hourly_spend,
            x="Hour_Label", y=amt_col,
            template="plotly_dark",
            title="Spending by Hour",
            labels={"Hour_Label": "Hour", amt_col: "Total Amount (₹)"}
        )
        fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
        fig.update_xaxes(tickangle=45)
        st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
    
    # Weekday vs Weekend Behaviour 
    st.markdown("### 📅 Weekday vs Weekend Behaviour")
    st.caption("*Weekend includes Friday after 7:00 PM, Saturday, and Sunday")
    
    f1, f2, f3 = st.columns([1.2, 1.2, 1])
    
    with f1:
        with st.popover("Filter Category"):
            all_categories = sorted(month_df["Category"].unique())
            selected_categories = [
                cat for cat in all_categories
                if st.checkbox(cat, value=True, key=f"cat_{cat}")
            ]
    
    if not selected_categories:
        selected_categories = all_categories
    
    filtered = month_df[month_df["Category"].isin(selected_categories)]
    
    with f2:
        with st.popover("Filter Sub Category"):
            all_subcategories = sorted(filtered["Sub Category"].unique())
            selected_subcategories = [
                sub for sub in all_subcategories
                if st.checkbox(sub, value=True, key=f"sub_{sub}")
            ]
    
    if not selected_subcategories:
        selected_subcategories = all_subcategories
    
    filtered = filtered[filtered["Sub Category"].isin(selected_subcategories)]
    
    with f3:
        metric = st.selectbox("Metric", ["Total Spend", "Average Spend (per calendar day)"])
    
    if not filtered.empty:
        if metric == "Total Spend":
            day_metric = filtered.groupby("Weekday")[amt_col].sum()
        else:
            day_metric = (
                filtered.groupby([date_col, "Weekday"])[amt_col].sum()
                .reset_index().groupby("Weekday")[amt_col].mean()
            )
        
        day_metric = day_metric.reindex(WEEK_ORDER).fillna(0).reset_index()
        
        c1, c2 = st.columns([2.2, 1])
        
        with c1:
            fig = px.bar(day_metric, x="Weekday", y=amt_col, template="plotly_dark",
                   title=f"{metric} by Day")
            fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
            st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
        
        with c2:
            weektype_data = filtered.groupby("WeekType")[amt_col].mean().reset_index()
            fig = px.bar(weektype_data,
                   x="WeekType", y=amt_col, template="plotly_dark",
                   title="Weekday vs Weekend")
            fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
            st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
    else:
        st.info("No data available for the selected filters")

# =========================================================
# TAB 3 — INSIGHTS
# =========================================================
with tab3:
    st.markdown("### 💡 Smart Insights")
    
    insights = generate_insights(month_df, previous_month_df, amt_col, date_col)
    
    if insights:
        for insight in insights:
            st.markdown(f"""
            <div class="insight-box">
                <div class="insight-text">{insight}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Not enough data to generate insights yet.")

# =========================================================
# TAB 4 — INTELLIGENCE
# =========================================================
with tab4:
    st.markdown("### 🧠 Signals & Risks")
    
    st.markdown("#### 🔁 Recurring (Uncategorized)")
    uncategorized = df[df["Category"] == "Uncategorized"]
    
    if not uncategorized.empty:
        recurring = (
            uncategorized
            .groupby("Description")[amt_col]
            .agg(["count", "mean", "std"])
            .reset_index()
        )
        recurring["std"] = recurring["std"].fillna(0)
        recurring = recurring[(recurring["count"] >= 3) & ((recurring["std"] / recurring["mean"].replace(0, 1)) < 0.1)]
        
        if not recurring.empty:
            st.dataframe(recurring, use_container_width=True)
        else:
            st.info("No recurring uncategorized transactions found")
    else:
        st.info("No uncategorized transactions")
    
    st.markdown("#### 🚨 Large Expenses (> ₹3000)")
    alerts = df[(df["Category"] != "Bill Payment") & (df[amt_col] > 3000)]
    
    if not alerts.empty:
        st.dataframe(alerts[[date_col, "Description", amt_col]], use_container_width=True)
    else:
        st.info("No large expenses found")

# =========================================================
# TAB 5 — EXPORT
# =========================================================
with tab5:
    st.markdown("### 📤 Export Data")
    
    buf = BytesIO()
    df.sort_values(date_col).to_excel(buf, index=False)
    buf.seek(0)
    
    st.download_button(
        "📥 Download Clean Excel",
        data=buf,
        file_name="expense_intelligence_clean.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    # Show data preview
    st.markdown("#### 📋 Data Preview")
    st.dataframe(df.head(20), use_container_width=True)

st.markdown("---")
st.markdown("<div class='subtle'>Built for thinking, not panic.</div>", unsafe_allow_html=True)
