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
# CONFIG
# =========================================================
st.set_page_config(
    page_title="Expense Intelligence - UAT",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =========================================================
# CSS TO PREVENT SCROLL JUMP + SMOOTH SCROLLING
# =========================================================
st.markdown("""
<style>
/* Smooth scrolling */
html {
    scroll-behavior: smooth;
}

/* Hide anchor links visually but keep them functional */
.anchor-link {
    display: block;
    position: relative;
    top: -80px;
    visibility: hidden;
}

/* Mobile optimizations */
@media (max-width: 768px) {
    .stSelectbox, .stCheckbox {
        touch-action: manipulation;
    }
}
</style>

<script>
// Preserve scroll position
window.addEventListener('load', function() {
    const scrollPos = sessionStorage.getItem('scrollPos');
    if (scrollPos) {
        window.scrollTo(0, parseInt(scrollPos));
        sessionStorage.removeItem('scrollPos');
    }
});

// Save scroll position before rerun
window.addEventListener('beforeunload', function() {
    sessionStorage.setItem('scrollPos', window.scrollY);
});
</script>
""", unsafe_allow_html=True)

# Initialize debug log in session state
if 'debug_log' not in st.session_state:
    st.session_state['debug_log'] = []

def add_debug_log(message, level="info"):
    """Add a message to the debug log"""
    timestamp = pd.Timestamp.now().strftime("%H:%M:%S")
    st.session_state['debug_log'].append({
        "time": timestamp,
        "level": level,
        "message": message
    })

def clear_debug_log():
    """Clear the debug log"""
    st.session_state['debug_log'] = []

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
.insight-text { font-size: 1rem; line-height: 1.6; }
.debug-card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 16px; margin: 8px 0; }
.debug-title { color: #60a5fa; font-weight: 600; font-size: 0.9rem; margin-bottom: 8px; }
.debug-value { color: #e2e8f0; font-family: monospace; font-size: 0.85rem; word-wrap: break-word; }
.stat-card { background: linear-gradient(135deg, #065f46 0%, #059669 100%); border-radius: 12px; padding: 16px; margin: 8px 0; color: white; }
.warning-card { background: linear-gradient(135deg, #92400e 0%, #d97706 100%); border-radius: 12px; padding: 16px; margin: 8px 0; color: white; }
.error-card { background: linear-gradient(135deg, #991b1b 0%, #dc2626 100%); border-radius: 12px; padding: 16px; margin: 8px 0; color: white; }
.log-info { background: #1e3a5f; border-left: 4px solid #3b82f6; padding: 8px 12px; margin: 4px 0; font-family: monospace; font-size: 0.8rem; }
.log-success { background: #1e3f2e; border-left: 4px solid #10b981; padding: 8px 12px; margin: 4px 0; font-family: monospace; font-size: 0.8rem; }
.log-warning { background: #3f2e1e; border-left: 4px solid #f59e0b; padding: 8px 12px; margin: 4px 0; font-family: monospace; font-size: 0.8rem; }
.log-error { background: #3f1e1e; border-left: 4px solid #ef4444; padding: 8px 12px; margin: 4px 0; font-family: monospace; font-size: 0.8rem; }
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
        unique_ids = list(set(matches))
        add_debug_log(f"Found {len(unique_ids)} sheet(s)", "success" if unique_ids else "warning")
        return unique_ids
    except Exception as e:
        add_debug_log(f"Error: {e}", "error")
        return []

def load_google_sheet_by_id(sheet_id):
    add_debug_log(f"Loading sheet: {sheet_id}")
    try:
        df = pd.read_csv(f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv")
        add_debug_log(f"Loaded {len(df)} rows", "success")
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
        return files_info
    except Exception as e:
        add_debug_log(f"Error: {e}", "error")
        return []

def load_data_from_drive(folder_id, manual_sheet_links=None):
    add_debug_log("=" * 40)
    add_debug_log("STARTING DATA LOAD")
    dfs, file_info = [], []
    
    # Method 1: Regular files
    for f in get_files_from_drive_folder(folder_id):
        try:
            temp_df = pd.read_csv(f["path"]) if f["type"] == "csv" else pd.read_excel(f["path"])
            if not temp_df.empty:
                dfs.append(temp_df)
                file_info.append({"name": f["name"], "rows": len(temp_df), "cols": len(temp_df.columns), "type": f["type"]})
        except:
            pass
    
    # Method 2: Google Sheets in folder
    for sheet_id in get_google_sheets_from_folder(folder_id):
        temp_df = load_google_sheet_by_id(sheet_id)
        if temp_df is not None:
            dfs.append(temp_df)
            file_info.append({"name": f"Sheet ({sheet_id[:8]}...)", "rows": len(temp_df), "cols": len(temp_df.columns), "type": "gsheet"})
    
    # Method 3: Embed scan
    try:
        response = requests.get(f"https://drive.google.com/embeddedfolderview?id={folder_id}", headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if response.status_code == 200:
            for file_id in re.findall(r'\["([a-zA-Z0-9_-]{20,50})"', response.text)[:10]:
                if file_id != folder_id:
                    temp_df = try_load_as_google_sheet(file_id)
                    if temp_df is not None and not any(f.get('name', '').startswith(f"Sheet ({file_id[:8]}") for f in file_info):
                        dfs.append(temp_df)
                        file_info.append({"name": f"Sheet ({file_id[:8]}...)", "rows": len(temp_df), "cols": len(temp_df.columns), "type": "gsheet"})
    except:
        pass
    
    # Method 4: Manual links
    if manual_sheet_links:
        for link in manual_sheet_links:
            sheet_id = extract_sheet_id_from_link(link)
            if sheet_id:
                temp_df = load_google_sheet_by_id(sheet_id)
                if temp_df is not None:
                    dfs.append(temp_df)
                    file_info.append({"name": "Sheet (manual)", "rows": len(temp_df), "cols": len(temp_df.columns), "type": "gsheet"})
    
    add_debug_log(f"TOTAL: {len(dfs)} loaded", "success" if dfs else "error")
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

def generate_insights(current_month_df, previous_month_df, amt_col, date_col):
    insights = []
    try:
        current_total = current_month_df[amt_col].sum()
        prev_total = previous_month_df[amt_col].sum() if not previous_month_df.empty else 0
        
        if prev_total > 0:
            pct = ((current_total - prev_total) / prev_total) * 100
            if pct > 10:
                insights.append(f"💸 Spending ↑ {pct:.1f}% vs last month (₹{current_total:,.0f} vs ₹{prev_total:,.0f})")
            elif pct < -10:
                insights.append(f"✅ Saved {abs(pct):.1f}% vs last month (₹{current_total:,.0f} vs ₹{prev_total:,.0f})")
            else:
                insights.append(f"📊 Stable at ₹{current_total:,.0f}")
        
        if "Category" in current_month_df.columns:
            curr_cat = current_month_df.groupby("Category")[amt_col].sum()
            prev_cat = previous_month_df.groupby("Category")[amt_col].sum() if not previous_month_df.empty else pd.Series()
            for cat in curr_cat.index:
                if cat in prev_cat.index and prev_cat[cat] > 0:
                    change = ((curr_cat[cat] - prev_cat[cat]) / prev_cat[cat]) * 100
                    if change > 25:
                        insights.append(f"⚠️ {cat} ↑ {change:.1f}%")
        
        if not current_month_df.empty and "Description" in current_month_df.columns:
            top = current_month_df.nlargest(1, amt_col).iloc[0]
            insights.append(f"🔝 Biggest: ₹{top[amt_col]:,.0f} on {top['Description']}")
        
        if "Hour" in current_month_df.columns:
            peak = current_month_df.groupby("Hour")[amt_col].sum().idxmax()
            insights.append(f"⏰ Peak hour: {int(peak)}:00")
    except:
        pass
    return insights

def get_data_quality_score(df, date_col, amt_col, cat_col, time_col):
    issues, score = [], 100
    if df[date_col].isna().sum() > 0:
        issues.append(f"⚠️ {df[date_col].isna().sum()} missing dates")
        score -= 10
    if (df[amt_col] == 0).sum() > 0:
        issues.append(f"⚠️ {(df[amt_col] == 0).sum()} zero amounts")
        score -= 10
    if "Category" in df.columns and (df["Category"] == "Uncategorized").sum() > 0:
        issues.append(f"📝 {(df['Category'] == 'Uncategorized').sum()} uncategorized")
        score -= 5
    if not time_col:
        issues.append("ℹ️ No time column")
        score -= 5
    return max(0, score), issues

WEEK_ORDER = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.markdown("### 📂 Data Source")
    mode = st.radio("", ["Google Drive (Auto-sync)", "Manual Upload"], key="mode", label_visibility="collapsed")

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
                    pass
else:
    user_drive_link = st.session_state.get('user_drive_link', '')
    folder_id = extract_folder_id_from_link(user_drive_link)
    sheet_id = extract_sheet_id_from_link(user_drive_link)
    
    with st.sidebar:
        if st.button("🔄 Sync Data", use_container_width=True):
            if 'gdrive_loaded' in st.session_state:
                del st.session_state['gdrive_loaded']
        
        with st.expander("⚙️ Advanced", expanded=False):
            sheet_links_input = st.text_area("Manual Sheet URLs", height=60, placeholder="https://docs.google.com/spreadsheets/d/...")
            manual_sheet_links = [l.strip() for l in sheet_links_input.split('\n') if '/spreadsheets/' in l]
            st.caption(f"Folder: `{folder_id or 'None'}`")
    
    if not user_drive_link:
        st.info("📁 No Drive link. Use Manual Upload.")
        st.stop()
    
    if 'gdrive_loaded' not in st.session_state:
        clear_debug_log()
        with st.spinner("Loading..."):
            if sheet_id:
                temp_df = load_google_sheet_by_id(sheet_id)
                if temp_df is not None:
                    dfs, file_info = [temp_df], [{"name": "Google Sheet", "rows": len(temp_df), "cols": len(temp_df.columns), "type": "gsheet"}]
            elif folder_id:
                dfs, file_info = load_data_from_drive(folder_id, manual_sheet_links)
            
            if dfs:
                st.session_state['gdrive_loaded'] = True
                st.session_state['gdrive_dfs'] = dfs
                st.session_state['file_info'] = file_info
            else:
                st.error("❌ No data found. Check sharing settings or add Manual Sheet URLs.")
                st.stop()
    
    if 'gdrive_dfs' in st.session_state:
        dfs = st.session_state['gdrive_dfs']
        file_info = st.session_state.get('file_info', [])

if not dfs:
    st.info("📁 Click 'Sync Data' or upload files")
    st.stop()

df = pd.concat(dfs, ignore_index=True)

# =========================================================
# DATA PREP
# =========================================================
date_col = detect(df, ["date"])
time_col = detect(df, ["time"])
amt_col = detect(df, ["amount"])
cat_col = detect(df, ["category"])
sub_col = detect(df, ["sub-category", "sub category", "subcategory"])
desc_col = detect(df, ["merchant", "person", "description", "name"])

detection_info = {"Date": date_col, "Time": time_col, "Amount": amt_col, "Category": cat_col, "Sub-cat": sub_col, "Desc": desc_col}

if not date_col or not amt_col:
    st.error(f"❌ Missing columns. Found: {list(df.columns)}")
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
with st.sidebar:
    st.markdown("---")
    selected_month = st.selectbox("📅 Month", months, index=len(months)-1, format_func=format_month)
    st.caption(f"📊 {len(file_info)} sources • {sum(f['rows'] for f in file_info):,} rows")

month_df = df[df["Month"] == selected_month]
non_bill_df = month_df[month_df["Category"] != "Bill Payment"]
prev_month_df = df[df["Month"] == months[months.index(selected_month) - 1]] if months.index(selected_month) > 0 else pd.DataFrame()

# =========================================================
# TABS
# =========================================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📈 Trends", "📅 Monthly", "💡 Insights", "🧠 Intelligence", "📤 Export", "🔧 Admin"])

# =========================================================
# TAB 1 — TRENDS
# =========================================================
with tab1:
    st.markdown("### 📈 Long-term Trends")
    c1, c2 = st.columns(2)
    with c1:
        fig = px.line(df.groupby(["Month","Category"])[amt_col].sum().reset_index(), x="Month", y=amt_col, color="Category", template="plotly_dark", title="By Category")
        fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
        st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
    with c2:
        fig = px.line(df.groupby("Month")[amt_col].sum().reset_index(), x="Month", y=amt_col, markers=True, template="plotly_dark", title="Total Monthly")
        fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
        st.plotly_chart(fig, use_container_width=True, config=get_chart_config())

# =========================================================
# TAB 2 — MONTHLY VIEW
# =========================================================
with tab2:
    st.markdown(f"### 📅 {format_month(selected_month)}")
    
    # KPIs
    k1, k2, k3, k4 = st.columns(4)
    total_spend = month_df[amt_col].sum()
    excl_bills = non_bill_df[amt_col].sum()
    daily_avg = non_bill_df.groupby(date_col)[amt_col].sum().mean() if not non_bill_df.empty else 0
    top_cat = non_bill_df.groupby("Category")[amt_col].sum().idxmax() if not non_bill_df.empty else "N/A"
    
    for col, title, val in [(k1,"Total",total_spend),(k2,"Excl Bills",excl_bills),(k3,"Daily Avg",daily_avg),(k4,"Top Cat",top_cat)]:
        disp = f"₹{val:,.0f}" if isinstance(val,(int,float,np.number)) else str(val)
        col.markdown(f"<div class='card'><div class='kpi-title'>{title}</div><div class='kpi-value'>{disp}</div></div>", unsafe_allow_html=True)
    
    # Budget + Composition
    left, right = st.columns([1.4, 1])
    with left:
        st.markdown("#### 📉 Budget Burn-down")
        budget = st.number_input("Budget", value=30000, step=1000, key="budget")
        try:
            y, m = int(selected_month.split("-")[0]), int(selected_month.split("-")[1])
            days = calendar.monthrange(y, m)[1]
            if not non_bill_df.empty:
                daily = non_bill_df.groupby(date_col)[amt_col].sum().reindex(pd.date_range(month_df[date_col].min(), month_df[date_col].max()), fill_value=0).cumsum().reset_index()
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
            total = chart_df[amt_col].sum()
            cat_sums = chart_df.groupby("Category")[amt_col].sum()
            chart_df["CatLabel"] = chart_df["Category"].apply(lambda x: f"{x} ({cat_sums.get(x,0)/total:.1%})")
            fig = px.treemap(chart_df, path=["CatLabel", "Sub Category"], values=amt_col, template="plotly_dark")
            fig.update_traces(texttemplate="%{label}<br>₹%{value:,.0f}")
            st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
    
    # Patterns
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
    
    # Time-based
    st.markdown("#### ⏰ Time Analysis")
    h1, h2 = st.columns(2)
    with h1:
        period_order = ["Morning (5AM-12PM)", "Afternoon (12PM-5PM)", "Evening (5PM-9PM)", "Night (9PM-5AM)"]
        fig = px.bar(month_df.groupby("TimePeriod")[amt_col].sum().reindex(period_order).fillna(0).reset_index(), x="TimePeriod", y=amt_col, template="plotly_dark", title="By Period", color="TimePeriod", color_discrete_sequence=["#FFD700","#FF8C00","#FF4500","#4169E1"])
        fig.update_layout(showlegend=False, xaxis_fixedrange=True, yaxis_fixedrange=True)
        st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
    with h2:
        hourly = pd.DataFrame({"Hour": range(24)}).merge(month_df.groupby("Hour")[amt_col].sum().reset_index(), how="left").fillna(0)
        hourly["Label"] = hourly["Hour"].apply(lambda x: f"{int(x):02d}:00")
        fig = px.bar(hourly, x="Label", y=amt_col, template="plotly_dark", title="By Hour")
        fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
        fig.update_xaxes(tickangle=45)
        st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
    
    # =========================================================
    # WEEKDAY ANALYSIS - USING CONTAINER TO PREVENT JUMP
    # =========================================================
    st.markdown('<div id="weekday-section"></div>', unsafe_allow_html=True)
    st.markdown("### 📅 Weekday vs Weekend")
    st.caption("*Weekend = Fri 7PM+ & Sat & Sun")
    
    # Use a container to isolate the interactive elements
    weekday_container = st.container()
    
    with weekday_container:
        # Initialize states
        if 'cat_filter' not in st.session_state:
            st.session_state['cat_filter'] = {c: True for c in month_df["Category"].unique()}
        if 'sub_filter' not in st.session_state:
            st.session_state['sub_filter'] = {}
        if 'metric_choice' not in st.session_state:
            st.session_state['metric_choice'] = "Total Spend"
        
        f1, f2, f3 = st.columns([1.2, 1.2, 1])
        
        all_cats = sorted(month_df["Category"].unique().tolist())
        
        with f1:
            with st.popover("🏷️ Categories"):
                ca, cb = st.columns(2)
                if ca.button("All", key="sel_all_cat", use_container_width=True):
                    st.session_state['cat_filter'] = {c: True for c in all_cats}
                if cb.button("None", key="clr_all_cat", use_container_width=True):
                    st.session_state['cat_filter'] = {c: False for c in all_cats}
                st.markdown("---")
                for cat in all_cats:
                    if cat not in st.session_state['cat_filter']:
                        st.session_state['cat_filter'][cat] = True
                    st.session_state['cat_filter'][cat] = st.checkbox(cat, value=st.session_state['cat_filter'][cat], key=f"c_{cat}")
        
        sel_cats = [c for c in all_cats if st.session_state['cat_filter'].get(c, True)]
        if not sel_cats:
            sel_cats = all_cats
        
        filtered = month_df[month_df["Category"].isin(sel_cats)]
        all_subs = sorted(filtered["Sub Category"].unique().tolist())
        
        with f2:
            with st.popover("📂 Sub-categories"):
                sa, sb = st.columns(2)
                if sa.button("All", key="sel_all_sub", use_container_width=True):
                    st.session_state['sub_filter'] = {s: True for s in all_subs}
                if sb.button("None", key="clr_all_sub", use_container_width=True):
                    st.session_state['sub_filter'] = {s: False for s in all_subs}
                st.markdown("---")
                for sub in all_subs:
                    if sub not in st.session_state['sub_filter']:
                        st.session_state['sub_filter'][sub] = True
                    st.session_state['sub_filter'][sub] = st.checkbox(sub, value=st.session_state['sub_filter'].get(sub, True), key=f"s_{sub}")
        
        sel_subs = [s for s in all_subs if st.session_state['sub_filter'].get(s, True)]
        if not sel_subs:
            sel_subs = all_subs
        
        filtered = filtered[filtered["Sub Category"].isin(sel_subs)]
        
        with f3:
            # Use index based on session state to prevent jump
            metric_idx = 0 if st.session_state['metric_choice'] == "Total Spend" else 1
            metric = st.selectbox("Metric", ["Total Spend", "Avg/Day"], index=metric_idx, key="metric_sel")
            st.session_state['metric_choice'] = metric
        
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
                wt = filtered.groupby("WeekType")[amt_col].mean().reset_index()
                fig = px.bar(wt, x="WeekType", y=amt_col, template="plotly_dark", title="Weekday vs Weekend")
                fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
                st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
        else:
            st.info("No data for filters")

# =========================================================
# TAB 3 — INSIGHTS
# =========================================================
with tab3:
    st.markdown("### 💡 Smart Insights")
    for insight in generate_insights(month_df, prev_month_df, amt_col, date_col):
        st.markdown(f"<div class='insight-box'><div class='insight-text'>{insight}</div></div>", unsafe_allow_html=True)

# =========================================================
# TAB 4 — INTELLIGENCE
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
# TAB 5 — EXPORT
# =========================================================
with tab5:
    st.markdown("### 📤 Export")
    buf = BytesIO()
    df.sort_values(date_col).to_excel(buf, index=False)
    st.download_button("📥 Download Excel", buf.getvalue(), "expense_data.xlsx")

# =========================================================
# TAB 6 — ADMIN
# =========================================================
with tab6:
    st.markdown("### 🔧 Admin")
    
    if st.button("🗑️ Clear Logs"):
        clear_debug_log()
    
    if st.session_state.get('debug_log'):
        for log in st.session_state['debug_log'][-30:]:
            st.markdown(f"<div class='log-{log['level']}'>[{log['time']}] {log['message']}</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown(f"**Quality: {data_quality_score}/100**")
    for issue in data_issues:
        st.markdown(f"<div class='warning-card'>{issue}</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("**Columns:**")
    for k, v in detection_info.items():
        st.markdown(f"{'✅' if v else '❌'} {k}: `{v or 'None'}`")
    
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
