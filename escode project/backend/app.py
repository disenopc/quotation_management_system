"""
MAIN APPLICATION FILE WITH CONTENT FILTER

Backend server for Quotation Management System using SQLite3 Database class.
Flask handles API endpoints and connects frontend with database, email, and AI.

NUEVO: Filtro de contenido extraíble en sync_emails
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
    
    # Check if user is admin or manager
    if user.get('role') not in ['admin', 'manager']:
        return jsonify({"error": "Unauthorized - Admin or Manager access required"}), 403
    
    try:
        with db.get_connection() as conn:
            # Check if client has inquiries
            inquiries = conn.execute(
                "SELECT COUNT(*) as count FROM inquiries WHERE client_id=?", 
                (client_id,)
            ).fetchone()
            
            if inquiries['count'] > 0:
                return jsonify({
                    "error": "Cannot delete client with existing inquiries",
                    "inquiries_count": inquiries['count']
                }), 400
            
            # Delete client
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
        # JOIN con clients para traer el nombre
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
        
        # Total también con filtro si aplica
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
# RESPONSE ROUTES
# ============================================================================
@app.route('/api/responses', methods=['POST'])
@login_required
def create_response():
    """Create response to inquiry"""
    data = request.get_json()
    inquiry_id = data.get('inquiry_id')
    response_text = data.get('response_text')
    
    if not inquiry_id or not response_text:
        return jsonify({"error": "Missing required fields"}), 400
    
    user = AuthManager.get_current_user()
    
    with db.get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO responses (inquiry_id, user_id, response_text) VALUES (?,?,?)",
            (inquiry_id, user['id'], response_text)
        )
        response_id = cursor.lastrowid
        
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
    """Get single response by ID"""
    with db.get_connection() as conn:
        query = """
            SELECT 
                r.id,
                r.inquiry_id,
                r.response_text,
                r.sent_at,
                r.client_replied,
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
    
    return jsonify(dict(row)), 200


@app.route('/api/responses/<int:response_id>/mark-replied', methods=['PUT'])
@login_required
def mark_client_replied(response_id):
    """Mark that client replied to this response"""
    data = request.get_json()
    client_replied = data.get('client_replied', 1)  # 1 = replied, 0 = not replied
    
    with db.get_connection() as conn:
        # Verificar que existe
        response = conn.execute(
            "SELECT id FROM responses WHERE id = ?",
            (response_id,)
        ).fetchone()
        
        if not response:
            return jsonify({"error": "Response not found"}), 404
        
        # Actualizar
        conn.execute(
            "UPDATE responses SET client_replied = ? WHERE id = ?",
            (client_replied, response_id)
        )
    
    return jsonify({
        "success": True, 
        "message": f"Response marked as {'replied' if client_replied else 'not replied'}"
    }), 200

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
        # Get current user info for signature
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
# EMAIL ROUTES - CON FILTRO DE CONTENIDO EXTRAÍBLE
# ============================================================================
@app.route('/api/email/sync', methods=['POST'])
@login_required
def sync_emails():
    """
    Sync emails manually - SOLO NO LEIDOS (UNSEEN)
    CON FILTRO: Solo procesa emails con información completa (min 3 de 4 campos)
    """
    try:
        import re
        
        # Fetch new emails using email_handler
        new_emails = email_handler.fetch_new_emails()
        count = 0
        rejected_count = 0
        
        logging.info(f"\nProcesando {len(new_emails)} emails nuevos...")
        
        for email_data in new_emails:
            # Extract data
            from_email = email_data.get('from')
            body = email_data.get('body', '')
            raw_subject = email_data.get('subject', '').strip()
            
            # ========================================================================
            # PASO 1: EXTRAER INFORMACIÓN DE CONTACTO
            # ========================================================================
            
            # Extract phone from body (various formats)
            phone = None
            phone_patterns = [
                r'[Pp]hone[\s:]+\*?(\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9})\*?',  # Phone: *+1-202-334-8912*
                r'[Tt]el[eé]fono[\s:]+\*?(\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9})\*?',  # Teléfono:
                r'\*(\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9})\*',  # *+1-202-334-8912*
                r'\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',  # General international
            ]
            for pattern in phone_patterns:
                match = re.search(pattern, body)
                if match:
                    phone_raw = match.group(1) if match.lastindex else match.group(0)
                    phone_raw = phone_raw.strip().replace('*', '')
                    # Validar que tenga al menos 6 dígitos
                    if len(re.findall(r'\d', phone_raw)) >= 6:
                        phone = phone_raw
                        break
            
            # Extract company from body (common patterns)
            company = None
            company_patterns = [
                r'[Ff]rom\s+\*([A-Z][A-Za-z\s&.]+)\*',  # from *BrightWave Solutions*
                r'[Ff]rom\s+([A-Z][A-Za-z\s&.]+?)(?:\.|$|\n)',  # from Acme Corp
                r'(?:company|empresa|organization|org)[\s:]+\*?([A-Z][A-Za-z\s&.,]+?)\*?(?:\n|$|\.|,)',
                r'\*([A-Z][A-Za-z\s&.]+(?:Solutions|Inc|LLC|Ltd|Corp|SA|SRL|Systems|Technologies|Group|Company))\*',
                r'([A-Z][A-Za-z\s&.]+(?:Solutions|Inc|LLC|Ltd|Corp|SA|SRL|Systems|Technologies|Group))',
            ]
            for pattern in company_patterns:
                match = re.search(pattern, body, re.IGNORECASE | re.MULTILINE)
                if match:
                    company = match.group(1).strip().replace('*', '')
                    # Clean up company name
                    company = re.sub(r'\s+', ' ', company)  # Remove extra spaces
                    # Remove trailing periods or commas
                    company = re.sub(r'[.,]+$', '', company)
                    if len(company) > 3:  # Only if reasonable length
                        break
            
            # Extract name from email or body - improved patterns
            full_name = from_email.split('@')[0]
            
            # Try multiple name patterns (order matters - most specific first)
            name_patterns = [
                r'(?:my name is|I am|I\'m)\s+\*?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\*?\s+from',  # "My name is John Smith from"
                r'(?:my name is|I am|I\'m)\s+\*?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\*?',  # "My name is *Emily Parker*"
                r'(?:name|nombre)[\s:]+\*?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\*?',  # "Name: John Smith"
                r'^\*?([A-Z][a-z]+\s+[A-Z][a-z]+)\*?',  # "*Emily Parker*" at start
            ]
            
            for pattern in name_patterns:
                name_match = re.search(pattern, body, re.IGNORECASE | re.MULTILINE)
                if name_match:
                    full_name = name_match.group(1).strip()
                    break
            
            # Extract client email from body (for WordPress forms and future integrations)
            client_email = None
            email_patterns = [
                r'(?:email|e-mail|correo)[\s:]+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',  # "Email: user@example.com"
                r'(?:contact|contacto)[\s:]+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',  # "Contact: user@example.com"
                r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',  # Any email in body
            ]
            
            for pattern in email_patterns:
                email_match = re.search(pattern, body, re.IGNORECASE)
                if email_match:
                    extracted_email = email_match.group(1).lower()
                    # Ignore common system emails
                    if not any(x in extracted_email for x in ['noreply', 'no-reply', 'wordpress', 'system', 'mailer']):
                        client_email = extracted_email
                        break
            
            # If no email found in body, use sender email as fallback
            if not client_email:
                client_email = from_email
            
            # ========================================================================
            # PASO 2: FILTRO DE CONTENIDO - Verificar información completa
            # ========================================================================
            
            # Validar cada campo extraído
            valid_name = bool(full_name and full_name != from_email.split('@')[0] and len(full_name) > 2)
            valid_email = bool(client_email and '@' in client_email)
            valid_phone = bool(phone)
            valid_company = bool(company and len(company) > 1)
            
            # Contar campos válidos
            valid_fields_count = sum([valid_name, valid_email, valid_phone, valid_company])
            
            # CONFIGURACIÓN: Ajusta este número según necesites (2, 3 o 4)
            MIN_REQUIRED_FIELDS = 3
            
            # Si no cumple con el mínimo, RECHAZAR
            if valid_fields_count < MIN_REQUIRED_FIELDS:
                rejected_count += 1
                
                # Log detallado de por qué se rechazó
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
                
                logging.warning(f"REJECTED Email ({valid_fields_count}/{MIN_REQUIRED_FIELDS} campos): {raw_subject[:50]}")
                logging.warning(f"   Tiene: {', '.join(has) if has else 'Nada'}")
                logging.warning(f"   Falta: {', '.join(missing)}")
                continue  # Saltar este email
            
            # ========================================================================
            # PASO 3: Email válido - Procesarlo
            # ========================================================================
            
            logging.info(f"VALID Email ({valid_fields_count}/4 campos): {raw_subject[:50]}")
            
            # Generate subject: Company - Date (or use original if present)
            if not raw_subject or raw_subject == '':
                # Build subject from extracted data: Company - Date
                current_date = datetime.now().strftime('%d/%m/%Y')
                if company:
                    subject = f"{company} - {current_date}"
                else:
                    subject = f"{full_name} - {current_date}"
            else:
                subject = raw_subject
            
            # Get or create client
            with db.get_connection() as conn:
                # ESTRATEGIA: Identificar cliente por (nombre + compañía)
                # El email puede repetirse entre clientes, no es confiable
                # Crear email sintético único para cumplir restricción UNIQUE en BD
                
                # Buscar cliente existente por nombre y compañía
                cursor = conn.execute(
                    "SELECT id, email FROM clients WHERE full_name = ? AND company = ?",
                    (full_name, company if company else '')
                )
                client = cursor.fetchone()
                
                if not client:
                    # Cliente nuevo - crear email sintético único
                    # Formato: nombre.compañia@internal.local
                    name_slug = full_name.lower().replace(' ', '.').replace('*', '')
                    company_slug = company.lower().replace(' ', '.').replace('*', '') if company else 'unknown'
                    synthetic_email = f"{name_slug}.{company_slug}@internal.local"
                    
                    # Create new client with extracted info
                    cursor = conn.execute(
                        "INSERT INTO clients (full_name, email, phone, company) VALUES (?, ?, ?, ?)",
                        (full_name, synthetic_email, phone, company)
                    )
                    client_id = cursor.lastrowid
                    logging.info(f"   NEW cliente creado: {full_name} - {company} ({synthetic_email})")
                else:
                    client_id = client[0]
                    # Update existing client if we found new info
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
                        logging.info(f"   UPDATED Cliente actualizado: {full_name} - {company}")
                
                # Check if inquiry already exists (avoid duplicates)
                existing = conn.execute(
                    "SELECT id FROM inquiries WHERE client_id=? AND subject=? AND message=?",
                    (client_id, subject, body)
                ).fetchone()
                
                if not existing:
                    # Create inquiry only if it doesn't exist
                    conn.execute(
                        "INSERT INTO inquiries (client_id, subject, message, status, received_at) VALUES (?, ?, ?, ?, ?)",
                        (client_id, subject, body, 'pending', datetime.utcnow())
                    )
                    count += 1
                    logging.info(f"   CREATED Inquiry creado: {subject[:50]}")
                else:
                    logging.info(f"   DUPLICATE Inquiry duplicado, omitido: {subject[:50]}")
        
        # ========================================================================
        # RESUMEN FINAL
        # ========================================================================
        logging.info(f"\nRESUMEN DEL SYNC:")
        logging.info(f"   Total procesados: {len(new_emails)}")
        logging.info(f"   VALID Válidos (con info completa): {count + (len(new_emails) - count - rejected_count)}")
        logging.info(f"   REJECTED Rechazados (info incompleta): {rejected_count}")
        logging.info(f"   CREATED Inquiries creados: {count}\n")
        
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
    print(f"Filtro de contenido: ACTIVADO (mínimo {3} de 4 campos)")
    app.run(debug=config.DEBUG, host='0.0.0.0', port=5001)