# =========================================================
# IMPORTS
# =========================================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from io import BytesIO
import calendar
import re
import pdfplumber

# Google Sheets
import gspread
from google.oauth2.service_account import Credentials

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="Expense Intelligence",
    page_icon="💳",
    layout="wide"
)

# =========================================================
# PDF EXTRACTION
# =========================================================
def extract_gpay_pdf(file):
    records = []

    try:
        with pdfplumber.open(file) as pdf:
            full_text = ""
            for page in pdf.pages:
                full_text += page.extract_text() + "\n"

        lines = full_text.split("\n")

        i = 0
        while i < len(lines):

            if re.match(r'\d{2} \w{3}, \d{4}', lines[i]):

                date = lines[i]
                time = lines[i+1] if i+1 < len(lines) else ""
                details = lines[i+2] if i+2 < len(lines) else ""
                upi_line = lines[i+3] if i+3 < len(lines) else ""

                amount_line = ""
                for j in range(i, i+8):
                    if j < len(lines) and "₹" in lines[j]:
                        amount_line = lines[j]
                        break

                txn_type = "Other"
                name = ""

                if "Paid to" in details:
                    txn_type = "Debit"
                    name = details.replace("Paid to", "").strip()
                elif "Received from" in details:
                    txn_type = "Credit"
                    name = details.replace("Received from", "").strip()
                elif "Self transfer" in details:
                    txn_type = "Self"

                upi_id = ""
                if "UPI Transaction ID" in upi_line:
                    upi_id = upi_line.split(":")[-1].strip()

                amount = float(re.sub(r"[^\d.]", "", amount_line)) if amount_line else 0

                records.append({
                    "Date": date,
                    "Time": time,
                    "Description": name,
                    "Type": txn_type,
                    "Amount": amount,
                    "UPI_ID": upi_id
                })

                i += 5
            else:
                i += 1

        df = pd.DataFrame(records)
        df["Date"] = pd.to_datetime(df["Date"], format="%d %b, %Y", errors="coerce")

        return df

    except Exception as e:
        st.error(f"PDF Error: {e}")
        return pd.DataFrame()

# =========================================================
# DEDUPLICATION
# =========================================================
def remove_duplicates(df):
    if "UPI_ID" in df.columns:
        before = len(df)
        df = df.drop_duplicates(subset=["UPI_ID"])
        st.info(f"Removed {before - len(df)} duplicates")
    return df

# =========================================================
# LOAD BRAIN
# =========================================================
def load_brain(sheet_id):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        df = pd.read_csv(url)
        df["UPI_ID"] = df["UPI_ID"].astype(str)
        return df
    except:
        return pd.DataFrame()

# =========================================================
# FILTER NEW DATA
# =========================================================
def filter_new(pdf_df, brain_df):
    if brain_df.empty:
        return pdf_df

    existing = set(brain_df["UPI_ID"].astype(str))
    pdf_df["UPI_ID"] = pdf_df["UPI_ID"].astype(str)

    new_df = pdf_df[~pdf_df["UPI_ID"].isin(existing)]

    st.success(f"New: {len(new_df)} | Skipped: {len(pdf_df)-len(new_df)}")
    return new_df

# =========================================================
# APPEND TO GOOGLE SHEET
# =========================================================
def push_to_sheet(df, sheet_id):

    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )

    client = gspread.authorize(creds)
    sheet = client.open_by_key(sheet_id).sheet1

    existing = sheet.get_all_records()

    if not existing:
        sheet.append_row(df.columns.tolist())

    sheet.append_rows(df.values.tolist())

# =========================================================
# UI
# =========================================================
st.title("💳 Expense Intelligence")

# =========================================================
# PDF UPLOAD
# =========================================================
st.sidebar.markdown("### 📄 Upload GPay PDF")
pdf_file = st.sidebar.file_uploader("Upload PDF", type=["pdf"])

BRAIN_SHEET_ID = "YOUR_SHEET_ID_HERE"

pdf_df = pd.DataFrame()

if pdf_file:

    pdf_df = extract_gpay_pdf(pdf_file)

    if not pdf_df.empty:

        pdf_df = remove_duplicates(pdf_df)

        brain_df = load_brain(BRAIN_SHEET_ID)

        new_data = filter_new(pdf_df, brain_df)

        st.dataframe(new_data.head(20), use_container_width=True)

        if not new_data.empty:
            if st.button("🚀 Push to Brain"):
                push_to_sheet(new_data, BRAIN_SHEET_ID)
                st.success("Uploaded successfully!")

# =========================================================
# MERGE WITH DASHBOARD
# =========================================================
if not pdf_df.empty:
    df = pdf_df.copy()
else:
    st.stop()

# =========================================================
# BASIC DASHBOARD
# =========================================================
st.markdown("## 📊 Overview")

total = df["Amount"].sum()
st.metric("Total Spend", f"₹{total:,.0f}")

monthly = df.groupby(df["Date"].dt.to_period("M"))["Amount"].sum().reset_index()
monthly["Date"] = monthly["Date"].astype(str)

fig = px.line(monthly, x="Date", y="Amount", markers=True)
st.plotly_chart(fig, use_container_width=True)

cat = df.groupby("Description")["Amount"].sum().reset_index().sort_values("Amount", ascending=False).head(10)

fig = px.bar(cat, x="Description", y="Amount")
st.plotly_chart(fig, use_container_width=True)
