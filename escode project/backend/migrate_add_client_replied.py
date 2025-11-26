"""
MIGRACIÓN: Agregar trazabilidad a responses
Ejecutar desde: backend/
Comando: python migrate_add_client_replied.py
"""
import sqlite3
import os

DB_PATH = 'database/quotations.db'

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"ERROR: No se encuentra {DB_PATH}")
        print("Ejecutar desde el directorio backend/")
        return
    
    print("="*60)
    print("MIGRACIÓN: Agregar trazabilidad a responses")
    print("="*60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Verificar si la columna ya existe
        cursor.execute("PRAGMA table_info(responses)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'client_replied' in columns:
            print("\nLa columna 'client_replied' ya existe.")
            print("No se necesita migración.")
        else:
            print("\nAgregando columna 'client_replied' a tabla responses...")
            cursor.execute("""
                ALTER TABLE responses 
                ADD COLUMN client_replied INTEGER DEFAULT 0
            """)
            conn.commit()
            print("Columna agregada exitosamente!")
        
        # Verificar estructura final
        print("\n" + "="*60)
        print("ESTRUCTURA ACTUAL DE TABLA RESPONSES:")
        print("="*60)
        cursor.execute("PRAGMA table_info(responses)")
        for col in cursor.fetchall():
            default = f"DEFAULT {col[4]}" if col[4] else ""
            print(f"  {col[1]:20} {col[2]:15} {'NOT NULL' if col[3] else ''} {default}")
        
        print("\n" + "="*60)
        print("MIGRACIÓN COMPLETADA EXITOSAMENTE")
        print("="*60)
        print("\nCampos disponibles:")
        print("  - id: ID único de la response")
        print("  - inquiry_id: ID del inquiry relacionado")
        print("  - user_id: Usuario que creó la response")
        print("  - response_text: Texto de la respuesta enviada")
        print("  - sent_at: Fecha/hora de envío")
        print("  - client_replied: 0=No respondió, 1=Cliente respondió")
        print("\n" + "="*60)
        
    except Exception as e:
        print(f"\nERROR durante la migración: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()