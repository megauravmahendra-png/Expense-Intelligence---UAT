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
st.title("📄 GPay PDF Extractor (Final)")

# ==========================================
# PDF PARSER (FINAL - BASED ON YOUR LOGIC)
# ==========================================
def parse_pdf(file):

    rows = []

    with pdfplumber.open(file) as pdf:
        full_text = ""

        for page in pdf.pages:
            text = page.extract_text() or ""

            # 🔥 KEY FIX: normalize broken text
            text = re.sub(r'(?<=\d)(?=[A-Za-z])', ' ', text)
            text = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', text)

            full_text += text + "\n"

    # 🔥 REMOVE HEADERS / NOISE
    full_text = re.sub(r'Transaction statement.*?Amount', '', full_text, flags=re.DOTALL)
    full_text = re.sub(r'Note:.*?Page\d+of\d+', '', full_text, flags=re.DOTALL)

    # 🔥 MAIN PATTERN (IMPORTANT)
    pattern = re.findall(
        r'(\d{1,2}\s?[A-Za-z]{3},\s?\d{4})\s+'
        r'(Paid to|Received from|Self transfer.*?)\s+'
        r'₹\s*([\d,]+\.?\d*)\s+'
        r'(\d{1,2}:\d{2}[AP]M)\s+'
        r'UPI Transaction ID:\s*(\d+)',
        full_text
    )

    for match in pattern:
        try:
            date_str, txn_text, amount, time, upi_id = match

            date = pd.to_datetime(date_str, errors="coerce")
            amount = float(amount.replace(",", ""))

            txn_text_lower = txn_text.lower()

            if "paid to" in txn_text_lower:
                txn_type = "Debit"
                desc = txn_text.replace("Paid to", "").strip()

            elif "received from" in txn_text_lower:
                txn_type = "Credit"
                desc = txn_text.replace("Received from", "").strip()

            else:
                txn_type = "Self"
                desc = "Self Transfer"

            # Clean description
            desc = re.sub(r'[^A-Za-z ]', '', desc).strip()

            rows.append({
                "Date": date,
                "Time": time,
                "Description": desc,
                "Type": txn_type,
                "Amount": amount,
                "UPI_ID": upi_id
            })

        except:
            continue

    df = pd.DataFrame(rows)

    return df

# ==========================================
# UI
# ==========================================
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
            st.metric("Transactions", len(df))

        with col2:
            st.metric("Total Amount", f"₹{df['Amount'].sum():,.2f}")
