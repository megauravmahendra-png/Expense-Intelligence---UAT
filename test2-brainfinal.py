# =========================================================
# IMPORTS
# =========================================================
import streamlit as st
import pandas as pd
import re
import pdfplumber

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(layout="wide")
st.title("📄 GPay PDF Extractor")

# =========================================================
# PDF PARSER (FINAL STABLE)
# =========================================================
def parse_pdf(file):

    records = []

    with pdfplumber.open(file) as pdf:

        all_lines = []

        # Extract all text lines
        for page in pdf.pages:
            text = page.extract_text() or ""
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            all_lines.extend(lines)

        i = 0
        while i < len(all_lines):

            line = all_lines[i]

            # Detect transaction start (Date)
            if re.match(r"\d{2} \w{3}, \d{4}", line):

                try:
                    date = pd.to_datetime(line, format="%d %b, %Y", errors="coerce")

                    # Time
                    time = ""
                    if i+1 < len(all_lines) and re.search(r"\d{1,2}:\d{2}", all_lines[i+1]):
                        time = all_lines[i+1]

                    txn_type = "Other"
                    description = "Unknown"
                    upi_id = ""
                    amount = None

                    # Scan transaction block
                    for j in range(i+1, min(i+12, len(all_lines))):

                        l = all_lines[j]

                        if "Paid to" in l:
                            txn_type = "Debit"
                            description = l.replace("Paid to", "").strip()

                        elif "Received from" in l:
                            txn_type = "Credit"
                            description = l.replace("Received from", "").strip()

                        elif "Self transfer" in l:
                            txn_type = "Self"
                            description = "Self Transfer"

                        if "UPI Transaction ID" in l:
                            upi_id = l.split(":")[-1].strip()

                        if "₹" in l:
                            amt = re.sub(r"[^\d.]", "", l)
                            if amt:
                                amount = float(amt)

                    # Save valid transactions
                    if amount is not None:
                        records.append({
                            "Date": date,
                            "Time": time,
                            "Description": description,
                            "Type": txn_type,
                            "Amount": amount,
                            "UPI_ID": upi_id
                        })

                except:
                    pass

            i += 1

    df = pd.DataFrame(records)

    return df

# =========================================================
# UI
# =========================================================
uploaded_file = st.file_uploader("Upload GPay PDF", type=["pdf"])

if uploaded_file:

    st.info("⏳ Extracting transactions...")

    df = parse_pdf(uploaded_file)

    if df.empty:
        st.error("❌ No transactions extracted")
    else:
        st.success(f"✅ Extracted {len(df)} transactions")

        st.dataframe(df, use_container_width=True)

        # Summary
        st.markdown("### 📊 Summary")

        col1, col2 = st.columns(2)

        with col1:
            st.metric("Total Transactions", len(df))

        with col2:
            st.metric("Total Amount", f"₹{df['Amount'].sum():,.2f}")
