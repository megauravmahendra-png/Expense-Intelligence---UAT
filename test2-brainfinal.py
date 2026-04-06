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
st.title("🧪 GPay PDF Debug Mode")

# ==========================================
# DEBUG PARSER
# ==========================================
def debug_parse_pdf(file):

    records = []
    debug_logs = []

    with pdfplumber.open(file) as pdf:

        all_lines = []

        for page_num, page in enumerate(pdf.pages):

            text = page.extract_text() or ""

            # Show raw page text
            st.subheader(f"📄 Page {page_num+1} Raw Text")
            st.text(text[:2000])  # limit for UI

            # Normalize text
            text = re.sub(r'(?<=\d)(?=[A-Za-z])', ' ', text)
            text = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', text)

            lines = [l.strip() for l in text.split("\n") if l.strip()]

            all_lines.extend(lines)

        # Show extracted lines
        st.subheader("🧾 Extracted Lines")
        st.write(all_lines[:50])  # show first 50

        i = 0
        while i < len(all_lines) - 1:

            line1 = all_lines[i]
            line2 = all_lines[i+1]

            # Log what we are checking
            debug_logs.append(f"Checking: {line1} || {line2}")

            # CONDITION CHECK
            if "₹" in line1:

                debug_logs.append(f"💰 Found ₹ in: {line1}")

                try:
                    date_match = re.search(r'\d{1,2}[A-Za-z]{3},\d{4}', line1)

                    if not date_match:
                        debug_logs.append("❌ Date NOT found")
                        i += 1
                        continue

                    debug_logs.append(f"✅ Date Found: {date_match.group()}")

                    amt_match = re.search(r'₹\s*([\d,]+\.?\d*)', line1)

                    if not amt_match:
                        debug_logs.append("❌ Amount NOT found")
                        i += 1
                        continue

                    amount = float(amt_match.group(1).replace(",", ""))

                    # TYPE
                    if "Paidto" in line1 or "Paid to" in line1:
                        txn_type = "Debit"
                    elif "Receivedfrom" in line1 or "Received from" in line1:
                        txn_type = "Credit"
                    else:
                        txn_type = "Other"

                    # TIME
                    time_match = re.search(r'\d{1,2}:\d{2}[AP]M', line2)
                    if not time_match:
                        debug_logs.append("❌ Time NOT found")
                    else:
                        debug_logs.append(f"✅ Time Found: {time_match.group()}")

                    # UPI
                    upi_match = re.search(r'UPI\s*Transaction\s*ID:\s*(\d+)', line2)
                    if not upi_match:
                        debug_logs.append("❌ UPI NOT found")
                    else:
                        debug_logs.append(f"✅ UPI Found: {upi_match.group(1)}")

                    # Save anyway for testing
                    records.append({
                        "Raw_Line": line1,
                        "Next_Line": line2,
                        "Amount": amount,
                        "Type": txn_type
                    })

                except Exception as e:
                    debug_logs.append(f"❌ Error: {str(e)}")

            i += 1

    df = pd.DataFrame(records)

    return df, debug_logs

# ==========================================
# UI
# ==========================================
uploaded_file = st.file_uploader("Upload GPay PDF", type=["pdf"])

if uploaded_file:

    st.info("⏳ Running Debug Mode...")

    df, logs = debug_parse_pdf(uploaded_file)

    st.subheader("📊 Extracted (Partial)")
    st.dataframe(df)

    st.subheader("🧠 Debug Logs")
    for log in logs[:200]:
        st.write(log)

    if df.empty:
        st.error("❌ Still no structured extraction — check logs above")
