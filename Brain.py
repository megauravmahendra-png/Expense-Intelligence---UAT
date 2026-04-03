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

        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )

        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID).sheet1

        st.write("✅ Connected to Google Sheet")
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

    if not desc_col:
        st.error("❌ Description column not found")
        return pd.DataFrame()

    # assign columns
    df["merchant_raw"] = df[desc_col].astype(str)

    if cat_col:
        df["Category"] = df[cat_col]
    else:
        st.warning("⚠️ No Category column found → using 'Uncategorized'")
        df["Category"] = "Uncategorized"

    if subcat_col:
        df["Sub Category"] = df[subcat_col]
    else:
        df["Sub Category"] = "General"

    # normalize
    df["merchant_key"] = df["merchant_raw"].apply(normalize_merchant)

    # DEBUG SHAPES
    st.write("📊 Before filtering:", df.shape)

    # filtering
    df_filtered = df[df["Category"].notna()]

    if df_filtered.empty:
        st.warning("⚠️ No categorized data → using full dataset")
        df_filtered = df.copy()

    st.write("📊 After filtering:", df_filtered.shape)

    # group
    grouped = df_filtered.groupby("merchant_key").agg({
        "merchant_raw": "first",
        "Category": lambda x: x.mode()[0] if not x.mode().empty else "Other",
        "Sub Category": lambda x: x.mode()[0] if not x.mode().empty else "General",
    }).reset_index()

    # seen count
    seen_counts = df_filtered.groupby("merchant_key").size().reset_index(name="seen")
    grouped = grouped.merge(seen_counts, on="merchant_key", how="left")

    grouped["last_updated"] = datetime.now().strftime("%Y-%m-%d")

    grouped = grouped.rename(columns={
        "merchant_raw": "merchant",
        "Category": "category",
        "Sub Category": "sub_category"
    })

    st.write("📊 Final Brain DF Shape:", grouped.shape)

    return grouped[[
        "merchant_key",
        "merchant",
        "category",
        "sub_category",
        "seen",
        "last_updated"
    ]]

# ==========================================
# UPLOAD TO GOOGLE SHEET
# ==========================================
def upload_to_gsheet(df):
    try:
        st.write("🚀 Starting upload...")

        sheet = connect_gsheet()
        if sheet is None:
            return False

        st.write("📊 Rows to upload:", len(df))

        sheet.clear()
        st.write("🧹 Sheet cleared")

        sheet.update([df.columns.values.tolist()] + df.values.tolist())

        st.success("🎉 Upload successful!")

        return True

    except Exception as e:
        st.error(f"❌ Upload failed: {e}")
        return False

# ==========================================
# STREAMLIT UI
# ==========================================
st.set_page_config(page_title="Brain Builder", layout="wide")

st.title("🧠 Brain Builder (FINAL DEBUG VERSION)")

file = st.file_uploader("Upload your file", type=["xlsx", "csv"])

if file:
    df = pd.read_csv(file) if file.name.endswith(".csv") else pd.read_excel(file)

    st.subheader("📊 Data Preview")
    st.dataframe(df.head())

    st.write("🧾 Columns:", list(df.columns))

    if st.button("🧠 Build Brain"):
        brain_df = build_brain_df(df)

        if not brain_df.empty:
            st.dataframe(brain_df)

            if st.button("🚀 Upload to Google Sheet"):
                upload_to_gsheet(brain_df)

# ==========================================
# TEST BUTTON
# ==========================================
st.divider()
st.subheader("🧪 Connection Test")

if st.button("TEST GOOGLE SHEET"):
    sheet = connect_gsheet()
    if sheet:
        sheet.update([["test"], ["hello working"]])
        st.success("✅ Test successful")
