# =========================================================
# IMPORTS
# =========================================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import re
import pdfplumber

# Google Sheets
import gspread
from google.oauth2.service_account import Credentials

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(page_title="Expense Intelligence", layout="wide")
st.title("💳 Expense Intelligence")

# =========================================================
# 🔥 ULTRA ROBUST PDF PARSER (FINAL FIX)
# =========================================================
def extract_gpay_pdf(file):
    records = []

    try:
        with pdfplumber.open(file) as pdf:
            lines = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    lines.extend([l.strip() for l in text.split("\n") if l.strip()])

        i = 0
        while i < len(lines):

            # Match date
            if re.match(r"\d{2} \w{3}, \d{4}", lines[i]):

                date = lines[i]

                # Next line should be time
                time = ""
                if i+1 < len(lines) and re.search(r"\d{1,2}:\d{2}", lines[i+1]):
                    time = lines[i+1]

                txn_type = "Other"
                name = "Unknown"
                upi_id = ""
                amount = None

                # Look ahead safely
                for j in range(i+1, min(i+12, len(lines))):

                    line = lines[j]

                    if "Paid to" in line:
                        txn_type = "Debit"
                        name = line.replace("Paid to", "").strip()

                    elif "Received from" in line:
                        txn_type = "Credit"
                        name = line.replace("Received from", "").strip()

                    elif "Self transfer" in line:
                        txn_type = "Self"
                        name = "Self Transfer"

                    if "UPI Transaction ID" in line:
                        upi_id = line.split(":")[-1].strip()

                    if "₹" in line:
                        amt = re.sub(r"[^\d.]", "", line)
                        if amt:
                            amount = float(amt)

                # Only add valid rows
                if amount is not None:
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
            st.error("❌ Still no data — PDF structure changed")
            return df

        # Convert date
        df["Date"] = pd.to_datetime(df["Date"], format="%d %b, %Y", errors="coerce")

        # CLEANING
        df = df[df["Amount"] > 1]      # remove ₹0.01
        df = df[df["Type"] != "Self"]  # remove self transfer

        st.success(f"✅ Extracted {len(df)} transactions")

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
        st.info(f"Duplicates removed: {before - len(df)}")
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
# FILTER NEW
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
# PUSH TO SHEET
# =========================================================
def push_to_sheet(df, sheet_id):

    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )

    client = gspread.authorize(creds)
    sheet = client.open_by_key(sheet_id).sheet1

    if not sheet.get_all_records():
        sheet.append_row(df.columns.tolist())

    sheet.append_rows(df.values.tolist())

    st.success("✅ Uploaded to Brain")

# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.markdown("### 📄 Upload GPay PDF")
pdf_file = st.sidebar.file_uploader("Upload PDF", type=["pdf"])

BRAIN_SHEET_ID = "YOUR_SHEET_ID_HERE"

# =========================================================
# MAIN FLOW
# =========================================================
if pdf_file:

    df = extract_gpay_pdf(pdf_file)

    if not df.empty:

        df = remove_duplicates(df)

        brain_df = load_brain(BRAIN_SHEET_ID)

        new_data = filter_new(df, brain_df)

        st.dataframe(new_data.head(20), use_container_width=True)

        if not new_data.empty:
            if st.button("🚀 Push to Brain"):
                push_to_sheet(new_data, BRAIN_SHEET_ID)

        # DASHBOARD
        st.markdown("## 📊 Overview")

        total = df["Amount"].sum()
        st.metric("Total Spend", f"₹{total:,.0f}")

        monthly = df.groupby(df["Date"].dt.to_period("M"))["Amount"].sum().reset_index()
        monthly["Date"] = monthly["Date"].astype(str)

        fig = px.line(monthly, x="Date", y="Amount", markers=True)
        st.plotly_chart(fig, use_container_width=True)

        top = df.groupby("Description")["Amount"].sum().reset_index().sort_values("Amount", ascending=False).head(10)

        fig = px.bar(top, x="Description", y="Amount")
        st.plotly_chart(fig, use_container_width=True)
