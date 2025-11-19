from database import db

print("Creando tablas...")

# Crear tabla users
db.execute_update("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT 1
)
""")
print("✓ Tabla users creada")

# Crear tabla clients
db.execute_update("""
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
)
""")
print("✓ Tabla clients creada")

# Crear tabla inquiries
db.execute_update("""
CREATE TABLE IF NOT EXISTS inquiries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER,
    subject TEXT NOT NULL,
    message TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    responded_at TIMESTAMP,
    assigned_to INTEGER,
    FOREIGN KEY (client_id) REFERENCES clients(id),
    FOREIGN KEY (assigned_to) REFERENCES users(id)
)
""")
print("✓ Tabla inquiries creada")

# Crear tabla responses
db.execute_update("""
CREATE TABLE IF NOT EXISTS responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inquiry_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    response_text TEXT NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (inquiry_id) REFERENCES inquiries(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
)
""")
print("✓ Tabla responses creada")

# Crear tabla publishers
db.execute_update("""
CREATE TABLE IF NOT EXISTS publishers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    category TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
print("✓ Tabla publishers creada")

# Crear índices
db.execute_update("CREATE INDEX IF NOT EXISTS idx_clients_email ON clients(email)")
db.execute_update("CREATE INDEX IF NOT EXISTS idx_inquiries_status ON inquiries(status)")
db.execute_update("CREATE INDEX IF NOT EXISTS idx_inquiries_received ON inquiries(received_at DESC)")
db.execute_update("CREATE INDEX IF NOT EXISTS idx_publishers_email ON publishers(email)")
db.execute_update("CREATE INDEX IF NOT EXISTS idx_responses_inquiry ON responses(inquiry_id)")
print("✓ Índices creados")

print("\n✓✓✓ Base de datos completa!")