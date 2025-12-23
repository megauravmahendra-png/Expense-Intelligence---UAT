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
    """Extract folder ID from various Google Drive link formats"""
    if not link or pd.isna(link):
        return None
    
    link = str(link).strip()
    
    if '/folders/' in link:
        try:
            folder_id = link.split('/folders/')[1].split('?')[0].split('/')[0].strip()
            add_debug_log(f"Extracted folder ID: {folder_id}", "success")
            return folder_id
        except Exception as e:
            add_debug_log(f"Failed to extract folder ID: {e}", "error")
            return None
    
    if len(link) > 20 and '/' not in link:
        return link
    
    return None

def extract_sheet_id_from_link(link):
    """Extract Google Sheet ID from URL"""
    if not link:
        return None
    
    link = str(link).strip()
    
    if '/spreadsheets/d/' in link:
        try:
            sheet_id = link.split('/spreadsheets/d/')[1].split('/')[0].split('?')[0]
            return sheet_id
        except:
            return None
    
    return None

def get_google_sheets_from_folder(folder_id):
    """Scan folder for Google Sheets"""
    add_debug_log(f"Scanning folder for Google Sheets: {folder_id}")
    
    folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(folder_url, headers=headers, timeout=15)
        add_debug_log(f"Folder page status: {response.status_code}")
        
        if response.status_code != 200:
            return []
        
        content = response.text
        sheet_ids = []
        
        spreadsheet_pattern = r'/spreadsheets/d/([a-zA-Z0-9_-]+)'
        matches = re.findall(spreadsheet_pattern, content)
        sheet_ids.extend(matches)
        
        unique_sheet_ids = list(set(sheet_ids))
        add_debug_log(f"Found {len(unique_sheet_ids)} sheet(s)", "success" if unique_sheet_ids else "warning")
        
        return unique_sheet_ids
        
    except Exception as e:
        add_debug_log(f"Error scanning folder: {e}", "error")
        return []

def load_google_sheet_by_id(sheet_id, sheet_name=None):
    """Load a Google Sheet by its ID"""
    add_debug_log(f"Loading Google Sheet: {sheet_id}")
    
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        if sheet_name:
            url += f"&sheet={sheet_name}"
        
        df = pd.read_csv(url)
        add_debug_log(f"Loaded {len(df)} rows, {len(df.columns)} columns", "success")
        
        return df
    except Exception as e:
        add_debug_log(f"Error loading sheet {sheet_id}: {e}", "error")
        return None

def try_load_as_google_sheet(file_id):
    """Try to load a Google Drive file ID as a Google Sheet"""
    try:
        url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=csv"
        response = requests.head(url, allow_redirects=True, timeout=10)
        
        if response.status_code == 200:
            df = pd.read_csv(url)
            if not df.empty:
                add_debug_log(f"Loaded sheet {file_id[:8]}...: {len(df)} rows", "success")
                return df
        return None
    except:
        return None

def get_files_from_drive_folder(folder_id):
    """Get list of files from a Google Drive folder"""
    add_debug_log(f"Downloading files from folder: {folder_id}")
    
    try:
        folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
        
        temp_dir = Path("temp_data")
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir(exist_ok=True)
        
        gdown.download_folder(folder_url, output=str(temp_dir), quiet=True, use_cookies=False, remaining_ok=True)
        
        files_info = []
        all_files = list(temp_dir.iterdir())
        add_debug_log(f"Files downloaded: {[f.name for f in all_files]}")
        
        excel_files = list(temp_dir.glob("*.xlsx")) + list(temp_dir.glob("*.xls"))
        csv_files = list(temp_dir.glob("*.csv"))
        
        for f in excel_files:
            if not f.name.startswith("~$"):
                files_info.append({"type": "excel", "path": str(f), "name": f.name})
        
        for f in csv_files:
            if not f.name.startswith("~$"):
                files_info.append({"type": "csv", "path": str(f), "name": f.name})
        
        return files_info
    except Exception as e:
        add_debug_log(f"Error downloading: {e}", "error")
        return []

def load_data_from_drive(folder_id, manual_sheet_links=None):
    """Load data from Google Drive folder"""
    add_debug_log("=" * 50)
    add_debug_log("STARTING DATA LOAD")
    add_debug_log("=" * 50)
    
    dfs = []
    file_info = []
    
    # METHOD 1: Download regular files
    add_debug_log("--- METHOD 1: Regular files ---")
    files = get_files_from_drive_folder(folder_id)
    
    for f in files:
        try:
            if f["type"] == "csv":
                temp_df = pd.read_csv(f["path"])
            else:
                temp_df = pd.read_excel(f["path"])
            
            if not temp_df.empty:
                dfs.append(temp_df)
                file_info.append({
                    "name": f["name"], "rows": len(temp_df), "cols": len(temp_df.columns),
                    "type": f["type"], "source": "folder_download"
                })
        except Exception as e:
            add_debug_log(f"Error loading {f['name']}: {e}", "error")
    
    # METHOD 2: Scan for Google Sheets
    add_debug_log("--- METHOD 2: Scanning for Sheets ---")
    sheet_ids_from_folder = get_google_sheets_from_folder(folder_id)
    
    for sheet_id in sheet_ids_from_folder:
        temp_df = load_google_sheet_by_id(sheet_id)
        if temp_df is not None and not temp_df.empty:
            dfs.append(temp_df)
            file_info.append({
                "name": f"Google Sheet (auto)", "rows": len(temp_df), "cols": len(temp_df.columns),
                "type": "gsheet", "source": "folder_scan", "sheet_id": sheet_id[:10] + "..."
            })
    
    # METHOD 3: Embed view scan
    add_debug_log("--- METHOD 3: Embed view ---")
    try:
        embed_url = f"https://drive.google.com/embeddedfolderview?id={folder_id}"
        response = requests.get(embed_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        
        if response.status_code == 200:
            file_id_pattern = r'\["([a-zA-Z0-9_-]{20,50})"'
            potential_ids = re.findall(file_id_pattern, response.text)
            
            for file_id in potential_ids[:10]:
                if file_id != folder_id:
                    temp_df = try_load_as_google_sheet(file_id)
                    if temp_df is not None:
                        is_duplicate = any(f.get('sheet_id', '').startswith(file_id[:10]) for f in file_info)
                        if not is_duplicate:
                            dfs.append(temp_df)
                            file_info.append({
                                "name": f"Google Sheet ({file_id[:8]}...)", "rows": len(temp_df),
                                "cols": len(temp_df.columns), "type": "gsheet",
                                "source": "embed_scan", "sheet_id": file_id[:10] + "..."
                            })
    except Exception as e:
        add_debug_log(f"Embed scan failed: {e}", "warning")
    
    # METHOD 4: Manual links
    add_debug_log("--- METHOD 4: Manual links ---")
    if manual_sheet_links:
        for link in manual_sheet_links:
            sheet_id = extract_sheet_id_from_link(link)
            if sheet_id:
                temp_df = load_google_sheet_by_id(sheet_id)
                if temp_df is not None and not temp_df.empty:
                    dfs.append(temp_df)
                    file_info.append({
                        "name": f"Google Sheet (manual)", "rows": len(temp_df),
                        "cols": len(temp_df.columns), "type": "gsheet",
                        "source": "manual_link", "sheet_id": sheet_id[:10] + "..."
                    })
    
    add_debug_log(f"TOTAL: {len(dfs)} dataframe(s) loaded", "success" if dfs else "error")
    
    return dfs, file_info

def parse_time_to_hour(time_val):
    """Parse various time formats and return hour (0-23)"""
    if pd.isna(time_val):
        return 12
    
    time_str = str(time_val).strip().upper()
    
    am_pm_match = re.match(r'(\d{1,2}):(\d{2})(?::\d{2})?\s*(AM|PM)', time_str)
    if am_pm_match:
        hour = int(am_pm_match.group(1))
        am_pm = am_pm_match.group(3)
        
        if am_pm == 'PM' and hour != 12:
            hour += 12
        elif am_pm == 'AM' and hour == 12:
            hour = 0
        
        return hour
    
    time_24_match = re.match(r'(\d{1,2}):(\d{2})(?::\d{2})?', time_str)
    if time_24_match:
        hour = int(time_24_match.group(1))
        if 0 <= hour <= 23:
            return hour
    
    return 12

def determine_weekend(row, date_col):
    """Determine if a transaction is during weekend"""
    try:
        day_of_week = row[date_col].weekday()
        
        if day_of_week >= 5:
            return "Weekend"
        
        if day_of_week == 4:
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
    """Generate intelligent insights"""
    insights = []
    
    try:
        current_total = current_month_df[amt_col].sum()
        prev_total = previous_month_df[amt_col].sum() if not previous_month_df.empty else 0
        
        if prev_total > 0:
            pct_change = ((current_total - prev_total) / prev_total) * 100
            if pct_change > 10:
                insights.append(f"💸 Spending increased by {pct_change:.1f}% vs last month (₹{current_total:,.0f} vs ₹{prev_total:,.0f})")
            elif pct_change < -10:
                insights.append(f"✅ Great! You saved {abs(pct_change):.1f}% vs last month (₹{current_total:,.0f} vs ₹{prev_total:,.0f})")
            else:
                insights.append(f"📊 Spending stable at ₹{current_total:,.0f}, similar to last month")
        
        if "Category" in current_month_df.columns:
            current_cat = current_month_df.groupby("Category")[amt_col].sum()
            prev_cat = previous_month_df.groupby("Category")[amt_col].sum() if not previous_month_df.empty else pd.Series()
            
            for cat in current_cat.index:
                if cat in prev_cat.index and prev_cat[cat] > 0:
                    cat_change = ((current_cat[cat] - prev_cat[cat]) / prev_cat[cat]) * 100
                    if cat_change > 25:
                        insights.append(f"⚠️ {cat} jumped {cat_change:.1f}% (₹{current_cat[cat]:,.0f} vs ₹{prev_cat[cat]:,.0f})")
        
        if "WeekType" in current_month_df.columns:
            weekend_data = current_month_df[current_month_df["WeekType"] == "Weekend"]
            weekday_data = current_month_df[current_month_df["WeekType"] == "Weekday"]
            
            if not weekend_data.empty and not weekday_data.empty:
                weekend_avg = weekend_data.groupby(date_col)[amt_col].sum().mean()
                weekday_avg = weekday_data.groupby(date_col)[amt_col].sum().mean()
                
                if pd.notna(weekend_avg) and pd.notna(weekday_avg) and weekday_avg > 0:
                    if weekend_avg > weekday_avg * 1.3:
                        insights.append(f"🎉 You spend {((weekend_avg/weekday_avg - 1) * 100):.0f}% more on weekends")
        
        if not current_month_df.empty and "Description" in current_month_df.columns:
            top_expense = current_month_df.nlargest(1, amt_col).iloc[0]
            insights.append(f"🔝 Largest expense: ₹{top_expense[amt_col]:,.0f} on {top_expense['Description']}")
        
        if "Hour" in current_month_df.columns:
            hour_spend = current_month_df.groupby("Hour")[amt_col].sum()
            if not hour_spend.empty:
                peak_hour = hour_spend.idxmax()
                insights.append(f"⏰ Peak spending hour: {int(peak_hour)}:00 - {int(peak_hour)+1}:00")
    except:
        pass
    
    return insights

def get_data_quality_score(df, date_col, amt_col, cat_col, time_col):
    """Calculate data quality score"""
    issues = []
    score = 100
    
    missing_dates = df[date_col].isna().sum()
    if missing_dates > 0:
        issues.append(f"⚠️ {missing_dates} rows with missing dates")
        score -= min(20, missing_dates * 2)
    
    missing_amounts = (df[amt_col] == 0).sum() + df[amt_col].isna().sum()
    if missing_amounts > 0:
        issues.append(f"⚠️ {missing_amounts} rows with zero/missing amounts")
        score -= min(20, missing_amounts * 2)
    
    if "Category" in df.columns:
        uncategorized = (df["Category"] == "Uncategorized").sum()
        if uncategorized > 0:
            pct = (uncategorized / len(df)) * 100
            issues.append(f"📝 {uncategorized} ({pct:.1f}%) uncategorized")
            score -= min(15, pct / 2)
    
    if not time_col:
        issues.append(f"ℹ️ No time column - using defaults")
        score -= 5
    
    return max(0, score), issues

WEEK_ORDER = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

# =========================================================
# SIDEBAR - CLEAN UI
# =========================================================
with st.sidebar:
    # Data Source Selection
    st.markdown("### 📂 Data Source")
    mode = st.radio("", ["Google Drive (Auto-sync)", "Manual Upload"], key="data_source_mode", label_visibility="collapsed")

# Initialize variables
dfs = []
file_info = []
manual_sheet_links = []

# Handle data loading based on mode
if mode == "Manual Upload":
    with st.sidebar:
        uploads = st.file_uploader(
            "Upload Excel/CSV files",
            type=["xlsx", "xls", "csv"],
            accept_multiple_files=True,
            key="file_uploader"
        )
        if uploads:
            for f in uploads:
                try:
                    if f.name.endswith('.csv'):
                        temp_df = pd.read_csv(f)
                    else:
                        temp_df = pd.read_excel(f)
                    dfs.append(temp_df)
                    file_info.append({"name": f.name, "rows": len(temp_df), "cols": len(temp_df.columns), "type": "upload"})
                except Exception as e:
                    st.warning(f"Could not read {f.name}: {e}")
else:
    # Google Drive mode
    user_drive_link = st.session_state.get('user_drive_link', '')
    folder_id = extract_folder_id_from_link(user_drive_link)
    sheet_id = extract_sheet_id_from_link(user_drive_link)
    
    with st.sidebar:
        # Sync button - prominent
        if st.button("🔄 Sync Data", use_container_width=True, key="sync_button"):
            st.session_state['force_sync'] = True
            if 'gdrive_loaded' in st.session_state:
                del st.session_state['gdrive_loaded']
        
        # Advanced options in expander
        with st.expander("⚙️ Advanced Options", expanded=False):
            st.markdown("**📄 Manual Sheet Links**")
            st.caption("If auto-detection fails, paste Google Sheet URL(s)")
            sheet_links_input = st.text_area(
                "Sheet URLs", 
                height=80, 
                key="sheet_links_input",
                placeholder="https://docs.google.com/spreadsheets/d/...",
                label_visibility="collapsed"
            )
            manual_sheet_links = [link.strip() for link in sheet_links_input.split('\n') if link.strip() and '/spreadsheets/' in link]
            
            st.markdown("---")
            st.markdown("**🔍 Debug Info**")
            st.code(user_drive_link[:50] + "..." if len(user_drive_link) > 50 else user_drive_link or "No link", language=None)
            st.markdown(f"Folder ID: `{folder_id or 'None'}`")
            st.markdown(f"Sheet ID: `{sheet_id or 'None'}`")
    
    # Load data
    if not user_drive_link:
        st.sidebar.error("📁 Drive link missing")
        st.info("📁 No Drive link found. Please switch to Manual Upload.")
        st.stop()
    
    if sheet_id:
        # Direct sheet link
        if 'gdrive_loaded' not in st.session_state:
            clear_debug_log()
            with st.spinner("Loading Google Sheet..."):
                temp_df = load_google_sheet_by_id(sheet_id)
                if temp_df is not None and not temp_df.empty:
                    dfs = [temp_df]
                    file_info = [{"name": "Google Sheet", "rows": len(temp_df), "cols": len(temp_df.columns), "type": "gsheet"}]
                    st.session_state['gdrive_loaded'] = True
                    st.session_state['gdrive_dfs'] = dfs
                    st.session_state['file_info'] = file_info
                else:
                    st.error("❌ Could not load Google Sheet. Make sure it's publicly shared.")
                    st.stop()
        
        if 'gdrive_dfs' in st.session_state:
            dfs = st.session_state['gdrive_dfs']
            file_info = st.session_state.get('file_info', [])
    
    elif folder_id:
        # Folder link
        if 'gdrive_loaded' not in st.session_state:
            clear_debug_log()
            with st.spinner("🔍 Scanning Google Drive..."):
                dfs, file_info = load_data_from_drive(folder_id, manual_sheet_links if manual_sheet_links else None)
                
                if dfs:
                    st.session_state['gdrive_loaded'] = True
                    st.session_state['gdrive_dfs'] = dfs
                    st.session_state['file_info'] = file_info
                else:
                    st.error("""
                    📂 **No data found**
                    
                    **Try these steps:**
                    1. Open your Google Sheet → Share → Anyone with link → Viewer
                    2. Copy the Sheet URL
                    3. Go to ⚙️ Advanced Options → Paste the URL
                    4. Click 🔄 Sync Data
                    
                    📞 Contact Mahendra: 7627068716
                    """)
                    st.stop()
        
        if 'gdrive_dfs' in st.session_state:
            dfs = st.session_state['gdrive_dfs']
            file_info = st.session_state.get('file_info', [])
    else:
        st.error("⚠️ Invalid link format")
        st.stop()

if not dfs:
    st.info("📁 Click '🔄 Sync Data' to load, or switch to Manual Upload")
    st.stop()

df = pd.concat(dfs, ignore_index=True)

# =========================================================
# DATA PREP
# =========================================================
date_col = detect(df, ["date"])
time_col = detect(df, ["time"])
amt_col = detect(df, ["amount"])
cat_col = detect(df, ["category"])
sub_col = detect(df, ["sub-category", "sub category", "subcategory", "sub_category"])
desc_col = detect(df, ["merchant", "person", "description", "name"])
type_col = detect(df, ["paid", "received", "type"])

detection_info = {
    "Date Column": date_col,
    "Time Column": time_col,
    "Amount Column": amt_col,
    "Category Column": cat_col,
    "Sub-category Column": sub_col,
    "Description Column": desc_col,
    "Type Column": type_col
}

if not date_col:
    st.error("❌ Could not find a Date column.")
    st.write("**Available columns:**", list(df.columns))
    st.stop()

if not amt_col:
    st.error("❌ Could not find an Amount column.")
    st.write("**Available columns:**", list(df.columns))
    st.stop()

try:
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
except Exception as e:
    st.error(f"Error parsing dates: {e}")
    st.stop()

df[amt_col] = pd.to_numeric(df[amt_col], errors="coerce").fillna(0)

if time_col:
    df["Hour"] = df[time_col].apply(parse_time_to_hour)
else:
    df["Hour"] = 12

df["Category"] = df[cat_col].fillna("Uncategorized") if cat_col else "Uncategorized"
df["Sub Category"] = df[sub_col].fillna("Uncategorized") if sub_col else "Uncategorized"
df["Description"] = df[desc_col].fillna("Unknown") if desc_col else "Unknown"
df["Transaction Type"] = df[type_col].fillna("Paid") if type_col else "Paid"

df["Month"] = df[date_col].dt.to_period("M").astype(str)
df["Weekday"] = df[date_col].dt.day_name()
df["WeekType"] = df.apply(lambda row: determine_weekend(row, date_col), axis=1)
df["TimePeriod"] = df["Hour"].apply(get_time_period)

df = df.dropna(subset=[date_col])

if df.empty:
    st.error("❌ No valid data found.")
    st.stop()

data_quality_score, data_issues = get_data_quality_score(df, date_col, amt_col, cat_col, time_col)

# =========================================================
# MONTH FILTER - IN SIDEBAR (AFTER DATA LOAD)
# =========================================================
months = sorted(df["Month"].unique())

if not months:
    st.error("❌ No valid months found.")
    st.stop()

with st.sidebar:
    st.markdown("---")
    st.markdown("### 📅 Select Month")
    selected_month = st.selectbox(
        "Month",
        months,
        index=len(months)-1,
        format_func=format_month,
        key="month_selector",
        label_visibility="collapsed"
    )
    
    # Show data summary
    st.markdown("---")
    st.markdown("### 📊 Data Summary")
    total_rows = sum(f['rows'] for f in file_info) if file_info else len(df)
    st.markdown(f"**{len(file_info)} source(s)** • **{total_rows:,} rows**")

month_df = df[df["Month"] == selected_month]
non_bill_df = month_df[month_df["Category"] != "Bill Payment"]

current_month_idx = months.index(selected_month)
previous_month_df = df[df["Month"] == months[current_month_idx - 1]] if current_month_idx > 0 else pd.DataFrame()

# =========================================================
# TABS
# =========================================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈 Trends",
    "📅 Monthly View",
    "💡 Insights",
    "🧠 Intelligence",
    "📤 Export",
    "🔧 Admin"
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
    
    k1,k2,k3,k4 = st.columns(4)
    
    total_spend = month_df[amt_col].sum()
    excl_bills = non_bill_df[amt_col].sum()
    daily_avg = non_bill_df.groupby(date_col)[amt_col].sum().mean() if not non_bill_df.empty else 0
    
    if not non_bill_df.empty and len(non_bill_df.groupby("Category")) > 0:
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
    
    left, right = st.columns([1.4, 1])
    
    with left:
        st.markdown("#### 📉 Budget Burn-down")
        budget = st.number_input("Monthly Budget", value=30000, step=1000, key="budget_input")
        
        try:
            year = int(selected_month.split("-")[0])
            month_num = int(selected_month.split("-")[1])
            days = calendar.monthrange(year, month_num)[1]
            
            if not non_bill_df.empty:
                daily = (
                    non_bill_df.groupby(date_col)[amt_col]
                    .sum()
                    .reindex(pd.date_range(month_df[date_col].min(), month_df[date_col].max()), fill_value=0)
                    .cumsum()
                    .reset_index()
                )
                daily.columns = ["Date", "Actual"]
                ideal = np.linspace(0, budget, days)
                
                fig = px.line(daily, x="Date", y="Actual", template="plotly_dark")
                fig.add_scatter(x=pd.date_range(daily["Date"].min(), periods=days), y=ideal, name="Ideal")
                fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
                st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
        except:
            st.info("No data for burn-down chart")
    
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
                
                fig = px.treemap(chart_df, path=["Category Label", "Sub Category"], values=amt_col, template="plotly_dark")
                fig.update_traces(textinfo="label+value+percent root", texttemplate="%{label}<br>₹%{value:,.0f}<br>%{percentRoot:.1%}")
                fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
                st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
    
    st.markdown("#### 📆 Spending Pattern")
    c1, c2 = st.columns(2)
    
    with c1:
        cat_data = month_df.groupby("Category")[amt_col].sum().reset_index()
        fig = px.bar(cat_data, x="Category", y=amt_col, template="plotly_dark", title="Category vs Amount")
        fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
        st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
    
    with c2:
        day_data = month_df.groupby(date_col)[amt_col].sum().reset_index()
        fig = px.bar(day_data, x=date_col, y=amt_col, template="plotly_dark", title="Amount vs Day")
        fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
        st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
    
    st.markdown("#### ⏰ Time-based Analysis")
    h1, h2 = st.columns(2)
    
    with h1:
        period_order = ["Morning (5AM-12PM)", "Afternoon (12PM-5PM)", "Evening (5PM-9PM)", "Night (9PM-5AM)"]
        period_spend = month_df.groupby("TimePeriod")[amt_col].sum().reindex(period_order).fillna(0).reset_index()
        
        fig = px.bar(period_spend, x="TimePeriod", y=amt_col, template="plotly_dark",
                    title="Spending by Time of Day", color="TimePeriod",
                    color_discrete_sequence=["#FFD700", "#FF8C00", "#FF4500", "#4169E1"])
        fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True, showlegend=False)
        st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
    
    with h2:
        hourly_spend = month_df.groupby("Hour")[amt_col].sum().reset_index()
        all_hours = pd.DataFrame({"Hour": range(24)})
        hourly_spend = all_hours.merge(hourly_spend, on="Hour", how="left").fillna(0)
        hourly_spend["Hour_Label"] = hourly_spend["Hour"].apply(lambda x: f"{int(x):02d}:00")
        
        fig = px.bar(hourly_spend, x="Hour_Label", y=amt_col, template="plotly_dark", title="Spending by Hour")
        fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
        fig.update_xaxes(tickangle=45)
        st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
    
    # =========================================================
    # WEEKDAY VS WEEKEND - WITH FIXED FILTERS
    # =========================================================
    st.markdown("### 📅 Weekday vs Weekend Behaviour")
    st.caption("*Weekend includes Friday after 7:00 PM, Saturday, and Sunday")
    
    # Initialize session state for filters if not exists
    if 'selected_metric' not in st.session_state:
        st.session_state['selected_metric'] = "Total Spend"
    
    f1, f2, f3 = st.columns([1.2, 1.2, 1])
    
    # Get all categories
    all_categories = sorted(month_df["Category"].unique().tolist())
    
    with f1:
        with st.popover("🏷️ Filter Category"):
            # Use multiselect instead of individual checkboxes
            selected_categories = st.multiselect(
                "Select Categories",
                options=all_categories,
                default=all_categories,
                key="category_filter_multiselect"
            )
    
    if not selected_categories:
        selected_categories = all_categories
    
    filtered = month_df[month_df["Category"].isin(selected_categories)]
    
    # Get subcategories based on filtered categories
    all_subcategories = sorted(filtered["Sub Category"].unique().tolist())
    
    with f2:
        with st.popover("📂 Filter Sub Category"):
            selected_subcategories = st.multiselect(
                "Select Sub Categories",
                options=all_subcategories,
                default=all_subcategories,
                key="subcategory_filter_multiselect"
            )
    
    if not selected_subcategories:
        selected_subcategories = all_subcategories
    
    filtered = filtered[filtered["Sub Category"].isin(selected_subcategories)]
    
    with f3:
        # Use session state to maintain selection
        metric = st.selectbox(
            "Metric",
            ["Total Spend", "Average Spend (per calendar day)"],
            key="metric_selector",
            index=0 if st.session_state.get('selected_metric', "Total Spend") == "Total Spend" else 1
        )
        st.session_state['selected_metric'] = metric
    
    if not filtered.empty:
        if metric == "Total Spend":
            day_metric = filtered.groupby("Weekday")[amt_col].sum()
        else:
            day_metric = filtered.groupby([date_col, "Weekday"])[amt_col].sum().reset_index().groupby("Weekday")[amt_col].mean()
        
        day_metric = day_metric.reindex(WEEK_ORDER).fillna(0).reset_index()
        
        c1, c2 = st.columns([2.2, 1])
        
        with c1:
            fig = px.bar(day_metric, x="Weekday", y=amt_col, template="plotly_dark", title=f"{metric} by Day")
            fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
            st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
        
        with c2:
            weektype_data = filtered.groupby("WeekType")[amt_col].mean().reset_index()
            fig = px.bar(weektype_data, x="WeekType", y=amt_col, template="plotly_dark", title="Weekday vs Weekend")
            fig.update_layout(xaxis_fixedrange=True, yaxis_fixedrange=True)
            st.plotly_chart(fig, use_container_width=True, config=get_chart_config())
    else:
        st.info("No data for selected filters")

# =========================================================
# TAB 3 — INSIGHTS
# =========================================================
with tab3:
    st.markdown("### 💡 Smart Insights")
    
    insights = generate_insights(month_df, previous_month_df, amt_col, date_col)
    
    if insights:
        for insight in insights:
            st.markdown(f"""<div class="insight-box"><div class="insight-text">{insight}</div></div>""", unsafe_allow_html=True)
    else:
        st.info("Not enough data for insights")

# =========================================================
# TAB 4 — INTELLIGENCE
# =========================================================
with tab4:
    st.markdown("### 🧠 Signals & Risks")
    
    st.markdown("#### 🔁 Recurring (Uncategorized)")
    uncategorized = df[df["Category"] == "Uncategorized"]
    
    if not uncategorized.empty:
        recurring = uncategorized.groupby("Description")[amt_col].agg(["count", "mean", "std"]).reset_index()
        recurring["std"] = recurring["std"].fillna(0)
        recurring = recurring[(recurring["count"] >= 3) & ((recurring["std"] / recurring["mean"].replace(0, 1)) < 0.1)]
        
        if not recurring.empty:
            st.dataframe(recurring, use_container_width=True)
        else:
            st.info("No recurring uncategorized transactions")
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
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download_button"
    )

# =========================================================
# TAB 6 — ADMIN
# =========================================================
with tab6:
    st.markdown("### 🔧 Admin Panel")
    
    # Debug Log
    st.markdown("#### 📜 Backend Debug Log")
    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        if st.button("🗑️ Clear Log", key="clear_log_btn"):
            clear_debug_log()
            st.rerun()
    
    if st.session_state.get('debug_log'):
        log_container = st.container()
        with log_container:
            for log in st.session_state['debug_log'][-50:]:  # Show last 50 logs
                log_class = f"log-{log['level']}"
                st.markdown(f"""<div class="{log_class}"><strong>[{log['time']}]</strong> {log['message']}</div>""", unsafe_allow_html=True)
    else:
        st.info("No logs yet. Click 'Sync Data' to generate logs.")
    
    st.markdown("---")
    
    # Data Quality
    st.markdown("#### 📊 Data Quality Score")
    score_color = "#10b981" if data_quality_score >= 80 else "#f59e0b" if data_quality_score >= 60 else "#ef4444"
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {score_color}20, {score_color}40); 
                border: 2px solid {score_color}; border-radius: 16px; padding: 24px; text-align: center;">
        <div style="font-size: 3rem; font-weight: 800; color: {score_color};">{data_quality_score}/100</div>
    </div>
    """, unsafe_allow_html=True)
    
    if data_issues:
        for issue in data_issues:
            st.markdown(f"""<div class="warning-card">{issue}</div>""", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Column Detection
    st.markdown("#### 🔍 Column Detection")
    col1, col2 = st.columns(2)
    with col1:
        for col_name, detected in list(detection_info.items())[:4]:
            status = "✅" if detected else "❌"
            st.markdown(f"{status} **{col_name}:** `{detected or 'Not found'}`")
    with col2:
        for col_name, detected in list(detection_info.items())[4:]:
            status = "✅" if detected else "❌"
            st.markdown(f"{status} **{col_name}:** `{detected or 'Not found'}`")
    
    st.markdown("---")
    
    # Files Loaded
    st.markdown("#### 📁 Loaded Sources")
    if file_info:
        for f in file_info:
            st.markdown(f"📄 **{f['name']}** — {f['rows']} rows × {f['cols']} cols | `{f.get('type', 'unknown')}`")
    
    st.markdown("---")
    
    # Stats
    st.markdown("#### 📈 Statistics")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Transactions", f"{len(df):,}")
    c2.metric("Months", len(months))
    c3.metric("Categories", df['Category'].nunique())
    c4.metric("Total Spend", f"₹{df[amt_col].sum():,.0f}")
    
    st.markdown("---")
    
    # Data Preview
    st.markdown("#### 👀 Data Preview (First 10 rows)")
    st.dataframe(df.head(10), use_container_width=True)

st.markdown("---")
st.markdown("<div class='subtle'>Built for thinking, not panic.</div>", unsafe_allow_html=True)
