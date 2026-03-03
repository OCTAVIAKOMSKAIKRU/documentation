import mysql.connector
import bcrypt
import os
import streamlit as st
from dotenv import load_dotenv
import hashlib

# Load variables from .env
load_dotenv()

def get_db_connection():
    try:
        return mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME"),
            port=int(os.getenv("DB_PORT", 3306))
        )
    except mysql.connector.Error as e:
        st.error(f"📡 Database Connection Error: {e}")
        return None

# 2. Database Initialization
def init_db():
    conn = get_db_connection()
    if conn is None:
        st.error("Could not connect to database. Please check your credentials.")
        return  # Stop execution if connection failed
    try:
        
        cursor = conn.cursor()
    
    # 1. Users Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. Sessions Table (For Security & Scalability)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            session_id VARCHAR(64) PRIMARY KEY,
            user_id INT NOT NULL,
            ip_address VARCHAR(45),
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    
    # 2. NEW: Documents Table (The Vault)
    # This stores the record of the PDF itself
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            doc_id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            file_name VARCHAR(255),
            display_name VARCHAR(255),
            file_hash VARCHAR(64),
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            file_type ENUM('statement', 'receipt') DEFAULT 'statement',
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    """)
        
        # SCHEMA MIGRATION: Manually add file_hash if it doesn't exist
        try:
            cursor.execute("ALTER TABLE documents ADD COLUMN file_hash VARCHAR(64) AFTER display_name")
            conn.commit()
        except mysql.connector.Error as err:
            if err.errno == 1060: # Column already exists
                pass
            else:
                raise err
    
    # Added doc_id to track which PDF a transaction came from
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            doc_id INT,
            date DATE NOT NULL,
            description TEXT,
            amount DECIMAL(10,2),
            balance DECIMAL(10,2),
            category VARCHAR(50) DEFAULT 'Uncategorized',
            receipt_matched BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
        )
    """)

    # 4. Receipts Table (For Match & Verify)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS receipts (
            receipt_id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            merchant_name VARCHAR(100),
            total_amount DECIMAL(10,2),
            items_json JSON, 
            image_path TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
        conn.commit()
    finally:
        conn.close()
    
# --- NEW: DOCUMENT MANAGEMENT FUNCTIONS ---

def get_user_documents(user_id):
    """Fetches all uploaded document records for a specific user."""
    conn = get_db_connection()
    # dictionary=True allows us to access columns by name like doc['display_name']
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM documents WHERE user_id = %s ORDER BY upload_date DESC"
    cursor.execute(query, (user_id,))
    result = cursor.fetchall()
    conn.close()
    return result

def get_document_by_hash(user_id, file_hash):
    """Checks if this exact file content already exists for this user."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM documents WHERE user_id = %s AND file_hash = %s"
    cursor.execute(query, (user_id, file_hash))
    result = cursor.fetchone()
    conn.close()
    return result

# Update create_document_record to include file_hash
def create_document_record(user_id, file_name, display_name, file_hash, file_type='statement'):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO documents (user_id, file_name, display_name, file_hash, file_type)
        VALUES (%s, %s, %s, %s, %s)
    """, (user_id, file_name, display_name, file_hash, file_type))
    doc_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return doc_id

def delete_document(doc_id):
    """
    Standard Engineering Practice: Cascading Delete.
    Because of 'ON DELETE CASCADE' in init_db, deleting the document
    automatically removes all transactions linked to it.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    # This single line handles the entire cleanup
    cursor.execute("DELETE FROM documents WHERE doc_id = %s", (doc_id,))
    conn.commit()
    conn.close()
    return True

def delete_document_bundle(doc_id, user_id):
    """
    Removes a document record and all transactions associated with it.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Delete associated transactions first (Foreign Key safety)
            sql_tx = "DELETE FROM transactions WHERE doc_id = %s AND user_id = %s"
            cursor.execute(sql_tx, (doc_id, user_id))
            
            # 2. Delete the document record itself
            sql_doc = "DELETE FROM documents WHERE doc_id = %s AND user_id = %s"
            cursor.execute(sql_doc, (doc_id, user_id))
            
        conn.commit()
        return True, "Bundle deleted successfully."
    except Exception as e:
        conn.rollback()
        return False, f"Deletion failed: {str(e)}"
    finally:
        conn.close()

def rename_document(doc_id, new_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE documents SET display_name = %s WHERE doc_id = %s", (new_name, doc_id))
    conn.commit()
    conn.close()

# 3. AUTHENTICATION FUNCTIONS def register_user(username, password):
def register_user(username, password):
    if not username or not password:
        return False, "Username and password cannot be empty."
    
    conn = get_db_connection()
    if not conn: return False, "Database offline."
    
    c = conn.cursor()
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    try:
        c.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, hashed))
        conn.commit()
        return True, "Success"
    except mysql.connector.Error as err:
        if err.errno == 1062: # Duplicate entry
            return False, "This username is already taken."
        return False, f"Database error: {err}"
    finally:
        conn.close()

def login_user(username, password):
    conn = get_db_connection()
    if not conn: return None
    c = conn.cursor()
    c.execute("SELECT user_id, password_hash FROM users WHERE username = %s", (username,))
    result = c.fetchone()
    conn.close()
    
    if result:
        user_id, hashed = result
        if bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8')):
            return user_id
    return None

def get_user_transactions(user_id):
    """Fetches all transactions for the user to populate the UI automatically."""
    conn = get_db_connection()
    # Using Dictionary=True makes it easy to convert to a DataFrame
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM transactions WHERE user_id = %s ORDER BY date DESC", (user_id,))
    data = cursor.fetchall()
    conn.close()
    return data

def save_to_mysql(user_id, transactions, doc_id=None):
    """Saves transactions and links them to a specific document parent."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    insert_query = """
        INSERT INTO transactions (user_id, doc_id, date, description, amount, balance, category)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    
    data_tuples = [
        (user_id, doc_id, t['date'], t['description'], t['amount'], t['balance'], t.get('category', 'Uncategorized'))
        for t in transactions
    ]
    
    # Using executemany is 10x faster than a for-loop (Engineering Standard)
    cursor.executemany(insert_query, data_tuples)
    
    conn.commit()
    conn.close()

def update_mysql_records(df):
    """
    Engineering Standard: Synchronizes the UI Dataframe changes back to MySQL.
    This ensures user-edited categories are permanently saved.
    """
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()
    
    update_query = """
        UPDATE transactions 
        SET category = %s, description = %s 
        WHERE id = %s
    """
    
    # Convert dataframe rows to a list of tuples for batch processing
    update_data = [
        (row['category'], row['description'], row['id']) 
        for _, row in df.iterrows()
    ]
    
    try:
        cursor.executemany(update_query, update_data)
        conn.commit()
    except Exception as e:
        print(f"Error updating records: {e}")
    finally:
        conn.close()