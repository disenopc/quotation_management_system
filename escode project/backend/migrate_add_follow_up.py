"""
Migration: Add advanced tracking fields to responses table
- follow_up_method: email, other_channel, null
- deal_status: open, closed_won, closed_lost
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
    print("MIGRATION: Add advanced tracking to responses")
    print("="*70)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check existing columns
        cursor.execute("PRAGMA table_info(responses)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add follow_up_method if not exists
        if 'follow_up_method' not in columns:
            print("\nAdding column 'follow_up_method'...")
            cursor.execute("""
                ALTER TABLE responses 
                ADD COLUMN follow_up_method TEXT DEFAULT NULL
            """)
            print("  ✓ Column added")
        else:
            print("\nColumn 'follow_up_method' already exists")
        
        # Add deal_status if not exists
        if 'deal_status' not in columns:
            print("\nAdding column 'deal_status'...")
            cursor.execute("""
                ALTER TABLE responses 
                ADD COLUMN deal_status TEXT DEFAULT 'open'
            """)
            print("  ✓ Column added")
        else:
            print("\nColumn 'deal_status' already exists")
        
        conn.commit()
        
        # Verify final structure
        print("\n" + "="*70)
        print("UPDATED RESPONSES TABLE STRUCTURE:")
        print("="*70)
        cursor.execute("PRAGMA table_info(responses)")
        for col in cursor.fetchall():
            default = f"DEFAULT {col[4]}" if col[4] else ""
            print(f"  {col[1]:25} {col[2]:15} {default}")
        
        print("\n" + "="*70)
        print("MIGRATION COMPLETED SUCCESSFULLY")
        print("="*70)
        print("\nNew fields:")
        print("  - follow_up_method: NULL | 'email' | 'other_channel'")
        print("  - deal_status: 'open' | 'closed_won' | 'closed_lost'")
        print("\nMeaning:")
        print("  client_replied=1 + follow_up_method='email' → Client replied by email")
        print("  follow_up_method='other_channel' → Conversation continued by other means")
        print("  deal_status='closed_won' → Deal won")
        print("  deal_status='closed_lost' → Deal lost")
        print("="*70)
        
    except Exception as e:
        print(f"\nERROR during migration: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
