# ==========================================
# IMPORTS
# ==========================================
import streamlit as st
import pandas as pd
import re
import pdfplumber

# ==========================================
# CONFIG
# ==========================================
st.set_page_config(layout="wide")
st.title("📄 GPay PDF Extractor (SMART VERSION)")

# ==========================================
# PARSER
# ==========================================
def parse_pdf(file):

    records = []

    with pdfplumber.open(file) as pdf:

        lines = []

        for page in pdf.pages:
            text = page.extract_text() or ""

            text = re.sub(r'(?<=\d)(?=[A-Za-z])', ' ', text)
            text = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', text)

            page_lines = [l.strip() for l in text.split("\n") if l.strip()]
            lines.extend(page_lines)

    i = 0

    while i < len(lines) - 1:

        line1 = lines[i]
        line2 = lines[i + 1]

        if "₹" in line1:

            try:
                # DATE
                date_match = re.search(r'\d{1,2}\s[A-Za-z]{3},\d{4}', line1)
                if not date_match:
                    i += 1
                    continue

                date = pd.to_datetime(date_match.group(), format="%d %b,%Y", errors="coerce")

                # AMOUNT
                amt_match = re.search(r'₹\s*([\d,]+\.?\d*)', line1)
                amount = float(amt_match.group(1).replace(",", "")) if amt_match else None

                # TYPE LOGIC
                if "Selftransfer" in line1 or "Self transfer" in line1:
                    txn_type = "Self Transfer"
                    desc = "Self Transfer"

                elif "Paidto" in line1 or "Paid to" in line1:
                    txn_type = "Debit"
                    desc = re.split(r'Paidto|Paid to', line1)[1]

                elif "Receivedfrom" in line1 or "Received from" in line1:
                    txn_type = "Credit"
                    desc = re.split(r'Receivedfrom|Received from', line1)[1]

                else:
                    txn_type = "Other"
                    desc = ""

                desc = desc.split("₹")[0]
                desc = re.sub(r'[^A-Za-z ]', '', desc).strip()

                # TIME
                time_match = re.search(r'\d{1,2}:\d{2}\s?[AP]M', line2)
                time = time_match.group() if time_match else ""

                # UPI
                upi_match = re.search(r'UPI\s*Transaction\s*ID:\s*(\d+)', line2)
                upi_id = upi_match.group(1) if upi_match else ""

                # SIGN LOGIC
                if txn_type == "Debit":
                    final_amount = amount
                elif txn_type == "Credit":
                    final_amount = -amount
                else:
                    final_amount = amount

                if amount is not None:
                    records.append({
                        "Date": date,
                        "Time": time,
                        "Description": desc,
                        "Type": txn_type,
                        "Amount": final_amount,
                        "UPI_ID": upi_id
                    })

                i += 2
                continue

            except:
                pass

        i += 1

    df = pd.DataFrame(records)

    # REMOVE DUPLICATES (IMPORTANT)
    df = df.drop_duplicates(subset=["UPI_ID"])

    return df

# ==========================================
# UI
# ==========================================
uploaded_file = st.file_uploader("Upload GPay PDF", type=["pdf"])

if uploaded_file:

    st.info("⏳ Extracting transactions...")

    df = parse_pdf(uploaded_file)

    if df.empty:
        st.error("❌ No transactions found")
    else:
        st.success(f"✅ Extracted {len(df)} transactions")

        # =========================
        # SPLIT DATA
        # =========================
        debit_df = df[df["Type"] == "Debit"]
        credit_df = df[df["Type"] == "Credit"]
        self_df = df[df["Type"] == "Self Transfer"]

        # =========================
        # SUMMARY
        # =========================
        st.markdown("## 📊 Summary")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Transactions", len(df))

        with col2:
            st.metric("Money Spent", f"₹{debit_df['Amount'].sum():,.2f}")

        with col3:
            st.metric("Money Received", f"₹{abs(credit_df['Amount'].sum()):,.2f}")

        with col4:
            st.metric("Self Transfer", f"₹{self_df['Amount'].sum():,.2f}")

        # =========================
        # DATA TABLE
        # =========================
        st.markdown("## 📄 All Transactions")
        st.dataframe(df, use_container_width=True)

        # =========================
        # OPTIONAL TABS
        # =========================
        tab1, tab2, tab3 = st.tabs(["💸 Spent", "💰 Received", "🔁 Self Transfer"])

        with tab1:
            st.dataframe(debit_df)

        with tab2:
            st.dataframe(credit_df)

        with tab3:
            st.dataframe(self_df)
