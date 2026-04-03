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
# MERCHANT NORMALIZATION
# ==========================================
STOP_WORDS = [
    "private", "limited", "ltd", "pvt", "pvt ltd",
    "marketplace", "services", "solutions", "india"
]

def normalize_merchant(name):
    name = str(name).lower()

    # remove symbols
    name = re.sub(r'[^a-z\s]', ' ', name)

    # remove stop words
    for word in STOP_WORDS:
        name = name.replace(word, "")

    # remove extra spaces
    name = re.sub(r'\s+', ' ', name).strip()

    # fallback → first word
    return name.split()[0] if name else name

# ==========================================
# BUILD BRAIN DATA
# ==========================================
def build_brain_df(df):

    # detect columns
    desc_col = detect_column(df, ["description", "narration", "merchant", "details", "name"])
    cat_col = detect_column(df, ["category"])
    subcat_col = detect_column(df, ["sub category", "subcategory", "sub-category"])

    # debug view
    st.write("📌 Detected Columns:")
    st.write({
        "Description": desc_col,
        "Category": cat_col,
        "Sub Category": subcat_col
    })

    if not desc_col:
        st.error("❌ Could not detect Description column")
        return pd.DataFrame()

    if not cat_col:
        st.error("❌ Could not detect Category column")
        return pd.DataFrame()

    # assign columns
    df["merchant_raw"] = df[desc_col].astype(str)
    df["Category"] = df[cat_col]

    if subcat_col:
        df["Sub Category"] = df[subcat_col]
    else:
        df["Sub Category"] = "General"

    # normalize merchant
    df["merchant_key"] = df["merchant_raw"].apply(normalize_merchant)

    # remove uncategorized
    df = df[df["Category"].notna()]
    df = df[df["Category"] != "Uncategorized"]

    if df.empty:
        st.warning("⚠️ No categorized data found")
        return pd.DataFrame()

    # aggregate
    grouped = df.groupby("merchant_key").agg({
        "merchant_raw": "first",
        "Category": lambda x: x.mode()[0] if not x.mode().empty else "Other",
        "Sub Category": lambda x: x.mode()[0] if not x.mode().empty else "General",
    }).reset_index()

    # seen count
    seen_counts = df.groupby("merchant_key").size().reset_index(name="seen")
    grouped = grouped.merge(seen_counts, on="merchant_key", how="left")

    grouped["last_updated"] = datetime.now().strftime("%Y-%m-%d")

    # rename
    grouped = grouped.rename(columns={
        "merchant_raw": "merchant",
        "Category": "category",
        "Sub Category": "sub_category"
    })

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
        sheet = connect_gsheet()

        # clear existing data
        sheet.clear()

        # write new data
        sheet.update([df.columns.values.tolist()] + df.values.tolist())

        return True

    except Exception as e:
        st.error(f"❌ Upload failed: {e}")
        return False

# ==========================================
# STREAMLIT UI
# ==========================================
st.set_page_config(page_title="Brain Builder", layout="wide")

st.title("🧠 Brain Builder (Upload → Learn → Store)")

file = st.file_uploader("Upload your 6-month data", type=["xlsx", "csv"])

if file:
    df = pd.read_csv(file) if file.name.endswith(".csv") else pd.read_excel(file)

    st.subheader("📊 Data Preview")
    st.dataframe(df.head())

    st.write("🧾 Available Columns:", list(df.columns))

    if st.button("🧠 Build Brain"):
        brain_df = build_brain_df(df)

        if not brain_df.empty:
            st.success(f"✅ Generated {len(brain_df)} unique merchants")

            st.subheader("🧠 Brain Preview")
            st.dataframe(brain_df)

            if st.button("🚀 Upload to Google Sheet"):
                success = upload_to_gsheet(brain_df)

                if success:
                    st.success("🎉 Brain successfully uploaded to Google Sheet!")
