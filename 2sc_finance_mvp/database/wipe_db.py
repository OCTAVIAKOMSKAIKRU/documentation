import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def wipe_tables():
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        database=os.getenv("DB_NAME")
    )
    cursor = conn.cursor()
    
    print("🛠️ Starting Database Wipe...")
    
    # Disable checks to avoid 'foreign key constraint' errors
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
    
    # Drop the tables causing the 'doc_id' conflict
    cursor.execute("DROP TABLE IF EXISTS transactions;")
    cursor.execute("DROP TABLE IF EXISTS documents;")
    
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
    conn.commit()
    
    print("✅ Success! Tables dropped. Now run 'streamlit run main.py' to rebuild them.")
    conn.close()

if __name__ == "__main__":
    wipe_tables()