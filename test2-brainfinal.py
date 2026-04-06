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
st.title("📄 GPay PDF Extractor (FINAL WORKING)")

# ==========================================
# FINAL PARSER (FIXED DATE REGEX)
# ==========================================
def parse_pdf(file):

    records = []

    with pdfplumber.open(file) as pdf:

        lines = []

        for page in pdf.pages:
            text = page.extract_text() or ""

            # Normalize spacing
            text = re.sub(r'(?<=\d)(?=[A-Za-z])', ' ', text)
            text = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', text)

            page_lines = [l.strip() for l in text.split("\n") if l.strip()]
            lines.extend(page_lines)

    i = 0

    while i < len(lines) - 1:

        line1 = lines[i]
        line2 = lines[i + 1]

        # MAIN CONDITION
        if "₹" in line1:

            try:
                # ✅ FIXED DATE REGEX (IMPORTANT)
                date_match = re.search(r'\d{1,2}\s[A-Za-z]{3},\d{4}', line1)

                if not date_match:
                    i += 1
                    continue

                date = pd.to_datetime(date_match.group(), format="%d %b,%Y", errors="coerce")

                # AMOUNT
                amt_match = re.search(r'₹\s*([\d,]+\.?\d*)', line1)
                amount = float(amt_match.group(1).replace(",", "")) if amt_match else None

                # TYPE + DESC
                if "Paidto" in line1 or "Paid to" in line1:
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

                if amount is not None:
                    records.append({
                        "Date": date,
                        "Time": time,
                        "Description": desc,
                        "Type": txn_type,
                        "Amount": amount,
                        "UPI_ID": upi_id
                    })

                i += 2
                continue

            except:
                pass

        i += 1

    df = pd.DataFrame(records)

    return df

# ==========================================
# UI
# ==========================================
uploaded_file = st.file_uploader("Upload GPay PDF", type=["pdf"])

if uploaded_file:

    st.info("⏳ Extracting transactions...")

    df = parse_pdf(uploaded_file)

    if df.empty:
        st.error("❌ Still no transactions — something unexpected")
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
