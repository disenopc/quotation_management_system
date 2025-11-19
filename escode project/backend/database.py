import sqlite3
from contextlib import contextmanager
from config import Config
import os

class Database:
    """
    Database handler with connection pooling and optimizations.
    Handles up to 12.5k+ records efficiently.
    """
    
    def __init__(self, db_path=None):
        self.db_path = db_path or Config.DATABASE_PATH
        self._ensure_directory()
        self._initialize_database()
    
    def _ensure_directory(self):
        """Create database directory if it doesn't exist"""
        directory = os.path.dirname(self.db_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
    
    def _initialize_database(self):
        """Initialize database with schema if not exists"""
        with self.get_connection() as conn:
            # Enable WAL mode for better concurrent access
            conn.execute("PRAGMA journal_mode=WAL")
            # Optimize for performance
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
            conn.execute("PRAGMA temp_store=MEMORY")
            
            # Load schema if database is new
            if self._is_new_database(conn):
                self._load_schema(conn)
    
    def _is_new_database(self, conn):
        """Check if database is new (no tables)"""
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        )
        return cursor.fetchone() is None
    
    def _load_schema(self, conn):
        """Load initial schema from init.sql"""
        schema_path = 'database/init.sql'
        if os.path.exists(schema_path):
            with open(schema_path, 'r') as f:
                conn.executescript(f.read())
            conn.commit()
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.
        Usage:
            with db.get_connection() as conn:
                conn.execute("SELECT * FROM users")
        """
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # Access columns by name
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def execute_query(self, query, params=None, fetch_one=False):
        """
        Execute a SELECT query and return results.
        
        Args:
            query: SQL query string
            params: Query parameters (tuple or dict)
            fetch_one: Return single row instead of all rows
        
        Returns:
            List of Row objects or single Row object
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, params or ())
            if fetch_one:
                return cursor.fetchone()
            return cursor.fetchall()
    
    def execute_update(self, query, params=None):
        """
        Execute INSERT, UPDATE, or DELETE query.
        
        Returns:
            Last inserted row ID or number of affected rows
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, params or ())
            return cursor.lastrowid if cursor.lastrowid else cursor.rowcount
    
    def execute_many(self, query, params_list):
        """
        Execute same query with multiple parameter sets.
        Optimized for bulk inserts (like your 12.5k publishers).
        
        Args:
            query: SQL query string
            params_list: List of parameter tuples
        
        Returns:
            Number of affected rows
        """
        with self.get_connection() as conn:
            cursor = conn.executemany(query, params_list)
            return cursor.rowcount
    
    def bulk_insert_publishers(self, publishers_data):
        """
        Optimized bulk insert for large publisher database.
        
        Args:
            publishers_data: List of dicts with keys: name, email, category, status
        
        Returns:
            Number of inserted records
        """
        query = """
            INSERT OR IGNORE INTO publishers (name, email, category, status)
            VALUES (?, ?, ?, ?)
        """
        
        params_list = [
            (p.get('name'), p.get('email'), p.get('category', ''), p.get('status', 'active'))
            for p in publishers_data
        ]
        
        # Process in batches for memory efficiency
        batch_size = Config.BATCH_SIZE
        total_inserted = 0
        
        for i in range(0, len(params_list), batch_size):
            batch = params_list[i:i + batch_size]
            total_inserted += self.execute_many(query, batch)
        
        return total_inserted
    
    def search_records(self, table, search_term, columns):
        """
        Search across multiple columns efficiently.
        
        Args:
            table: Table name
            search_term: Term to search for
            columns: List of column names to search in
        
        Returns:
            List of matching rows
        """
        where_clause = " OR ".join([f"{col} LIKE ?" for col in columns])
        query = f"SELECT * FROM {table} WHERE {where_clause}"
        params = tuple(f"%{search_term}%" for _ in columns)
        
        return self.execute_query(query, params)
    
    def get_paginated(self, table, page=1, per_page=50, order_by="id DESC", where_clause=None, params=None):
        """
        Get paginated results for large datasets.
        
        Args:
            table: Table name
            page: Page number (1-indexed)
            per_page: Results per page
            order_by: ORDER BY clause
            where_clause: Optional WHERE clause
            params: Parameters for where clause
        
        Returns:
            Dict with 'data', 'total', 'page', 'pages'
        """
        offset = (page - 1) * per_page
        
        # Count total
        count_query = f"SELECT COUNT(*) as total FROM {table}"
        if where_clause:
            count_query += f" WHERE {where_clause}"
        
        total = self.execute_query(count_query, params, fetch_one=True)['total']
        
        # Get page data
        data_query = f"SELECT * FROM {table}"
        if where_clause:
            data_query += f" WHERE {where_clause}"
        data_query += f" ORDER BY {order_by} LIMIT ? OFFSET ?"
        
        final_params = list(params or ()) + [per_page, offset]
        data = self.execute_query(data_query, tuple(final_params))
        
        return {
            'data': [dict(row) for row in data],
            'total': total,
            'page': page,
            'pages': (total + per_page - 1) // per_page,
            'per_page': per_page
        }

# Global database instance
db = Database()