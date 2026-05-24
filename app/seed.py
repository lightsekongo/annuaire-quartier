"""
Script de peuplement initial de la base PostgreSQL.

Lit les données fictives générées par app/fixtures.py et les insère
dans les 4 tables (commune, quartier, menage, membre).

USAGE :
    python -m app.seed

Le script est IDEMPOTENT : il vide la base avant chaque exécution
et repeuple avec exactement les mêmes données reproductibles.
Pratique pour repartir d'un état propre avant une démo / soutenance.
"""
import sys
from flask import Flask
from config import Config

# Imports des données fictives (ne modifient pas la base)
from app.fixtures import (
    COMMUNES, QUARTIERS, CENTROIDES_COMMUNES,
    get_menages, get_membres, get_quartiers,
)


def _conn():
    """Ouvre une connexion PostgreSQL en dehors du contexte Flask."""
    import psycopg2
    if Config.DATABASE_URL:
        return psycopg2.connect(Config.DATABASE_URL)
    return psycopg2.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        dbname=Config.DB_NAME,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
    )


def _vider_tables(cur):
    """Vide les tables dans l'ordre inverse des FK (membre → menage → quartier → commune)."""
    cur.execute("TRUNCATE TABLE membre RESTART IDENTITY CASCADE")
    cur.execute("TRUNCATE TABLE menage RESTART IDENTITY CASCADE")
    cur.execute("TRUNCATE TABLE quartier RESTART IDENTITY CASCADE")
    cur.execute("TRUNCATE TABLE commune RESTART IDENTITY CASCADE")
    print("  ✓ Tables vidées")


def _peupler_communes(cur):
    """Insère les 13 communes du District d'Abidjan."""
    for id_c, nom, slug, type_c, population in COMMUNES:
        centroide = CENTROIDES_COMMUNES.get(slug, (None, None))
        cur.execute("""
            INSERT INTO commune (id_commune, nom, slug, type,
                                 population_osm, centroid_lat, centroid_lng)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (id_c, nom, slug, type_c, population, centroide[0], centroide[1]))

    # Important : on remet le compteur SERIAL au max + 1
    cur.execute(
        "SELECT setval('commune_id_commune_seq', "
        "(SELECT MAX(id_commune) FROM commune))"
    )
    print(f"  ✓ {len(COMMUNES)} communes insérées")


def _peupler_quartiers(cur):
    """Insère les quartiers avec leurs coordonnées GPS générées."""
    tous_quartiers = get_quartiers()
    for q in tous_quartiers:
        cur.execute("""
            INSERT INTO quartier (id_quartier, nom, id_commune, lat, lng)
            VALUES (%s, %s, %s, %s, %s)
        """, (q['id_quartier'], q['nom'], q['id_commune'], q['lat'], q['lng']))

    cur.execute(
        "SELECT setval('quartier_id_quartier_seq', "
        "(SELECT MAX(id_quartier) FROM quartier))"
    )
    print(f"  ✓ {len(tous_quartiers)} quartiers insérés")


def _peupler_menages(cur):
    """Insère les 120 ménages fictifs."""
    menages = get_menages()
    inserees = 0

    for m in menages:
        # Cherche l'id_quartier correspondant (peut être NULL)
        cur.execute("""
            SELECT id_quartier FROM quartier
            WHERE id_commune = %s AND nom = %s
        """, (m['id_commune'], m['quartier']))
        row = cur.fetchone()
        id_quartier = row[0] if row else None

        cur.execute("""
            INSERT INTO menage (
                id_menage, nom_menage, id_commune, id_quartier, quartier_nom,
                type_logement, statut_occupation, nombre_pieces,
                source_eau, type_toilettes, source_eclairage, gestion_ordures,
                biens_durables, date_recensement
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s
            )
        """, (
            m['id_menage'],
            m['nom_menage'],
            m['id_commune'],
            id_quartier,
            m['quartier'],
            m.get('type_logement', ''),
            m.get('statut_occupation', ''),
            m.get('nombre_pieces', 0),
            m.get('source_eau', ''),
            m.get('type_toilettes', ''),
            m.get('source_eclairage', ''),
            m.get('gestion_ordures', ''),
            m.get('biens_durables', []),
            m.get('date_recensement') or None,
        ))
        inserees += 1

    cur.execute(
        "SELECT setval('menage_id_menage_seq', "
        "(SELECT MAX(id_menage) FROM menage))"
    )
    print(f"  ✓ {inserees} ménages insérés")


def _peupler_membres(cur):
    """Insère tous les membres des ménages."""
    membres = get_membres()
    inserees = 0

    for m in membres:
        cur.execute("""
            INSERT INTO membre (
                id_membre, id_menage,
                prenom, nom, sexe, date_naissance, lien_chef,
                situation_matrimoniale, niveau_instruction, sait_lire_ecrire,
                situation_activite, type_emploi, secteur_emploi,
                piece_identite, handicap
            ) VALUES (
                %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s
            )
        """, (
            m['id_membre'],
            m['id_menage'],
            m['prenom'],
            m['nom'],
            m['sexe'],
            m['date_naissance'],
            m.get('lien_chef', ''),
            m.get('situation_matrimoniale', 'Célibataire'),
            m.get('niveau_instruction', 'Aucun'),
            m.get('sait_lire_ecrire', 'Non'),
            m.get('situation_activite', 'Inactif'),
            m.get('type_emploi', ''),
            m.get('secteur_emploi', ''),
            m.get('piece_identite', 'Aucune'),
            m.get('handicap', 'Aucun'),
        ))
        inserees += 1

    cur.execute(
        "SELECT setval('membre_id_membre_seq', "
        "(SELECT MAX(id_membre) FROM membre))"
    )
    print(f"  ✓ {inserees} membres insérés")


def seed():
    """Pipeline complet du seed."""
    print("\n🌱  Peuplement de la base annuaire_quartier")
    print("-" * 50)

    conn = _conn()
    try:
        with conn.cursor() as cur:
            _vider_tables(cur)
            _peupler_communes(cur)
            _peupler_quartiers(cur)
            _peupler_menages(cur)
            _peupler_membres(cur)
        conn.commit()

        # Petit récap final
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    (SELECT COUNT(*) FROM commune),
                    (SELECT COUNT(*) FROM quartier),
                    (SELECT COUNT(*) FROM menage),
                    (SELECT COUNT(*) FROM membre)
            """)
            nc, nq, nm, nb = cur.fetchone()
        print("-" * 50)
        print(f"✅  Seed terminé : {nc} communes · {nq} quartiers · "
              f"{nm} ménages · {nb} membres")
        print()

    except Exception as e:
        conn.rollback()
        print(f"\n❌  Erreur pendant le seed : {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    seed()