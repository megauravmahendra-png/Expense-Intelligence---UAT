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
# GOOGLE SHEETS CONNECTION
# ==========================================
def connect_gsheet():
    try:
        st.write("🔐 Loading credentials...")
        st.write("Secrets keys:", list(st.secrets.keys()))

        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )

        st.write("✅ Credentials loaded")

        client = gspread.authorize(creds)
        st.write("✅ Authorized client")

        sheet = client.open_by_key(SHEET_ID).sheet1
        st.write("✅ Connected to sheet")

        return sheet

    except Exception as e:
        st.error(f"❌ Connection failed: {e}")
        return None

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
# MERCHANT NORMALIZATION
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
# BUILD BRAIN DATA
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

    if not desc_col or not cat_col:
        st.error("❌ Required columns not found")
        return pd.DataFrame()

    df["merchant_raw"] = df[desc_col].astype(str)
    df["Category"] = df[cat_col]

    if subcat_col:
        df["Sub Category"] = df[subcat_col]
    else:
        df["Sub Category"] = "General"

    df["merchant_key"] = df["merchant_raw"].apply(normalize_merchant)

    df = df[df["Category"].notna()]
    df = df[df["Category"] != "Uncategorized"]

    if df.empty:
        st.warning("⚠️ No categorized data found")
        return pd.DataFrame()

    grouped = df.groupby("merchant_key").agg({
        "merchant_raw": "first",
        "Category": lambda x: x.mode()[0] if not x.mode().empty else "Other",
        "Sub Category": lambda x: x.mode()[0] if not x.mode().empty else "General",
    }).reset_index()

    seen_counts = df.groupby("merchant_key").size().reset_index(name="seen")
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
# UPLOAD TO GOOGLE SHEET (DEBUG)
# ==========================================
def upload_to_gsheet(df):
    try:
        st.write("🚀 Starting upload...")

        sheet = connect_gsheet()
        if sheet is None:
            st.error("❌ Sheet connection failed")
            return False

        st.write("📊 Rows to upload:", len(df))

        st.write("🧹 Clearing sheet...")
        sheet.clear()

        st.write("✍️ Writing data...")
        sheet.update([df.columns.values.tolist()] + df.values.tolist())

        st.success("✅ Upload successful!")

        return True

    except Exception as e:
        st.error(f"❌ Upload failed: {e}")
        return False

# ==========================================
# STREAMLIT UI
# ==========================================
st.set_page_config(page_title="Brain Debug Tool", layout="wide")

st.title("🧠 Brain Builder (DEBUG MODE)")

file = st.file_uploader("Upload your file", type=["xlsx", "csv"])

if file:
    df = pd.read_csv(file) if file.name.endswith(".csv") else pd.read_excel(file)

    st.subheader("📊 Data Preview")
    st.dataframe(df.head())

    st.write("🧾 Columns Found:", list(df.columns))

    if st.button("🧠 Build Brain"):
        brain_df = build_brain_df(df)

        if not brain_df.empty:
            st.dataframe(brain_df)

            if st.button("🚀 Upload to Google Sheet"):
                upload_to_gsheet(brain_df)

# ==========================================
# EXTRA TEST BUTTON
# ==========================================
st.divider()
st.subheader("🧪 Connection Test")

if st.button("TEST GOOGLE SHEET"):
    try:
        sheet = connect_gsheet()
        if sheet:
            sheet.update([["test"], ["hello from streamlit"]])
            st.success("✅ Test write successful")
    except Exception as e:
        st.error(f"❌ Test failed: {e}")
