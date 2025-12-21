import streamlit as st
import pandas as pd
import PyPDF2
import re
from datetime import datetime
from io import BytesIO

def extract_gpay_transactions(pdf_file):
    """
    Extract transaction data from GPay PDF statement
    Uses regex pattern matching on the entire text
    """
    
    # Read PDF
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    all_text = ""
    
    # Extract text from all pages
    for page in pdf_reader.pages:
        all_text += page.extract_text() + "\n"
    
    transactions = []
    
    # Debug: Show first 500 chars
    st.write("**PDF Text Preview:**")
    st.code(all_text[:1000])
    
    # Pattern to match GPay transactions
    # Format: DD MMM, YYYY\nHH:MM AM/PM\nPaid to NAME\nUPI Transaction ID: XXX\nPaid by Bank XXX\n₹AMOUNT
    
    # More flexible pattern - match date, description, and amount
    pattern = r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec),?\s+\d{4}).*?(?:Paid to|Received from)\s+(.+?)(?:\n|UPI).*?₹\s*([\d,]+\.?\d*)'
    
    matches = re.findall(pattern, all_text, re.DOTALL | re.MULTILINE)
    
    st.write(f"**Found {len(matches)} potential transactions**")
    
    for match in matches:
        try:
            date_str, description, amount_str = match
            
            # Parse date
            date_clean = date_str.replace(',', '').strip()
            date = datetime.strptime(date_clean, '%d %b %Y')
            
            # Clean amount
            amount = float(amount_str.replace(',', ''))
            
            # Clean description - take first line only
            description = description.split('\n')[0].strip()
            
            # Skip rewards and self-transfers
            skip_keywords = ['Google Pay rewards', 'Self transfer', 'Google Play']
            if any(keyword in description for keyword in skip_keywords):
                continue
            
            # Auto-categorize
            category, sub_category = auto_categorize(description)
            
            transactions.append({
                'Date': date,
                'Description': description,
                'Amount': amount,
                'Type': 'Expense',
                'Category': category,
                'Sub Category': sub_category
            })
            
        except Exception as e:
            st.write(f"Error parsing: {e}")
            continue
    
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
                # Format the data to match your dashboard's expected format
                export_df = edited_df.copy()
                export_df = export_df.rename(columns={
                    'Date': 'Date',
                    'Description': 'Description',
                    'Amount': 'Amount',
                    'Category': 'Category',
                    'Sub Category': 'Sub Category'
                })
                # Keep only expense transactions for the dashboard
                export_df = export_df[export_df['Type'] == 'Expense']
                export_df = export_df[['Date', 'Description', 'Amount', 'Category', 'Sub Category']]
                
                export_df.to_excel(buffer, index=False)
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
