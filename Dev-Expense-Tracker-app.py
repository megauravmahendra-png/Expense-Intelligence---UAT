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
import requests

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Expense Intelligence - UAT",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =========================================================
# INITIALIZE ALL SESSION STATES UPFRONT
# =========================================================
def initialize_all_session_states():
    """Initialize all session states at app start to prevent first-run refresh"""
    
    defaults = {
        'authenticated': False,
        'username': '',
        'user_drive_link': '',
        'gdrive_loaded': False,
        'gdrive_dfs': [],
        'file_info': [],
        'debug_log': [],
        'cat_filter': {},
        'sub_filter': {},
        'metric_choice': "Total Spend",
        'filters_initialized': False,
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

initialize_all_session_states()

# =========================================================
# CSS STYLES + JAVASCRIPT
# =========================================================
st.markdown("""
<style>
html { scroll-behavior: smooth; }
.stSelectbox > div > div { min-height: 38px; }

@media (max-width: 768px) {
    .stSelectbox, .stCheckbox, .stButton > button {
        touch-action: manipulation;
        -webkit-tap-highlight-color: transparent;
    }
    .stCheckbox > label { padding: 8px 0; }
}

body { background: #0b1220; color: #e5e7eb; }

.card { 
    background: #111827; 
    border: 1px solid #1f2937; 
    border-radius: 16px; 
    padding: 18px; 
    transition: 0.25s; 
}
.card:hover { 
    transform: translateY(-4px); 
    box-shadow: 0 10px 24px rgba(0,0,0,0.35); 
}

.kpi-title { font-size: 0.7rem; letter-spacing: 0.08em; color: #9ca3af; text-transform: uppercase; }
.kpi-value { font-size: 1.8rem; font-weight: 700; }
.subtle { color: #9ca3af; font-size: 0.85rem; }

.insight-box { 
    background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); 
    border-radius: 16px; 
    padding: 20px; 
    margin: 10px 0; 
    color: white; 
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3); 
}
.insight-text { font-size: 1rem; line-height: 1.6; }

.debug-card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 16px; margin: 8px 0; }
.debug-title { color: #60a5fa; font-weight: 600; font-size: 0.9rem; margin-bottom: 8px; }
.debug-value { color: #e2e8f0; font-family: monospace; font-size: 0.85rem; word-wrap: break-word; }

.stat-card { background: linear-gradient(135deg, #065f46 0%, #059669 100%); border-radius: 12px; padding: 16px; margin: 8px 0; color: white; }
.warning-card { background: linear-gradient(135deg, #92400e 0%, #d97706 100%); border-radius: 12px; padding: 16px; margin: 8px 0; color: white; }

.log-info { background: #1e3a5f; border-left: 4px solid #3b82f6; padding: 8px 12px; margin: 4px 0; font-family: monospace; font-size: 0.8rem; }
.log-success { background: #1e3f2e; border-left: 4px solid #10b981; padding: 8px 12px; margin: 4px 0; font-family: monospace; font-size: 0.8rem; }
.log-warning { background: #3f2e1e; border-left: 4px solid #f59e0b; padding: 8px 12px; margin: 4px 0; font-family: monospace; font-size: 0.8rem; }
.log-error { background: #3f1e1e; border-left: 4px solid #ef4444; padding: 8px 12px; margin: 4px 0; font-family: monospace; font-size: 0.8rem; }

.login-container {
    max-width: 450px;
    margin: 50px auto;
    padding: 50px 40px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 24px;
    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
}
.login-title { font-size: 2.5rem; font-weight: 800; text-align: center; color: white; margin-bottom: 10px; }
.login-subtitle { text-align: center; color: rgba(255,255,255,0.9); margin-bottom: 40px; }
.creator-text { text-align: center; color: rgba(255,255,255,0.8); margin-top: 30px; font-style: italic; }
</style>

<script>
const saveScroll = () => sessionStorage.setItem('scrollY', window.scrollY);
const loadScroll = () => {
    const y = sessionStorage.getItem('scrollY');
    if (y) setTimeout(() => window.scrollTo(0, parseInt(y)), 100);
};
window.addEventListener('beforeunload', saveScroll);
window.addEventListener('load', loadScroll);
document.addEventListener('click', saveScroll);
</script>
""", unsafe_allow_html=True)

# =========================================================
# DEBUG LOGGING
# =========================================================
def add_debug_log(message, level="info"):
    timestamp = pd.Timestamp.now().strftime("%H:%M:%S")
    st.session_state['debug_log'].append({"time": timestamp, "level": level, "message": str(message)})

def clear_debug_log():
    st.session_state['debug_log'] = []

# =========================================================
# AUTHENTICATION
# =========================================================
def load_credentials():
    sheet_id = "1Im3g5NNm5962SUA-rd4WBr09n0nX2pLH5yHWc5BlXVA"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    try:
        df = pd.read_csv(url)
        add_debug_log(f"Loaded {len(df)} user credentials", "success")
        return df
    except Exception as e:
        add_debug_log(f"Failed to load credentials: {e}", "error")
        return None

def login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<div class="login-title">💳 Expense Intelligence</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-subtitle">Designed for awareness, not anxiety</div>', unsafe_allow_html=True)
        
        with st.form(key="login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            login_btn = st.form_submit_button("🔐 Login", use_container_width=True)
        
        if login_btn:
            if username and password:
                credentials = load_credentials()
                if credentials is not None:
                    # ===== CASE-INSENSITIVE LOGIN =====
                    user_match = credentials[
                        (credentials['User Name'].str.strip().str.lower() == username.strip().lower()) & 
                        (credentials['Password'].astype(str).str.strip().str.lower() == password.strip().lower())
                    ]
                    if not user_match.empty:
                        drive_link = user_match.iloc[0].get('Google Drive Data Link', '')
                        st.session_state['authenticated'] = True
                        st.session_state['username'] = username
                        st.session_state['user_drive_link'] = str(drive_link).strip() if pd.notna(drive_link) else ''
                        add_debug_log(f"User '{username}' logged in", "success")
                        st.rerun()
                    else:
                        st.error("❌ Incorrect username or password")
            else:
                st.warning("⚠️ Please enter both username and password")
        
        st.markdown('<div class="creator-text">Created by Gaurav Mahendra</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

if not st.session_state['authenticated']:
    login_page()
    st.stop()

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
# HELPER FUNCTIONS
# =========================================================
def detect(df, keys):
    for col in df.columns:
        for key in keys:
            if key.lower() in col.lower():
                return col
    return None

def format_month(m):
    try:
        return pd.to_datetime(m + "-01").strftime("%B %y")
    except:
        return m

def get_chart_config():
    return {
        'displayModeBar': False,
        'scrollZoom': False,
        'doubleClick': False,
        'dragMode': False,
        'staticPlot': False,
        'displaylogo': False,
    }

def extract_folder_id_from_link(link):
    if not link or pd.isna(link):
        return None
    link = str(link).strip()
    if '/folders/' in link:
        try:
            folder_id = link.split('/folders/')[1].split('?')[0].split('/')[0].strip()
            add_debug_log(f"Extracted folder ID: {folder_id}", "success")
            return folder_id
        except:
            return None
    if len(link) > 20 and '/' not in link:
        return link
    return None

def extract_sheet_id_from_link(link):
    if not link:
        return None
    link = str(link).strip()
    if '/spreadsheets/d/' in link:
        try:
            return link.split('/spreadsheets/d/')[1].split('/')[0].split('?')[0]
        except:
            return None
    return None

def get_google_sheets_from_folder(folder_id):
    add_debug_log(f"Scanning folder: {folder_id}")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(f"https://drive.google.com/drive/folders/{folder_id}", headers=headers, timeout=15)
        if response.status_code != 200:
            return []
        matches = re.findall(r'/spreadsheets/d/([a-zA-Z0-9_-]+)', response.text)
        unique_ids = list(dict.fromkeys(matches))
        add_debug_log(f"Found {len(unique_ids)} sheet(s)", "success" if unique_ids else "warning")
        return unique_ids
    except Exception as e:
        add_debug_log(f"Error: {e}", "error")
        return []

def load_google_sheet_by_id(sheet_id):
    add_debug_log(f"Loading sheet: {sheet_id}")
    try:
        df = pd.read_csv(f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv")
        add_debug_log(f"Loaded: {len(df)} rows", "success")
        return df
    except Exception as e:
        add_debug_log(f"Error: {e}", "error")
        return None

def try_load_as_google_sheet(file_id):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=csv"
        response = requests.head(url, allow_redirects=True, timeout=10)
        if response.status_code == 200:
            df = pd.read_csv(url)
            if not df.empty:
                return df
        return None
    except:
        return None

def get_files_from_drive_folder(folder_id):
    add_debug_log(f"Downloading from folder: {folder_id}")
    try:
        temp_dir = Path("temp_data")
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir(exist_ok=True)
        gdown.download_folder(f"https://drive.google.com/drive/folders/{folder_id}", output=str(temp_dir), quiet=True, use_cookies=False, remaining_ok=True)
        files_info = []
        for f in list(temp_dir.glob("*.xlsx")) + list(temp_dir.glob("*.xls")):
            if not f.name.startswith("~$"):
                files_info.append({"type": "excel", "path": str(f), "name": f.name})
        for f in temp_dir.glob("*.csv"):
            if not f.name.startswith("~$"):
                files_info.append({"type": "csv", "path": str(f), "name": f.name})
        add_debug_log(f"Downloaded {len(files_info)} file(s)", "success" if files_info else "warning")
        return files_info
    except Exception as e:
        add_debug_log(f"Error: {e}", "error")
        return []

def load_data_from_drive(folder_id, manual_sheet_links=None):
    add_debug_log("=" * 50)
    add_debug_log("STARTING DATA LOAD")
    add_debug_log("=" * 50)
    
    dfs, file_info = [], []
    
    # Method 1: Download regular files
    for f in get_files_from_drive_folder(folder_id):
        try:
            temp_df = pd.read_csv(f["path"]) if f["type"] == "csv" else pd.read_excel(f["path"])
            if not temp_df.empty:
                dfs.append(temp_df)
                file_info.append({"name": f["name"], "rows": len(temp_df), "cols": len(temp_df.columns), "type": f["type"], "source": "download"})
        except:
            pass
    
    # Method 2: Scan for Google Sheets
    for sheet_id in get_google_sheets_from_folder(folder_id):
        if not any(sheet_id[:10] in str(f.get('sheet_id', '')) for f in file_info):
            temp_df = load_google_sheet_by_id(sheet_id)
            if temp_df is not None and not temp_df.empty:
                dfs.append(temp_df)
                file_info.append({"name": "Google Sheet (auto)", "rows": len(temp_df), "cols": len(temp_df.columns), "type": "gsheet", "source": "scan", "sheet_id": sheet_id[:15]})
    
    # Method 3: Embed view
    try:
        response = requests.get(f"https://drive.google.com/embeddedfolderview?id={folder_id}", headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if response.status_code == 200:
            for file_id in re.findall(r'\["([a-zA-Z0-9_-]{20,50})"', response.text)[:10]:
                if file_id != folder_id and not any(file_id[:10] in str(f.get('sheet_id', '')) for f in file_info):
                    temp_df = try_load_as_google_sheet(file_id)
                    if temp_df is not None:
                        dfs.append(temp_df)
                        file_info.append({"name": f"Sheet ({file_id[:8]}...)", "rows": len(temp_df), "cols": len(temp_df.columns), "type": "gsheet", "source": "embed", "sheet_id": file_id[:15]})
    except:
        pass
    
    # Method 4: Manual links
    if manual_sheet_links:
        for link in manual_sheet_links:
            sheet_id = extract_sheet_id_from_link(link)
            if sheet_id:
                temp_df = load_google_sheet_by_id(sheet_id)
                if temp_df is not None and not temp_df.empty:
                    dfs.append(temp_df)
                    file_info.append({"name": "Sheet (manual)", "rows": len(temp_df), "cols": len(temp_df.columns), "type": "gsheet", "source": "manual", "sheet_id": sheet_id[:15]})
    
    add_debug_log(f"COMPLETE: {len(dfs)} dataframe(s)", "success" if dfs else "error")
    return dfs, file_info

def parse_time_to_hour(time_val):
    if pd.isna(time_val):
        return 12
    time_str = str(time_val).strip().upper()
    match = re.match(r'(\d{1,2}):(\d{2})(?::\d{2})?\s*(AM|PM)?', time_str)
    if match:
        hour = int(match.group(1))
        am_pm = match.group(3)
        if am_pm == 'PM' and hour != 12:
            hour += 12
        elif am_pm == 'AM' and hour == 12:
            hour = 0
        return hour
    return 12

def determine_weekend(row, date_col):
    try:
        dow = row[date_col].weekday()
        if dow >= 5:
            return "Weekend"
        if dow == 4 and row.get("Hour", 12) >= 19:
            return "Weekend"
        return "Weekday"
    except:
        return "Weekday"

def get_time_period(hour):
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

def generate_insights(current_df, prev_df, amt_col, date_col):
    insights = []
    try:
        curr_total = current_df[amt_col].sum()
        prev_total = prev_df[amt_col].sum() if not prev_df.empty else 0
        
        if prev_total > 0:
            pct = ((curr_total - prev_total) / prev_total) * 100
            if pct > 10:
                insights.append(f"💸 Spending ↑ {pct:.1f}% vs last month (₹{curr_total:,.0f} vs ₹{prev_total:,.0f})")
            elif pct < -10:
                insights.append(f"✅ Saved {abs(pct):.1f}% vs last month (₹{curr_total:,.0f} vs ₹{prev_total:,.0f})")
            else:
                insights.append(f"📊 Stable spending at ₹{curr_total:,.0f}")
        
        if "Category" in current_df.columns:
            curr_cat = current_df.groupby("Category")[amt_col].sum()
            prev_cat = prev_df.groupby("Category")[amt_col].sum() if not prev_df.empty else pd.Series()
            for cat in curr_cat.index:
                if cat in prev_cat.index and prev_cat[cat] > 0:
                    change = ((curr_cat[cat] - prev_cat[cat]) / prev_cat[cat]) * 100
                    if change > 25:
                        insights.append(f"⚠️ {cat} ↑ {change:.1f}%")
        
        if "WeekType" in current_df.columns:
            we = current_df[current_df["WeekType"] == "Weekend"]
            wd = current_df[current_df["WeekType"] == "Weekday"]
            if not we.empty and not wd.empty:
                we_avg = we.groupby(date_col)[amt_col].sum().mean()
                wd_avg = wd.groupby(date_col)[amt_col].sum().mean()
                if pd.notna(we_avg) and pd.notna(wd_avg) and wd_avg > 0 and we_avg > wd_avg * 1.3:
                    insights.append(f"🎉 Weekend spending {((we_avg/wd_avg)-1)*100:.0f}% higher")
        
        if not current_df.empty and "Description" in current_df.columns:
            top = current_df.nlargest(1, amt_col).iloc[0]
            insights.append(f"🔝 Biggest: ₹{top[amt_col]:,.0f} on {top['Description']}")
        
        if "Hour" in current_df.columns and not current_df.empty:
            peak = int(current_df.groupby("Hour")[amt_col].sum().idxmax())
            insights.append(f"⏰ Peak hour: {peak}:00-{peak+1}:00")
    except:
        pass
    return insights

def get_data_quality_score(df, date_col, amt_col, cat_col, time_col):
    issues, score = [], 100
    missing_dates = df[date_col].isna().sum()
    if missing_dates > 0:
        issues.append(f"⚠️ {missing_dates} missing dates")
        score -= min(20, missing_dates * 2)
    zero_amounts = (df[amt_col] == 0).sum()
    if zero_amounts > 0:
        issues.append(f"⚠️ {zero_amounts} zero amounts")
        score -= min(15, zero_amounts)
    if "Category" in df.columns:
        uncat = (df["Category"] == "Uncategorized").sum()
        if uncat > 0:
            issues.append(f"📝 {uncat} uncategorized")
            score -= min(10, uncat)
    if not time_col:
        issues.append("ℹ️ No time column")
        score -= 5
    return max(0, score), issues

WEEK_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.markdown("### 📂 Data Source")
    mode = st.radio("", ["Google Drive (Auto-sync)", "Manual Upload"], key="data_mode", label_visibility="collapsed")

dfs, file_info, manual_sheet_links = [], [], []

if mode == "Manual Upload":
    with st.sidebar:
        uploads = st.file_uploader("Upload files", type=["xlsx", "xls", "csv"], accept_multiple_files=True)
        if uploads:
            for f in uploads:
                try:
                    temp_df = pd.read_csv(f) if f.name.endswith('.csv') else pd.read_excel(f)
                    dfs.append(temp_df)
                    file_info.append({"name": f.name, "rows": len(temp_df), "cols": len(temp_df.columns), "type": "upload"})
                except:
                    st.warning(f"Error: {f.name}")
else:
    user_drive_link = st.session_state.get('user_drive_link', '')
    folder_id = extract_folder_id_from_link(user_drive_link)
    sheet_id = extract_sheet_id_from_link(user_drive_link)
    
    with st.sidebar:
        if st.button("🔄 Sync Data", use_container_width=True):
            st.session_state['gdrive_loaded'] = False
        
        with st.expander("⚙️ Advanced", expanded=False):
            sheet_input = st.text_area("Manual Sheet URLs", height=60, placeholder="https://docs.google.com/spreadsheets/d/...")
            manual_sheet_links = [l.strip() for l in sheet_input.split('\n') if '/spreadsheets/' in l]
            st.caption(f"Folder: `{folder_id or 'None'}`")
    
    if not user_drive_link:
        st.info("📁 No Drive link. Use Manual Upload.")
        st.stop()
    
    if not st.session_state['gdrive_loaded']:
        clear_debug_log()
        with st.spinner("Loading data..."):
            if sheet_id:
                temp_df = load_google_sheet_by_id(sheet_id)
                if temp_df is not None:
                    dfs = [temp_df]
                    file_info = [{"name": "Google Sheet", "rows": len(temp_df), "cols": len(temp_df.columns), "type": "gsheet"}]
            elif folder_id:
                dfs, file_info = load_data_from_drive(folder_id, manual_sheet_links)
            
            if dfs:
                st.session_state['gdrive_loaded'] = True
                st.session_state['gdrive_dfs'] = dfs
                st.session_state['file_info'] = file_info
            else:
                st.error("❌ No data found. Make sheet public or add Manual Sheet URLs.")
                st.stop()
    
    if st.session_state['gdrive_loaded']:
        dfs = st.session_state['gdrive_dfs']
        file_info = st.session_state['file_info']

if not dfs:
    st.info("📁 Click 'Sync Data' or upload files")
    st.stop()

df = pd.concat(dfs, ignore_index=True)

# =========================================================
# DATA PREPARATION
# =========================================================
date_col = detect(df, ["date"])
time_col = detect(df, ["time"])
amt_col = detect(df, ["amount"])
cat_col = detect(df, ["category"])
sub_col = detect(df, ["sub-category", "sub category", "subcategory"])
desc_col = detect(df, ["merchant", "person", "description", "name"])

detection_info = {"Date": date_col, "Time": time_col, "Amount": amt_col, "Category": cat_col, "Sub-cat": sub_col, "Desc": desc_col}

if not date_col or not amt_col:
    st.error(f"❌ Missing Date/Amount columns. Found: {list(df.columns)}")
    st.stop()

df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
df[amt_col] = pd.to_numeric(df[amt_col], errors="coerce").fillna(0)
df["Hour"] = df[time_col].apply(parse_time_to_hour) if time_col else 12
df["Category"] = df[cat_col].fillna("Uncategorized") if cat_col else "Uncategorized"
df["Sub Category"] = df[sub_col].fillna("Uncategorized") if sub_col else "Uncategorized"
df["Description"] = df[desc_col].fillna("Unknown") if desc_col else "Unknown"
df["Month"] = df[date_col].dt.to_period("M").astype(str)
df["Weekday"] = df[date_col].dt.day_name()
df["WeekType"] = df.apply(lambda r: determine_weekend(r, date_col), axis=1)
df["TimePeriod"] = df["Hour"].apply(get_time_period)
df = df.dropna(subset=[date_col])

if df.empty:
    st.error("❌ No valid data")
    st.stop()

data_quality_score, data_issues = get_data_quality_score(df, date_col, amt_col, cat_col, time_col)
months = sorted(df["Month"].unique())

# Initialize filters with actual data ONCE
if not st.session_state['filters_initialized']:
    st.session_state['cat_filter'] = {cat: True for cat in df["Category"].unique()}
    st.session_state['sub_filter'] = {sub: True for sub in df["Sub Category"].unique()}
    st.session_state['filters_initialized'] = True

# Month selector in sidebar
with st.sidebar:
    st.markdown("---")
    selected_month = st.selectbox("📅 Month", months, index=len(months)-1, format_func=format_month)
    st.caption(f"📊 {len(file_info)} sources • {sum(f['rows'] for f in file_info):,} rows")

month_df = df[df["Month"] == selected_month]
non_bill_df = month_df[month_df["Category"] != "Bill Payment"]
prev_idx = months.index(selected_month) - 1
prev_month_df = df[df["Month"] == months[prev_idx]] if prev_idx >= 0 else pd.DataFrame()

# =========================================================
# TABS
# =========================================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📈 Trends", "📅 Monthly", "💡 Insights", "🧠 Intelligence", "📤 Export", "🔧 Admin"])

# =========================================================
# TAB 1 - TRENDS
# =========================================================
with tab1:
    st.markdown("### 📈 Long-term Trends")
    c1, c2 = st.columns(2)
    
    with c1:
        fig = px.line(df.groupby(["Month", "Category"])[amt_col].sum().reset_index(), 
                      x="Month", y=amt_col, color="Category", template="plotly_dark", title="By Category")
        fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
        st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
    
    with c2:
        fig = px.line(df.groupby("Month")[amt_col].sum().reset_index(), 
                      x="Month", y=amt_col, markers=True, template="plotly_dark", title="Total Monthly")
        fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
        st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
    
    # =========================================================
    # SPENDING HABITS - TIME ANALYSIS (ALL DATA)
    # =========================================================
    st.markdown("### 🕐 Spending Habits (All Time)")
    st.caption("Your overall spending patterns across all months")
    
    h1, h2 = st.columns(2)
    
    with h1:
        period_order = ["Morning (5AM-12PM)", "Afternoon (12PM-5PM)", "Evening (5PM-9PM)", "Night (9PM-5AM)"]
        period_data = df.groupby("TimePeriod")[amt_col].sum().reindex(period_order).fillna(0).reset_index()
        fig = px.bar(period_data, x="TimePeriod", y=amt_col, template="plotly_dark", 
                     title="Spending by Time of Day", color="TimePeriod",
                     color_discrete_sequence=["#FFD700", "#FF8C00", "#FF4500", "#4169E1"])
        fig.update_layout(showlegend=False, xaxis_fixedrange=True, yaxis_fixedrange=True)
        st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
    
    with h2:
        hourly = pd.DataFrame({"Hour": range(24)}).merge(df.groupby("Hour")[amt_col].sum().reset_index(), how="left").fillna(0)
        hourly["Label"] = hourly["Hour"].apply(lambda x: f"{int(x):02d}:00")
        fig = px.bar(hourly, x="Label", y=amt_col, template="plotly_dark", title="Spending by Hour")
        fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
        fig.update_xaxes(tickangle=45)
        st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
    
    # Weekday pattern (all time)
    st.markdown("### 📅 Weekly Pattern (All Time)")
    w1, w2 = st.columns([2.2, 1])
    
    with w1:
        weekday_data = df.groupby("Weekday")[amt_col].sum().reindex(WEEK_ORDER).fillna(0).reset_index()
        fig = px.bar(weekday_data, x="Weekday", y=amt_col, template="plotly_dark", title="Total Spend by Day of Week")
        fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
        st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
    
    with w2:
        weektype_data = df.groupby("WeekType")[amt_col].sum().reset_index()
        fig = px.pie(weektype_data, values=amt_col, names="WeekType", template="plotly_dark", 
                     title="Weekday vs Weekend", color_discrete_sequence=["#3b82f6", "#f59e0b"])
        fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
        st.plotly_chart(fig, use_container_width=True, config=get_chart_config())

# =========================================================
# TAB 2 - MONTHLY VIEW
# =========================================================
with tab2:
    st.markdown(f"### 📅 {format_month(selected_month)}")
    
    # KPIs
    k1, k2, k3, k4 = st.columns(4)
    total = month_df[amt_col].sum()
    excl_bills = non_bill_df[amt_col].sum()
    daily_avg = non_bill_df.groupby(date_col)[amt_col].sum().mean() if not non_bill_df.empty else 0
    top_cat = non_bill_df.groupby("Category")[amt_col].sum().idxmax() if not non_bill_df.empty else "N/A"
    
    for col, title, val in [(k1,"Total",total), (k2,"Excl Bills",excl_bills), (k3,"Daily Avg",daily_avg), (k4,"Top Cat",top_cat)]:
        disp = f"₹{val:,.0f}" if isinstance(val, (int,float,np.number)) else str(val)
        col.markdown(f"<div class='card'><div class='kpi-title'>{title}</div><div class='kpi-value'>{disp}</div></div>", unsafe_allow_html=True)
    
    # Budget & Composition
    left, right = st.columns([1.4, 1])
    
    with left:
        st.markdown("#### 📉 Budget Burn-down")
        budget = st.number_input("Budget", value=30000, step=1000, key="budget")
        try:
            y, m = int(selected_month.split("-")[0]), int(selected_month.split("-")[1])
            days = calendar.monthrange(y, m)[1]
            if not non_bill_df.empty:
                daily = non_bill_df.groupby(date_col)[amt_col].sum().reindex(
                    pd.date_range(month_df[date_col].min(), month_df[date_col].max()), fill_value=0
                ).cumsum().reset_index()
                daily.columns = ["Date", "Actual"]
                fig = px.line(daily, x="Date", y="Actual", template="plotly_dark")
                fig.add_scatter(x=pd.date_range(daily["Date"].min(), periods=days), y=np.linspace(0, budget, days), name="Ideal")
                fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
                st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
        except:
            pass
    
    with right:
        st.markdown("#### 🧩 Composition")
        if not month_df.empty and month_df[amt_col].sum() > 0:
            chart_df = month_df.copy()
            tot = chart_df[amt_col].sum()
            cat_sums = chart_df.groupby("Category")[amt_col].sum()
            chart_df["CatLabel"] = chart_df["Category"].apply(lambda x: f"{x} ({cat_sums.get(x,0)/tot:.1%})")
            fig = px.treemap(chart_df, path=["CatLabel", "Sub Category"], values=amt_col, template="plotly_dark")
            fig.update_traces(texttemplate="%{label}<br>₹%{value:,.0f}")
            st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
    
    # Patterns (unfiltered)
    st.markdown("#### 📆 Patterns")
    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(month_df.groupby("Category")[amt_col].sum().reset_index(), x="Category", y=amt_col, template="plotly_dark", title="By Category")
        fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
        st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
    with c2:
        fig = px.bar(month_df.groupby(date_col)[amt_col].sum().reset_index(), x=date_col, y=amt_col, template="plotly_dark", title="By Day")
        fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
        st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
    
    # =========================================================
    # FILTERS SECTION - SHARED ACROSS TIME & WEEKDAY ANALYSIS
    # =========================================================
    st.markdown("---")
    st.markdown("### 🎛️ Filter Analysis")
    st.caption("These filters apply to both Time Analysis and Weekday/Weekend charts below")
    
    f1, f2, f3 = st.columns([1.2, 1.2, 1])
    
    all_cats = sorted(month_df["Category"].unique().tolist())
    
    with f1:
        with st.popover("🏷️ Filter Categories"):
            ca, cb = st.columns(2)
            if ca.button("All", key="all_cat", use_container_width=True):
                for c in all_cats:
                    st.session_state['cat_filter'][c] = True
            if cb.button("None", key="none_cat", use_container_width=True):
                for c in all_cats:
                    st.session_state['cat_filter'][c] = False
            st.markdown("---")
            for cat in all_cats:
                if cat not in st.session_state['cat_filter']:
                    st.session_state['cat_filter'][cat] = True
                st.session_state['cat_filter'][cat] = st.checkbox(cat, value=st.session_state['cat_filter'][cat], key=f"cf_{cat}")
    
    sel_cats = [c for c in all_cats if st.session_state['cat_filter'].get(c, True)]
    if not sel_cats:
        sel_cats = all_cats
    
    # First level filter
    filtered_by_cat = month_df[month_df["Category"].isin(sel_cats)]
    all_subs = sorted(filtered_by_cat["Sub Category"].unique().tolist())
    
    with f2:
        with st.popover("📂 Filter Sub-categories"):
            sa, sb = st.columns(2)
            if sa.button("All", key="all_sub", use_container_width=True):
                for s in all_subs:
                    st.session_state['sub_filter'][s] = True
            if sb.button("None", key="none_sub", use_container_width=True):
                for s in all_subs:
                    st.session_state['sub_filter'][s] = False
            st.markdown("---")
            for sub in all_subs:
                if sub not in st.session_state['sub_filter']:
                    st.session_state['sub_filter'][sub] = True
                st.session_state['sub_filter'][sub] = st.checkbox(sub, value=st.session_state['sub_filter'].get(sub, True), key=f"sf_{sub}")
    
    sel_subs = [s for s in all_subs if st.session_state['sub_filter'].get(s, True)]
    if not sel_subs:
        sel_subs = all_subs
    
    # FINAL FILTERED DATA - Used for both Time Analysis and Weekday Analysis
    filtered = filtered_by_cat[filtered_by_cat["Sub Category"].isin(sel_subs)]
    
    with f3:
        metric_idx = 0 if st.session_state['metric_choice'] == "Total Spend" else 1
        metric = st.selectbox("Metric", ["Total Spend", "Avg/Day"], index=metric_idx, key="metric_sel")
        st.session_state['metric_choice'] = metric
    
    # Show filter summary
    if len(sel_cats) < len(all_cats) or len(sel_subs) < len(all_subs):
        st.info(f"🔍 Showing {len(filtered)} of {len(month_df)} transactions | Categories: {len(sel_cats)}/{len(all_cats)} | Sub-categories: {len(sel_subs)}/{len(all_subs)}")
    
    # =========================================================
    # TIME ANALYSIS - USING FILTERED DATA
    # =========================================================
    st.markdown("#### ⏰ Time Analysis (Filtered)")
    
    if not filtered.empty:
        h1, h2 = st.columns(2)
        
        with h1:
            period_order = ["Morning (5AM-12PM)", "Afternoon (12PM-5PM)", "Evening (5PM-9PM)", "Night (9PM-5AM)"]
            if metric == "Total Spend":
                period_data = filtered.groupby("TimePeriod")[amt_col].sum().reindex(period_order).fillna(0).reset_index()
            else:
                period_data = filtered.groupby([date_col, "TimePeriod"])[amt_col].sum().reset_index().groupby("TimePeriod")[amt_col].mean().reindex(period_order).fillna(0).reset_index()
            
            fig = px.bar(period_data, x="TimePeriod", y=amt_col, template="plotly_dark", 
                         title=f"{metric} by Period", color="TimePeriod",
                         color_discrete_sequence=["#FFD700", "#FF8C00", "#FF4500", "#4169E1"])
            fig.update_layout(showlegend=False, xaxis_fixedrange=True, yaxis_fixedrange=True)
            st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
        
        with h2:
            if metric == "Total Spend":
                hourly_data = filtered.groupby("Hour")[amt_col].sum().reset_index()
            else:
                hourly_data = filtered.groupby([date_col, "Hour"])[amt_col].sum().reset_index().groupby("Hour")[amt_col].mean().reset_index()
            
            hourly = pd.DataFrame({"Hour": range(24)}).merge(hourly_data, how="left").fillna(0)
            hourly["Label"] = hourly["Hour"].apply(lambda x: f"{int(x):02d}:00")
            fig = px.bar(hourly, x="Label", y=amt_col, template="plotly_dark", title=f"{metric} by Hour")
            fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
    else:
        st.info("No data for selected filters")
    
    # =========================================================
    # WEEKDAY VS WEEKEND - USING SAME FILTERED DATA
    # =========================================================
    st.markdown("#### 📅 Weekday vs Weekend (Filtered)")
    st.caption("*Weekend = Fri 7PM+ & Sat & Sun")
    
    if not filtered.empty:
        if metric == "Total Spend":
            day_data = filtered.groupby("Weekday")[amt_col].sum()
        else:
            day_data = filtered.groupby([date_col, "Weekday"])[amt_col].sum().reset_index().groupby("Weekday")[amt_col].mean()
        
        day_data = day_data.reindex(WEEK_ORDER).fillna(0).reset_index()
        
        c1, c2 = st.columns([2.2, 1])
        with c1:
            fig = px.bar(day_data, x="Weekday", y=amt_col, template="plotly_dark", title=f"{metric} by Day")
            fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
            st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
        with c2:
            if metric == "Total Spend":
                wt = filtered.groupby("WeekType")[amt_col].sum().reset_index()
            else:
                wt = filtered.groupby("WeekType")[amt_col].mean().reset_index()
            fig = px.bar(wt, x="WeekType", y=amt_col, template="plotly_dark", title="Weekday vs Weekend")
            fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
            st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
    else:
        st.info("No data for selected filters")

# =========================================================
# TAB 3 - INSIGHTS
# =========================================================
with tab3:
    st.markdown("### 💡 Smart Insights")
    for insight in generate_insights(month_df, prev_month_df, amt_col, date_col):
        st.markdown(f"<div class='insight-box'><div class='insight-text'>{insight}</div></div>", unsafe_allow_html=True)

# =========================================================
# TAB 4 - INTELLIGENCE
# =========================================================
with tab4:
    st.markdown("### 🧠 Signals & Risks")
    
    st.markdown("#### 🔁 Recurring Uncategorized")
    uncat = df[df["Category"] == "Uncategorized"]
    if not uncat.empty:
        rec = uncat.groupby("Description")[amt_col].agg(["count","mean","std"]).reset_index()
        rec["std"] = rec["std"].fillna(0)
        rec = rec[(rec["count"] >= 3) & ((rec["std"] / rec["mean"].replace(0,1)) < 0.1)]
        if not rec.empty:
            st.dataframe(rec, use_container_width=True)
        else:
            st.info("None found")
    else:
        st.info("No uncategorized")
    
    st.markdown("#### 🚨 Large (>₹3000)")
    large = df[(df["Category"] != "Bill Payment") & (df[amt_col] > 3000)]
    if not large.empty:
        st.dataframe(large[[date_col, "Description", amt_col]], use_container_width=True)
    else:
        st.info("None found")

# =========================================================
# TAB 5 - EXPORT
# =========================================================
with tab5:
    st.markdown("### 📤 Export")
    buf = BytesIO()
    df.sort_values(date_col).to_excel(buf, index=False)
    st.download_button("📥 Download Excel", buf.getvalue(), "expense_data.xlsx")

# =========================================================
# TAB 6 - ADMIN
# =========================================================
with tab6:
    st.markdown("### 🔧 Admin")
    
    if st.button("🗑️ Clear Logs"):
        clear_debug_log()
        st.rerun()
    
    if st.session_state.get('debug_log'):
        for log in st.session_state['debug_log'][-40:]:
            st.markdown(f"<div class='log-{log['level']}'>[{log['time']}] {log['message']}</div>", unsafe_allow_html=True)
    else:
        st.info("No logs. Click Sync Data to generate.")
    
    st.markdown("---")
    st.markdown(f"**Quality: {data_quality_score}/100**")
    for issue in data_issues:
        st.markdown(f"<div class='warning-card'>{issue}</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("**Column Detection:**")
    for k, v in detection_info.items():
        st.markdown(f"{'✅' if v else '❌'} {k}: `{v or 'None'}`")
    
    st.markdown("---")
    st.markdown("**Loaded Sources:**")
    for f in file_info:
        st.markdown(f"📄 {f['name']} — {f['rows']} rows | `{f.get('type')}`")
    
    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows", f"{len(df):,}")
    c2.metric("Months", len(months))
    c3.metric("Categories", df['Category'].nunique())
    c4.metric("Total", f"₹{df[amt_col].sum():,.0f}")
    
    st.markdown("---")
    st.dataframe(df.head(10), use_container_width=True)

st.markdown("---")
st.markdown("<div class='subtle'>Built for thinking, not panic.</div>", unsafe_allow_html=True)
