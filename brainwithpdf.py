import streamlit as st
import pandas as pd
import re
from datetime import datetime
import pdfplumber
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
# LOAD BRAIN FROM SHEET
# ==========================================
def load_brain():
    sheet = connect_gsheet()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    brain = {}
    for _, row in df.iterrows():
        key = str(row["merchant_key"]).strip().lower()
        brain[key] = {
            "category": row["category"],
            "sub_category": row["sub_category"]
        }

    return brain

# ==========================================
# NORMALIZATION
# ==========================================
STOP_WORDS = [
    "private", "limited", "ltd", "pvt", "marketplace"
]

def normalize_merchant(name):
    name = str(name).lower()
    name = re.sub(r'[^a-z\s]', ' ', name)

    for word in STOP_WORDS:
        name = name.replace(word, "")

    name = re.sub(r'\s+', ' ', name).strip()

    return name.split()[0] if name else name

# ==========================================
# PDF PARSER (GPay)
# ==========================================
def parse_pdf(file):

    rows = []

    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""

            # clean spacing
            text = re.sub(r'(?<=\d)(?=[A-Za-z])', ' ', text)
            text = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', text)

            lines = text.split("\n")

            for line in lines:
                if "₹" not in line:
                    continue

                try:
                    date_match = re.search(r'\d{1,2}\s?[A-Za-z]{3},\s?\d{4}', line)
                    amt_match = re.search(r'₹\s*([\d,]+\.?\d*)', line)

                    if not date_match or not amt_match:
                        continue

                    date = pd.to_datetime(date_match.group(), errors="coerce")
                    amount = float(amt_match.group(1).replace(",", ""))

                    line_lower = line.lower()

                    if "received" in line_lower or "self transfer" in line_lower:
                        continue

                    if "paidto" in line_lower:
                        merchant = re.split("paidto", line, flags=re.IGNORECASE)[1]
                    else:
                        continue

                    merchant = merchant.split("₹")[0]
                    merchant = re.sub(r'[^A-Za-z ]', '', merchant).strip()

                    rows.append({
                        "Date": date,
                        "Description": merchant,
                        "Amount": amount
                    })

                except:
                    continue

    return pd.DataFrame(rows)

# ==========================================
# BRAIN LOOKUP
# ==========================================
def apply_brain(df, brain):

    df["merchant_key"] = df["Description"].apply(normalize_merchant)

    categories = []
    subcats = []

    for _, row in df.iterrows():
        key = row["merchant_key"]

        if key in brain:
            categories.append(brain[key]["category"])
            subcats.append(brain[key]["sub_category"])
        else:
            categories.append("Uncategorized")
            subcats.append("Uncategorized")

    df["Category"] = categories
    df["Sub Category"] = subcats

    return df

# ==========================================
# RULE ENGINE
# ==========================================
def apply_rules(df):

    for i, row in df.iterrows():

        if row["Category"] != "Uncategorized":
            continue

        amount = row["Amount"]
        hour = row["Date"].hour if pd.notna(row["Date"]) else 12

        # RULE: auto
        if 10 <= amount <= 60 and 7 <= hour <= 12:
            df.at[i, "Category"] = "Transport"
            df.at[i, "Sub Category"] = "Auto"

    return df

# ==========================================
# UI
# ==========================================
st.set_page_config(layout="wide")
st.title("🧠 Expense Intelligence Engine (Phase 2)")

uploaded_file = st.file_uploader("Upload GPay PDF", type=["pdf"])

if uploaded_file:

    st.write("📄 Parsing PDF...")

    df = parse_pdf(uploaded_file)

    st.write("📊 Raw Transactions")
    st.dataframe(df)

    if not df.empty:

        brain = load_brain()

        # Step 1: Brain
        df = apply_brain(df, brain)

        # Step 2: Rules
        df = apply_rules(df)

        st.write("🧠 Final Categorized Data")
        st.dataframe(df)

        st.success(f"✅ Processed {len(df)} transactions")
