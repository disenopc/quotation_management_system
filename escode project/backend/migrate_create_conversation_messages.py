"""
Migration: Create conversation_messages table for threaded conversations
This allows tracking complete conversation history between client and agent
"""
import sqlite3
import os

DB_PATH = 'database/quotations.db'

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database not found at {DB_PATH}")
        print("Run this script from backend/ directory")
        return
    
    print("="*70)
    print("MIGRATION: Create conversation_messages table")
    print("="*70)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='conversation_messages'
        """)
        
        if cursor.fetchone():
            print("\nTable 'conversation_messages' already exists")
            print("Skipping creation...")
        else:
            print("\nCreating table 'conversation_messages'...")
            cursor.execute("""
                CREATE TABLE conversation_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    response_id INTEGER NOT NULL,
                    sender TEXT NOT NULL,
                    message TEXT NOT NULL,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (response_id) REFERENCES responses(id) ON DELETE CASCADE
                )
            """)
            print("  ✓ Table created")
            
            # Create index for faster queries
            cursor.execute("""
                CREATE INDEX idx_conversation_response 
                ON conversation_messages(response_id)
            """)
            print("  ✓ Index created")
        
        conn.commit()
        
        # Show table structure
        print("\n" + "="*70)
        print("TABLE STRUCTURE: conversation_messages")
        print("="*70)
        cursor.execute("PRAGMA table_info(conversation_messages)")
        for col in cursor.fetchall():
            default = f"DEFAULT {col[4]}" if col[4] else ""
            print(f"  {col[1]:20} {col[2]:15} {default}")
        
        print("\n" + "="*70)
        print("MIGRATION COMPLETED SUCCESSFULLY")
        print("="*70)
        print("\nTable structure:")
        print("  - id: Primary key")
        print("  - response_id: Links to responses table")
        print("  - sender: 'agent' or 'client'")
        print("  - message: Message text")
        print("  - sent_at: Timestamp")
        print("\nUsage:")
        print("  - Each response can have multiple messages")
        print("  - Creates a complete conversation thread")
        print("  - Auto-populated when client replies by email")
        print("="*70)
        
    except Exception as e:
        print(f"\nERROR during migration: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()