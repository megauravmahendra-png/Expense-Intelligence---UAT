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
# FINAL PARSER (STATE MACHINE - CORRECT)
# =========================================================
def parse_pdf(file):

    records = []

    with pdfplumber.open(file) as pdf:

        lines = []

        # Extract all lines cleanly
        for page in pdf.pages:
            text = page.extract_text() or ""
            page_lines = [l.strip() for l in text.split("\n") if l.strip()]
            lines.extend(page_lines)

    i = 0

    while i < len(lines):

        line = lines[i]

        # STEP 1: detect DATE
        if re.match(r"\d{2} \w{3}, \d{4}", line):

            try:
                date = pd.to_datetime(line, format="%d %b, %Y", errors="coerce")

                # STEP 2: TIME
                time = ""
                if i+1 < len(lines) and re.search(r"\d{1,2}:\d{2}", lines[i+1]):
                    time = lines[i+1]

                txn_type = "Other"
                description = "Unknown"
                upi_id = ""
                amount = None

                j = i + 1

                # STEP 3: walk until next transaction
                while j < len(lines):

                    current = lines[j]

                    # Stop when next date found
                    if j != i and re.match(r"\d{2} \w{3}, \d{4}", current):
                        break

                    # TYPE + NAME
                    if "Paid to" in current:
                        txn_type = "Debit"
                        description = current.replace("Paid to", "").strip()

                    elif "Received from" in current:
                        txn_type = "Credit"
                        description = current.replace("Received from", "").strip()

                    elif "Self transfer" in current:
                        txn_type = "Self"
                        description = "Self Transfer"

                    # UPI ID
                    if "UPI Transaction ID" in current:
                        upi_id = current.split(":")[-1].strip()

                    # AMOUNT
                    if "₹" in current:
                        amt = re.sub(r"[^\d.]", "", current)
                        if amt:
                            amount = float(amt)

                    j += 1

                # SAVE only valid
                if amount is not None:
                    records.append({
                        "Date": date,
                        "Time": time,
                        "Description": description,
                        "Type": txn_type,
                        "Amount": amount,
                        "UPI_ID": upi_id
                    })

                i = j
                continue

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
