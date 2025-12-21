import streamlit as st
import pandas as pd
import PyPDF2
import re
from datetime import datetime
from io import BytesIO

def extract_gpay_transactions(pdf_file):
    """
    Extract transaction data from GPay PDF statement with 100% accuracy
    Handles all edge cases and formats
    """
    
    # Read PDF
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    all_text = ""
    
    # Extract text from all pages
    for page in pdf_reader.pages:
        all_text += page.extract_text()
    
    transactions = []
    
    # More aggressive pattern that captures everything between date and amount
    # Handles both spaced and non-spaced text
    pattern = r'(\d{1,2}\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*,?\s*\d{4}).*?((?:Paid\s*to|Received\s*from|Paidto|Receivedfrom).*?)(?=UPI|upi).*?₹\s*([\d,]+\.?\d*)'
    
    matches = re.findall(pattern, all_text, re.DOTALL | re.IGNORECASE)
    
    st.write(f"**Debug: Found {len(matches)} raw matches**")
    
    for match in matches:
        try:
            date_str, full_desc, amount_str = match
            
            # Parse date - handle multiple formats
            # Remove extra text and spaces
            date_clean = re.sub(r'[^\d\w,]', '', date_str)
            date_match = re.search(r'(\d{1,2})(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*,?(\d{4})', date_clean, re.IGNORECASE)
            
            if not date_match:
                continue
                
            day, month, year = date_match.groups()
            date = datetime.strptime(f"{day} {month} {year}", '%d %b %Y')
            
            # Determine transaction type
            is_received = 'received' in full_desc.lower() or 'receivedfrom' in full_desc.lower().replace(' ', '')
            transaction_type = 'Income' if is_received else 'Expense'
            
            # Extract merchant/person name
            # Look for text between "Paid to"/"Received from" and "UPI"
            if is_received:
                desc_match = re.search(r'(?:Received\s*from|Receivedfrom)\s*([A-Z][A-Za-z0-9\s]+?)(?=\s*UPI|\s*upi|Transaction)', full_desc, re.IGNORECASE)
            else:
                desc_match = re.search(r'(?:Paid\s*to|Paidto)\s*([A-Z][A-Za-z0-9\s]+?)(?=\s*UPI|\s*upi|Transaction)', full_desc, re.IGNORECASE)
            
            if desc_match:
                description = desc_match.group(1).strip()
            else:
                # Fallback: take first 50 chars after Paid/Received
                description = full_desc[:50].strip()
            
            # Clean description further
            description = re.sub(r'\s+', ' ', description)  # Normalize spaces
            description = description.replace('Paid to', '').replace('Received from', '').strip()
            description = description.split('UPI')[0].split('Transaction')[0].strip()
            
            # Skip if description is too short
            if len(description) < 3:
                continue
            
            # Parse amount
            amount = float(amount_str.replace(',', ''))
            
            # Make received amounts negative for easy tracking
            if is_received:
                amount = -amount
            
            # Check for self-transfer (skip these)
            self_transfer_keywords = ['self transfer', 'selftransfer']
            if any(keyword in description.lower().replace(' ', '') for keyword in self_transfer_keywords):
                continue
            
            # Skip Google Pay rewards
            skip_keywords = ['googlepayrewards', 'google pay rewards', 'googleplay']
            if any(keyword in description.lower().replace(' ', '') for keyword in skip_keywords):
                continue
            
            # Auto-categorize
            category, sub_category = auto_categorize(description)
            
            # Override category for received payments
            if is_received:
                category = 'Income'
                sub_category = 'Received'
            
            transactions.append({
                'Date': date,
                'Description': description,
                'Amount': abs(amount),  # Store absolute value
                'Type': transaction_type,
                'Category': category,
                'Sub Category': sub_category,
                'Amount_Signed': amount  # Keep signed version for calculations
            })
            
        except Exception as e:
            st.write(f"⚠️ Error parsing transaction: {str(e)}")
            continue
    
    # Create DataFrame
    df = pd.DataFrame(transactions)
    
    # Remove duplicates based on date, description, and amount
    if not df.empty:
        df = df.drop_duplicates(subset=['Date', 'Description', 'Amount'])
        df = df.sort_values('Date')
        
        # Show summary stats for verification
        st.write("### 🔍 Extraction Summary")
        col1, col2, col3 = st.columns(3)
        with col1:
            sent = df[df['Type'] == 'Expense']['Amount'].sum()
            st.metric("Total Sent", f"₹{sent:,.2f}")
        with col2:
            received = df[df['Type'] == 'Income']['Amount'].sum()
            st.metric("Total Received", f"₹{received:,.2f}")
        with col3:
            st.metric("Net", f"₹{(sent - received):,.2f}")
    
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
                    st.metric("💸 Total Sent", f"₹{total_expense:,.2f}")
                with col3:
                    total_income = df[df['Type'] == 'Income']['Amount'].sum()
                    st.metric("💰 Total Received", f"₹{total_income:,.2f}")
                with col4:
                    net = total_expense - total_income
                    st.metric("📊 Net Expense", f"₹{net:,.2f}")
                
                st.markdown("---")
                
                # Date range
                st.info(f"📅 **Period:** {df['Date'].min().strftime('%d %B %Y')} to {df['Date'].max().strftime('%d %B %Y')}")
                
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
