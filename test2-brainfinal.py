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
# FINAL PARSER (TEXT-BASED REGEX)
# =========================================================
def parse_pdf(file):

    records = []

    with pdfplumber.open(file) as pdf:

        full_text = ""

        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"

    # 🔥 KEY FIX: normalize text
    full_text = re.sub(r'\n+', '\n', full_text)

    # Split using DATE as anchor
    pattern = r'(\d{2} \w{3}, \d{4}\s+\d{2}:\d{2} [AP]M.*?)₹\s*([\d,]+\.\d+|\d+)'

    matches = re.findall(pattern, full_text, re.DOTALL)

    for block, amount in matches:

        try:
            # Date + Time
            dt_match = re.search(r'(\d{2} \w{3}, \d{4})\s+(\d{2}:\d{2} [AP]M)', block)

            if not dt_match:
                continue

            date = pd.to_datetime(dt_match.group(1), format="%d %b, %Y", errors="coerce")
            time = dt_match.group(2)

            # Type + Description
            if "Paid to" in block:
                txn_type = "Debit"
                desc = re.search(r'Paid to (.*)', block)
            elif "Received from" in block:
                txn_type = "Credit"
                desc = re.search(r'Received from (.*)', block)
            else:
                txn_type = "Other"
                desc = None

            description = desc.group(1).split("UPI")[0].strip() if desc else "Unknown"

            # UPI ID
            upi_match = re.search(r'UPI Transaction ID:\s*(\d+)', block)
            upi_id = upi_match.group(1) if upi_match else ""

            # Amount
            amt = float(amount.replace(",", ""))

            records.append({
                "Date": date,
                "Time": time,
                "Description": description,
                "Type": txn_type,
                "Amount": amt,
                "UPI_ID": upi_id
            })

        except:
            continue

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
