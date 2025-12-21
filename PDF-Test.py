import streamlit as st
import pandas as pd
import PyPDF2
import re
from datetime import datetime
from io import BytesIO

def extract_gpay_transactions(pdf_file):
    """
    Extract transaction data from GPay PDF statement
    Format: Date & time | Transaction details | Amount
    """
    
    # Read PDF
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    all_text = ""
    
    # Extract text from all pages
    for page in pdf_reader.pages:
        all_text += page.extract_text() + "\n"
    
    transactions = []
    
    # Split into lines
    lines = all_text.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Pattern: "DD MMM, YYYY" or "DD MMM, YYYY\nHH:MM AM/PM"
        date_pattern = r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec),?\s+\d{4})'
        
        if re.match(date_pattern, line):
            try:
                # Get date
                date_str = line
                
                # Get time (next line)
                i += 1
                time_str = lines[i].strip() if i < len(lines) else ""
                
                # Get transaction details (next line)
                i += 1
                description = lines[i].strip() if i < len(lines) else ""
                
                # Skip UPI Transaction ID line
                i += 1
                if i < len(lines) and "UPI Transaction ID" in lines[i]:
                    i += 1
                
                # Skip "Paid by/to" line
                if i < len(lines) and ("Paid by" in lines[i] or "Paid to" in lines[i]):
                    i += 1
                
                # Get amount (should be on current line)
                amount_line = lines[i].strip() if i < len(lines) else ""
                
                # Extract amount using pattern ₹X,XXX or ₹XXX.XX
                amount_match = re.search(r'₹\s*([\d,]+\.?\d*)', amount_line)
                
                if amount_match:
                    amount_str = amount_match.group(1).replace(',', '')
                    amount = float(amount_str)
                    
                    # Parse date
                    try:
                        # Handle both "01 Jun, 2025" and "01 Jun 2025"
                        date_clean = date_str.replace(',', '').strip()
                        date = datetime.strptime(date_clean, '%d %b %Y')
                    except:
                        i += 1
                        continue
                    
                    # Clean description (remove "Paid to" or "Received from")
                    description = description.replace('Paid to ', '').replace('Received from ', '').strip()
                    
                    # Skip if it's a reward, self-transfer, or Google Pay related
                    skip_keywords = ['Google Pay rewards', 'Self transfer']
                    if any(keyword in description for keyword in skip_keywords):
                        i += 1
                        continue
                    
                    # Determine if it's income or expense
                    transaction_type = 'Expense'
                    if 'Received from' in lines[i-3] if i >= 3 else False:
                        transaction_type = 'Income'
                    
                    # Auto-categorize
                    category, sub_category = auto_categorize(description)
                    
                    transactions.append({
                        'Date': date,
                        'Description': description,
                        'Amount': amount,
                        'Type': transaction_type,
                        'Category': category,
                        'Sub Category': sub_category
                    })
            except Exception as e:
                pass
        
        i += 1
    
    # Create DataFrame
    df = pd.DataFrame(transactions)
    
    # Remove duplicates
    if not df.empty:
        df = df.drop_duplicates(subset=['Date', 'Description', 'Amount'])
        df = df.sort_values('Date')
    
    return df

def auto_categorize(description):
    """Auto-categorize transactions based on merchant name"""
    desc_lower = description.lower()
    
    # Food & Dining
    food_keywords = ['swiggy', 'zomato', 'restaurant', 'cafe', 'food', 'dominos', 'pizza', 
                     'burger', 'mcdonald', 'kfc', 'subway', 'biryani', 'kitchen', 'dhaba',
                     'mama mea', 'jumboking', 'belgian waffle', 'pvr inox', 'cinepolis',
                     'chaayos', 'juice', 'parathe', 'misthan', 'golgappe', 'chat', 'bhaji']
    if any(word in desc_lower for word in food_keywords):
        return 'Food & Dining', 'Food Delivery/Restaurant'
    
    # Shopping
    shopping_keywords = ['amazon', 'flipkart', 'myntra', 'ajio', 'meesho', 'blinkit', 
                         'zepto', 'dmart', 'store', 'kirana', 'general', 'market', 'mall',
                         'supermarket', 'trading', 'enterprises', 'shop']
    if any(word in desc_lower for word in shopping_keywords):
        return 'Shopping', 'Online/Retail Shopping'
    
    # Transportation
    transport_keywords = ['uber', 'ola', 'rapido', 'metro', 'railway', 'irctc', 'petrol', 
                          'fuel', 'parking', 'redbus', 'mmrda', 'train', 'bus']
    if any(word in desc_lower for word in transport_keywords):
        return 'Transportation', 'Cab/Metro/Train'
    
    # Entertainment
    entertainment_keywords = ['netflix', 'amazon prime', 'hotstar', 'spotify', 'movie', 
                              'cinema', 'pvr', 'inox', 'ott play', 'kukufm', 'gaming']
    if any(word in desc_lower for word in entertainment_keywords):
        return 'Entertainment', 'Streaming/Movies'
    
    # Bills & Utilities
    bills_keywords = ['electricity', 'water', 'gas', 'broadband', 'internet', 'mobile', 
                      'recharge', 'jio', 'airtel', 'vi', 'prepaid', 'postpaid', 'payments bank']
    if any(word in desc_lower for word in bills_keywords):
        return 'Bills & Utilities', 'Mobile/Internet'
    
    # Healthcare
    health_keywords = ['pharma', 'medicine', 'hospital', 'clinic', 'doctor', 'medical', 
                       'apollo', 'medplus', 'chemist', 'druggist']
    if any(word in desc_lower for word in health_keywords):
        return 'Healthcare', 'Medicines/Doctor'
    
    # Education
    education_keywords = ['physicswallah', 'iit', 'college', 'university', 'course', 
                          'tuition', 'coaching', 'openai', 'chatgpt']
    if any(word in desc_lower for word in education_keywords):
        return 'Education', 'Courses/Fees'
    
    # Fitness
    fitness_keywords = ['gym', 'fitness', 'sports', 'yoga', 'workout', 'banga sports']
    if any(word in desc_lower for word in fitness_keywords):
        return 'Personal Care', 'Fitness/Gym'
    
    # Personal (Individual names - likely friends/family)
    if any(word in desc_lower for word in ['ishika', 'aviral', 'twinkle', 'salahuddin', 
                                            'gaurav', 'dev mahendra', 'briz']):
        return 'Personal', 'Friends/Family'
    
    # Default
    return 'Uncategorized', 'Uncategorized'


# =========================================================
# STREAMLIT UI
# =========================================================

st.title("📄 GPay PDF Statement Extractor")

st.markdown("""
Upload your Google Pay PDF statement and automatically extract all transactions!

**Features:**
- ✅ Auto-extracts Date, Description, Amount, Type
- ✅ Auto-categorizes transactions intelligently
- ✅ Exports to Excel format ready for dashboard
- ✅ Filters out rewards & self-transfers
""")

st.markdown("---")

uploaded_pdf = st.file_uploader("📎 Upload GPay PDF Statement", type=['pdf'])

if uploaded_pdf:
    with st.spinner("🔄 Extracting transactions from PDF..."):
        try:
            df = extract_gpay_transactions(uploaded_pdf)
            
            if not df.empty:
                st.success(f"✅ Successfully extracted **{len(df)} transactions**!")
                
                # Summary metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Transactions", len(df))
                with col2:
                    total_expense = df[df['Type'] == 'Expense']['Amount'].sum()
                    st.metric("Total Expenses", f"₹{total_expense:,.0f}")
                with col3:
                    total_income = df[df['Type'] == 'Income']['Amount'].sum()
                    st.metric("Total Income", f"₹{total_income:,.0f}")
                with col4:
                    date_range = f"{df['Date'].min().strftime('%d %b')} - {df['Date'].max().strftime('%d %b')}"
                    st.metric("Date Range", date_range)
                
                st.markdown("---")
                
                # Preview
                st.markdown("### 📊 Transaction Preview")
                st.dataframe(df.head(20), use_container_width=True)
                
                # Category breakdown
                st.markdown("### 📈 Category Summary")
                col1, col2 = st.columns(2)
                
                with col1:
                    expenses = df[df['Type'] == 'Expense']
                    if not expenses.empty:
                        cat_summary = expenses.groupby('Category')['Amount'].sum().reset_index()
                        cat_summary = cat_summary.sort_values('Amount', ascending=False)
                        cat_summary['Amount'] = cat_summary['Amount'].apply(lambda x: f"₹{x:,.0f}")
                        st.dataframe(cat_summary, use_container_width=True, hide_index=True)
                
                with col2:
                    # Top merchants
                    st.markdown("**Top 10 Merchants**")
                    top_merchants = expenses.groupby('Description')['Amount'].sum().reset_index()
                    top_merchants = top_merchants.sort_values('Amount', ascending=False).head(10)
                    top_merchants['Amount'] = top_merchants['Amount'].apply(lambda x: f"₹{x:,.0f}")
                    st.dataframe(top_merchants, use_container_width=True, hide_index=True)
                
                st.markdown("---")
                
                # Edit categories
                st.markdown("### ✏️ Edit Categories (Optional)")
                st.info("💡 You can edit the categories below before downloading")
                edited_df = st.data_editor(df, use_container_width=True, num_rows="fixed")
                
                # Download
                st.markdown("### 💾 Download Excel")
                
                buffer = BytesIO()
                edited_df.to_excel(buffer, index=False)
                buffer.seek(0)
                
                filename = f"gpay_transactions_{df['Date'].min().strftime('%Y%m')}_to_{df['Date'].max().strftime('%Y%m')}.xlsx"
                
                st.download_button(
                    label="📥 Download Excel File",
                    data=buffer,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
                
                st.success("✅ Upload this Excel file to your Google Drive folder to include it in your dashboard!")
                
            else:
                st.error("❌ No transactions found in the PDF. Please check the file format.")
                st.info("💡 Make sure you're uploading a valid Google Pay transaction statement PDF")
                
        except Exception as e:
            st.error(f"❌ Error processing PDF: {str(e)}")
            st.info("💡 Please make sure you're uploading a Google Pay statement PDF")

else:
    st.info("👆 Upload your GPay PDF statement to get started")

st.markdown("---")
st.markdown("**📝 Note:** This tool works with standard GPay transaction statement PDFs. Rewards and self-transfers are automatically filtered out.")
