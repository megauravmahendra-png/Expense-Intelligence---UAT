import streamlit as st
import pandas as pd
import PyPDF2
import re
from datetime import datetime
from io import BytesIO

def extract_gpay_transactions(pdf_file):
    """
    Extract transaction data from GPay PDF statement
    Focus on Send/Receive KPIs
    """
    
    # Read PDF
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    all_text = ""
    
    # Extract text from all pages
    for page in pdf_reader.pages:
        all_text += page.extract_text()
    
    transactions = []
    
    # Enhanced pattern to capture all transaction variations
    # This pattern is more flexible to handle various PDF formatting issues
    pattern = r'(\d{1,2}\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*,?\s*\d{4}).*?((?:Paid\s*to|Received\s*from|Paidto|Receivedfrom|Paid to|Received from)\s*.*?)(?:UPI|upi).*?₹\s*([\d,]+\.?\d*)'
    
    matches = re.findall(pattern, all_text, re.DOTALL | re.IGNORECASE)
    
    st.write(f"**🔍 Debug: Found {len(matches)} raw pattern matches**")
    
    for match in matches:
        try:
            date_str, full_desc, amount_str = match
            
            # Skip self-transfers early (mentioned in PDF header)
            if 'self transfer' in full_desc.lower().replace(' ', ''):
                continue
            
            # Parse date
            date_clean = re.sub(r'[^\d\w,]', '', date_str)
            date_match = re.search(r'(\d{1,2})(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*,?(\d{4})', date_clean, re.IGNORECASE)
            
            if not date_match:
                continue
                
            day, month, year = date_match.groups()
            date = datetime.strptime(f"{day} {month} {year}", '%d %b %Y')
            
            # Determine transaction type
            is_received = 'received' in full_desc.lower() or 'receivedfrom' in full_desc.lower().replace(' ', '')
            transaction_type = 'Received' if is_received else 'Sent'
            
            # Extract merchant/person name
            if is_received:
                desc_match = re.search(r'(?:Received\s*from|Receivedfrom)\s*([A-Z][A-Za-z0-9\s]+?)(?=\s*UPI|\s*upi|Transaction)', full_desc, re.IGNORECASE)
            else:
                desc_match = re.search(r'(?:Paid\s*to|Paidto)\s*([A-Z][A-Za-z0-9\s]+?)(?=\s*UPI|\s*upi|Transaction)', full_desc, re.IGNORECASE)
            
            if desc_match:
                description = desc_match.group(1).strip()
            else:
                description = full_desc[:50].strip()
            
            # Clean description
            description = re.sub(r'\s+', ' ', description)
            description = description.replace('Paid to', '').replace('Received from', '').strip()
            description = description.split('UPI')[0].split('Transaction')[0].strip()
            
            # Skip if description is too short or empty
            if len(description) < 2:
                continue
            
            # Parse amount - handle all decimal formats
            amount_clean = amount_str.replace(',', '').strip()
            amount = float(amount_clean)
            
            # Skip invalid amounts
            if amount <= 0:
                continue
            
            # Skip rewards but NOT other valid Google Pay transactions
            skip_keywords = ['google pay rewards', 'googlepayrewards']
            if any(keyword in description.lower().replace(' ', '') for keyword in skip_keywords):
                continue
            
            transactions.append({
                'Date': date,
                'Description': description,
                'Amount': amount,
                'Type': transaction_type
            })
            
        except Exception as e:
            continue
    
    # Create DataFrame
    df = pd.DataFrame(transactions)
    
    # Remove duplicates - be more careful about what we consider duplicates
    if not df.empty:
        # Only remove if EXACT match on all three fields
        df = df.drop_duplicates(subset=['Date', 'Description', 'Amount'], keep='first')
        df = df.sort_values('Date')
        
        # Debug: Show totals before and after deduplication
        total_before = len(transactions)
        total_after = len(df)
        if total_before != total_after:
            st.write(f"⚠️ Removed {total_before - total_after} duplicate entries")
    
    return df

# =========================================================
# STREAMLIT UI - KPI FOCUSED
# =========================================================
st.title("💳 GPay Transaction Analyzer")
st.markdown("**Simple Send/Receive KPI Dashboard**")
st.markdown("---")

uploaded_pdf = st.file_uploader("📎 Upload GPay PDF Statement", type=['pdf'])

if uploaded_pdf:
    with st.spinner("🔄 Processing..."):
        try:
            df = extract_gpay_transactions(uploaded_pdf)
            
            if not df.empty:
                # Calculate KPIs
                total_sent = df[df['Type'] == 'Sent']['Amount'].sum()
                total_received = df[df['Type'] == 'Received']['Amount'].sum()
                net_position = total_sent - total_received
                
                sent_count = len(df[df['Type'] == 'Sent'])
                received_count = len(df[df['Type'] == 'Received'])
                
                # Date range
                date_from = df['Date'].min().strftime('%d %b %Y')
                date_to = df['Date'].max().strftime('%d %b %Y')
                
                st.success(f"✅ Analyzed **{len(df)} transactions** from **{date_from}** to **{date_to}**")
                
                # Accuracy check
                expected_sent = 550486.70
                expected_received = 169923.91
                
                sent_diff = abs(total_sent - expected_sent)
                received_diff = abs(total_received - expected_received)
                
                if sent_diff < 1 and received_diff < 1:
                    st.success("🎯 **100% ACCURACY ACHIEVED!**")
                elif sent_diff < 100:
                    st.warning(f"⚠️ Sent amount off by ₹{sent_diff:.2f} (Expected: ₹{expected_sent:,.2f})")
                
                st.markdown("---")
                
                # Main KPIs - Large Display
                st.markdown("## 📊 Key Metrics")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### 💸 Money Sent")
                    st.markdown(f"# ₹{total_sent:,.2f}")
                    st.caption(f"{sent_count} transactions")
                
                with col2:
                    st.markdown("### 💰 Money Received")
                    st.markdown(f"# ₹{total_received:,.2f}")
                    st.caption(f"{received_count} transactions")
                
                st.markdown("---")
                
                # Net Position
                st.markdown("## 🎯 Net Position")
                if net_position > 0:
                    st.markdown(f"# 📉 -₹{net_position:,.2f}")
                    st.error(f"You spent ₹{net_position:,.2f} more than you received")
                elif net_position < 0:
                    st.markdown(f"# 📈 +₹{abs(net_position):,.2f}")
                    st.success(f"You received ₹{abs(net_position):,.2f} more than you spent")
                else:
                    st.markdown(f"# ⚖️ ₹0.00")
                    st.info("Perfectly balanced!")
                
                st.markdown("---")
                
                # Transaction Breakdown
                st.markdown("## 📋 Transaction Details")
                
                tab1, tab2, tab3 = st.tabs(["💸 Sent", "💰 Received", "📊 All"])
                
                with tab1:
                    sent_df = df[df['Type'] == 'Sent'].copy()
                    if not sent_df.empty:
                        sent_df['Date'] = sent_df['Date'].dt.strftime('%d %b %Y')
                        sent_df['Amount'] = sent_df['Amount'].apply(lambda x: f"₹{x:,.2f}")
                        st.dataframe(sent_df[['Date', 'Description', 'Amount']], use_container_width=True, hide_index=True)
                    else:
                        st.info("No sent transactions found")
                
                with tab2:
                    received_df = df[df['Type'] == 'Received'].copy()
                    if not received_df.empty:
                        received_df['Date'] = received_df['Date'].dt.strftime('%d %b %Y')
                        received_df['Amount'] = received_df['Amount'].apply(lambda x: f"₹{x:,.2f}")
                        st.dataframe(received_df[['Date', 'Description', 'Amount']], use_container_width=True, hide_index=True)
                    else:
                        st.info("No received transactions found")
                
                with tab3:
                    all_df = df.copy()
                    all_df['Date'] = all_df['Date'].dt.strftime('%d %b %Y')
                    all_df['Amount'] = all_df['Amount'].apply(lambda x: f"₹{x:,.2f}")
                    st.dataframe(all_df[['Date', 'Description', 'Amount', 'Type']], use_container_width=True, hide_index=True)
                
                st.markdown("---")
                
                # Download Excel
                st.markdown("## 💾 Export Data")
                
                buffer = BytesIO()
                export_df = df.copy()
                export_df.to_excel(buffer, index=False)
                buffer.seek(0)
                
                filename = f"gpay_transactions_{df['Date'].min().strftime('%Y%m%d')}_{df['Date'].max().strftime('%Y%m%d')}.xlsx"
                
                st.download_button(
                    label="📥 Download Excel",
                    data=buffer,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
                
            else:
                st.error("❌ No transactions found in the PDF")
                st.info("💡 Make sure you're uploading a valid Google Pay statement")
                
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            
else:
    st.info("👆 Upload your GPay PDF to see your Send/Receive metrics")
    
    # Example metrics display
    st.markdown("---")
    st.markdown("### 📊 You'll see:")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💸 Total Sent", "₹XX,XXX")
    with col2:
        st.metric("💰 Total Received", "₹XX,XXX")
    with col3:
        st.metric("🎯 Net Position", "₹XX,XXX")
