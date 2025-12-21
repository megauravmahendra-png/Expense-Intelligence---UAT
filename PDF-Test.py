import streamlit as st
import pandas as pd
import PyPDF2
import re
from datetime import datetime
from io import BytesIO

def extract_gpay_transactions(pdf_file):
    """
    Extract transaction data from GPay PDF statement
    Returns a DataFrame with Date, Description, Amount, Category, Sub Category
    """
    
    # Read PDF
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    all_text = ""
    
    # Extract text from all pages
    for page in pdf_reader.pages:
        all_text += page.extract_text()
    
    transactions = []
    
    # Common GPay statement patterns
    # Pattern 1: Date | Description | Amount
    # Example: "12 Dec 2024 Swiggy ₹450.00"
    pattern1 = r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})\s+(.+?)\s+₹\s*([\d,]+\.?\d*)'
    
    # Pattern 2: Alternative format
    # Example: "2024-12-12 | Restaurant Name | 450.00"
    pattern2 = r'(\d{4}-\d{2}-\d{2})\s*\|\s*(.+?)\s*\|\s*₹?\s*([\d,]+\.?\d*)'
    
    # Try pattern 1
    matches = re.findall(pattern1, all_text, re.MULTILINE)
    
    if not matches:
        # Try pattern 2
        matches = re.findall(pattern2, all_text, re.MULTILINE)
    
    for match in matches:
        date_str, description, amount_str = match
        
        # Parse date
        try:
            if '-' in date_str:
                date = datetime.strptime(date_str, '%Y-%m-%d')
            else:
                date = datetime.strptime(date_str, '%d %b %Y')
        except:
            continue
        
        # Clean amount
        amount = float(amount_str.replace(',', ''))
        
        # Clean description
        description = description.strip()
        
        # Auto-categorize based on keywords
        category, sub_category = auto_categorize(description)
        
        transactions.append({
            'Date': date,
            'Description': description,
            'Amount': amount,
            'Category': category,
            'Sub Category': sub_category
        })
    
    # Create DataFrame
    df = pd.DataFrame(transactions)
    
    return df

def auto_categorize(description):
    """
    Auto-categorize transactions based on merchant name/description
    """
    description_lower = description.lower()
    
    # Food & Dining
    if any(word in description_lower for word in ['swiggy', 'zomato', 'restaurant', 'cafe', 'food', 'dominos', 'pizza', 'mcdonald', 'kfc', 'subway']):
        return 'Food & Dining', 'Food Delivery'
    
    # Shopping
    if any(word in description_lower for word in ['amazon', 'flipkart', 'myntra', 'ajio', 'shop', 'store', 'mall']):
        return 'Shopping', 'Online Shopping'
    
    # Transportation
    if any(word in description_lower for word in ['uber', 'ola', 'rapido', 'metro', 'petrol', 'fuel', 'parking']):
        return 'Transportation', 'Cab/Auto'
    
    # Entertainment
    if any(word in description_lower for word in ['netflix', 'amazon prime', 'hotstar', 'spotify', 'movie', 'cinema', 'pvr', 'inox']):
        return 'Entertainment', 'Streaming/Movies'
    
    # Bills & Utilities
    if any(word in description_lower for word in ['electricity', 'water', 'gas', 'broadband', 'internet', 'mobile', 'recharge', 'jio', 'airtel', 'vi']):
        return 'Bills & Utilities', 'Mobile/Internet'
    
    # Healthcare
    if any(word in description_lower for word in ['pharma', 'medicine', 'hospital', 'clinic', 'doctor', 'apollo', 'medplus']):
        return 'Healthcare', 'Medicines'
    
    # Default
    return 'Uncategorized', 'Uncategorized'


# =========================================================
# STREAMLIT UI FOR PDF UPLOAD
# =========================================================

st.title("📄 GPay PDF Statement Extractor")

st.markdown("""
Upload your Google Pay PDF statement and we'll automatically extract all transactions!

**Features:**
- Auto-extracts Date, Description, and Amount
- Auto-categorizes transactions (Food, Shopping, Transport, etc.)
- Exports to Excel format ready for the dashboard
""")

uploaded_pdf = st.file_uploader("Upload GPay PDF Statement", type=['pdf'])

if uploaded_pdf:
    with st.spinner("Extracting transactions from PDF..."):
        try:
            df = extract_gpay_transactions(uploaded_pdf)
            
            if not df.empty:
                st.success(f"✅ Extracted {len(df)} transactions!")
                
                # Show preview
                st.markdown("### 📊 Preview")
                st.dataframe(df, use_container_width=True)
                
                # Summary
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Transactions", len(df))
                with col2:
                    st.metric("Total Amount", f"₹{df['Amount'].sum():,.0f}")
                with col3:
                    st.metric("Date Range", f"{df['Date'].min().strftime('%d %b')} - {df['Date'].max().strftime('%d %b')}")
                
                # Category breakdown
                st.markdown("### 📈 Category Breakdown")
                cat_summary = df.groupby('Category')['Amount'].sum().reset_index()
                cat_summary = cat_summary.sort_values('Amount', ascending=False)
                st.dataframe(cat_summary, use_container_width=True)
                
                # Allow editing
                st.markdown("### ✏️ Edit Categories (Optional)")
                edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic")
                
                # Download as Excel
                st.markdown("### 💾 Download")
                
                buffer = BytesIO()
                edited_df.to_excel(buffer, index=False)
                buffer.seek(0)
                
                st.download_button(
                    label="📥 Download as Excel",
                    data=buffer,
                    file_name=f"gpay_transactions_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
                st.info("💡 Upload this Excel file to your Google Drive folder to include it in your dashboard!")
                
            else:
                st.error("❌ No transactions found in the PDF. Please check the file format.")
                
        except Exception as e:
            st.error(f"❌ Error processing PDF: {str(e)}")
            st.info("💡 Make sure you're uploading a valid Google Pay statement PDF")

st.markdown("---")
st.markdown("**Note:** This extractor works with standard GPay statement formats. If your PDF format is different, contact support.")
