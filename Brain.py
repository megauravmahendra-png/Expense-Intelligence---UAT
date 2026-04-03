import streamlit as st
import pandas as pd
import re
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# ==========================================
# CONFIG
# ==========================================
SHEET_ID = "1NrNZ6adL8lsNRVFcpwmrTroHnem4I082Xv--_ruG43Y"

# ==========================================
# INIT SESSION
# ==========================================
if "brain_df" not in st.session_state:
    st.session_state.brain_df = None

# ==========================================
# GOOGLE SHEETS CONNECTION
# ==========================================
def connect_gsheet():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).sheet1
    return sheet

# ==========================================
# COLUMN DETECTION
# ==========================================
def detect_column(df, possible_names):
    for col in df.columns:
        for name in possible_names:
            if name.lower() in col.lower():
                return col
    return None

# ==========================================
# NORMALIZATION
# ==========================================
STOP_WORDS = [
    "private", "limited", "ltd", "pvt", "pvt ltd",
    "marketplace", "services", "solutions", "india"
]

def normalize_merchant(name):
    name = str(name).lower()
    name = re.sub(r'[^a-z\s]', ' ', name)

    for word in STOP_WORDS:
        name = name.replace(word, "")

    name = re.sub(r'\s+', ' ', name).strip()

    return name.split()[0] if name else name

# ==========================================
# BUILD BRAIN
# ==========================================
def build_brain_df(df):

    desc_col = detect_column(df, ["description", "narration", "merchant", "details", "name"])
    cat_col = detect_column(df, ["category"])
    subcat_col = detect_column(df, ["sub category", "subcategory", "sub-category"])

    st.write("📌 Detected Columns:")
    st.write({
        "Description": desc_col,
        "Category": cat_col,
        "Sub Category": subcat_col
    })

    df["merchant_raw"] = df[desc_col].astype(str)
    df["Category"] = df[cat_col]
    df["Sub Category"] = df[subcat_col] if subcat_col else "General"

    df["merchant_key"] = df["merchant_raw"].apply(normalize_merchant)

    st.write("📊 Before filtering:", df.shape)

    df_filtered = df[df["Category"].notna()]

    if df_filtered.empty:
        st.warning("⚠️ No categorized data → using full dataset")
        df_filtered = df.copy()

    st.write("📊 After filtering:", df_filtered.shape)

    grouped = df_filtered.groupby("merchant_key").agg({
        "merchant_raw": "first",
        "Category": lambda x: x.mode()[0] if not x.mode().empty else "Other",
        "Sub Category": lambda x: x.mode()[0] if not x.mode().empty else "General",
    }).reset_index()

    seen_counts = df_filtered.groupby("merchant_key").size().reset_index(name="seen")
    grouped = grouped.merge(seen_counts, on="merchant_key", how="left")

    grouped["last_updated"] = datetime.now().strftime("%Y-%m-%d")

    grouped = grouped.rename(columns={
        "merchant_raw": "merchant",
        "Category": "category",
        "Sub Category": "sub_category"
    })

    st.write("📊 Final Brain DF Shape:", grouped.shape)

    return grouped

# ==========================================
# UPLOAD
# ==========================================
def upload_to_gsheet(df):
    try:
        st.write("🚀 Uploading...")

        sheet = connect_gsheet()

        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist())

        st.success("🎉 Uploaded successfully!")
    except Exception as e:
        st.error(f"❌ Upload failed: {e}")

# ==========================================
# UI
# ==========================================
st.set_page_config(page_title="Brain Builder", layout="wide")

st.title("🧠 Brain Builder (FINAL)")

file = st.file_uploader("Upload your file", type=["xlsx", "csv"])

if file:
    df = pd.read_csv(file) if file.name.endswith(".csv") else pd.read_excel(file)

    st.subheader("📊 Data Preview")
    st.dataframe(df.head())

    st.write("🧾 Columns:", list(df.columns))

    # BUILD
    if st.button("🧠 Build Brain"):
        st.session_state.brain_df = build_brain_df(df)

# SHOW RESULT (PERSISTENT)
if st.session_state.brain_df is not None:
    st.subheader("🧠 Brain Data")
    st.dataframe(st.session_state.brain_df)

    if st.button("🚀 Upload to Google Sheet"):
        upload_to_gsheet(st.session_state.brain_df)

# TEST
st.divider()
if st.button("TEST GOOGLE SHEET"):
    sheet = connect_gsheet()
    sheet.update([["test"], ["hello working"]])
    st.success("✅ Test successful")
