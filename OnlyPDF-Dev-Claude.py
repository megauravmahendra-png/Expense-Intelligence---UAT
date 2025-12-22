import streamlit as st
import pandas as pd
import PyPDF2
import re
from datetime import datetime
from io import BytesIO
import pdfplumber

# Page configuration
st.set_page_config(
    page_title="Google Pay PDF to Excel Converter",
    page_icon="📊",
    layout="wide"
)

# Title and description
st.title("📊 Google Pay Transaction Analyzer")
st.markdown("Upload your Google Pay transaction statement PDF to view and export data")

# Category mapping function
def categorize_transaction(name):
    name_lower = name.lower()
    
    if any(word in name_lower for word in ['zomato', 'swiggy', 'dominos', 'pizza']):
        return 'Food Delivery'
    elif any(word in name_lower for word in ['blinkit', 'zepto', 'dmart', 'grocery']):
        return 'Groceries'
    elif any(word in name_lower for word in ['railway', 'irctc', 'rapido', 'metro', 'uber', 'ola']):
        return 'Transport'
    elif any(word in name_lower for word in ['pvr', 'inox', 'spotify', 'ott', 'netflix', 'prime']):
        return 'Entertainment'
    elif any(word in name_lower for word in ['airtel', 'jio', 'vodafone', 'electricity', 'gas']):
        return 'Utilities'
    elif any(word in name_lower for word in ['pharmacy', 'medical', 'hospital', 'clinic']):
        return 'Healthcare'
    elif any(word in name_lower for word in ['openai', 'subscription']):
        return 'Subscription'
    elif any(word in name_lower for word in ['hotel', 'restaurant', 'cafe', 'bakery', 'food']):
        return 'Food & Dining'
    elif any(word in name_lower for word in ['shop', 'store', 'mall', 'retail']):
        return 'Shopping'
    elif any(word in name_lower for word in ['blue dart', 'dhl', 'shiprocket', 'courier']):
        return 'Courier'
    else:
        return 'Personal'

# Get day of week
def get_day_of_week(date_str):
    try:
        months = {
            'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
            'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
        }
        
        parts = date_str.split()
        day = int(parts[0])
        month = months[parts[1].replace(',', '')]
        year = int(parts[2])
        
        date_obj = datetime(year, month, day)
        return date_obj.strftime('%A')
    except:
        return 'Unknown'

# Enhanced PDF parsing function
def parse_gpay_pdf(pdf_file):
    transactions = []
    
    try:
        # Try with pdfplumber first (better text extraction)
        try:
            import pdfplumber
            with pdfplumber.open(pdf_file) as pdf:
                full_text = ""
                for page in pdf.pages:
                    full_text += page.extract_text() + "\n"
        except:
            # Fallback to PyPDF2
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            full_text = ""
            for page in pdf_reader.pages:
                full_text += page.extract_text() + "\n"
        
        # Debug: Show extracted text sample
        st.write("📄 PDF Text Sample (first 500 chars):")
        st.text(full_text[:500])
        
        lines = full_text.split('\n')
        
        current_date = ""
        current_time = ""
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Skip empty lines and headers
            if not line or 'Transaction statement' in line or 'Page' in line or 'megauravmahendra' in line:
                continue
            
            # Pattern 1: Date and Time on same line (e.g., "01 Oct, 2025 10:01 AM")
            date_time_match = re.match(r'(\d{2}\s+\w{3},\s+\d{4})\s+(\d{1,2}:\d{2}\s+[AP]M)', line)
            if date_time_match:
                current_date = date_time_match.group(1)
                current_time = date_time_match.group(2)
                continue
            
            # Pattern 2: Date only
            date_match = re.match(r'(\d{2}\s+\w{3},\s+\d{4})', line)
            if date_match:
                current_date = date_match.group(1)
                continue
            
            # Pattern 3: Time only
            time_match = re.match(r'(\d{1,2}:\d{2}\s+[AP]M)', line)
            if time_match:
                current_time = time_match.group(1)
                continue
            
            # Look for transaction patterns
            if any(keyword in line for keyword in ['Paid to', 'Received from', 'Self transfer']):
                transaction = {
                    'date': current_date,
                    'time': current_time,
                    'type': '',
                    'name': '',
                    'upi_id': '',
                    'bank': '',
                    'amount': 0
                }
                
                # Determine transaction type and name
                if 'Paid to' in line:
                    transaction['type'] = 'Paid'
                    transaction['name'] = line.replace('Paid to', '').strip()
                elif 'Received from' in line:
                    transaction['type'] = 'Received'
                    transaction['name'] = line.replace('Received from', '').strip()
                elif 'Self transfer' in line:
                    transaction['type'] = 'Self Transfer'
                    transaction['name'] = line.replace('Self transfer to', '').strip()
                
                # Look ahead for UPI ID, Bank, and Amount
                for j in range(i+1, min(i+10, len(lines))):
                    next_line = lines[j].strip()
                    
                    # UPI Transaction ID
                    if 'UPI Transaction ID:' in next_line:
                        transaction['upi_id'] = next_line.replace('UPI Transaction ID:', '').strip()
                    
                    # Bank account
                    bank_match = re.search(r'(Canara Bank \d+|HDFC Bank \d+)', next_line)
                    if bank_match:
                        transaction['bank'] = bank_match.group(1)
                    
                    # Amount
                    amount_match = re.search(r'₹\s*([\d,]+\.?\d*)', next_line)
                    if amount_match:
                        amount = float(amount_match.group(1).replace(',', ''))
                        if transaction['type'] == 'Received':
                            transaction['amount'] = amount
                        else:
                            transaction['amount'] = -amount
                        break
                
                if transaction['date'] and transaction['amount'] != 0:
                    transactions.append(transaction)
        
        return transactions
    
    except Exception as e:
        st.error(f"Error parsing PDF: {str(e)}")
        import traceback
        st.text(traceback.format_exc())
        return []

# Convert to DataFrame
def create_dataframe(transactions):
    data = []
    for txn in transactions:
        data.append({
            'Date': txn.get('date', ''),
            'Time': txn.get('time', ''),
            'Day of Week': get_day_of_week(txn.get('date', '')),
            'Transaction Type': txn.get('type', ''),
            'Payee/Payer Name': txn.get('name', ''),
            'UPI Transaction ID': txn.get('upi_id', ''),
            'Bank Account': txn.get('bank', ''),
            'Amount (₹)': txn.get('amount', 0),
            'Category': categorize_transaction(txn.get('name', '')),
            'Notes': ''
        })
    
    return pd.DataFrame(data)

# Convert DataFrame to Excel
@st.cache_data
def convert_df_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Transactions')
        
        # Auto-adjust columns width
        worksheet = writer.sheets['Transactions']
        for idx, col in enumerate(df.columns):
            max_length = max(
                df[col].astype(str).map(len).max(),
                len(col)
            )
            worksheet.column_dimensions[chr(65 + idx)].width = min(max_length + 2, 50)
    
    return output.getvalue()

# Main app
uploaded_file = st.file_uploader("Upload Google Pay PDF Statement", type=['pdf'])

if uploaded_file is not None:
    with st.spinner('Processing PDF...'):
        transactions = parse_gpay_pdf(uploaded_file)
        
        st.write(f"🔍 Found {len(transactions)} transactions")
        
        if transactions:
            df = create_dataframe(transactions)
            
            # Display summary statistics
            st.success(f"✅ Successfully extracted {len(transactions)} transactions")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                total_sent = df[df['Amount (₹)'] < 0]['Amount (₹)'].sum()
                st.metric("Total Sent", f"₹{abs(total_sent):,.2f}")
            
            with col2:
                total_received = df[df['Amount (₹)'] > 0]['Amount (₹)'].sum()
                st.metric("Total Received", f"₹{total_received:,.2f}")
            
            with col3:
                net_balance = total_received + total_sent
                st.metric("Net Balance", f"₹{net_balance:,.2f}")
            
            # Category breakdown
            st.subheader("📊 Spending by Category")
            category_df = df[df['Amount (₹)'] < 0].groupby('Category')['Amount (₹)'].sum().abs().sort_values(ascending=False)
            
            if not category_df.empty:
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.bar_chart(category_df)
                
                with col2:
                    st.dataframe(category_df.reset_index().rename(columns={'Amount (₹)': 'Total Spent (₹)'}), use_container_width=True)
            
            # Display transactions table
            st.subheader("📋 Transaction Details")
            
            # Filters
            col1, col2, col3 = st.columns(3)
            
            with col1:
                transaction_type_filter = st.multiselect(
                    "Filter by Type",
                    options=df['Transaction Type'].unique(),
                    default=df['Transaction Type'].unique()
                )
            
            with col2:
                category_filter = st.multiselect(
                    "Filter by Category",
                    options=df['Category'].unique(),
                    default=df['Category'].unique()
                )
            
            with col3:
                min_amount = float(df['Amount (₹)'].min())
                max_amount = float(df['Amount (₹)'].max())
                amount_range = st.slider(
                    "Amount Range",
                    min_value=min_amount,
                    max_value=max_amount,
                    value=(min_amount, max_amount)
                )
            
            # Apply filters
            filtered_df = df[
                (df['Transaction Type'].isin(transaction_type_filter)) &
                (df['Category'].isin(category_filter)) &
                (df['Amount (₹)'] >= amount_range[0]) &
                (df['Amount (₹)'] <= amount_range[1])
            ]
            
            # Display filtered data
            st.dataframe(filtered_df, use_container_width=True, height=400)
            
            # Export options
            st.subheader("💾 Export Options")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Export as Excel
                excel_data = convert_df_to_excel(filtered_df)
                st.download_button(
                    label="📥 Download as Excel",
                    data=excel_data,
                    file_name="gpay_transactions.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
            with col2:
                # Export as CSV
                csv = filtered_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download as CSV",
                    data=csv,
                    file_name="gpay_transactions.csv",
                    mime="text/csv"
                )
        
        else:
            st.error("❌ No transactions found in the PDF. Please check the file format.")
            st.info("💡 Tip: Make sure you're uploading a Google Pay transaction statement PDF")

else:
    # Instructions
    st.info("👆 Please upload your Google Pay transaction statement PDF to begin")
    
    with st.expander("ℹ️ How to use this app"):
        st.markdown("""
        1. **Download** your Google Pay transaction statement:
           - Open Google Pay app
           - Go to Profile → Payment activity → Download statement
        
        2. **Upload** the PDF file using the uploader above
        
        3. **View** your transactions with interactive filters and analytics
        
        4. **Export** the data as Excel or CSV for further analysis
        
        **Features:**
        - Automatic transaction categorization
        - Spending analytics and visualizations
        - Interactive filters (Type, Category, Amount)
        - Export to Excel/CSV
        - Summary statistics
        """)
    
    with st.expander("📋 Excel Columns"):
        st.markdown("""
        The exported Excel file will contain these columns:
        - **Date**: Transaction date
        - **Time**: Transaction time
        - **Day of Week**: Calculated day
        - **Transaction Type**: Paid/Received/Self Transfer
        - **Payee/Payer Name**: Merchant or person name
        - **UPI Transaction ID**: Unique transaction identifier
        - **Bank Account**: Source/destination bank
        - **Amount (₹)**: Transaction amount (negative for payments)
        - **Category**: Auto-categorized spending category
        - **Notes**: Empty field for your personal notes
        """)
