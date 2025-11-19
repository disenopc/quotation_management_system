"""
MAIN APPLICATION FILE

Backend server for Quotation Management System using SQLite3 Database class.
Flask handles API endpoints and connects frontend with database, email, and AI.
"""

from flask import Flask, request, jsonify, send_from_directory
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

# Enable CORS for API routes
CORS(
    app,
    resources={r"/api/*": {"origins": "http://localhost:5173"}},  # URL exacta de tu frontend
    supports_credentials=True
)



# ---------------------------------------------------------------------------
# Serve Frontend
# ---------------------------------------------------------------------------
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../frontend')

@app.route('/')
def serve_index():
    """Serve the main index.html"""
    return send_from_directory(FRONTEND_DIR, 'index.html')

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
    data = request.get_json()
    username = data.get('email')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Email and password required"}), 400

    user = AuthManager.login(username, password)
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({
        "token": user['token'],
        "user": {
            "id": user['id'],
            "email": user['email'],
            "full_name": user['full_name']
        }
    }), 200

@app.route('/api/auth/logout', methods=['POST'])
@login_required
def logout():
    AuthManager.logout()
    return jsonify({"message": "Logged out successfully"}), 200

@app.route('/api/auth/change-password', methods=['POST'])
@login_required
def change_user_password():
    data = request.get_json()
    user = AuthManager.get_current_user()

    if not user:
        return jsonify({"error": "User not found in session"}), 401

    old_password = data.get('old_password')
    new_password = data.get('new_password')

    if not old_password or not new_password:
        return jsonify({"error": "Both passwords required"}), 400

    if len(new_password) < config.MIN_PASSWORD_LENGTH:
        return jsonify({"error": f"Password must be at least {config.MIN_PASSWORD_LENGTH} characters"}), 400

    success = User.change_password(user['id'], old_password, new_password)
    if success:
        return jsonify({"message": "Password changed successfully"}), 200
    else:
        return jsonify({"error": "Invalid current password"}), 401

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
        "clients": clients,
        "total": total,
        "page": page,
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
    return jsonify({"id": client_id, "message": "Client created successfully"}), 201

@app.route('/api/clients/<int:client_id>', methods=['PUT'])
@login_required
def update_client(client_id):
    data = request.get_json()
    with db.get_connection() as conn:
        conn.execute(
            "UPDATE clients SET full_name=?, email=?, phone=?, notes=?, updated_at=? WHERE id=?",
            (data.get('full_name'), data.get('email'), data.get('phone'), data.get('notes'), datetime.utcnow(), client_id)
        )
    return jsonify({"message": "Client updated successfully"}), 200

# ============================================================================
# INQUIRY ROUTES
# ============================================================================
@app.route('/api/inquiries', methods=['GET'])
@login_required
def get_inquiries():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    status_filter = request.args.get('status', '')
    sort = request.args.get('sort', 'date')

    with db.get_connection() as conn:
        query = "SELECT * FROM inquiries"
        params = []
        if status_filter:
            query += " WHERE status=?"
            params = [status_filter]
        if sort == 'date':
            query += " ORDER BY inquiry_date DESC"
        else:
            query += " ORDER BY priority DESC"
        query += " LIMIT ? OFFSET ?"
        params += [per_page, (page-1)*per_page]
        rows = conn.execute(query, tuple(params)).fetchall()
        total = conn.execute("SELECT COUNT(*) as total FROM inquiries").fetchone()['total']

    inquiries = [dict(r) for r in rows]
    return jsonify({"inquiries": inquiries, "total": total, "page": page, "per_page": per_page}), 200

@app.route('/api/inquiries', methods=['POST'])
@login_required
def create_inquiry():
    data = request.get_json()
    client_email = data['client_email']
    client_name = data['client_name']
    subject = data['subject']
    message = data['message']
    source = data.get('source', 'phone')

    with db.get_connection() as conn:
        row = conn.execute("SELECT id FROM clients WHERE email=?", (client_email,)).fetchone()
        if row:
            client_id = row['id']
        else:
            cursor = conn.execute("INSERT INTO clients (full_name,email) VALUES (?,?)", (client_name, client_email))
            client_id = cursor.lastrowid

        priority = get_inquiry_priority(message)
        cursor = conn.execute(
            "INSERT INTO inquiries (client_id, subject, message, source, priority, status) VALUES (?,?,?,?,?,?)",
            (client_id, subject, message, source, priority, 'pending')
        )
        inquiry_id = cursor.lastrowid

    return jsonify({"id": inquiry_id, "message": "Inquiry created successfully"}), 201

# ============================================================================
# PUBLISHER ROUTES
# ============================================================================
@app.route('/api/publishers/bulk-upload', methods=['POST'])
@login_required
def bulk_upload_publishers():
    data = request.get_json()
    publishers_data = data.get('publishers', [])
    if not publishers_data:
        return jsonify({"error": "No publishers data provided"}), 400

    total_inserted = db.bulk_insert_publishers(publishers_data)
    return jsonify({"message": f"Successfully uploaded {total_inserted} publishers", "total": total_inserted}), 200

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
        query += " LIMIT ? OFFSET ?"
        params += (per_page, (page-1)*per_page)
        rows = conn.execute(query, params).fetchall()
        total = conn.execute("SELECT COUNT(*) as total FROM publishers").fetchone()['total']

    publishers = [dict(r) for r in rows]
    return jsonify({"publishers": publishers, "total": total, "page": page, "per_page": per_page}), 200

# ============================================================================
# SYSTEM ROUTES
# ============================================================================
@app.route('/api/system/start-email-monitoring', methods=['POST'])
@login_required
def start_email_monitor():
    email_handler.start_email_monitoring()
    return jsonify({"message": "Email monitoring started"}), 200

@app.route('/api/system/stop-email-monitoring', methods=['POST'])
@login_required
def stop_email_monitor():
    email_handler.stop_email_monitoring()
    return jsonify({"message": "Email monitoring stopped"}), 200

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
    app.run(debug=config.DEBUG, host='0.0.0.0', port=5001)
