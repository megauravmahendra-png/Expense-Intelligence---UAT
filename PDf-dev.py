import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from io import BytesIO
import calendar
import gdown
from pathlib import Path
import shutil
import PyPDF2
import re
from datetime import datetime

# Try importing fuzzywuzzy, warn if missing
try:
    from fuzzywuzzy import fuzz
except ImportError:
    st.error("⚠️ 'fuzzywuzzy' library is missing. Please add 'fuzzywuzzy' and 'python-Levenshtein' to your requirements.txt")
    fuzz = None

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
# PDF EXTRACTION FUNCTIONS
# =========================================================
def extract_gpay_transactions_from_pdf(pdf_file):
    """
    Extract transaction data from GPay PDF statement.
    Handles 'Date', 'Description', 'Amount', 'Transaction ID', 'Bank', and 'Time'.
    Explicitly IGNORES 'Self transfer' transactions.
    """
    
    # Read PDF
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    all_text = ""
    
    for page in pdf_reader.pages:
        all_text += page.extract_text()
    
    transactions = []
    
    # --- REGEX PATTERN (Captures ALL 6 FIELDS) ---
    # 1. Date
    # 2. Type (Paid to/Received from/Self transfer to)
    # 3. Description (Name)
    # 4. Amount
    # 5. Transaction ID
    # 6. Bank Name (Optional)
    pattern = r'(\d{1,2}\s*[A-Za-z]{3},?\s*\d{4}).*?(Paid\s*to|Received\s*from|Self\s*transfer\s*to)\s+(.*?)(?:\s+UPI|\s+₹).*?₹\s*([\d,]+\.?\d*).*?UPI Transaction ID:\s*(\d+)(?:.*?Paid\s*(?:by|to)\s*(.*?))?'
    
    matches = re.findall(pattern, all_text, re.DOTALL | re.IGNORECASE)
    
    for match in matches:
        try:
            # Safety check: We expect 6 groups.
            if len(match) != 6:
                continue
                
            date_str, type_str, description_raw, amount_str, trans_id, bank_raw = match
            
            # --- 1. IGNORE SELF TRANSFERS ---
            full_check = (type_str + " " + description_raw).lower().replace(' ', '')
            if 'selftransfer' in full_check:
                continue
            
            # --- 2. PARSE DATE ---
            date_clean = re.sub(r'[^\d\w]', ' ', date_str).strip()
            date_clean = re.sub(r'\s+', ' ', date_clean)
            try:
                date = datetime.strptime(date_clean, '%d %b %Y')
            except ValueError:
                continue # Skip if date fails

            # --- 3. PARSE AMOUNT ---
            amount_clean = amount_str.replace(',', '').strip()
            amount = float(amount_clean)
            if amount <= 0:
                continue

            # --- 4. CLEAN DESCRIPTION ---
            description = description_raw.strip()
            # Clean up common artifacts
            description = description.split('UPI Transaction')[0].strip()
            description = re.sub(r'\s+', ' ', description)
            
            if len(description) < 2:
                continue
                
            # Filter out Rewards
            skip_keywords = ['google pay rewards', 'googlepayrewards', 'better luck next time']
            if any(keyword in description.lower().replace(' ', '') for keyword in skip_keywords):
                continue

            # --- 5. DETERMINE TYPE ---
            is_received = 'received' in type_str.lower()
            transaction_type = 'Received' if is_received else 'Sent'
            
            # --- 6. CLEAN BANK ---
            bank = bank_raw.strip() if bank_raw else "Unknown"
            
            transactions.append({
                'Date': date,
                'Description': description,
                'Amount': amount,
                'Type': transaction_type,
                'Transaction ID': trans_id,
                'Bank': bank
            })
            
        except Exception as e:
            continue
    
    # Create DataFrame
    df = pd.DataFrame(transactions)
    
    # Remove duplicates
    if not df.empty:
        if 'Transaction ID' in df.columns:
            df = df.drop_duplicates(subset=['Transaction ID'], keep='first')
        else:
            df = df.drop_duplicates(subset=['Date', 'Description', 'Amount'], keep='first')
        df = df.sort_values('Date')
    
    return df

def categorize_transaction(description, amount, logic_sheet_df):
    """Categorize transaction using smart fuzzy matching"""
    
    if not logic_sheet_df.empty and fuzz is not None:
        best_match_score = 0
        best_match_row = None
        desc_search = str(description).lower()
        
        for idx, row in logic_sheet_df.iterrows():
            merchant = str(row.get('Merchant', '')).strip().lower()
            if not merchant:
                continue
            
            # Fuzzy Match using Token Set Ratio (Smartest for partial matches)
            score = fuzz.token_set_ratio(desc_search, merchant)
            
            if score > best_match_score:
                best_match_score = score
                best_match_row = row
        
        # Threshold: 70
        if best_match_score >= 70 and best_match_row is not None:
            sub_cat = str(best_match_row.get('Subcategory', 'Yet to Name'))
            return (
                str(best_match_row.get('Category', 'Misc')),
                sub_cat
            )
    
    # Fallback Rules
    desc_lower = description.lower()
    transport_keywords = ['rapido', 'auto', 'ola', 'uber', 'metro', 'mmrda', 'railway', 'irctc', 'train', 'bus']
    
    if (15 <= amount <= 50) or any(kw in desc_lower for kw in transport_keywords):
        if any(kw in desc_lower for kw in ['metro', 'mmrda']):
            return ('Transport', 'Metro')
        elif any(kw in desc_lower for kw in ['railway', 'irctc', 'train']):
            return ('Transport', 'Train')
        else:
            return ('Transport', 'Auto')
    
    return ('Misc', 'Yet to Name')

def process_pdf_data(pdf_files, logic_sheet_df):
    """Process multiple PDF files and categorize transactions"""
    all_transactions = []
    
    for pdf_path in pdf_files:
        try:
            with open(pdf_path, 'rb') as f:
                df = extract_gpay_transactions_from_pdf(f)
                if not df.empty:
                    all_transactions.append(df)
        except Exception as e:
            st.warning(f"Could not process {Path(pdf_path).name}")
    
    if not all_transactions:
        return pd.DataFrame()
    
    combined_df = pd.concat(all_transactions, ignore_index=True)
    
    if 'Transaction ID' in combined_df.columns:
        combined_df = combined_df.drop_duplicates(subset=['Transaction ID'], keep='first')
    
    # Categorize
    combined_df['Category'] = 'Misc'
    combined_df['Sub Category'] = 'Yet to Name'
    
    for idx, row in combined_df.iterrows():
        # Tag Income but EXCLUDE later
        if row['Type'] == 'Received':
            combined_df.at[idx, 'Category'] = 'Income'
            combined_df.at[idx, 'Sub Category'] = 'Received'
        else:
            category, subcategory = categorize_transaction(
                row['Description'], 
                row['Amount'], 
                logic_sheet_df
            )
            combined_df.at[idx, 'Category'] = category
            combined_df.at[idx, 'Sub Category'] = subcategory
    
    # FILTER: Keep only 'Sent' transactions (Expenses)
    expense_df = combined_df[combined_df['Type'] == 'Sent'].copy()
    expense_df = expense_df.drop('Type', axis=1)
    
    return expense_df

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
    st.markdown("""
    <style>
    .login-container { max-width: 450px; margin: 100px auto; padding: 50px 40px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 24px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }
    .login-title { font-size: 2.5rem; font-weight: 800; text-align: center; color: white; margin-bottom: 10px; }
    .login-subtitle { text-align: center; color: rgba(255,255,255,0.9); margin-bottom: 40px; font-size: 1rem; }
    .stTextInput > div > div > input { background: rgba(255,255,255,0.2); border: 2px solid rgba(255,255,255,0.3); border-radius: 12px; color: white; font-size: 1rem; padding: 12px 16px; }
    .stTextInput > label { color: white !important; font-weight: 600; font-size: 0.9rem; }
    .login-button > button { width: 100%; background: white; color: #667eea; font-weight: 700; font-size: 1.1rem; padding: 14px; border-radius: 12px; border: none; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-container"><div class="login-title">💳 Expense Intelligence</div><div class="login-subtitle">Designed for awareness, not anxiety</div>', unsafe_allow_html=True)
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("🔐 Login", use_container_width=True):
            if username and password:
                creds = load_credentials()
                if creds is not None:
                    user_match = creds[(creds['User Name'].str.strip() == username.strip()) & (creds['Password'].astype(str).str.strip() == password.strip())]
                    if not user_match.empty:
                        row = user_match.iloc[0]
                        st.session_state.update({
                            'authenticated': True,
                            'username': username,
                            'excel_drive_link': str(row.get('Excel Google Drive Data Link', '')).strip(),
                            'pdf_drive_link': str(row.get('PDF Google Drive Data Link', '')).strip(),
                            'logic_sheet_link': str(row.get('Logic Sheet', '')).strip()
                        })
                        st.rerun()
                    else:
                        st.error("❌ Incorrect username or password")
            else:
                st.warning("⚠️ Please enter both username and password")
        st.markdown('</div>', unsafe_allow_html=True)

if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    login_page()
    st.stop()

# =========================================================
# UI THEME
# =========================================================
st.markdown("""
<style>
body { background:#0b1220; color:#e5e7eb; }
.card { background:#111827; border:1px solid #1f2937; border-radius:16px; padding:18px; transition:0.25s; }
.card:hover { transform:translateY(-4px); box-shadow:0 10px 24px rgba(0,0,0,0.35); }
.kpi-title { font-size:0.7rem; letter-spacing:0.08em; color:#9ca3af; text-transform:uppercase; }
.kpi-value { font-size:1.8rem; font-weight:700; }
.insight-box { background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); border-radius: 16px; padding: 20px; margin: 10px 0; color: white; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# HEADER
# =========================================================
col1, col2 = st.columns([6, 1])
with col1:
    st.markdown("## 💳 Expense Intelligence - UAT")
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
            if k.lower() in c.lower(): return c
    return None

def format_month(m):
    return pd.to_datetime(m + "-01").strftime("%B %y")

def get_chart_config():
    return {'displayModeBar': False}

def download_from_gdrive_folder(folder_id):
    temp_dir = Path("temp_data")
    if temp_dir.exists(): shutil.rmtree(temp_dir)
    temp_dir.mkdir(exist_ok=True)
    try:
        gdown.download_folder(f"https://drive.google.com/drive/folders/{folder_id}", output=str(temp_dir), quiet=False, use_cookies=False, remaining_ok=True)
        return temp_dir
    except: return None

def extract_folder_id_from_link(link):
    if not link or pd.isna(link): return None
    link = str(link).strip()
    if '/folders/' in link: return link.split('/folders/')[1].split('?')[0].strip()
    return link if len(link) > 20 and '/' not in link else None

def load_logic_sheet(link):
    if not link or pd.isna(link): return pd.DataFrame()
    try:
        sheet_id = link.split('/d/')[1].split('/')[0] if '/d/' in link else link
        gid_param = f"&gid={link.split('gid=')[1].split('&')[0].split('#')[0]}" if 'gid=' in link else ""
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv{gid_param}"
        df = pd.read_csv(url)
        
        if df.empty: return df
        clean_cols = {c.lower().replace(' ', '').replace('-', '').replace('_', ''): c for c in df.columns}
        mapping = {
            'Merchant': ['merchant', 'name', 'party', 'description'],
            'Category': ['category', 'cat', 'type'],
            'Subcategory': ['subcategory', 'sub-category', 'sub category']
        }
        rename_dict = {}
        for std, vars_ in mapping.items():
            for v in vars_:
                clean_v = v.replace(' ', '')
                if clean_v in clean_cols:
                    rename_dict[clean_cols[clean_v]] = std
                    break
        if rename_dict: df = df.rename(columns=rename_dict)
        
        if 'Merchant' in df.columns: df['Merchant'] = df['Merchant'].astype(str)
        return df
    except: return pd.DataFrame()

def generate_insights(current, prev, amt_col):
    insights = []
    curr_tot = current[amt_col].sum()
    prev_tot = prev[amt_col].sum() if not prev.empty else 0
    
    if prev_tot > 0:
        pct = ((curr_tot - prev_tot) / prev_tot) * 100
        if pct > 10: insights.append(f"💸 Spending increased by {pct:.1f}% (₹{curr_tot:,.0f} vs ₹{prev_tot:,.0f})")
        elif pct < -10: insights.append(f"✅ You saved {abs(pct):.1f}% (₹{curr_tot:,.0f} vs ₹{prev_tot:,.0f})")
    
    top = current.nlargest(1, amt_col).iloc[0] if not current.empty else None
    if top is not None: insights.append(f"🔝 Largest expense: ₹{top[amt_col]:,.0f} on {top['Description']}")
    
    return insights

WEEK_ORDER = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

# =========================================================
# DATA LOADING
# =========================================================
with st.sidebar:
    st.markdown("### 📂 Data Source")
    data_mode = st.radio("", ["📊 Excel/CSV Database", "📄 PDF Database"])

logic_sheet_df = load_logic_sheet(st.session_state.get('logic_sheet_link', ''))
dfs = []

if data_mode == "📊 Excel/CSV Database":
    fid = extract_folder_id_from_link(st.session_state.get('excel_drive_link', ''))
    if fid:
        if st.sidebar.button("🔄 Sync Now") or 'excel_loaded' not in st.session_state:
            with st.spinner("Syncing..."):
                td = download_from_gdrive_folder(fid)
                if td:
                    files = list(td.glob("*.xlsx")) + list(td.glob("*.csv"))
                    for f in files:
                        try: dfs.append(pd.read_csv(f) if f.suffix=='.csv' else pd.read_excel(f))
                        except: pass
                    if dfs:
                        st.session_state['excel_loaded'] = True
                        st.session_state['excel_dfs'] = dfs
                        st.sidebar.success(f"Loaded {len(dfs)} files")
    if 'excel_dfs' in st.session_state: dfs = st.session_state['excel_dfs']

else:
    fid = extract_folder_id_from_link(st.session_state.get('pdf_drive_link', ''))
    if fid:
        if st.sidebar.button("🔄 Sync Now") or 'pdf_loaded' not in st.session_state:
            with st.spinner("Processing PDFs..."):
                td = download_from_gdrive_folder(fid)
                if td:
                    files = list(td.glob("*.pdf"))
                    pdf_df = process_pdf_data(files, logic_sheet_df)
                    if not pdf_df.empty:
                        dfs = [pdf_df]
                        st.session_state['pdf_loaded'] = True
                        st.session_state['pdf_dfs'] = dfs
                        st.sidebar.success(f"Processed {len(files)} PDFs")
    if 'pdf_dfs' in st.session_state: dfs = st.session_state['pdf_dfs']

if not dfs:
    st.info("Please Click 'Sync Now' in the sidebar to load data.")
    st.stop()

df = pd.concat(dfs, ignore_index=True)

# =========================================================
# DASHBOARD
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

months = sorted(df["Month"].unique())
selected_month = st.sidebar.selectbox("Month", months, index=len(months)-1, format_func=format_month)

month_df = df[df["Month"] == selected_month]
non_bill_df = month_df[month_df["Category"] != "Bill Payment"]
prev_df = df[df["Month"] == months[months.index(selected_month)-1]] if months.index(selected_month)>0 else pd.DataFrame()

tab1, tab2, tab3, tab4 = st.tabs(["📈 Trends", "📅 Monthly", "💡 Insights", "📤 Export"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        monthly = df.groupby("Month")[amt_col].sum().reset_index()
        st.plotly_chart(px.line(monthly, x="Month", y=amt_col, template="plotly_dark", title="Total Monthly Spend"), use_container_width=True)
    with c2:
        cat_trend = df.groupby(["Month","Category"])[amt_col].sum().reset_index()
        st.plotly_chart(px.line(cat_trend, x="Month", y=amt_col, color="Category", template="plotly_dark", title="Category Trend"), use_container_width=True)

with tab2:
    k1,k2,k3 = st.columns(3)
    k1.metric("Total Spend", f"₹{month_df[amt_col].sum():,.0f}")
    k2.metric("Daily Avg", f"₹{non_bill_df.groupby(date_col)[amt_col].sum().mean():,.0f}")
    k3.metric("Top Category", non_bill_df.groupby("Category")[amt_col].sum().idxmax() if not non_bill_df.empty else "-")
    
    c1, c2 = st.columns([1.5, 1])
    with c1:
        budget = st.number_input("Budget", value=30000, step=1000)
        daily = non_bill_df.groupby(date_col)[amt_col].sum().cumsum().reset_index()
        fig = px.line(daily, x=date_col, y=amt_col, template="plotly_dark", title="Budget Burndown")
        fig.add_hline(y=budget, line_dash="dot", annotation_text="Budget")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.plotly_chart(px.pie(month_df, names="Category", values=amt_col, template="plotly_dark", title="Composition"), use_container_width=True)

with tab3:
    for i in generate_insights(month_df, prev_df, amt_col):
        st.markdown(f"<div class='insight-box'>{i}</div>", unsafe_allow_html=True)

with tab4:
    buf = BytesIO()
    df.to_excel(buf, index=False)
    st.download_button("Download Excel", data=buf.getvalue(), file_name="expenses.xlsx")
