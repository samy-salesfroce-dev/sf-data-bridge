import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'migration.db')

def get_connection():
    """Returns a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the SQLite schema."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Projects table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            source_username TEXT,
            source_domain TEXT,
            target_username TEXT,
            target_domain TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Selected Objects for Migration
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS project_objects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            object_name TEXT,
            status TEXT DEFAULT 'Pending',
            validation_errors TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
    """)
    
    # Field Mappings
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS field_mappings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_object_id INTEGER,
            source_field TEXT,
            target_field TEXT,
            transformation_logic TEXT,
            FOREIGN KEY(project_object_id) REFERENCES project_objects(id)
        )
    """)
    
    # Record tracking for updates/upserts
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS migration_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_object_id INTEGER,
            source_record_id TEXT,
            target_record_id TEXT,
            status TEXT,
            error_message TEXT,
            FOREIGN KEY(project_object_id) REFERENCES project_objects(id)
        )
    """)
    
    conn.commit()
    conn.close()

# --- CRUD Operations ---

def create_project(name, src_username, src_domain, tgt_username, tgt_domain):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO projects (name, source_username, source_domain, target_username, target_domain)
            VALUES (?, ?, ?, ?, ?)
        """, (name, src_username, src_domain, tgt_username, tgt_domain))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def get_projects():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects ORDER BY created_at DESC")
    projects = cursor.fetchall()
    conn.close()
    return [dict(row) for row in projects]

def get_project_by_id(project_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    project = cursor.fetchone()
    conn.close()
    return dict(project) if project else None

def add_project_object(project_id, object_name):
    conn = get_connection()
    cursor = conn.cursor()
    # verify it doesnt exist first
    cursor.execute("SELECT id FROM project_objects WHERE project_id = ? AND object_name = ?", (project_id, object_name))
    if cursor.fetchone():
        conn.close()
        return None
    
    cursor.execute("""
        INSERT INTO project_objects (project_id, object_name)
        VALUES (?, ?)
    """, (project_id, object_name))
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id

def get_project_objects(project_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM project_objects WHERE project_id = ?", (project_id,))
    objects = cursor.fetchall()
    conn.close()
    return [dict(row) for row in objects]

def save_field_mapping(project_object_id, source_field, target_field, transform=None):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if mapping exists
    cursor.execute("SELECT id FROM field_mappings WHERE project_object_id = ? AND source_field = ?", (project_object_id, source_field))
    row = cursor.fetchone()
    
    if row:
        cursor.execute("""
            UPDATE field_mappings SET target_field = ?, transformation_logic = ? WHERE id = ?
        """, (target_field, transform, row['id']))
    else:
        cursor.execute("""
            INSERT INTO field_mappings (project_object_id, source_field, target_field, transformation_logic)
            VALUES (?, ?, ?, ?)
        """, (project_object_id, source_field, target_field, transform))
        
    conn.commit()
    conn.close()

def get_field_mappings(project_object_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM field_mappings WHERE project_object_id = ?", (project_object_id,))
    mappings = cursor.fetchall()
    conn.close()
    return [dict(row) for row in mappings]

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
