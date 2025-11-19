-- TABLAS DE LA PLATAFORMA DE COTIZACIONES
-- Ejecutar este archivo una sola vez al iniciar

-- Tabla de usuarios autentificados (los que pueden entrar)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT 1
);

-- Tabla de clientes (tus potenciales clientes)
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

-- Tabla de consultas/emails recibidos
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
);

-- Tabla de respuestas enviadas
CREATE TABLE IF NOT EXISTS responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inquiry_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    response_text TEXT NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (inquiry_id) REFERENCES inquiries(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Tabla de publishers (tu base de 12,500)
CREATE TABLE IF NOT EXISTS publishers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    category TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indices para velocidad (IMPORTANTE para 12.5k registros)
CREATE INDEX IF NOT EXISTS idx_clients_email ON clients(email);
CREATE INDEX IF NOT EXISTS idx_inquiries_status ON inquiries(status);
CREATE INDEX IF NOT EXISTS idx_inquiries_received ON inquiries(received_at DESC);
CREATE INDEX IF NOT EXISTS idx_publishers_email ON publishers(email);
CREATE INDEX IF NOT EXISTS idx_responses_inquiry ON responses(inquiry_id);

-- Usuario admin por defecto (password: admin123 - CAMBIAR DESPUES)
INSERT OR IGNORE INTO users (username, password_hash, full_name, email) 
VALUES ('admin', 'scrypt:32768:8:1$YourHashHere$hash', 'Administrator', 'admin@company.com');