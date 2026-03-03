import streamlit as st
import pandas as pd
import os
import sqlalchemy
from logic.parsers import parse_absa_robust, parse_receipt_ocr, categorize_transaction
from database.db_manager import (
    init_db, get_db_connection, login_user,get_user_documents, get_document_by_hash, create_document_record,delete_document_bundle, 
    register_user,get_user_transactions ,save_to_mysql, update_mysql_records
)
from ui.dashboard import render_metrics, render_charts, render_monthly_view
import hashlib

# --- SQLALCHEMY ENGINE SETUP (Fixes the Pandas Warning) ---
# Create this once at the top so it can be reused
def get_engine():
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASS", "")
    host = os.getenv("DB_HOST", "localhost")
    db = os.getenv("DB_NAME", "second_story")
    # Using pymysql as the driver is standard for SQLAlchemy + MySQL
    return sqlalchemy.create_engine(f"mysql+pymysql://{user}:{password}@{host}/{db}")

def get_file_hash(file_bytes):
    return hashlib.sha256(file_bytes).hexdigest()

@st.dialog("Duplicate Document Detected")
def duplicate_conflict_modal(existing_doc, new_file_bytes, file_hash):
    st.warning(f"The document '**{existing_doc['display_name']}**' (Uploaded {existing_doc['upload_date']}) contains the exact same data as this file.")
    st.write("What would you like to do?")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("♻️ Replace Existing", use_container_width=True):
            # 1. Delete the old one
            delete_document_bundle(existing_doc['doc_id'], st.session_state.user_id)
            # 2. Trigger fresh process (This will run the standard flow)
            st.session_state.force_upload = True
            st.rerun()
            
    with col2:
        if st.button("📂 Go to Vault", use_container_width=True):
            # This is a trick to switch tabs programmatically if you use session state for tabs
            st.info("Please click the 'Vault' tab above to manage this file.")
            st.stop()

# 1. Initialize Database and Session
st.set_page_config(page_title="2SC Finance Hub", layout="wide")
init_db()

if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None

# --- VIEW 1: AUTHENTICATION ---
if not st.session_state.user_id:
    st.title("🛡️ Second Story Finance | Secure Login")
    tab_l, tab_r = st.tabs(["Login", "Register"])
    
    with tab_l:
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        
        if st.button("Login"):
            # 1. Attempt login
            logged_in_id = login_user(u, p)
            
            if logged_in_id:
                # 2. Update session state immediately
                st.session_state.user_id = logged_in_id
                st.session_state.username = u # Capturing username for the sidebar
                
                # 3. Pull history so the next view is ready
                existing_data = get_user_transactions(logged_in_id)
                if existing_data:
                    st.session_state.df = pd.DataFrame(existing_data)
                
                st.success("Welcome back!")
                st.rerun()
            else:
                st.error("Invalid username or password")
                
    with tab_r:
        new_u = st.text_input("Choose Username", key="reg_u")
        new_p = st.text_input("Choose Password", type="password", key="reg_p")
        if st.button("Create Account"):
            success, message = register_user(new_u, new_p)
            if success:
                st.success("Account created! You can now log in.")
                st.balloons()
            else:
                st.error(message)

else:
    # --- VIEW 2: LOGGED IN ---
    
    # 1. Initialize variables for this run
    df = pd.DataFrame() 
    user_id = st.session_state.user_id
    
    st.sidebar.image("https://via.placeholder.com/150x50?text=2SC+LOGO", use_container_width=True)
    st.sidebar.markdown(f"👤 **User:** {st.session_state.username}")
    
    if st.sidebar.button("Logout"):
        st.session_state.user_id = None
        st.session_state.df = pd.DataFrame()
        st.rerun()
    
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    # --- 2. FETCH DATA (Only runs if we have a user_id) ---
    try:
        engine = get_engine()
        query = sqlalchemy.text("SELECT * FROM transactions WHERE user_id = :uid")
        db_df = pd.read_sql(query, engine, params={'uid': user_id})
        
        if 'df' in st.session_state and not st.session_state.df.empty:
            df = st.session_state.df
        else:
            df = db_df
    except Exception as e:
        st.error(f"Database connection error: {e}")

    # --- 3. GLOBAL CLEANUP ---
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        
        
        df = df[df['amount'].abs() != df['balance'].abs()]
        
        df = df[~((df['category'] == 'Groceries & Essentials') & (df['amount'].abs() > 5000))]
        df = df[~((df['description'].str.contains('FEE|SMS|NOTIFY', case=False)) & (df['amount'].abs() > 500))]
        
        reversal_mask = df['description'].str.contains('UNPAID|UNSUCCESSFUL', case=False, na=False)
        df.loc[reversal_mask, 'amount'] = df.loc[reversal_mask, 'amount'].abs()
        df.loc[reversal_mask, 'amount'] = 0
        
        if 'receipt_matched' not in df.columns:
            df['receipt_matched'] = 0
            
        # Specific fix for the "Balance as Fee" bug
        df = df[~((df['description'].str.contains('TRANSACTION FEE', case=False)) & (df['amount'].abs() > 500))]
            
        df = df.drop_duplicates(subset=['date', 'description', 'amount', 'balance'])
        
        df['category'] = df.apply(lambda x: categorize_transaction(x['description'], x['amount']), axis=1)
        df['Month'] = df['date'].dt.strftime('%B %Y')
        st.session_state.df = df
    
    # --- 4. UI TABS ---
    st.title("📊 Financial Control Center")
    tab_sync, tab_reconcile, tab_insights, tab_vault = st.tabs([
    "🔄 Sync Ledger", 
    "⚖️ Reconcile", 
    "📊 Insights", 
    "📂 Vault"
])

    with tab_sync:
        col_pdf, col_receipt = st.columns(2)
    
        with col_pdf:
            st.subheader("1. Upload ABSA Statement")
            pdf_file = st.file_uploader("Drop your PDF here", type="pdf")
        
        if pdf_file:
            file_bytes = pdf_file.read()
            file_hash = get_file_hash(file_bytes)
        
        # Check if hash exists
            existing_doc = get_document_by_hash(st.session_state.user_id, file_hash)
        
        # Trigger popup if duplicate found AND we aren't forcing a replacement
            if existing_doc and not st.session_state.get('force_upload'):
                duplicate_conflict_modal(existing_doc, file_bytes, file_hash)
                st.stop()
            
            if pdf_file and st.button("Process Statement"):
                with st.spinner("Executing Robust Parse..."):
                    data = parse_absa_robust(pdf_file.read())
                    
                    if data:
                        try:
                            # --- UX AUTOMATION: Auto-Generate Document Name ---
                            temp_df = pd.DataFrame(data)
                            min_date = pd.to_datetime(temp_df['date']).min().strftime('%d %b %Y')
                            max_date = pd.to_datetime(temp_df['date']).max().strftime('%d %b %Y')
                            auto_doc_name = f"Absa Statement: {min_date} to {max_date}"
                            
                            # (In Phase 3, you will save 'auto_doc_name' into a 'documents' SQL table)
                            new_doc_id = create_document_record(
                                st.session_state.user_id, 
                                pdf_file.name, 
                                auto_doc_name,
                                file_hash)
                            
                            save_to_mysql(
                                st.session_state.user_id, 
                                data, 
                                doc_id=new_doc_id)
                            
                            st.session_state.force_upload = False
                            st.success("Successfully processed!")
                            st.rerun()

                            # 2. Save transactions linked to that ID (No more global DELETE)
                            new_df = pd.DataFrame(data)
                            st.session_state.df = new_df 
                            st.session_state.current_data = data  # This feeds your 'if df.empty' logic
                            st.cache_data.clear() # Forces the app to fetch fresh data on the next cycle
                            
                            st.balloons()
                            st.success(f"✅ Synced: {auto_doc_name}")
                            st.info("👈 **Next Step:** Click on the **'Transaction Ledger'** tab above to view your categorized results.")
                            
                            st.rerun() 
                        except Exception as e:
                            st.error(f"Sync failed: {e}")
                    else:
                        st.error("No valid transactions found.")

        with col_receipt:
            st.subheader("2. Snap Receipt")
            img_file = st.camera_input("Reconcile a purchase")
            if img_file:
                receipt_data = parse_receipt_ocr(img_file.read())
                st.metric("Detected Amount", f"R {receipt_data['amount']}")
                st.info("Matching receipt to cloud records...")




    with tab_reconcile:
        if not df.empty:
            month_list = sorted(df['Month'].unique(), reverse=True)
            sel_month = st.selectbox("Select Month", month_list)
            m_df = df[df['Month'] == sel_month]
            render_metrics(m_df)
            st.data_editor(m_df[['date', 'description', 'amount', 'category']], use_container_width=True)
        else:
            st.info("👋 Welcome! Start by uploading your first bank statement.")

    with tab_insights:
        if not df.empty:
            st.subheader("Your Real-World Spend Reflection")
            
            # Allow user to view insights for the specific month or all time
            insight_period = st.radio("Insights Period:", ["All Time"] + month_list)
            
            if insight_period == "All Time":
                insight_df = df
            else:
                insight_df = df[df['Month'] == insight_period]

            render_charts(insight_df)
            
            # STITCHING LOGIC
            matched = insight_df[insight_df['receipt_matched'] == 1]
            if not matched.empty:
                st.success(f"⚡ We've stitched {len(matched)} receipts to your bank statement!")
            
            # Debt & Rent Tracker Logic
            st.markdown("### 🔍 Critical Infrastructure Trackers")
            col_r, col_d = st.columns(2)
            
            with col_r:
                rent_tx = insight_df[insight_df['category'] == 'Rent & Accommodation']
                if not rent_tx.empty:
                    last_rent = abs(rent_tx.sort_values('date').iloc[-1]['amount'])
                    st.info(f"🏠 **Rent Detected:** R {last_rent:,.2f}")
                    st.caption("Tracking reduction to R4,300 in February.")
            
            with col_d:
                debt_tx = insight_df[insight_df['category'] == 'Credit Card Payment']
                if not debt_tx.empty:
                    total_debt_service = abs(debt_tx['amount'].sum())
                    st.warning(f"💳 **Debt Servicing (Credit Cards):** R {total_debt_service:,.2f}")
                    
    with tab_vault:
        st.subheader("📂 Your Financial Archive")
        st.info("Manage your uploaded statements and stitched receipts here.")
        
        # Mocking the Document Database for the UI 
        # (In production, SELECT * FROM documents WHERE user_id = ...)
        user_docs = get_user_documents(st.session_state.user_id)
        
        if not user_docs:
            st.info("No documents uploaded yet.")
        else:
            for doc in user_docs:
                with st.container():
                    col_icon, col_details, col_actions = st.columns([1, 4, 2])
                with col_icon:
                    st.markdown("📄 **PDF**")
                with col_details:
                    # Show the display name from the DB
                    new_name = st.text_input("Name", value=doc['display_name'], key=f"rename_{doc['doc_id']}")
                    st.caption(f"Uploaded on: {doc['upload_date']}")
                with col_actions:
                    if st.button("🗑️ Delete", key=f"del_{doc['doc_id']}", type="primary"):
                        success, msg = delete_document_bundle(doc['doc_id'], st.session_state.user_id)
                        if success:
                    # BRAND STANDARD: Clear local state so the charts update immediately
                                st.session_state.df = pd.DataFrame() 
                                st.cache_data.clear()
                                st.success("Record purged.")
                                st.rerun()
                
        # The Destructive Action Modal/Warning
        if st.session_state.get('confirm_delete', False):
            st.warning("⚠️ **Wait! Deleting this statement will impact your Insights.**")
            st.write("This statement has **3 stitched receipts** attached to it. Deleting it will un-sync those receipts and clear your ledger for these dates.")
            
            col_yes, col_no = st.columns(2)
            with col_yes:
                if st.button("Yes, Delete Everything"):
                    target_doc_id = st.session_state.get('last_doc_id') 
                    
                    if target_doc_id:
                        success, msg = delete_document_bundle(target_doc_id, st.session_state.user_id)
                        if success:
                            st.success("Document and related transactions removed.")
                            # Clear session data so the UI refreshes to an empty state
                            st.session_state.df = pd.DataFrame()
                            st.session_state.confirm_delete = False
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.error("Could not find document ID to delete.")