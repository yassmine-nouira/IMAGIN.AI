import os

class Config:
    DB_NAME = "artify_db"
    DB_USER = "postgres"
    DB_PASS = "eya"  # Ton nouveau mot de passe
    DB_HOST = "localhost"
    # On essaie 5433 d'abord car ta base est sur PG 18
    DB_PORT = "5433"