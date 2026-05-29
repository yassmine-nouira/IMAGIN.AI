import psycopg2
from psycopg2.extras import RealDictCursor

# Configuration de connexion PostgreSQL
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'artify_db',
    'user': 'postgres',
    'password': 'postgres'  # Change ici si nécessaire
}

def get_db_connection():
    """Crée une connexion à la base de données"""
    conn = psycopg2.connect(**DB_CONFIG)
    return conn

def create_tables():
    """Crée la table users si elle n'existe pas"""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(100) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("✅ Table 'users' créée avec succès")

def insert_user(username, email, password):
    """Insère un nouvel utilisateur"""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO users (username, email, password) VALUES (%s, %s, %s) RETURNING id",
        (username, email, password)
    )

    user_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    return user_id

def get_user_by_email(email):
    """Récupère un utilisateur par email"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        "SELECT * FROM users WHERE email = %s",
        (email,)
    )

    user = cur.fetchone()
    cur.close()
    conn.close()

    return user