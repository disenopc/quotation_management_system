from database import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User:
    """User model for authentication"""
    
    @staticmethod
    def create(username, password, full_name, email):
        """Create new user"""
        password_hash = generate_password_hash(password)
        query = """
            INSERT INTO users (username, password_hash, full_name, email)
            VALUES (?, ?, ?, ?)
        """
        return db.execute_update(query, (username, password_hash, full_name, email))
    
    @staticmethod
    def get_by_username(username):
        """Get user by username"""
        query = "SELECT * FROM users WHERE username = ? AND is_active = 1"
        return db.execute_query(query, (username,), fetch_one=True)
    
    @staticmethod
    def get_by_email(email):
        """Get user by email"""
        query = "SELECT * FROM users WHERE email = ? AND is_active = 1"
        return db.execute_query(query, (email,), fetch_one=True)
    
    @staticmethod
    def verify_password(user, password):
        """Verify user password"""
        if not user:
            return False
        return check_password_hash(user['password_hash'], password)
    
    @staticmethod
    def get_all():
        """Get all active users"""
        query = "SELECT id, username, full_name, email, created_at FROM users WHERE is_active = 1"
        return db.execute_query(query)


class Client:
    """Client model"""
    
    @staticmethod
    def create(full_name, email, phone=None, notes=None):
        """Create new client"""
        query = """
            INSERT INTO clients (full_name, email, phone, notes)
            VALUES (?, ?, ?, ?)
        """
        return db.execute_update(query, (full_name, email, phone, notes))
    
    @staticmethod
    def get_by_email(email):
        """Get client by email"""
        query = "SELECT * FROM clients WHERE email = ?"
        return db.execute_query(query, (email,), fetch_one=True)
    
    @staticmethod
    def get_or_create(full_name, email, phone=None):
        """Get existing client or create new one"""
        client = Client.get_by_email(email)
        if client:
            return dict(client)
        
        client_id = Client.create(full_name, email, phone)
        return {
            'id': client_id,
            'full_name': full_name,
            'email': email,
            'phone': phone
        }
    
    @staticmethod
    def get_all(page=1, per_page=50):
        """Get all clients paginated"""
        return db.get_paginated('clients', page=page, per_page=per_page, order_by="created_at DESC")
    
    @staticmethod
    def search(search_term):
        """Search clients by name or email"""
        return db.search_records('clients', search_term, ['full_name', 'email', 'phone'])
    
    @staticmethod
    def update(client_id, **kwargs):
        """Update client information"""
        allowed_fields = ['full_name', 'email', 'phone', 'notes']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            return False
        
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        query = f"UPDATE clients SET {set_clause} WHERE id = ?"
        params = tuple(updates.values()) + (client_id,)
        
        return db.execute_update(query, params)


class Inquiry:
    """Inquiry/Email model"""
    
    @staticmethod
    def create(client_id, subject, message, status='pending'):
        """Create new inquiry"""
        query = """
            INSERT INTO inquiries (client_id, subject, message, status)
            VALUES (?, ?, ?, ?)
        """
        return db.execute_update(query, (client_id, subject, message, status))
    
    @staticmethod
    def get_all(page=1, per_page=50, status=None):
        """Get all inquiries with optional status filter"""
        where_clause = "status = ?" if status else None
        params = (status,) if status else None
        
        return db.get_paginated(
            'inquiries',
            page=page,
            per_page=per_page,
            order_by="received_at DESC",
            where_clause=where_clause,
            params=params
        )
    
    @staticmethod
    def get_with_client_info(inquiry_id):
        """Get inquiry with client details"""
        query = """
            SELECT 
                i.*,
                c.full_name as client_name,
                c.email as client_email,
                c.phone as client_phone
            FROM inquiries i
            LEFT JOIN clients c ON i.client_id = c.id
            WHERE i.id = ?
        """
        return db.execute_query(query, (inquiry_id,), fetch_one=True)
    
    @staticmethod
    def update_status(inquiry_id, status, assigned_to=None):
        """Update inquiry status"""
        query = "UPDATE inquiries SET status = ?, assigned_to = ? WHERE id = ?"
        return db.execute_update(query, (status, assigned_to, inquiry_id))
    
    @staticmethod
    def mark_responded(inquiry_id):
        """Mark inquiry as responded"""
        query = """
            UPDATE inquiries 
            SET status = 'responded', responded_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """
        return db.execute_update(query, (inquiry_id,))
    
    @staticmethod
    def get_statistics():
        """Get inquiry statistics by status"""
        query = """
            SELECT 
                status,
                COUNT(*) as count
            FROM inquiries
            GROUP BY status
        """
        results = db.execute_query(query)
        return {row['status']: row['count'] for row in results}


class Response:
    """Response model"""
    
    @staticmethod
    def create(inquiry_id, user_id, response_text):
        """Create new response"""
        query = """
            INSERT INTO responses (inquiry_id, user_id, response_text)
            VALUES (?, ?, ?)
        """
        response_id = db.execute_update(query, (inquiry_id, user_id, response_text))
        
        # Mark inquiry as responded
        Inquiry.mark_responded(inquiry_id)
        
        return response_id
    
    @staticmethod
    def get_by_inquiry(inquiry_id):
        """Get all responses for an inquiry"""
        query = """
            SELECT 
                r.*,
                u.full_name as user_name
            FROM responses r
            LEFT JOIN users u ON r.user_id = u.id
            WHERE r.inquiry_id = ?
            ORDER BY r.sent_at DESC
        """
        return db.execute_query(query, (inquiry_id,))


class Publisher:
    """Publisher model"""
    
    @staticmethod
    def bulk_insert(publishers_data):
        """
        Bulk insert publishers from list.
        
        Args:
            publishers_data: List of dicts with keys: name, email, category, status
        
        Example:
            publishers = [
                {'name': 'Publisher 1', 'email': 'pub1@example.com', 'category': 'Tech'},
                {'name': 'Publisher 2', 'email': 'pub2@example.com', 'category': 'News'},
            ]
            count = Publisher.bulk_insert(publishers)
        """
        return db.bulk_insert_publishers(publishers_data)
    
    @staticmethod
    def get_all(page=1, per_page=100):
        """Get all publishers paginated"""
        return db.get_paginated('publishers', page=page, per_page=per_page, order_by="name ASC")
    
    @staticmethod
    def search(search_term):
        """Search publishers"""
        return db.search_records('publishers', search_term, ['name', 'email', 'category'])
    
    @staticmethod
    def get_by_emails(email_list):
        """Get publishers by list of emails (for bulk operations)"""
        placeholders = ','.join(['?' for _ in email_list])
        query = f"SELECT * FROM publishers WHERE email IN ({placeholders})"
        return db.execute_query(query, tuple(email_list))
    
    @staticmethod
    def update_status_bulk(email_list, status):
        """Update status for multiple publishers"""
        placeholders = ','.join(['?' for _ in email_list])
        query = f"UPDATE publishers SET status = ? WHERE email IN ({placeholders})"
        params = (status,) + tuple(email_list)
        return db.execute_update(query, params)
    
    @staticmethod
    def get_count():
        """Get total publisher count"""
        query = "SELECT COUNT(*) as total FROM publishers"
        result = db.execute_query(query, fetch_one=True)
        return result['total']