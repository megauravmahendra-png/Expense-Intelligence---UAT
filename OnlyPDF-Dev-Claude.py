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
    
    pattern = r'(\d{1,2}\s*[A-Za-z]{3},?\s*\d{4}).*?(Paid\s*to|Received\s*from|Self\s*transfer\s*to)\s+(.*?)(?:\s+UPI|\s+₹).*?₹\s*([\d,]+\.?\d*).*?UPI Transaction ID:\s*(\d+)(?:.*?Paid\s*(?:by|to)\s*(.*?))?'
    
    matches = re.findall(pattern, all_text, re.DOTALL | re.IGNORECASE)
    
    for match in matches:
        try:
            date_str, type_str, description_raw, amount_str, trans_id, bank_raw = match
            
            full_check = (type_str + " " + description_raw).lower().replace(' ', '')
            if 'selftransfer' in full_check:
                continue
            
            date_clean = re.sub(r'[^\d\w]', ' ', date_str).strip()
            date_clean = re.sub(r'\s+', ' ', date_clean)
            try:
                date = datetime.strptime(date_clean, '%d %b %Y')
            except ValueError:
                date = datetime.strptime(date_clean, '%d %b %Y')
            
            amount_clean = amount_str.replace(',', '').strip()
            amount = float(amount_clean)
            if amount <= 0:
                continue
            
            description = description_raw.strip()
            description = description.split('UPI Transaction')[0].strip()
            description = re.sub(r'\s+', ' ', description)
            
            if len(description) < 2:
                continue
                
            skip_keywords = ['google pay rewards', 'googlepayrewards', 'better luck next time']
            if any(keyword in description.lower().replace(' ', '') for keyword in skip_keywords):
                continue
            
            is_received = 'received' in type_str.lower()
            transaction_type = 'Received' if is_received else 'Sent'
            
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
    
    df = pd.DataFrame(transactions)
    
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
            
            score = fuzz.token_set_ratio(desc_search, merchant)
            
            if score > best_match_score:
                best_match_score = score
                best_match_row = row
        
        if best_match_score >= 70 and best_match_row is not None:
            sub_cat = str(best_match_row.get('Subcategory', 'Yet to Name'))
            return (
                str(best_match_row.get('Category', 'Misc')),
                sub_cat
            )
    
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
    
    combined_df['Category'] = 'Misc'
    combined_df['Sub Category'] = 'Yet to Name'
    
    for idx, row in combined_df.iterrows():
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
    
    expense_df = combined_df[combined_df['Type'] == 'Sent'].copy()
    expense_df = expense_df.drop('Type', axis=1)
    
    return expense_df


# =========================================================
# HELPER FUNCTIONS
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
    temp_dir = Path("temp_data")
    
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    
    temp_dir.mkdir(exist_ok=True)
    folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
    
    try:
        gdown.download_folder(folder_url, output=str(temp_dir), quiet=False, use_cookies=False, remaining_ok=True)
        return temp_dir
    except Exception as e:
        return None


def extract_folder_id_from_link(link):
    if not link or pd.isna(link):
        return None
    
    link = str(link).strip()
    
    if '/folders/' in link:
        try:
            folder_id = link.split('/folders/')[1].split('?')[0].strip()
            return folder_id
        except:
            return None
    
    if len(link) > 20 and '/' not in link:
        return link
    
    return None


def load_logic_sheet(link):
    """Load categorization logic with SMART COLUMN DETECTION and GID support"""
    if not link or pd.isna(link):
        st.sidebar.warning("⚠️ Logic Sheet Link is missing")
        return pd.DataFrame()
    
    try:
        if '/d/' in link:
            sheet_id = link.split('/d/')[1].split('/')[0]
        else:
            sheet_id = link
            
        gid_param = ""
        if 'gid=' in link:
            try:
                gid = link.split('gid=')[1].split('&')[0].split('#')[0]
                gid_param = f"&gid={gid}"
            except:
                pass
        
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv{gid_param}"
        
        df = pd.read_csv(url)
        
        if df.empty:
            st.sidebar.warning("⚠️ Logic Sheet downloaded but is empty.")
            return df
            
        clean_cols = {c.lower().replace(' ', '').replace('-', '').replace('_', ''): c for c in df.columns}
        
        mapping = {
            'Merchant': ['merchant', 'name', 'party', 'description', 'payee'],
            'Category': ['category', 'cat', 'type'],
            'Subcategory': ['subcategory', 'sub-category', 'sub category', 'sub']
        }
        
        rename_dict = {}
        
        for standard, variations in mapping.items():
            for var in variations:
                clean_var = var.replace(' ', '').replace('-', '')
                if clean_var in clean_cols:
                    actual_col_name = clean_cols[clean_var]
                    rename_dict[actual_col_name] = standard
                    break
        
        if rename_dict:
            df = df.rename(columns=rename_dict)
        
        required_cols = ['Merchant', 'Category']
        found_cols = [c for c in required_cols if c in df.columns]
        
        with st.sidebar.expander("🐞 Logic Sheet Status", expanded=True):
            if len(found_cols) == len(required_cols):
                st.success(f"✅ Loaded {len(df)} rules")
                st.markdown("---")
                st.write("🔎 **Test Your Logic**")
                test_txt = st.text_input("Type a merchant name...", placeholder="e.g. Swiggy")
                if test_txt and fuzz:
                    best_s = 0
                    best_r = None
                    for _, r in df.iterrows():
                        mer = str(r['Merchant']).lower()
                        sc = fuzz.token_set_ratio(test_txt.lower(), mer)
                        if sc > best_s:
                            best_s = sc
                            best_r = r
                    
                    st.write(f"Best Match: **{best_r['Merchant']}**")
                    st.write(f"Score: **{best_s}**")
                    if best_s >= 70:
                        st.success(f"✅ Matched: {best_r['Category']}")
                    else:
                        st.error("❌ No Match (<70)")
            else:
                st.error("❌ Missing Columns")
                st.write(f"Found: {list(df.columns)}")
                st.write(f"Need: {required_cols}")
        
        if 'Merchant' in df.columns:
            df['Merchant'] = df['Merchant'].astype(str)
            
        return df
        
    except Exception as e:
        st.sidebar.error(f"❌ Logic Sheet Error: {str(e)[:100]}")
        return pd.DataFrame()


def generate_insights(current_month_df, previous_month_df, amt_col):
    insights = []
    
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
    
    current_cat = current_month_df.groupby("Category")[amt_col].sum()
    prev_cat = previous_month_df.groupby("Category")[amt_col].sum() if not previous_month_df.empty else pd.Series()
    
    for cat in current_cat.index:
        if cat in prev_cat.index and prev_cat[cat] > 0:
            cat_change = ((current_cat[cat] - prev_cat[cat]) / prev_cat[cat]) * 100
            if cat_change > 25:
                insights.append(f"⚠️ {cat} spending jumped by {cat_change:.1f}% (₹{current_cat[cat]:,.0f} vs ₹{prev_cat[cat]:,.0f})")
    
    weekend_avg = current_month_df[current_month_df["WeekType"] == "Weekend"].groupby(current_month_df[detect(current_month_df, ["date"])])[amt_col].sum().mean()
    weekday_avg = current_month_df[current_month_df["WeekType"] == "Weekday"].groupby(current_month_df[detect(current_month_df, ["date"])])[amt_col].sum().mean()
    
    if weekend_avg > weekday_avg * 1.3:
        insights.append(f"🎉 You spend {((weekend_avg/weekday_avg - 1) * 100):.0f}% more on weekends (₹{weekend_avg:,.0f} vs ₹{weekday_avg:,.0f} per day)")
    
    top_expense = current_month_df.nlargest(1, amt_col).iloc[0]
    insights.append(f"🔝 Your largest expense was ₹{top_expense[amt_col]:,.0f} on {top_expense['Description']}")
    
    return insights


WEEK_ORDER = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]


# =========================================================
# AUTHENTICATION FUNCTIONS
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


# =========================================================
# ADMIN DIAGNOSTIC PANEL
# =========================================================
def admin_diagnostic_panel():
    """
    Admin panel to diagnose all data sources and see what's working
    """
    st.markdown("""
    <style>
    .admin-header {
        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%);
        padding: 30px;
        border-radius: 16px;
        color: white;
        text-align: center;
        margin-bottom: 30px;
    }
    .status-box {
        background: #1f2937;
        border: 2px solid #374151;
        border-radius: 12px;
        padding: 20px;
        margin: 15px 0;
    }
    .status-good {
        border-color: #10b981;
        background: rgba(16, 185, 129, 0.1);
    }
    .status-warning {
        border-color: #f59e0b;
        background: rgba(245, 158, 11, 0.1);
    }
    .status-error {
        border-color: #ef4444;
        background: rgba(239, 68, 68, 0.1);
    }
    .diagnostic-title {
        font-size: 1.2rem;
        font-weight: 700;
        margin-bottom: 10px;
    }
    .code-block {
        background: #111827;
        padding: 15px;
        border-radius: 8px;
        font-family: 'Courier New', monospace;
        font-size: 0.85rem;
        overflow-x: auto;
        margin: 10px 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="admin-header">
        <h1>🔧 Admin Diagnostic Panel</h1>
        <p>Complete system health check and data flow monitoring</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Logout button
    col1, col2, col3 = st.columns([5, 1, 1])
    with col3:
        if st.button("🚪 Logout"):
            st.session_state['authenticated'] = False
            st.session_state['is_admin'] = False
            st.rerun()
    
    st.markdown("---")
    
    # =================================================================
    # 1. CREDENTIALS SHEET DIAGNOSTICS
    # =================================================================
    st.markdown("## 1️⃣ Credentials Sheet (Login Database)")
    
    with st.expander("📋 View Credentials Sheet", expanded=True):
        try:
            sheet_id = "1Im3g5NNm5962SUA-rd4WBr09n0nX2pLH5yHWc5BlXVA"
            url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
            
            st.markdown(f"**Sheet ID:** `{sheet_id}`")
            st.markdown(f"**URL:** [{url}]({url})")
            
            creds_df = pd.read_csv(url)
            
            status_class = "status-good"
            status_icon = "✅"
            status_msg = f"Successfully loaded {len(creds_df)} users"
            
            st.markdown(f"""
            <div class="status-box {status_class}">
                <div class="diagnostic-title">{status_icon} Status: WORKING</div>
                <p>{status_msg}</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("**📊 Columns Found:**")
            cols = list(creds_df.columns)
            st.write(cols)
            
            required_cols = ['User Name', 'Password', 'Excel Google Drive Data Link', 
                           'PDF Google Drive Data Link', 'Logic Sheet']
            missing_cols = [c for c in required_cols if c not in cols]
            
            if missing_cols:
                st.error(f"⚠️ Missing columns: {missing_cols}")
            else:
                st.success("✅ All required columns present")
            
            display_df = creds_df.copy()
            if 'Password' in display_df.columns:
                display_df['Password'] = display_df['Password'].apply(lambda x: '***' if pd.notna(x) else '')
            
            st.markdown("**👥 User Data:**")
            st.dataframe(display_df, use_container_width=True)
            
            st.markdown("**🔍 Data Completeness Check:**")
            for col in required_cols:
                if col in creds_df.columns:
                    empty_count = creds_df[col].isna().sum()
                    if empty_count > 0:
                        st.warning(f"⚠️ {col}: {empty_count} empty values")
                    else:
                        st.success(f"✅ {col}: All filled")
            
        except Exception as e:
            st.markdown(f"""
            <div class="status-box status-error">
                <div class="diagnostic-title">❌ Status: ERROR</div>
                <p>Failed to load credentials sheet</p>
                <div class="code-block">{str(e)}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # =================================================================
    # 2. USER DATA SOURCES
    # =================================================================
    st.markdown("## 2️⃣ User Data Sources")
    
    try:
        sheet_id = "1Im3g5NNm5962SUA-rd4WBr09n0nX2pLH5yHWc5BlXVA"
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        creds_df = pd.read_csv(url)
        
        usernames = creds_df['User Name'].dropna().tolist()
        selected_user = st.selectbox("👤 Select User to Diagnose", usernames)
        
        if selected_user:
            user_row = creds_df[creds_df['User Name'] == selected_user].iloc[0]
            
            excel_link = user_row.get('Excel Google Drive Data Link', '')
            pdf_link = user_row.get('PDF Google Drive Data Link', '')
            logic_link = user_row.get('Logic Sheet', '')
            
            # Test Excel Drive Link
            with st.expander("📊 Excel/CSV Drive Folder", expanded=True):
                st.markdown(f"**Link:** `{excel_link}`")
                
                if not excel_link or pd.isna(excel_link):
                    st.markdown("""
                    <div class="status-box status-warning">
                        <div class="diagnostic-title">⚠️ Status: EMPTY</div>
                        <p>No Excel Drive link configured for this user</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    folder_id = extract_folder_id_from_link(excel_link)
                    if folder_id:
                        st.success(f"✅ Valid Folder ID: `{folder_id}`")
                        st.markdown(f"**Drive URL:** [Open Folder](https://drive.google.com/drive/folders/{folder_id})")
                        
                        if st.button("🔍 Test Excel Folder Access", key="test_excel"):
                            with st.spinner("Testing folder access..."):
                                temp_dir = download_from_gdrive_folder(folder_id)
                                if temp_dir:
                                    files = list(temp_dir.glob("*.xlsx")) + list(temp_dir.glob("*.csv"))
                                    st.success(f"✅ Accessible! Found {len(files)} files")
                                    for f in files:
                                        st.write(f"- {f.name}")
                                    shutil.rmtree(temp_dir)
                                else:
                                    st.error("❌ Cannot access folder. Check permissions.")
                    else:
                        st.error("❌ Invalid folder link format")
            
            # Test PDF Drive Link
            with st.expander("📄 PDF Drive Folder", expanded=True):
                st.markdown(f"**Link:** `{pdf_link}`")
                
                if not pdf_link or pd.isna(pdf_link):
                    st.markdown("""
                    <div class="status-box status-warning">
                        <div class="diagnostic-title">⚠️ Status: EMPTY</div>
                        <p>No PDF Drive link configured for this user</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    folder_id = extract_folder_id_from_link(pdf_link)
                    if folder_id:
                        st.success(f"✅ Valid Folder ID: `{folder_id}`")
                        st.markdown(f"**Drive URL:** [Open Folder](https://drive.google.com/drive/folders/{folder_id})")
                        
                        if st.button("🔍 Test PDF Folder Access", key="test_pdf"):
                            with st.spinner("Testing folder access..."):
                                temp_dir = download_from_gdrive_folder(folder_id)
                                if temp_dir:
                                    files = list(temp_dir.glob("*.pdf"))
                                    st.success(f"✅ Accessible! Found {len(files)} PDFs")
                                    for f in files:
                                        st.write(f"- {f.name}")
                                    shutil.rmtree(temp_dir)
                                else:
                                    st.error("❌ Cannot access folder. Check permissions.")
                    else:
                        st.error("❌ Invalid folder link format")
            
            # Test Logic Sheet
            with st.expander("🧠 Logic Sheet (Categorization)", expanded=True):
                st.markdown(f"**Link:** `{logic_link}`")
                
                if not logic_link or pd.isna(logic_link):
                    st.markdown("""
                    <div class="status-box status-warning">
                        <div class="diagnostic-title">⚠️ Status: EMPTY</div>
                        <p>No Logic Sheet configured for this user</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    try:
                        if '/d/' in logic_link:
                            sheet_id = logic_link.split('/d/')[1].split('/')[0]
                        else:
                            sheet_id = logic_link
                        
                        gid_param = ""
                        if 'gid=' in logic_link:
                            gid = logic_link.split('gid=')[1].split('&')[0].split('#')[0]
                            gid_param = f"&gid={gid}"
                        
                        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv{gid_param}"
                        st.markdown(f"**Export URL:** [{url}]({url})")
                        
                        logic_df = pd.read_csv(url)
                        
                        st.markdown(f"""
                        <div class="status-box status-good">
                            <div class="diagnostic-title">✅ Status: WORKING</div>
                            <p>Successfully loaded {len(logic_df)} rules</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        st.markdown("**📊 Columns Found:**")
                        st.write(list(logic_df.columns))
                        
                        required = ['Merchant', 'Category']
                        found = [c for c in required if c in logic_df.columns]
                        
                        if len(found) == len(required):
                            st.success(f"✅ All required columns found: {found}")
                        else:
                            missing = [c for c in required if c not in logic_df.columns]
                            st.error(f"❌ Missing columns: {missing}")
                            st.info("💡 Tip: The app can auto-detect variations like 'Name', 'Merchant Name', etc.")
                        
                        st.markdown("**📄 Sample Rules:**")
                        st.dataframe(logic_df.head(10), use_container_width=True)
                        
                        if fuzz:
                            st.markdown("**🔍 Test Fuzzy Matching:**")
                            test_merchant = st.text_input("Enter a merchant name to test", 
                                                         placeholder="e.g., Swiggy")
                            if test_merchant:
                                best_score = 0
                                best_match = None
                                
                                for _, row in logic_df.iterrows():
                                    if 'Merchant' in row:
                                        merchant = str(row['Merchant']).lower()
                                        score = fuzz.token_set_ratio(test_merchant.lower(), merchant)
                                        if score > best_score:
                                            best_score = score
                                            best_match = row
                                
                                st.write(f"**Best Match:** {best_match.get('Merchant', 'N/A')}")
                                st.write(f"**Score:** {best_score}")
                                
                                if best_score >= 70:
                                    st.success(f"✅ Would categorize as: {best_match.get('Category', 'N/A')}")
                                else:
                                    st.warning("⚠️ Score too low (<70), would fallback to heuristics")
                        
                    except Exception as e:
                        st.markdown(f"""
                        <div class="status-box status-error">
                            <div class="diagnostic-title">❌ Status: ERROR</div>
                            <p>Failed to load Logic Sheet</p>
                            <div class="code-block">{str(e)}</div>
                        </div>
                        """, unsafe_allow_html=True)
    
    except Exception as e:
        st.error(f"Error loading users: {e}")
    
    st.markdown("---")
    
    # =================================================================
    # 3. SYSTEM CHECKS
    # =================================================================
    st.markdown("## 3️⃣ System Health Checks")
    
    with st.expander("🔧 Dependencies & Libraries", expanded=True):
        if fuzz:
            st.success("✅ fuzzywuzzy: Installed")
        else:
            st.error("❌ fuzzywuzzy: Missing - Add to requirements.txt")
        
        libs = {
            'pandas': pd,
            'numpy': np,
            'plotly': px,
            'PyPDF2': PyPDF2,
            'gdown': gdown
        }
        
        for lib_name, lib_obj in libs.items():
            st.success(f"✅ {lib_name}: Installed")
    
    with st.expander("📊 Session State", expanded=False):
        st.markdown("**Current Session Variables:**")
        st.json(dict(st.session_state))
    
    st.markdown("---")
    st.markdown("<div class='subtle' style='text-align: center;'>Admin Panel • Built for Debugging</div>", 
                unsafe_allow_html=True)


# =========================================================
# LOGIN PAGE (WITH ADMIN ACCESS)
# =========================================================
def login_page():
    """Beautiful login page with admin access"""
    
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
                # Check for admin credentials (hardcoded for security)
                if username.lower() == "admin" and password == "admin@123":
                    st.session_state['authenticated'] = True
                    st.session_state['is_admin'] = True
                    st.session_state['username'] = "Admin"
                    st.success("✅ Admin access granted!")
                    st.rerun()
                else:
                    # Check regular users
                    credentials = load_credentials()
                    
                    if credentials is not None:
                        user_match = credentials[
                            (credentials['User Name'].str.strip() == username.strip()) & 
                            (credentials['Password'].astype(str).str.strip() == password.strip())
                        ]
                        
                        if not user_match.empty:
                            excel_link = user_match.iloc[0].get('Excel Google Drive Data Link', '')
                            pdf_link = user_match.iloc[0].get('PDF Google Drive Data Link', '')
                            logic_link = user_match.iloc[0].get('Logic Sheet', '')
                            
                            st.session_state['authenticated'] = True
                            st.session_state['is_admin'] = False
                            st.session_state['username'] = username
                            st.session_state['excel_drive_link'] = str(excel_link).strip() if pd.notna(excel_link) else ''
                            st.session_state['pdf_drive_link'] = str(pdf_link).strip() if pd.notna(pdf_link) else ''
                            st.session_state['logic_sheet_link'] = str(logic_link).strip() if pd.notna(logic_link) else ''
                            st.rerun()
                        else:
                            st.error("❌ Incorrect username or password")
            else:
                st.warning("⚠️ Please enter both username and password")
        
        st.markdown('<div class="creator-text">Created by Gaurav Mahendra</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


# =========================================================
# AUTHENTICATION CHECK
# =========================================================
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if 'is_admin' not in st.session_state:
    st.session_state['is_admin'] = False

if not st.session_state['authenticated']:
    login_page()
    st.stop()

# If admin, show diagnostic panel instead of main app
if st.session_state.get('is_admin', False):
    admin_diagnostic_panel()
    st.stop()


# =========================================================
# UI THEME (AFTER LOGIN - FOR REGULAR USERS)
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
# DATA SOURCE TOGGLE
# =========================================================
with st.sidebar:
    st.markdown("### 📂 Data Source")
    data_mode = st.radio("", ["📊 Excel/CSV Database", "📄 PDF Database"])

# Load Logic Sheet (Smartly)
logic_sheet_df = load_logic_sheet(st.session_state.get('logic_sheet_link', ''))

dfs = []

if data_mode == "📊 Excel/CSV Database":
    # EXCEL/CSV MODE (Original logic)
    excel_link = st.session_state.get('excel_drive_link', '')
    
    if not excel_link:
        st.sidebar.error("📁 Excel Drive link is missing")
        st.stop()
    
    folder_id = extract_folder_id_from_link(excel_link)
    
    if not folder_id:
        st.sidebar.error("⚠️ Invalid Google Drive link")
        st.stop()
    
    st.sidebar.info(f"📁 Syncing Excel/CSV from Drive")
    
    if st.sidebar.button("🔄 Sync Now") or 'excel_loaded' not in st.session_state:
        with st.spinner("Downloading Excel/CSV files..."):
            temp_dir = download_from_gdrive_folder(folder_id)
            
            if temp_dir is None:
                st.error("⚠️ Could not access Google Drive folder")
                st.stop()
            
            excel_files = list(temp_dir.glob("*.xlsx")) + list(temp_dir.glob("*.csv"))
            excel_files = [f for f in excel_files if not f.name.startswith("~$")]
            
            if not excel_files:
                st.warning("📂 No Excel/CSV files found")
                st.stop()
            
            for f in excel_files:
                try:
                    if f.suffix == '.csv':
                        dfs.append(pd.read_csv(f))
                    else:
                        dfs.append(pd.read_excel(f))
                except Exception as e:
                    st.warning(f"Skipped: {f.name}")
            
            if dfs:
                st.session_state['excel_loaded'] = True
                st.session_state['excel_dfs'] = dfs
                st.sidebar.success(f"✅ Loaded {len(dfs)} files")
    
    if 'excel_dfs' in st.session_state:
        dfs = st.session_state['excel_dfs']

else:  # PDF MODE
    pdf_link = st.session_state.get('pdf_drive_link', '')
    
    if not pdf_link:
        st.sidebar.error("📁 PDF Drive link is missing")
        st.stop()
    
    folder_id = extract_folder_id_from_link(pdf_link)
    
    if not folder_id:
        st.sidebar.error("⚠️ Invalid Google Drive link")
        st.stop()
    
    st.sidebar.info(f"📄 Syncing PDFs from Drive")
    
    if st.sidebar.button("🔄 Sync Now") or 'pdf_loaded' not in st.session_state:
        with st.spinner("Downloading and processing PDFs..."):
            temp_dir = download_from_gdrive_folder(folder_id)
            
            if temp_dir is None:
                st.error("⚠️ Could not access Google Drive folder")
                st.stop()
            
            pdf_files = list(temp_dir.glob("*.pdf"))
            
            if not pdf_files:
                st.warning("📂 No PDF files found")
                st.stop()
            
            # Process all PDFs
            pdf_df = process_pdf_data(pdf_files, logic_sheet_df)
            
            if pdf_df.empty:
                st.error("❌ No transactions extracted from PDFs")
                st.stop()
            
            dfs = [pdf_df]
            st.session_state['pdf_loaded'] = True
            st.session_state['pdf_dfs'] = dfs
            st.sidebar.success(f"✅ Processed {len(pdf_files)} PDFs, {len(pdf_df)} transactions")
    
    if 'pdf_dfs' in st.session_state:
        dfs = st.session_state['pdf_dfs']

if not dfs:
    st.info("📁 Click 'Sync Now' to load data")
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
    
    k1,k2,k3,k4 = st.columns(4)
    kpis = [
        (k1,"Total Spend",month_df[amt_col].sum()),
        (k2,"Excl. Bills",non_bill_df[amt_col].sum()),
        (k3,"Daily Avg",non_bill_df.groupby(date_col)[amt_col].sum().mean()),
        (k4,"Top Category",non_bill_df.groupby("Category")[amt_col].sum().idxmax() if not non_bill_df.empty else "N/A")
    ]
    for col,title,val in kpis:
        display = f"₹{val:,.0f}" if isinstance(val,(int,float,np.number)) else str(val)
        col.markdown(
            f"<div class='card'><div class='kpi-title'>{title}</div><div class='kpi-value'>{display}</div></div>",
            unsafe_allow_html=True
        )
    
    left, right = st.columns([1.4, 1])
    
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
        daily.columns = ["Date", "Actual"]
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
        
        chart_df = month_df.copy()
        total_monthly = chart_df[amt_col].sum()
        
        cat_sums = chart_df.groupby("Category")[amt_col].sum()
        
        chart_df["Category Label"] = chart_df["Category"].apply(
            lambda x: f"{x} ({cat_sums.get(x, 0) / total_monthly:.1%})" if total_monthly > 0 else x
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
    
    if not recurring.empty:
        recurring = recurring[(recurring["count"]>=3)&((recurring["std"]/recurring["mean"])<0.1)]
        st.dataframe(recurring, use_container_width=True)
    else:
        st.write("No recurring uncategorized items found.")

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
