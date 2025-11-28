"""
MAIN APPLICATION FILE WITH CONTENT FILTER, ADVANCED TRACKING & CONVERSATION THREADS
Backend server for Quotation Management System using SQLite3 Database class.
Flask handles API endpoints and connects frontend with database, email, and AI.
FEATURES: Content filter + Auto-detection + Follow-up tracking + Conversation threads
"""
from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
from datetime import datetime
from config import config
from database import db
from auth import login_required, AuthManager
from models import User
from email_handler import email_handler
from ai_assistant import ai_assistant, get_ai_response, get_inquiry_priority
import logging
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Enable CORS for API routes
CORS(
    app,
    resources={r"/api/*": {"origins": ["http://localhost:5001", "http://localhost:5173"]}},
    supports_credentials=True
)

# ---------------------------------------------------------------------------
# Serve Frontend
# ---------------------------------------------------------------------------
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../frontend')

@app.route('/')
def serve_index():
    """Serve the login page"""
    return send_from_directory(FRONTEND_DIR, 'login.html')

@app.route('/dashboard')
def serve_dashboard():
    """Serve the main dashboard"""
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/login.html')
def serve_login():
    """Serve login page"""
    return send_from_directory(FRONTEND_DIR, 'login.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve frontend static files (JS, CSS, images)"""
    return send_from_directory(FRONTEND_DIR, path)

# ---------------------------------------------------------------------------
# Start email monitoring safely
# ---------------------------------------------------------------------------
try:
    email_handler.start_email_monitoring(interval=60)
except AttributeError:
    logging.warning("EmailHandler monitoring not fully implemented or already running.")

# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================
@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login endpoint - accepts email and password"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    email = data.get('email')
    password = data.get('password')
    
    logging.info(f"Login attempt with email: {email}")
    
    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400
    
    user = AuthManager.login_by_email(email, password)
    
    if not user:
        logging.warning(f"Failed login attempt for email: {email}")
        return jsonify({"error": "Invalid credentials"}), 401
    
    logging.info(f"Successful login for user: {user['email']}")
    
    return jsonify({
        "success": True,
        "user": {
            "id": user['id'],
            "username": user['username'],
            "email": user['email'],
            "full_name": user['full_name']
        },
        "token": user['token']
    }), 200

@app.route('/api/auth/check', methods=['GET'])
def check_auth():
    """Check if user is authenticated"""
    user = AuthManager.get_current_user()
    if user:
        return jsonify({'authenticated': True, 'user': user}), 200
    return jsonify({'authenticated': False}), 401

@app.route('/api/auth/logout', methods=['POST'])
@login_required
def logout():
    """Logout endpoint"""
    AuthManager.logout()
    return jsonify({"message": "Logged out successfully"}), 200

# ============================================================================
# CLIENT ROUTES
# ============================================================================
@app.route('/api/clients', methods=['GET'])
@login_required
def get_clients():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    search = request.args.get('search', '')
    
    with db.get_connection() as conn:
        query = "SELECT * FROM clients"
        params = []
        
        if search:
            query += " WHERE full_name LIKE ? OR email LIKE ?"
            params = (f"%{search}%", f"%{search}%")
        
        query += " LIMIT ? OFFSET ?"
        params += (per_page, (page-1)*per_page)
        
        rows = conn.execute(query, params).fetchall()
        total = conn.execute("SELECT COUNT(*) as total FROM clients").fetchone()['total']
    
    clients = [dict(r) for r in rows]
    return jsonify({
        "data": clients,
        "total": total,
        "page": page,
        "pages": (total + per_page - 1) // per_page,
        "per_page": per_page
    }), 200

@app.route('/api/clients', methods=['POST'])
@login_required
def create_client():
    data = request.get_json()
    
    with db.get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO clients (full_name,email,phone,notes) VALUES (?,?,?,?)",
            (data['full_name'], data['email'], data.get('phone'), data.get('notes'))
        )
        client_id = cursor.lastrowid
    
    return jsonify({"success": True, "client_id": client_id}), 201

@app.route('/api/clients/<int:client_id>', methods=['PUT'])
@login_required
def update_client(client_id):
    data = request.get_json()
    
    with db.get_connection() as conn:
        conn.execute(
            "UPDATE clients SET full_name=?, email=?, phone=?, company=?, notes=? WHERE id=?",
            (data.get('full_name'), data.get('email'), data.get('phone'), data.get('company'), data.get('notes'), client_id)
        )
    
    return jsonify({"success": True}), 200

@app.route('/api/clients/<int:client_id>', methods=['GET'])
@login_required
def get_client(client_id):
    """Get single client by ID"""
    with db.get_connection() as conn:
        row = conn.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
        
        if not row:
            return jsonify({"error": "Client not found"}), 404
        
        return jsonify(dict(row)), 200

@app.route('/api/clients/<int:client_id>', methods=['DELETE'])
@login_required
def delete_client(client_id):
    """Delete client - only for admin/manager"""
    user = AuthManager.get_current_user()
    
    if user.get('role') not in ['admin', 'manager']:
        return jsonify({"error": "Unauthorized - Admin or Manager access required"}), 403
    
    try:
        with db.get_connection() as conn:
            inquiries = conn.execute(
                "SELECT COUNT(*) as count FROM inquiries WHERE client_id=?", 
                (client_id,)
            ).fetchone()
            
            if inquiries['count'] > 0:
                return jsonify({
                    "error": "Cannot delete client with existing inquiries",
                    "inquiries_count": inquiries['count']
                }), 400
            
            cursor = conn.execute("DELETE FROM clients WHERE id=?", (client_id,))
            
            if cursor.rowcount == 0:
                return jsonify({"error": "Client not found"}), 404
            
            return jsonify({"success": True, "message": "Client deleted successfully"}), 200
    
    except Exception as e:
        logging.error(f"Error deleting client: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ============================================================================
# INQUIRY ROUTES
# ============================================================================
@app.route('/api/inquiries', methods=['GET'])
@login_required
def get_inquiries():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    status_filter = request.args.get('status', '')
    
    with db.get_connection() as conn:
        query = """
            SELECT i.*, c.full_name as client_name, c.email as client_email
            FROM inquiries i
            LEFT JOIN clients c ON i.client_id = c.id
        """
        params = []
        
        if status_filter:
            query += " WHERE i.status=?"
            params = [status_filter]
        
        query += " ORDER BY i.received_at DESC LIMIT ? OFFSET ?"
        params += [per_page, (page-1)*per_page]
        
        rows = conn.execute(query, tuple(params)).fetchall()
        
        total_query = "SELECT COUNT(*) as total FROM inquiries"
        if status_filter:
            total_query += " WHERE status=?"
            total = conn.execute(total_query, (status_filter,)).fetchone()['total']
        else:
            total = conn.execute(total_query).fetchone()['total']
    
    inquiries = [dict(r) for r in rows]
    return jsonify({
        "data": inquiries,
        "total": total,
        "page": page,
        "pages": (total + per_page - 1) // per_page,
        "per_page": per_page
    }), 200

@app.route('/api/inquiries/<int:inquiry_id>', methods=['GET'])
@login_required
def get_inquiry(inquiry_id):
    """Get single inquiry with client info"""
    with db.get_connection() as conn:
        row = conn.execute("""
            SELECT i.*, c.full_name as client_name, c.email as client_email, c.phone as client_phone
            FROM inquiries i
            LEFT JOIN clients c ON i.client_id = c.id
            WHERE i.id = ?
        """, (inquiry_id,)).fetchone()
        
        if not row:
            return jsonify({"error": "Inquiry not found"}), 404
        
        return jsonify(dict(row)), 200

@app.route('/api/inquiries/stats', methods=['GET'])
@login_required
def get_inquiry_stats():
    """Get inquiry statistics"""
    with db.get_connection() as conn:
        rows = conn.execute("SELECT status, COUNT(*) as count FROM inquiries GROUP BY status").fetchall()
        stats = {row['status']: row['count'] for row in rows}
    
    return jsonify(stats), 200

@app.route('/api/inquiries', methods=['POST'])
@login_required
def create_inquiry():
    data = request.get_json()
    client_id = data['client_id']
    subject = data['subject']
    message = data['message']
    
    with db.get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO inquiries (client_id, subject, message, status) VALUES (?,?,?,?)",
            (client_id, subject, message, 'pending')
        )
        inquiry_id = cursor.lastrowid
    
    return jsonify({"success": True, "inquiry_id": inquiry_id}), 201

# ============================================================================
# RESPONSE ROUTES WITH CONVERSATION THREADS
# ============================================================================
@app.route('/api/responses', methods=['POST'])
@login_required
def create_response():
    """Create response to inquiry with initial message in conversation thread"""
    data = request.get_json()
    inquiry_id = data.get('inquiry_id')
    response_text = data.get('response_text')
    
    if not inquiry_id or not response_text:
        return jsonify({"error": "Missing required fields"}), 400
    
    user = AuthManager.get_current_user()
    
    with db.get_connection() as conn:
        # Create response
        cursor = conn.execute(
            "INSERT INTO responses (inquiry_id, user_id, response_text) VALUES (?,?,?)",
            (inquiry_id, user['id'], response_text)
        )
        response_id = cursor.lastrowid
        
        # Create initial agent message in conversation thread
        conn.execute(
            "INSERT INTO conversation_messages (response_id, sender, message) VALUES (?, ?, ?)",
            (response_id, 'agent', response_text)
        )
        
        # Update inquiry status
        conn.execute(
            "UPDATE inquiries SET status='responded', responded_at=? WHERE id=?",
            (datetime.utcnow(), inquiry_id)
        )
    
    return jsonify({"success": True, "response_id": response_id, "email_sent": False}), 201

@app.route('/api/responses', methods=['GET'])
@login_required
def get_responses():
    """Get all responses with pagination and full client info"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    with db.get_connection() as conn:
        query = """
            SELECT 
                r.id,
                r.inquiry_id,
                r.response_text,
                r.sent_at,
                r.client_replied,
                r.follow_up_method,
                r.deal_status,
                i.subject as inquiry_subject,
                c.id as client_id,
                c.full_name as client_name,
                c.email as client_email,
                c.company as client_company,
                c.phone as client_phone,
                u.full_name as sent_by_user
            FROM responses r
            LEFT JOIN inquiries i ON r.inquiry_id = i.id
            LEFT JOIN clients c ON i.client_id = c.id
            LEFT JOIN users u ON r.user_id = u.id
            ORDER BY r.sent_at DESC
            LIMIT ? OFFSET ?
        """
        rows = conn.execute(query, (per_page, (page-1)*per_page)).fetchall()
        
        total_query = "SELECT COUNT(*) as total FROM responses"
        total = conn.execute(total_query).fetchone()['total']
    
    responses = [dict(r) for r in rows]
    return jsonify({
        "data": responses,
        "total": total,
        "page": page,
        "pages": (total + per_page - 1) // per_page,
        "per_page": per_page
    }), 200

@app.route('/api/responses/<int:response_id>', methods=['GET'])
@login_required
def get_response(response_id):
    """Get single response by ID with full conversation thread"""
    with db.get_connection() as conn:
        # Get response details
        query = """
            SELECT 
                r.id,
                r.inquiry_id,
                r.response_text,
                r.sent_at,
                r.client_replied,
                r.follow_up_method,
                r.deal_status,
                i.subject as inquiry_subject,
                i.message as inquiry_message,
                c.full_name as client_name,
                c.email as client_email,
                u.full_name as sent_by
            FROM responses r
            LEFT JOIN inquiries i ON r.inquiry_id = i.id
            LEFT JOIN clients c ON i.client_id = c.id
            LEFT JOIN users u ON r.user_id = u.id
            WHERE r.id = ?
        """
        row = conn.execute(query, (response_id,)).fetchone()
        
        if not row:
            return jsonify({"error": "Response not found"}), 404
        
        response_data = dict(row)
        
        # Get conversation thread (all messages)
        messages_query = """
            SELECT id, sender, message, sent_at
            FROM conversation_messages
            WHERE response_id = ?
            ORDER BY sent_at ASC
        """
        messages = conn.execute(messages_query, (response_id,)).fetchall()
        response_data['conversation_thread'] = [dict(m) for m in messages]
    
    return jsonify(response_data), 200

@app.route('/api/responses/<int:response_id>/mark-replied', methods=['PUT'])
@login_required
def mark_client_replied(response_id):
    """Mark that client replied to this response"""
    data = request.get_json()
    client_replied = data.get('client_replied', 1)
    
    with db.get_connection() as conn:
        response = conn.execute(
            "SELECT id FROM responses WHERE id = ?",
            (response_id,)
        ).fetchone()
        
        if not response:
            return jsonify({"error": "Response not found"}), 404
        
        conn.execute(
            "UPDATE responses SET client_replied = ? WHERE id = ?",
            (client_replied, response_id)
        )
    
    return jsonify({
        "success": True, 
        "message": f"Response marked as {'replied' if client_replied else 'not replied'}"
    }), 200

@app.route('/api/responses/<int:response_id>/update-follow-up', methods=['PUT'])
@login_required
def update_follow_up(response_id):
    """Update follow-up method and deal status"""
    data = request.get_json()
    follow_up_method = data.get('follow_up_method')
    deal_status = data.get('deal_status')
    client_replied = data.get('client_replied')
    
    with db.get_connection() as conn:
        response = conn.execute(
            "SELECT id FROM responses WHERE id = ?",
            (response_id,)
        ).fetchone()
        
        if not response:
            return jsonify({"error": "Response not found"}), 404
        
        update_fields = []
        update_values = []
        
        if follow_up_method is not None:
            update_fields.append("follow_up_method = ?")
            update_values.append(follow_up_method)
        
        if deal_status is not None:
            update_fields.append("deal_status = ?")
            update_values.append(deal_status)
        
        if client_replied is not None:
            update_fields.append("client_replied = ?")
            update_values.append(client_replied)
        
        if update_fields:
            update_values.append(response_id)
            query = f"UPDATE responses SET {', '.join(update_fields)} WHERE id = ?"
            conn.execute(query, tuple(update_values))
    
    return jsonify({
        "success": True,
        "message": "Response updated successfully"
    }), 200

@app.route('/api/responses/<int:response_id>/add-message', methods=['POST'])
@login_required
def add_message_to_conversation(response_id):
    """Manually add a message to conversation thread"""
    data = request.get_json()
    sender = data.get('sender')
    message = data.get('message')
    
    if not sender or not message:
        return jsonify({"error": "sender and message required"}), 400
    
    if sender not in ['agent', 'client']:
        return jsonify({"error": "sender must be 'agent' or 'client'"}), 400
    
    with db.get_connection() as conn:
        response = conn.execute(
            "SELECT id FROM responses WHERE id = ?",
            (response_id,)
        ).fetchone()
        
        if not response:
            return jsonify({"error": "Response not found"}), 404
        
        cursor = conn.execute(
            "INSERT INTO conversation_messages (response_id, sender, message) VALUES (?, ?, ?)",
            (response_id, sender, message)
        )
        message_id = cursor.lastrowid
        
        if sender == 'client':
            conn.execute(
                "UPDATE responses SET client_replied = 1, follow_up_method = 'email' WHERE id = ?",
                (response_id,)
            )
    
    return jsonify({
        "success": True,
        "message_id": message_id
    }), 201

# ============================================================================
# AI ROUTES
# ============================================================================
@app.route('/api/ai/generate-response', methods=['POST'])
@login_required
def generate_ai_response():
    """Generate AI response"""
    data = request.get_json()
    subject = data.get('subject')
    message = data.get('message')
    
    if not subject or not message:
        return jsonify({"error": "Subject and message required"}), 400
    
    try:
        user = AuthManager.get_current_user()
        context = {
            'user_name': user.get('full_name', user.get('username')),
            'user_email': user.get('email'),
            'user_phone': user.get('phone'),
            'user_position': user.get('position', 'Sales Representative')
        }
        
        response = get_ai_response(subject, message, context)
        return jsonify({"success": True, "response": response}), 200
    
    except Exception as e:
        logging.error(f"AI generation error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ============================================================================
# PUBLISHER ROUTES
# ============================================================================
@app.route('/api/publishers/bulk-import', methods=['POST'])
@login_required
def bulk_upload_publishers():
    data = request.get_json()
    publishers_data = data if isinstance(data, list) else data.get('publishers', [])
    
    if not publishers_data:
        return jsonify({"error": "No publishers data provided"}), 400
    
    total_inserted = db.bulk_insert_publishers(publishers_data)
    return jsonify({"success": True, "imported": total_inserted, "total": len(publishers_data)}), 200

@app.route('/api/publishers', methods=['GET'])
@login_required
def get_publishers():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 100, type=int)
    search = request.args.get('search', '')
    
    with db.get_connection() as conn:
        query = "SELECT * FROM publishers"
        params = []
        
        if search:
            query += " WHERE name LIKE ? OR email LIKE ?"
            params = (f"%{search}%", f"%{search}%")
        
        query += " ORDER BY name ASC LIMIT ? OFFSET ?"
        params += (per_page, (page-1)*per_page)
        
        rows = conn.execute(query, params).fetchall()
        total = conn.execute("SELECT COUNT(*) as total FROM publishers").fetchone()['total']
    
    publishers = [dict(r) for r in rows]
    return jsonify({
        "data": publishers,
        "total": total,
        "page": page,
        "pages": (total + per_page - 1) // per_page,
        "per_page": per_page
    }), 200

@app.route('/api/publishers/count', methods=['GET'])
@login_required
def get_publisher_count():
    """Get total publisher count"""
    with db.get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) as total FROM publishers").fetchone()['total']
    return jsonify({"count": total}), 200

# ============================================================================
# EMAIL ROUTES - WITH CONTENT FILTER, AUTO-DETECTION & CONVERSATION THREADS
# ============================================================================
@app.route('/api/email/sync', methods=['POST'])
@login_required
def sync_emails():
    """
    Sync emails manually - UNSEEN ONLY
    WITH FILTER: Only processes emails with complete info (min 3 of 4 fields)
    WITH AUTO-DETECTION: Detects client replies and adds to conversation thread
    """
    try:
        import re
        
        new_emails = email_handler.fetch_new_emails()
        count = 0
        rejected_count = 0
        
        logging.info(f"\nProcessing {len(new_emails)} new emails...")
        
        for email_data in new_emails:
            from_email = email_data.get('from')
            body = email_data.get('body', '')
            raw_subject = email_data.get('subject', '').strip()
            
            # Extract contact information
            phone = None
            phone_patterns = [
                r'[Pp]hone[\s:]+\*?(\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9})\*?',
                r'[Tt]el[eé]fono[\s:]+\*?(\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9})\*?',
                r'\*(\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9})\*',
                r'\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',
            ]
            
            for pattern in phone_patterns:
                match = re.search(pattern, body)
                if match:
                    phone_raw = match.group(1) if match.lastindex else match.group(0)
                    phone_raw = phone_raw.strip().replace('*', '')
                    if len(re.findall(r'\d', phone_raw)) >= 6:
                        phone = phone_raw
                        break
            
            # Extract company
            company = None
            company_patterns = [
                r'[Ff]rom\s+\*([A-Z][A-Za-z\s&.]+)\*',
                r'[Ff]rom\s+([A-Z][A-Za-z\s&.]+?)(?:\.|$|\n)',
                r'(?:company|empresa|organization|org)[\s:]+\*?([A-Z][A-Za-z\s&.,]+?)\*?(?:\n|$|\.|,)',
                r'\*([A-Z][A-Za-z\s&.]+(?:Solutions|Inc|LLC|Ltd|Corp|SA|SRL|Systems|Technologies|Group|Company))\*',
                r'([A-Z][A-Za-z\s&.]+(?:Solutions|Inc|LLC|Ltd|Corp|SA|SRL|Systems|Technologies|Group))',
            ]
            
            for pattern in company_patterns:
                match = re.search(pattern, body, re.IGNORECASE | re.MULTILINE)
                if match:
                    company = match.group(1).strip().replace('*', '')
                    company = re.sub(r'\s+', ' ', company)
                    company = re.sub(r'[.,]+$', '', company)
                    if len(company) > 3:
                        break
            
            # Extract name
            full_name = from_email.split('@')[0]
            name_patterns = [
                r'(?:my name is|I am|I\'m)\s+\*?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\*?\s+from',
                r'(?:my name is|I am|I\'m)\s+\*?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\*?',
                r'(?:name|nombre)[\s:]+\*?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\*?',
                r'^\*?([A-Z][a-z]+\s+[A-Z][a-z]+)\*?',
            ]
            
            for pattern in name_patterns:
                name_match = re.search(pattern, body, re.IGNORECASE | re.MULTILINE)
                if name_match:
                    full_name = name_match.group(1).strip()
                    break
            
            # Extract email
            client_email = None
            email_patterns = [
                r'(?:email|e-mail|correo)[\s:]+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                r'(?:contact|contacto)[\s:]+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            ]
            
            for pattern in email_patterns:
                email_match = re.search(pattern, body, re.IGNORECASE)
                if email_match:
                    extracted_email = email_match.group(1).lower()
                    if not any(x in extracted_email for x in ['noreply', 'no-reply', 'wordpress', 'system', 'mailer']):
                        client_email = extracted_email
                        break
            
            if not client_email:
                client_email = from_email
            
            # Validate fields
            valid_name = bool(full_name and full_name != from_email.split('@')[0] and len(full_name) > 2)
            valid_email = bool(client_email and '@' in client_email)
            valid_phone = bool(phone)
            valid_company = bool(company and len(company) > 1)
            
            valid_fields_count = sum([valid_name, valid_email, valid_phone, valid_company])
            
            MIN_REQUIRED_FIELDS = 3
            
            if valid_fields_count < MIN_REQUIRED_FIELDS:
                rejected_count += 1
                
                has = []
                missing = []
                if valid_name: has.append('OK Name')
                else: missing.append('MISSING Name')
                if valid_email: has.append('OK Email')
                else: missing.append('MISSING Email')
                if valid_phone: has.append('OK Phone')
                else: missing.append('MISSING Phone')
                if valid_company: has.append('OK Company')
                else: missing.append('MISSING Company')
                
                logging.warning(f"REJECTED Email ({valid_fields_count}/{MIN_REQUIRED_FIELDS} fields): {raw_subject[:50]}")
                logging.warning(f"   Has: {', '.join(has) if has else 'None'}")
                logging.warning(f"   Missing: {', '.join(missing)}")
                continue
            
            logging.info(f"VALID Email ({valid_fields_count}/4 fields): {raw_subject[:50]}")
            
            if not raw_subject or raw_subject == '':
                current_date = datetime.now().strftime('%d/%m/%Y')
                if company:
                    subject = f"{company} - {current_date}"
                else:
                    subject = f"{full_name} - {current_date}"
            else:
                subject = raw_subject
            
            with db.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT id, email FROM clients WHERE full_name = ? AND company = ?",
                    (full_name, company if company else '')
                )
                client = cursor.fetchone()
                
                if not client:
                    name_slug = full_name.lower().replace(' ', '.').replace('*', '')
                    company_slug = company.lower().replace(' ', '.').replace('*', '') if company else 'unknown'
                    synthetic_email = f"{name_slug}.{company_slug}@internal.local"
                    
                    cursor = conn.execute(
                        "INSERT INTO clients (full_name, email, phone, company) VALUES (?, ?, ?, ?)",
                        (full_name, synthetic_email, phone, company)
                    )
                    client_id = cursor.lastrowid
                    logging.info(f"   NEW client created: {full_name} - {company} ({synthetic_email})")
                else:
                    client_id = client[0]
                    
                    update_fields = []
                    update_values = []
                    
                    if phone:
                        update_fields.append("phone = ?")
                        update_values.append(phone)
                    
                    if update_fields:
                        update_values.append(client_id)
                        conn.execute(
                            f"UPDATE clients SET {', '.join(update_fields)} WHERE id = ?",
                            tuple(update_values)
                        )
                    logging.info(f"   UPDATED client: {full_name} - {company}")
                
                existing = conn.execute(
                    "SELECT id FROM inquiries WHERE client_id=? AND subject=? AND message=?",
                    (client_id, subject, body)
                ).fetchone()
                
                if not existing:
                    cursor = conn.execute(
                        "INSERT INTO inquiries (client_id, subject, message, status, received_at) VALUES (?, ?, ?, ?, ?)",
                        (client_id, subject, body, 'pending', datetime.utcnow())
                    )
                    inquiry_id = cursor.lastrowid
                    count += 1
                    logging.info(f"   CREATED inquiry: {subject[:50]}")
                    
                    # ========================================================================
                    # AUTO-DETECT: Did client reply to previous response?
                    # ========================================================================
                    cursor = conn.execute("""
                        SELECT r.id, r.inquiry_id
                        FROM responses r
                        JOIN inquiries i ON r.inquiry_id = i.id
                        WHERE i.client_id = ? AND r.client_replied = 0
                        ORDER BY r.sent_at DESC
                        LIMIT 1
                    """, (client_id,))
                    
                    pending_response = cursor.fetchone()
                    
                    if pending_response:
                        # Update response status
                        conn.execute("""
                            UPDATE responses 
                            SET client_replied = 1, 
                                follow_up_method = 'email'
                            WHERE id = ?
                        """, (pending_response['id'],))
                        
                        # ADD CLIENT MESSAGE TO CONVERSATION THREAD
                        conn.execute("""
                            INSERT INTO conversation_messages (response_id, sender, message, sent_at)
                            VALUES (?, 'client', ?, ?)
                        """, (pending_response['id'], body, datetime.utcnow()))
                        
                        logging.info(f"   AUTO-DETECTED: Client replied to response #{pending_response['id']}")
                        logging.info(f"   MESSAGE ADDED to conversation thread")
                else:
                    logging.info(f"   DUPLICATE inquiry skipped: {subject[:50]}")
        
        logging.info(f"\nSYNC SUMMARY:")
        logging.info(f"   Total processed: {len(new_emails)}")
        logging.info(f"   VALID (complete info): {count + (len(new_emails) - count - rejected_count)}")
        logging.info(f"   REJECTED (incomplete info): {rejected_count}")
        logging.info(f"   CREATED inquiries: {count}\n")
        
        return jsonify({
            "success": True, 
            "count": count,
            "rejected": rejected_count,
            "total_processed": len(new_emails),
            "message": f"Synced {count} new emails (rejected {rejected_count} incomplete)"
        }), 200
    
    except Exception as e:
        logging.error(f"Email sync error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ============================================================================
# ADMIN ROUTES
# ============================================================================
@app.route('/api/admin/migrate-conversations', methods=['POST'])
@login_required
def migrate_existing_conversations():
    """One-time migration: Populate conversation_messages from existing responses"""
    user = AuthManager.get_current_user()
    
    if user.get('role') != 'admin':
        return jsonify({"error": "Admin access required"}), 403
    
    with db.get_connection() as conn:
        responses = conn.execute("""
            SELECT id, response_text, sent_at
            FROM responses
            WHERE id NOT IN (
                SELECT DISTINCT response_id FROM conversation_messages
            )
        """).fetchall()
        
        count = 0
        for resp in responses:
            conn.execute("""
                INSERT INTO conversation_messages (response_id, sender, message, sent_at)
                VALUES (?, 'agent', ?, ?)
            """, (resp['id'], resp['response_text'], resp['sent_at']))
            count += 1
        
        logging.info(f"Migrated {count} existing responses to conversation threads")
    
    return jsonify({
        "success": True,
        "migrated": count,
        "message": f"Successfully migrated {count} responses"
    }), 200

# ============================================================================
# SYSTEM ROUTES
# ============================================================================
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()}), 200

# ============================================================================
# MAIN
# ============================================================================
if __name__ == '__main__':
    print("Starting Quotation Management System...")
    print(f"Server running on http://localhost:5001")
    print(f"Debug mode: {config.DEBUG}")
    print(f"Content filter: ENABLED (minimum {3} of 4 fields)")
    print(f"Auto-detection: ENABLED")
    print(f"Conversation threads: ENABLED")
    app.run(debug=config.DEBUG, host='0.0.0.0', port=5001)