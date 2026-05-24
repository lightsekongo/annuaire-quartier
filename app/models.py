import psycopg2
import psycopg2.extras
import pandas as pd
from flask import g, current_app
from config import Config


def get_db():
    """
    Ouvre une connexion PostgreSQL pour la durée d'une requête HTTP.

    Sur Render (et la plupart des plateformes cloud), une seule variable
    DATABASE_URL est fournie. En local, on assemble les morceaux depuis
    config.py.
    """
    if 'db' not in g:
        if Config.DATABASE_URL:
            # Cas Render / production : on utilise l'URL complète
            g.db = psycopg2.connect(Config.DATABASE_URL)
        else:
            # Cas développement local : on assemble les morceaux
            g.db = psycopg2.connect(
                host     = Config.DB_HOST,
                port     = Config.DB_PORT,
                dbname   = Config.DB_NAME,
                user     = Config.DB_USER,
                password = Config.DB_PASSWORD
            )
    return g.db


def close_db(e=None):
    """
    Ferme la connexion PostgreSQL à la fin de chaque requête HTTP.
    Appelée automatiquement par Flask via teardown_appcontext.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()


def query_df(sql, params=None):
    """
    Exécute une requête SELECT et retourne un DataFrame pandas.
    Utilisé pour tous les calculs statistiques.
    """
    conn = get_db()
    return pd.read_sql(sql, conn, params=params)


def execute(sql, params=None):
    """
    Exécute une requête INSERT / UPDATE / DELETE.
    Gère le commit et le rollback automatiquement.
    """
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    def query_dicts(sql, params=None):
    
        conn = get_db()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        # Convertit les RealDictRow en vrais dicts Python
        return [dict(row) for row in rows]

def query_dicts(sql, params=None):
    """
    Exécute un SELECT et renvoie une liste de dicts (au lieu de tuples).
    Format : [{'id_commune': 1, 'nom': 'Abobo', ...}, ...]
    Indispensable pour garder la même API que les fixtures Python.
    """
    conn = get_db()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    return [dict(row) for row in rows]


def query_one(sql, params=None):
    """
    Exécute un SELECT et renvoie le premier résultat sous forme de dict.
    Renvoie None si aucun résultat.
    """
    results = query_dicts(sql, params)
    return results[0] if results else None


def execute_returning(sql, params=None):
    """
    Exécute un INSERT/UPDATE avec clause RETURNING.
    Renvoie le premier résultat sous forme de dict.
    Indispensable pour récupérer l'id généré par SERIAL après un INSERT.
    """
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            result = cur.fetchone()
        conn.commit()
        return dict(result) if result else None
    except Exception as e:
        conn.rollback()
        raise e

def query_one(sql, params=None):
    """
    Exécute un SELECT et renvoie le premier résultat sous forme de dict.
    Renvoie None si aucun résultat.
    """
    results = query_dicts(sql, params)
    return results[0] if results else None


def execute_returning(sql, params=None):
    """
    Exécute un INSERT/UPDATE avec clause RETURNING.
    Renvoie le premier résultat sous forme de dict.
    Indispensable pour récupérer l'id généré par SERIAL après un INSERT.
    """
    conn = get_db()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            result = cur.fetchone()
        conn.commit()
        return dict(result) if result else None
    except Exception as e:
        conn.rollback()
        raise e