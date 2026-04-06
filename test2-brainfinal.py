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

st.title("💳 Expense Intelligence")

# =========================================================
# PDF EXTRACTION (ROBUST)
# =========================================================
def extract_gpay_pdf(file):
    records = []

    try:
        with pdfplumber.open(file) as pdf:
            full_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"

        lines = [l.strip() for l in full_text.split("\n") if l.strip()]

        i = 0
        while i < len(lines):

            if re.match(r"\d{2} \w{3}, \d{4}", lines[i]):

                date = lines[i]
                time = lines[i+1] if i+1 < len(lines) else ""

                txn_type = "Other"
                name = "Unknown"
                upi_id = ""
                amount = 0

                for j in range(i+2, min(i+10, len(lines))):

                    if "Paid to" in lines[j]:
                        txn_type = "Debit"
                        name = lines[j].replace("Paid to", "").strip()

                    elif "Received from" in lines[j]:
                        txn_type = "Credit"
                        name = lines[j].replace("Received from", "").strip()

                    elif "Self transfer" in lines[j]:
                        txn_type = "Self"
                        name = "Self Transfer"

                    if "UPI Transaction ID" in lines[j]:
                        upi_id = lines[j].split(":")[-1].strip()

                    if "₹" in lines[j]:
                        amt = re.sub(r"[^\d.]", "", lines[j])
                        if amt:
                            amount = float(amt)

                records.append({
                    "Date": date,
                    "Time": time,
                    "Description": name,
                    "Type": txn_type,
                    "Amount": amount,
                    "UPI_ID": upi_id
                })

                i += 1
            else:
                i += 1

        df = pd.DataFrame(records)

        if df.empty:
            st.error("❌ No transactions extracted")
            return df

        df["Date"] = pd.to_datetime(df["Date"], format="%d %b, %Y", errors="coerce")

        # CLEANING
        df = df[df["Amount"] > 1]          # remove ₹0.01 noise
        df = df[df["Type"] != "Self"]     # remove self transfers

        return df

    except Exception as e:
        st.error(f"❌ PDF Error: {e}")
        return pd.DataFrame()

# =========================================================
# REMOVE DUPLICATES
# =========================================================
def remove_duplicates(df):
    if "UPI_ID" in df.columns:
        before = len(df)
        df = df.drop_duplicates(subset=["UPI_ID"])
        removed = before - len(df)
        if removed > 0:
            st.warning(f"⚠️ Removed {removed} duplicates")
    return df

# =========================================================
# LOAD BRAIN
# =========================================================
def load_brain(sheet_id):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        df = pd.read_csv(url)

        if "UPI_ID" in df.columns:
            df["UPI_ID"] = df["UPI_ID"].astype(str)

        st.success(f"🧠 Brain Loaded: {len(df)} rows")
        return df

    except Exception as e:
        st.error(f"❌ Brain load failed: {e}")
        return pd.DataFrame()

# =========================================================
# FILTER NEW TRANSACTIONS
# =========================================================
def filter_new(pdf_df, brain_df):

    if brain_df.empty or "UPI_ID" not in brain_df.columns:
        return pdf_df

    existing_ids = set(brain_df["UPI_ID"].astype(str))
    pdf_df["UPI_ID"] = pdf_df["UPI_ID"].astype(str)

    new_df = pdf_df[~pdf_df["UPI_ID"].isin(existing_ids)]

    st.info(f"🆕 New: {len(new_df)} | Skipped: {len(pdf_df)-len(new_df)}")

    return new_df

# =========================================================
# PUSH TO GOOGLE SHEET
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

    st.success(f"✅ Uploaded {len(df)} new transactions")

# =========================================================
# SIDEBAR - PDF UPLOAD
# =========================================================
st.sidebar.markdown("### 📄 Upload GPay PDF")
pdf_file = st.sidebar.file_uploader("Upload PDF", type=["pdf"])

# 🔥 PUT YOUR SHEET ID HERE
BRAIN_SHEET_ID = "YOUR_SHEET_ID_HERE"

pdf_df = pd.DataFrame()

# =========================================================
# MAIN PIPELINE
# =========================================================
if pdf_file:

    with st.spinner("Processing PDF..."):
        pdf_df = extract_gpay_pdf(pdf_file)

    if not pdf_df.empty:

        # Step 1: Remove duplicates inside PDF
        pdf_df = remove_duplicates(pdf_df)

        # Step 2: Load brain
        brain_df = load_brain(BRAIN_SHEET_ID)

        # Step 3: Filter only new
        new_data = filter_new(pdf_df, brain_df)

        # Preview
        st.subheader("🧾 Extracted Data")
        st.dataframe(new_data.head(20), use_container_width=True)

        # Upload button
        if not new_data.empty:
            if st.button("🚀 Push to Brain"):
                push_to_sheet(new_data, BRAIN_SHEET_ID)
        else:
            st.success("✅ No new transactions (Already up-to-date)")

# =========================================================
# DASHBOARD
# =========================================================
if not pdf_df.empty:

    df = pdf_df.copy()

    st.markdown("## 📊 Overview")

    total = df["Amount"].sum()
    st.metric("Total Spend", f"₹{total:,.0f}")

    monthly = df.groupby(df["Date"].dt.to_period("M"))["Amount"].sum().reset_index()
    monthly["Date"] = monthly["Date"].astype(str)

    fig = px.line(monthly, x="Date", y="Amount", markers=True)
    st.plotly_chart(fig, use_container_width=True)

    top_spend = df.groupby("Description")["Amount"].sum().reset_index().sort_values("Amount", ascending=False).head(10)

    fig = px.bar(top_spend, x="Description", y="Amount")
    st.plotly_chart(fig, use_container_width=True)
