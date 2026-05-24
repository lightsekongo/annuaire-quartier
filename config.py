import os


class Config:
    """
    Configuration de l'application.

    Les paramètres de connexion peuvent être surchargés par des variables
    d'environnement (pratique pour le déploiement sur Render, Railway, etc.).
    En l'absence de variable, on utilise les valeurs par défaut pour
    le développement local.
    """

    # ─── Connexion PostgreSQL ─────────────────────────────────
    # Render fournit une variable DATABASE_URL au format complet.
    # En local, on assemble les morceaux ci-dessous.

    DATABASE_URL = os.environ.get('DATABASE_URL')

    DB_HOST     = os.environ.get('DB_HOST',     'localhost')
    DB_PORT     = int(os.environ.get('DB_PORT', 5432))
    DB_NAME     = os.environ.get('DB_NAME',     'annuaire_quartier')
    DB_USER     = os.environ.get('DB_USER',     'postgres')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'CHANGE_ME')

    # ─── Clé secrète Flask ────────────────────────────────────
    # Pour les sessions et les flash messages. Pas critique pour ce projet
    # mais nécessaire.
    SECRET_KEY = os.environ.get('SECRET_KEY', os.urandom(24))