import streamlit as st
import pandas as pd
import PyPDF2
import re
from datetime import datetime
from io import BytesIO

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

# Enhanced PDF parsing function for concatenated text
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
        with st.expander("📄 View PDF Text Sample"):
            st.text(full_text[:1000])
        
        # Pattern to match transactions with concatenated text
        # Example: "01Oct,2025 PaidtoSudamaSupane ₹26 10:01AM UPITransactionID:564069511552 PaidbyCanaraBank7191"
        
        # Split by date pattern to get individual transactions
        date_pattern = r'(\d{2}[A-Z][a-z]{2},\d{4})'
        parts = re.split(date_pattern, full_text)
        
        current_date = ""
        
        for i in range(1, len(parts), 2):
            if i+1 >= len(parts):
                break
                
            date_str = parts[i]  # e.g., "01Oct,2025"
            content = parts[i+1]  # Rest of the transaction info
            
            # Convert date format: "01Oct,2025" to "01 Oct, 2025"
            date_match = re.match(r'(\d{2})([A-Z][a-z]{2}),(\d{4})', date_str)
            if date_match:
                current_date = f"{date_match.group(1)} {date_match.group(2)}, {date_match.group(3)}"
            else:
                continue
            
            # Extract time
            time_match = re.search(r'(\d{1,2}:\d{2}[AP]M)', content)
            time = time_match.group(1) if time_match else ""
            
            # Format time with space before AM/PM
            if time:
                time = re.sub(r'([AP]M)', r' \1', time)
            
            # Extract transaction type and name
            transaction_type = ""
            name = ""
            
            # Check for all possible transaction type patterns (case variations)
            if 'Paidto' in content or 'PaidTo' in content or 'Paid to' in content:
                transaction_type = "Paid"
                # Extract name between "Paidto" and "₹" or "UPI"
                name_match = re.search(r'Paid[tT]o\s*([^₹UPI]+)', content)
                if name_match:
                    name = name_match.group(1).strip()
                    # Add spaces before capital letters
                    name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
                    name = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', name)
            elif 'Receivedfrom' in content or 'ReceivedFrom' in content or 'Received from' in content:
                transaction_type = "Received"
                name_match = re.search(r'Received[fF]rom\s*([^₹UPI]+)', content)
                if name_match:
                    name = name_match.group(1).strip()
                    name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
                    name = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', name)
            elif 'Selftransfer' in content or 'SelfTransfer' in content or 'Self transfer' in content:
                transaction_type = "Self Transfer"
                name_match = re.search(r'Self[tT]ransfer[tT]o\s*([^₹UPI]+)', content)
                if name_match:
                    name = name_match.group(1).strip()
                    name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
                    name = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', name)
            
            # Extract amount
            amount_match = re.search(r'₹([\d,]+\.?\d*)', content)
            amount = 0
            if amount_match:
                amount = float(amount_match.group(1).replace(',', ''))
                if transaction_type == "Received":
                    amount = amount
                elif transaction_type in ["Paid", "Self Transfer"]:
                    amount = -amount
            
            # Extract UPI Transaction ID
            upi_match = re.search(r'UPITransactionID:(\d+)', content)
            upi_id = upi_match.group(1) if upi_match else ""
            
            # Extract Bank
            bank_match = re.search(r'(CanaraBank\d+|HDFCBank\d+)', content)
            bank = ""
            if bank_match:
                bank_raw = bank_match.group(1)
                # Add space: "CanaraBank7191" -> "Canara Bank 7191"
                bank = re.sub(r'([a-z])([A-Z])', r'\1 \2', bank_raw)
                bank = re.sub(r'([A-Z][a-z]+)([A-Z])', r'\1 \2', bank)
                bank = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', bank)
            
            if current_date and transaction_type and amount != 0:
                transactions.append({
                    'date': current_date,
                    'time': time,
                    'type': transaction_type,
                    'name': name,
                    'upi_id': upi_id,
                    'bank': bank,
                    'amount': amount
                })
        
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
