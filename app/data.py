"""
Couche d'accès aux données — version PostgreSQL.

Remplace app/fixtures.py avec EXACTEMENT la même API publique.
Aucun changement nécessaire dans les templates ni les routes :
seuls les imports passent de `from app.fixtures import ...`
à `from app.data import ...`.

Hiérarchie de la base : commune → quartier → menage → membre
"""
from app.models import query_dicts, query_one, execute, execute_returning


# ============================================================
# COMMUNES
# ============================================================
def get_communes():
    """Liste des 13 communes (centroïdes castés en float pour JSON)."""
    return query_dicts("""
        SELECT
            id_commune,
            nom,
            slug,
            type,
            population_osm,
            centroid_lat::float  AS centroid_lat,
            centroid_lng::float  AS centroid_lng
        FROM commune
        ORDER BY nom
    """)


# ============================================================
# QUARTIERS
# ============================================================
def get_quartiers():
    """
    Liste tous les quartiers avec leurs coordonnées GPS.
    Les colonnes DECIMAL sont castées en FLOAT pour être JSON-sérialisables.
    """
    return query_dicts("""
        SELECT
            q.id_quartier,
            q.nom,
            q.id_commune,
            c.slug                       AS commune_slug,
            c.nom                        AS commune_nom,
            q.lat::float                 AS lat,
            q.lng::float                 AS lng,
            COALESCE(
                (SELECT COUNT(*) FROM menage m WHERE m.id_quartier = q.id_quartier),
                0
            )::int                       AS nb_menages
        FROM quartier q
        JOIN commune c ON c.id_commune = q.id_commune
        ORDER BY c.nom, q.nom
    """)


# ============================================================
# MÉNAGES — LECTURE
# ============================================================
def get_menages():
    """
    Liste tous les ménages avec nom, slug et type de commune.
    Format identique aux fixtures.
    """
    return query_dicts("""
        SELECT
            m.id_menage,
            m.nom_menage,
            m.id_commune,
            c.nom            AS commune,
            c.slug           AS commune_slug,
            c.type           AS commune_type,
            m.quartier_nom   AS quartier,
            m.id_quartier,
            m.type_logement,
            m.statut_occupation,
            m.nombre_pieces,
            m.source_eau,
            m.type_toilettes,
            m.source_eclairage,
            m.gestion_ordures,
            COALESCE(m.biens_durables, ARRAY[]::TEXT[]) AS biens_durables,
            m.date_recensement,
            m.cree_le
        FROM menage m
        JOIN commune c ON c.id_commune = m.id_commune
        ORDER BY m.id_menage
    """)


def get_menage_by_id(id_menage):
    """Renvoie un ménage par son id, ou None si introuvable."""
    return query_one("""
        SELECT
            m.id_menage,
            m.nom_menage,
            m.id_commune,
            c.nom            AS commune,
            c.slug           AS commune_slug,
            c.type           AS commune_type,
            m.quartier_nom   AS quartier,
            m.id_quartier,
            m.type_logement,
            m.statut_occupation,
            m.nombre_pieces,
            m.source_eau,
            m.type_toilettes,
            m.source_eclairage,
            m.gestion_ordures,
            COALESCE(m.biens_durables, ARRAY[]::TEXT[]) AS biens_durables,
            m.date_recensement,
            m.cree_le
        FROM menage m
        JOIN commune c ON c.id_commune = m.id_commune
        WHERE m.id_menage = %s
    """, (id_menage,))


# ============================================================
# MEMBRES — LECTURE
# ============================================================
def get_membres():
    """Liste tous les membres."""
    return query_dicts("""
        SELECT
            id_membre, id_menage,
            prenom, nom, sexe, date_naissance,
            lien_chef, situation_matrimoniale,
            niveau_instruction, sait_lire_ecrire,
            situation_activite, type_emploi, secteur_emploi,
            piece_identite, handicap
        FROM membre
        ORDER BY id_membre
    """)


def get_membres_by_menage(id_menage):
    """Liste les membres d'un ménage donné."""
    return query_dicts("""
        SELECT
            id_membre, id_menage,
            prenom, nom, sexe, date_naissance,
            lien_chef, situation_matrimoniale,
            niveau_instruction, sait_lire_ecrire,
            situation_activite, type_emploi, secteur_emploi,
            piece_identite, handicap
        FROM membre
        WHERE id_menage = %s
        ORDER BY
            CASE WHEN lien_chef = 'Chef' THEN 0 ELSE 1 END,
            date_naissance
    """, (id_menage,))


# ============================================================
# STATISTIQUES GLOBALES
# ============================================================
def get_stats_globales():
    """
    Renvoie les stats globales : nombre de ménages, de membres,
    taille moyenne. Format identique aux fixtures.
    """
    result = query_one("""
        SELECT
            (SELECT COUNT(*) FROM menage) AS nb_menages,
            (SELECT COUNT(*) FROM membre) AS nb_membres
    """)
    nb_menages = result['nb_menages'] or 0
    nb_membres = result['nb_membres'] or 0
    taille_moy = round(nb_membres / nb_menages, 2) if nb_menages else 0
    return {
        'nb_menages': nb_menages,
        'nb_membres': nb_membres,
        'taille_moyenne': taille_moy,
    }


# ============================================================
# MÉNAGES — ÉCRITURE (CREATE / UPDATE / DELETE)
# ============================================================
def creer_menage(donnees):
    """
    Crée un nouveau ménage. `donnees` est un dict avec au minimum :
        nom_menage, id_commune, quartier (= nom_quartier).
    Renvoie le ménage créé (avec son id_menage généré).
    """
    # Récupère le nom de commune et l'id_quartier correspondants
    commune = query_one(
        "SELECT nom FROM commune WHERE id_commune = %s",
        (donnees['id_commune'],)
    )
    nom_commune = commune['nom'] if commune else '—'

    # Cherche l'id_quartier si on a un nom (peut être None si quartier ad hoc)
    id_quartier_row = query_one("""
        SELECT id_quartier FROM quartier
        WHERE id_commune = %s AND nom = %s
    """, (donnees['id_commune'], donnees['quartier'].strip()))
    id_quartier = id_quartier_row['id_quartier'] if id_quartier_row else None

    nouveau = execute_returning("""
        INSERT INTO menage (
            nom_menage, id_commune, id_quartier, quartier_nom,
            type_logement, statut_occupation, nombre_pieces,
            source_eau, type_toilettes, source_eclairage, gestion_ordures,
            biens_durables, date_recensement
        ) VALUES (
            %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s
        )
        RETURNING id_menage
    """, (
        donnees['nom_menage'].strip(),
        donnees['id_commune'],
        id_quartier,
        donnees['quartier'].strip(),
        donnees.get('type_logement', ''),
        donnees.get('statut_occupation', ''),
        int(donnees.get('nombre_pieces') or 0),
        donnees.get('source_eau', ''),
        donnees.get('type_toilettes', ''),
        donnees.get('source_eclairage', ''),
        donnees.get('gestion_ordures', ''),
        donnees.get('biens_durables', []),
        donnees.get('date_recensement') or None,
    ))

    # On renvoie le ménage complet (pour cohérence avec l'ancienne API)
    return get_menage_by_id(nouveau['id_menage'])


def modifier_menage(id_menage, donnees):
    """
    Met à jour un ménage existant. Renvoie le ménage modifié ou None.
    """
    # Reconstruit le nom de commune et l'id_quartier si on change la commune
    id_quartier = None
    if 'id_commune' in donnees and 'quartier' in donnees:
        id_quartier_row = query_one("""
            SELECT id_quartier FROM quartier
            WHERE id_commune = %s AND nom = %s
        """, (donnees['id_commune'], donnees['quartier'].strip()))
        id_quartier = id_quartier_row['id_quartier'] if id_quartier_row else None

    execute("""
        UPDATE menage SET
            nom_menage        = %s,
            id_commune        = %s,
            id_quartier       = %s,
            quartier_nom      = %s,
            type_logement     = %s,
            statut_occupation = %s,
            nombre_pieces     = %s,
            source_eau        = %s,
            type_toilettes    = %s,
            source_eclairage  = %s,
            gestion_ordures   = %s,
            biens_durables    = %s,
            date_recensement  = %s
        WHERE id_menage = %s
    """, (
        donnees['nom_menage'].strip(),
        donnees['id_commune'],
        id_quartier,
        donnees['quartier'].strip(),
        donnees.get('type_logement', ''),
        donnees.get('statut_occupation', ''),
        int(donnees.get('nombre_pieces') or 0),
        donnees.get('source_eau', ''),
        donnees.get('type_toilettes', ''),
        donnees.get('source_eclairage', ''),
        donnees.get('gestion_ordures', ''),
        donnees.get('biens_durables', []),
        donnees.get('date_recensement') or None,
        id_menage,
    ))
    return get_menage_by_id(id_menage)


def supprimer_menage(id_menage):
    """
    Supprime un ménage et tous ses membres (ON DELETE CASCADE).
    Renvoie True si le ménage existait.
    """
    existe = query_one("SELECT 1 FROM menage WHERE id_menage = %s", (id_menage,))
    if not existe:
        return False
    execute("DELETE FROM menage WHERE id_menage = %s", (id_menage,))
    return True


# ============================================================
# MEMBRES — ÉCRITURE
# ============================================================
def creer_membre(donnees):
    """Crée un nouveau membre dans un ménage existant."""
    nouveau = execute_returning("""
        INSERT INTO membre (
            id_menage,
            prenom, nom, sexe, date_naissance, lien_chef,
            situation_matrimoniale, niveau_instruction, sait_lire_ecrire,
            situation_activite, type_emploi, secteur_emploi,
            piece_identite, handicap
        ) VALUES (
            %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s
        )
        RETURNING id_membre
    """, (
        donnees['id_menage'],
        donnees['prenom'].strip(),
        donnees['nom'].strip(),
        donnees['sexe'],
        donnees['date_naissance'],
        donnees.get('lien_chef', ''),
        donnees.get('situation_matrimoniale', 'Célibataire'),
        donnees.get('niveau_instruction', 'Aucun'),
        donnees.get('sait_lire_ecrire', 'Non'),
        donnees.get('situation_activite', 'Inactif'),
        donnees.get('type_emploi', ''),
        donnees.get('secteur_emploi', ''),
        donnees.get('piece_identite', 'Aucune'),
        donnees.get('handicap', 'Aucun'),
    ))
    # Renvoie le membre complet
    return query_one(
        "SELECT * FROM membre WHERE id_membre = %s",
        (nouveau['id_membre'],)
    )


def modifier_membre(id_membre, donnees):
    """Met à jour un membre. Renvoie le membre modifié ou None."""
    execute("""
        UPDATE membre SET
            prenom                 = %s,
            nom                    = %s,
            sexe                   = %s,
            date_naissance         = %s,
            lien_chef              = %s,
            situation_matrimoniale = %s,
            niveau_instruction     = %s,
            sait_lire_ecrire       = %s,
            situation_activite     = %s,
            type_emploi            = %s,
            secteur_emploi         = %s,
            piece_identite         = %s,
            handicap               = %s
        WHERE id_membre = %s
    """, (
        donnees['prenom'].strip(),
        donnees['nom'].strip(),
        donnees['sexe'],
        donnees['date_naissance'],
        donnees.get('lien_chef', ''),
        donnees.get('situation_matrimoniale', 'Célibataire'),
        donnees.get('niveau_instruction', 'Aucun'),
        donnees.get('sait_lire_ecrire', 'Non'),
        donnees.get('situation_activite', 'Inactif'),
        donnees.get('type_emploi', ''),
        donnees.get('secteur_emploi', ''),
        donnees.get('piece_identite', 'Aucune'),
        donnees.get('handicap', 'Aucun'),
        id_membre,
    ))
    return query_one(
        "SELECT * FROM membre WHERE id_membre = %s",
        (id_membre,)
    )


def supprimer_membre(id_membre):
    """Supprime un membre. Renvoie True si le membre existait."""
    existe = query_one("SELECT 1 FROM membre WHERE id_membre = %s", (id_membre,))
    if not existe:
        return False
    execute("DELETE FROM membre WHERE id_membre = %s", (id_membre,))
    return True 