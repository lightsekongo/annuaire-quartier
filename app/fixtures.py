"""
Données fictives pour le développement.

Génère ~120 ménages répartis sur les 13 communes du District d'Abidjan,
avec des membres et un questionnaire enrichi (conditions de vie incluses).

Reproductible via random.seed() : les mêmes données à chaque lancement.

Sera remplacé par des requêtes PostgreSQL en étape F sans toucher
au reste du code (les fonctions get_menages() / get_membres() exposent
la même interface qu'un futur module de base de données).
"""

import random
from datetime import date, timedelta
from itertools import count

# ============================================================
# CONFIGURATION
# ============================================================
random.seed(42)  # Reproductibilité

# Centroïdes approximatifs des 13 communes (lat, lng)
# Extraits du fichier abidjan_communes.geojson — utilisés pour positionner
# les quartiers (Option α : centroïdes + décalage déterministe).
CENTROIDES_COMMUNES = {
    "abobo":       (5.4371, -4.0603),
    "adjame":      (5.3589, -4.0270),
    "anyama":      (5.4953, -4.0517),
    "attecoube":   (5.3438, -4.0541),
    "bingerville": (5.3522, -3.9012),
    "cocody":      (5.3604, -3.9683),
    "koumassi":    (5.2906, -3.9512),
    "marcory":     (5.2996, -3.9874),
    "plateau":     (5.3252, -4.0220),
    "port-bouet":  (5.2530, -3.9320),
    "songon":      (5.3085, -4.2015),
    "treichville": (5.2934, -4.0118),
    "yopougon":    (5.3457, -4.1208),
}

# ============================================================
# CHARGEMENT DES POLYGONES DES COMMUNES (depuis le GeoJSON)
# ============================================================
import json
import os

# Chemin vers le fichier GeoJSON des communes
_GEOJSON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "app", "static", "data", "abidjan_communes.geojson"
)

# Fallback si le chemin ci-dessus ne trouve rien (selon où Python est lancé)
_GEOJSON_PATH_ALT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "static", "data", "abidjan_communes.geojson"
)


def _charger_polygones_communes():
    """
    Charge les polygones des communes depuis le GeoJSON.
    Renvoie un dict { slug: liste_de_points_lng_lat }.
    """
    chemin = None
    for c in (_GEOJSON_PATH, _GEOJSON_PATH_ALT):
        if os.path.exists(c):
            chemin = c
            break
    if not chemin:
        return {}

    with open(chemin, encoding="utf-8") as f:
        data = json.load(f)

    polygones = {}
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        slug = props.get("slug")
        geom = feature.get("geometry", {})
        if slug and geom.get("type") == "Polygon":
            # On prend l'anneau extérieur (premier élément des coordinates)
            polygones[slug] = geom["coordinates"][0]
    return polygones


# Chargement au démarrage du module — fait une seule fois
_POLYGONES_COMMUNES = _charger_polygones_communes()


def _point_dans_polygone(lng, lat, polygone):
    """
    Algorithme ray-casting : teste si un point (lng, lat) est dans
    le polygone (liste de coordonnées [lng, lat]).
    """
    n = len(polygone)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygone[i][0], polygone[i][1]
        xj, yj = polygone[j][0], polygone[j][1]
        if ((yi > lat) != (yj > lat)) and \
           (lng < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def _bounding_box(polygone):
    """Renvoie (minLng, minLat, maxLng, maxLat) d'un polygone."""
    xs = [p[0] for p in polygone]
    ys = [p[1] for p in polygone]
    return (min(xs), min(ys), max(xs), max(ys))

# Les 13 communes du District autonome d'Abidjan
# (id, nom, slug, type, poids_demographique pour la répartition)
COMMUNES = [
    (1,  "Abobo",       "abobo",       "commune_urbaine",   25),
    (2,  "Adjamé",      "adjame",       "commune_urbaine",   8),
    (3,  "Anyama",      "anyama",       "sous_prefecture",   5),
    (4,  "Attécoubé",   "attecoube",    "commune_urbaine",   6),
    (5,  "Bingerville", "bingerville",  "sous_prefecture",   3),
    (6,  "Cocody",      "cocody",       "commune_urbaine",  12),
    (7,  "Koumassi",    "koumassi",     "commune_urbaine",  10),
    (8,  "Marcory",     "marcory",      "commune_urbaine",   5),
    (9,  "Plateau",     "plateau",      "commune_urbaine",   2),
    (10, "Port-Bouët",  "port-bouet",   "commune_urbaine",   7),
    (11, "Songon",      "songon",       "sous_prefecture",   2),
    (12, "Treichville", "treichville",  "commune_urbaine",   4),
    (13, "Yopougon",    "yopougon",     "commune_urbaine",  20),
]

# Quartiers représentatifs par commune (échantillonnage réaliste)
QUARTIERS = {
    1:  ["Abobo Centre", "Abobo Baoulé", "Plaque", "Abobo Sagbé", "Abobo Dokoui"],
    2:  ["Adjamé Liberté", "Adjamé Roxy", "Williamsville", "220 Logements"],
    3:  ["Anyama Centre", "Anyama Adjamé"],
    4:  ["Locodjro", "Adjamé Bramakoté", "Sébroko"],
    5:  ["Bingerville Centre", "Akouédo Village"],
    6:  ["Cocody Riviera", "Cocody Angré", "Cocody Centre", "II Plateaux", "Mermoz"],
    7:  ["Koumassi Remblais", "Koumassi Soweto", "Sicogi Koumassi", "Prodomo"],
    8:  ["Marcory Résidentiel", "Zone 4", "Anoumabo"],
    9:  ["Plateau Indénié", "Plateau Centre"],
    10: ["Port-Bouët Vridi", "Port-Bouët Phare", "Gonzagueville"],
    11: ["Songon Agban", "Songon M'Brathé"],
    12: ["Treichville Arras", "Treichville Belleville", "Treichville Avenue 16"],
    13: ["Yopougon Sicogi", "Yopougon Toits Rouges", "Yopougon Niangon",
         "Yopougon Selmer", "Yopougon Andokoi", "Yopougon Maroc"],
}

# Listes de noms ivoiriens fréquents (échantillon non exhaustif, à fin pédagogique)
NOMS_FAMILLE = [
    "Kouassi", "Koffi", "Yao", "Konan", "Brou", "Kouamé", "N'Guessan",
    "Diabaté", "Touré", "Coulibaly", "Bamba", "Diallo", "Cissé", "Traoré",
    "Ouattara", "Bakayoko", "Soro", "Doumbia", "Camara", "Fofana",
    "Aké", "Bléhi", "Gnagne", "Tia", "Zoro", "Béhi", "Goré",
    "Adou", "Assamoi", "Ehui", "Tanoh", "Boni", "Atsé", "Akoua",
]

PRENOMS_M = [
    "Kouadio", "Yao", "Koffi", "Konan", "Aristide", "Eric", "Patrick",
    "Jean", "Pierre", "Paul", "Marc", "Olivier", "Romaric", "Cheick",
    "Ibrahim", "Mamadou", "Souleymane", "Adama", "Moussa", "Lassina",
    "Serge", "Désiré", "Hervé", "Roger", "Sylvain", "Didier", "Yannick",
]

PRENOMS_F = [
    "Aya", "Akissi", "Ahou", "Adjoua", "Affoué", "Amenan", "Amoin",
    "Marie", "Christine", "Sylvie", "Patricia", "Brigitte", "Estelle",
    "Aïcha", "Fatou", "Mariam", "Aminata", "Awa", "Salimata",
    "Gisèle", "Caroline", "Valérie", "Nadège", "Stéphanie", "Henriette",
]

# Tirages pondérés pour les modalités du questionnaire enrichi
LIENS_PARENTE = {
    "Chef de ménage":   1,    # exactement 1 par ménage, traité à part
    "Conjoint(e)":      1,
    "Enfant":           4,
    "Frère / Sœur":     0.4,
    "Neveu / Nièce":    0.3,
    "Ascendant (Père / Mère)": 0.2,
    "Autre parent":     0.3,
    "Sans lien de parenté": 0.1,
}

STATUTS_SCOLAIRES_PAR_AGE = {
    "<6":     {"Sans objet": 1.0},
    "6-15":   {"Scolarisé": 0.78, "Déscolarisé": 0.12, "Jamais scolarisé": 0.10},
    "16-24":  {"Scolarisé": 0.45, "Déscolarisé": 0.40, "Jamais scolarisé": 0.10, "Sans objet": 0.05},
    "25+":    {"Sans objet": 1.0},
}

NIVEAUX_INSTRUCTION = ["Aucun", "Primaire", "Secondaire 1er cycle",
                       "Secondaire 2nd cycle", "Supérieur"]

ACTIVITES_PAR_AGE = {
    "<15":   {"Sans activité (mineur)": 1.0},
    "15-24": {"Élève / Étudiant": 0.55, "Chômeur": 0.18, "Commerce": 0.08,
              "Artisanat": 0.06, "Travailleur indépendant / À son propre compte": 0.05,
              "Salarié privé": 0.04, "Au foyer": 0.04},
    "25-59": {"Commerce": 0.18, "Artisanat": 0.12,
              "Travailleur indépendant / À son propre compte": 0.15,
              "Salarié privé": 0.18, "Salarié public": 0.10,
              "Agriculture / Élevage / Pêche": 0.05,
              "Au foyer": 0.10, "Chômeur": 0.10, "Autre": 0.02},
    "60+":   {"Retraité": 0.45, "Au foyer": 0.30,
              "Commerce": 0.10, "Travailleur indépendant / À son propre compte": 0.10,
              "Agriculture / Élevage / Pêche": 0.05},
}

SITUATIONS_MATRIMONIALES_PAR_AGE = {
    "<18":   {"Célibataire": 1.0},
    "18-29": {"Célibataire": 0.70, "Marié(e)": 0.28, "Divorcé(e)": 0.02},
    "30-59": {"Marié(e)": 0.72, "Célibataire": 0.18, "Divorcé(e)": 0.06, "Veuf(ve)": 0.04},
    "60+":   {"Marié(e)": 0.55, "Veuf(ve)": 0.35, "Divorcé(e)": 0.05, "Célibataire": 0.05},
}

# Modalités logement (probabilités selon type commune)
SOURCES_EAU = {
    "commune_urbaine":  {"Robinet intérieur": 0.55, "Robinet extérieur / cour": 0.28,
                         "Borne fontaine": 0.12, "Eau en sachet": 0.04, "Puits": 0.01},
    "sous_prefecture":  {"Robinet intérieur": 0.20, "Robinet extérieur / cour": 0.25,
                         "Borne fontaine": 0.30, "Puits": 0.20, "Eau en sachet": 0.05},
}

TOILETTES = {
    "commune_urbaine":  {"Chasse d'eau": 0.45, "Latrine couverte": 0.40,
                         "Latrine non couverte": 0.12, "Aucune": 0.03},
    "sous_prefecture":  {"Chasse d'eau": 0.15, "Latrine couverte": 0.45,
                         "Latrine non couverte": 0.30, "Aucune": 0.10},
}

ECLAIRAGE = {
    "commune_urbaine":  {"CIE (réseau)": 0.92, "Solaire": 0.04,
                         "Lampe à pétrole": 0.03, "Aucune": 0.01},
    "sous_prefecture":  {"CIE (réseau)": 0.65, "Solaire": 0.15,
                         "Lampe à pétrole": 0.18, "Aucune": 0.02},
}

EVACUATION_ORDURES = ["Service de ramassage", "Dépôt collectif",
                      "Brûlage", "Enfouissement", "Dépôt sauvage"]

TYPES_LOGEMENT = ["Maison individuelle", "Cour commune",
                  "Appartement", "Baraque / Précaire"]

STATUTS_OCCUPATION = ["Propriétaire", "Locataire", "Logé gratuitement"]

# ============================================================
# UTILITAIRES DE TIRAGE
# ============================================================
def _weighted(distribution: dict):
    """Tirage aléatoire dans un dict {modalite: poids}."""
    items = list(distribution.items())
    total = sum(w for _, w in items)
    r = random.uniform(0, total)
    cum = 0
    for modalite, poids in items:
        cum += poids
        if r <= cum:
            return modalite
    return items[-1][0]


def _age_bucket_scol(age):
    if age < 6:    return "<6"
    if age <= 15:  return "6-15"
    if age <= 24:  return "16-24"
    return "25+"


def _age_bucket_act(age):
    if age < 15:   return "<15"
    if age <= 24:  return "15-24"
    if age <= 59:  return "25-59"
    return "60+"


def _age_bucket_mat(age):
    if age < 18:   return "<18"
    if age <= 29:  return "18-29"
    if age <= 59:  return "30-59"
    return "60+"


def _date_naissance(age_min, age_max):
    """Génère une date de naissance pour un âge entre les bornes."""
    today = date.today()
    age = random.randint(age_min, age_max)
    days_offset = random.randint(0, 364)
    return today - timedelta(days=age * 365 + days_offset)


def _age(date_naissance):
    return (date.today() - date_naissance).days // 365


# ============================================================
# GÉNÉRATION DES MEMBRES D'UN MÉNAGE
# ============================================================
def _generer_membres(id_menage, taille_cible):
    """
    Génère une liste de membres pour un ménage donné.
    Garantit toujours exactement 1 chef de ménage.
    """
    membres = []

    # 1. Chef de ménage (adulte 25-65 ans, plus souvent homme)
    sexe_chef = "Masculin" if random.random() < 0.78 else "Féminin"
    chef_ddn = _date_naissance(28, 65)
    membres.append(_creer_membre(
        id_menage, sexe_chef, chef_ddn, "Chef de ménage"
    ))

    if taille_cible == 1:
        return membres

    # 2. Conjoint(e) (60% des cas, sauf chef très jeune)
    age_chef = _age(chef_ddn)
    if age_chef >= 25 and random.random() < 0.62:
        sexe_conjoint = "Féminin" if sexe_chef == "Masculin" else "Masculin"
        ddn_conjoint = _date_naissance(max(18, age_chef - 8), age_chef + 4)
        membres.append(_creer_membre(
            id_menage, sexe_conjoint, ddn_conjoint, "Conjoint(e)"
        ))

    # 3. Le reste : enfants principalement, autres parents en marge
    while len(membres) < taille_cible:
        r = random.random()
        if r < 0.70:
            # Enfant
            sexe = random.choice(["Masculin", "Féminin"])
            age_max = max(2, age_chef - 18)
            ddn = _date_naissance(0, age_max)
            membres.append(_creer_membre(id_menage, sexe, ddn, "Enfant"))
        elif r < 0.82:
            sexe = random.choice(["Masculin", "Féminin"])
            ddn = _date_naissance(5, age_chef - 5)
            membres.append(_creer_membre(id_menage, sexe, ddn, "Neveu / Nièce"))
        elif r < 0.90:
            sexe = random.choice(["Masculin", "Féminin"])
            ddn = _date_naissance(12, age_chef - 5)
            membres.append(_creer_membre(id_menage, sexe, ddn, "Frère / Sœur"))
        elif r < 0.96:
            sexe = random.choice(["Masculin", "Féminin"])
            ddn = _date_naissance(60, 90)
            membres.append(_creer_membre(id_menage, sexe, ddn,
                                          "Ascendant (Père / Mère)"))
        else:
            sexe = random.choice(["Masculin", "Féminin"])
            ddn = _date_naissance(15, 70)
            membres.append(_creer_membre(id_menage, sexe, ddn, "Autre parent"))

    return membres

# ============================================================
# POSITIONNEMENT DES QUARTIERS SUR LA CARTE
# ============================================================
def _generer_position_quartier(slug_commune, idx_quartier, total_quartiers):
    """
    Génère une position lat/lng pour un quartier dans le polygone réel
    de sa commune (approche dispersion réaliste).

    Algorithme :
      1. On récupère le polygone de la commune depuis le GeoJSON
      2. On tire des points pseudo-aléatoires dans la bounding box
      3. On garde le premier qui tombe à l'intérieur du polygone
      4. Pour la reproductibilité : seed fonction de slug+idx

    Si le polygone n'est pas disponible (GeoJSON manquant),
    on retombe sur l'ancien algorithme circulaire.
    """
    polygone = _POLYGONES_COMMUNES.get(slug_commune)

    # Fallback : ancien algorithme en cercle si pas de polygone
    if not polygone:
        return _position_quartier_fallback(slug_commune, idx_quartier, total_quartiers)

    # Seed déterministe pour ce quartier précis
    # → garantit la reproductibilité d'un lancement à l'autre
    seed = hash((slug_commune, idx_quartier)) & 0x7FFFFFFF
    rng = random.Random(seed)

    minLng, minLat, maxLng, maxLat = _bounding_box(polygone)

    # On évite le bord de la commune en réduisant légèrement la bounding box
    # (les points trop proches de la frontière sont visuellement gênants)
    margin_lng = (maxLng - minLng) * 0.08
    margin_lat = (maxLat - minLat) * 0.08
    minLng += margin_lng
    maxLng -= margin_lng
    minLat += margin_lat
    maxLat -= margin_lat

    # Tire jusqu'à 200 points : on prend le premier qui est dans le polygone
    for _ in range(200):
        lng = rng.uniform(minLng, maxLng)
        lat = rng.uniform(minLat, maxLat)
        if _point_dans_polygone(lng, lat, polygone):
            return (round(lat, 5), round(lng, 5))

    # Dernier recours : centroïde de la bounding box (ne devrait jamais arriver)
    return (round((minLat + maxLat) / 2, 5),
            round((minLng + maxLng) / 2, 5))


def _position_quartier_fallback(slug_commune, idx_quartier, total_quartiers):
    """
    Algorithme de secours (cercle autour du centroïde) si le GeoJSON
    n'est pas disponible. Identique à l'ancienne version.
    """
    import math
    centre = CENTROIDES_COMMUNES.get(slug_commune, (5.36, -4.00))
    lat_c, lng_c = centre

    if total_quartiers == 1:
        return (round(lat_c, 5), round(lng_c, 5))

    rayon = 0.012
    angle = (2 * math.pi * idx_quartier) / total_quartiers
    lat = lat_c + rayon * math.sin(angle)
    lng = lng_c + rayon * math.cos(angle)
    return (round(lat, 5), round(lng, 5))

_membre_id_counter = count(1)


def _creer_membre(id_menage, sexe, date_naissance, lien_parente):
    """Crée un dict-membre complet avec questionnaire enrichi."""
    age = _age(date_naissance)

    # Nom et prénom
    nom = random.choice(NOMS_FAMILLE)
    prenom = random.choice(PRENOMS_M if sexe == "Masculin" else PRENOMS_F)

    # Statut scolaire (selon âge)
    statut_scolaire = _weighted(STATUTS_SCOLAIRES_PAR_AGE[_age_bucket_scol(age)])

    # Niveau d'instruction (corrélé à l'âge et au statut)
    if age < 6:
        niveau = "Aucun"
    elif age < 12:
        niveau = random.choices(
            ["Aucun", "Primaire"], weights=[0.15, 0.85])[0]
    elif age < 16:
        niveau = random.choices(
            ["Aucun", "Primaire", "Secondaire 1er cycle"],
            weights=[0.10, 0.40, 0.50])[0]
    elif age < 25:
        niveau = random.choices(
            NIVEAUX_INSTRUCTION,
            weights=[0.05, 0.20, 0.30, 0.30, 0.15])[0]
    else:
        niveau = random.choices(
            NIVEAUX_INSTRUCTION,
            weights=[0.18, 0.25, 0.20, 0.20, 0.17])[0]

    sait_lire_ecrire = niveau != "Aucun" or (age < 6 and False)
    if age >= 6 and niveau == "Aucun":
        sait_lire_ecrire = random.random() < 0.10  # alphabétisation hors école

    # Activité principale
    activite = _weighted(ACTIVITES_PAR_AGE[_age_bucket_act(age)])

    # Situation matrimoniale
    sit_mat = _weighted(SITUATIONS_MATRIMONIALES_PAR_AGE[_age_bucket_mat(age)])
    if lien_parente == "Conjoint(e)":
        sit_mat = "Marié(e)"

    # Pièce d'identité (probabilité croissante avec l'âge)
    if age < 16:
        piece_id = False
    elif age < 25:
        piece_id = random.random() < 0.78
    else:
        piece_id = random.random() < 0.92

    # Handicap (prévalence ~3%)
    handicap = random.random() < 0.03

    return {
        "id_membre": next(_membre_id_counter),
        "id_menage": id_menage,
        "nom": nom,
        "prenom": prenom,
        "sexe": sexe,
        "date_naissance": date_naissance,
        "lien_parente": lien_parente,
        "statut_scolaire": statut_scolaire,
        "niveau_instruction": niveau,
        "sait_lire_ecrire": sait_lire_ecrire,
        "activite_principale": activite,
        "situation_matrimoniale": sit_mat,
        "possede_piece_identite": piece_id,
        "situation_handicap": handicap,
    }


# ============================================================
# GÉNÉRATION DES MÉNAGES
# ============================================================
_menage_id_counter = count(1)


def _generer_menage(commune_id, commune_nom, commune_slug, commune_type, quartier):
    """Crée un ménage avec ses caractéristiques de logement."""
    id_menage = next(_menage_id_counter)

    # Taille du ménage (loi log-normale tronquée, moyenne ~5)
    taille = max(1, min(12, int(random.lognormvariate(1.4, 0.5))))

    # Nombre de pièces (corrélé à la taille mais variable)
    nb_pieces = max(1, min(8, taille // 2 + random.randint(0, 2)))

    # Date d'enregistrement (sur les 6 derniers mois)
    days_ago = random.randint(0, 180)
    date_enr = date.today() - timedelta(days=days_ago)

    menage = {
        "id_menage": id_menage,
        "nom_menage": f"Famille {random.choice(NOMS_FAMILLE)}",
        "id_quartier": None,  # quartier référencé par nom pour l'instant
        "quartier": quartier,
        "id_commune": commune_id,
        "commune": commune_nom,
        "commune_slug": commune_slug,
        "commune_type": commune_type,
        "date_enregistrement": date_enr,

        # Conditions de vie (probabilités selon type de commune)
        "type_logement": random.choices(
            TYPES_LOGEMENT,
            weights=[0.35, 0.45, 0.15, 0.05] if commune_type == "commune_urbaine"
            else [0.65, 0.25, 0.05, 0.05])[0],
        "statut_occupation": random.choices(
            STATUTS_OCCUPATION, weights=[0.35, 0.55, 0.10])[0],
        "source_eau": _weighted(SOURCES_EAU[commune_type]),
        "type_toilettes": _weighted(TOILETTES[commune_type]),
        "source_eclairage": _weighted(ECLAIRAGE[commune_type]),
        "mode_evacuation_ordures": random.choices(
            EVACUATION_ORDURES,
            weights=[0.45, 0.25, 0.18, 0.07, 0.05] if commune_type == "commune_urbaine"
            else [0.20, 0.25, 0.30, 0.15, 0.10])[0],
        "nombre_pieces": nb_pieces,

        # Possession de biens durables (corrélée à la richesse présumée)
        # On fait varier la probabilité par commune (Cocody/Plateau plus aisés)
        "possede_frigo":      random.random() < (0.85 if commune_id in (6, 9) else 0.55),
        "possede_tele":       random.random() < (0.92 if commune_type == "commune_urbaine" else 0.65),
        "possede_moto":       random.random() < 0.30,
        "possede_voiture":    random.random() < (0.45 if commune_id in (6, 9) else 0.18),
        "possede_smartphone": random.random() < (0.92 if commune_type == "commune_urbaine" else 0.72),
        "possede_ordinateur": random.random() < (0.55 if commune_id in (6, 9) else 0.18),

        "_taille_cible": taille,  # interne, utilisé pour générer les membres
    }
    return menage


# ============================================================
# CONSTRUCTION DU JEU DE DONNÉES COMPLET
# ============================================================
def _construire_donnees():
    """Construit l'ensemble des ménages et membres une seule fois."""
    menages = []
    membres = []

    # Cible : ~120 ménages au total, répartis selon les poids démographiques
    total_poids = sum(c[4] for c in COMMUNES)
    nb_total_menages = 120

    for id_c, nom_c, slug_c, type_c, poids in COMMUNES:
        nb_menages_commune = max(1, round(nb_total_menages * poids / total_poids))
        quartiers = QUARTIERS[id_c]

        for _ in range(nb_menages_commune):
            quartier = random.choice(quartiers)
            menage = _generer_menage(id_c, nom_c, slug_c, type_c, quartier)
            taille = menage.pop("_taille_cible")
            menages.append(menage)
            membres.extend(_generer_membres(menage["id_menage"], taille))

    return menages, membres


# Données générées une seule fois au chargement du module
_MENAGES, _MEMBRES = _construire_donnees()


# ============================================================
# INTERFACE PUBLIQUE
# ============================================================
def get_communes():
    """Liste des 13 communes du District."""
    return [
        {"id_commune": id_c, "nom": nom, "slug": slug, "type": type_c}
        for id_c, nom, slug, type_c, _ in COMMUNES
    ]


def get_menages():
    """Liste de tous les ménages enregistrés."""
    return list(_MENAGES)


def get_membres():
    """Liste de tous les membres enregistrés."""
    return list(_MEMBRES)


def get_menage_by_id(id_menage):
    return next((m for m in _MENAGES if m["id_menage"] == id_menage), None)


def get_membres_by_menage(id_menage):
    return [m for m in _MEMBRES if m["id_menage"] == id_menage]


def get_stats_globales():
    """Stats brutes utilisées pour debug."""
    return {
        "nb_menages": len(_MENAGES),
        "nb_membres": len(_MEMBRES),
        "nb_communes": len(COMMUNES),
        "nb_quartiers": sum(len(q) for q in QUARTIERS.values()),
    }

def get_quartiers():
    """
    Liste de tous les quartiers avec leurs coordonnées GPS.

    Renvoie une liste de dicts :
        [{
            "id_quartier": 1,
            "nom": "Abobo Centre",
            "id_commune": 1,
            "commune_slug": "abobo",
            "commune_nom": "Abobo",
            "lat": 5.4371,
            "lng": -4.0603,
            "nb_menages": 6,    # nombre de ménages enregistrés ici
        }, ...]
    """
    quartiers = []
    id_quartier = 1

    # Pour chaque commune, génère ses quartiers avec leurs positions
    for id_c, nom_c, slug_c, type_c, _ in COMMUNES:
        noms_quartiers = QUARTIERS[id_c]
        total = len(noms_quartiers)

        for idx, nom_q in enumerate(noms_quartiers):
            lat, lng = _generer_position_quartier(slug_c, idx, total)

            # Compter combien de ménages sont dans ce quartier
            nb_menages_q = sum(
                1 for m in _MENAGES
                if m["id_commune"] == id_c and m["quartier"] == nom_q
            )

            quartiers.append({
                "id_quartier": id_quartier,
                "nom": nom_q,
                "id_commune": id_c,
                "commune_slug": slug_c,
                "commune_nom": nom_c,
                "lat": lat,
                "lng": lng,
                "nb_menages": nb_menages_q,
            })
            id_quartier += 1

    return quartiers

# ============================================================
# FONCTIONS DE MANIPULATION DES DONNÉES (CRUD en mémoire)
# ============================================================
# Ces fonctions modifient directement les listes _MENAGES et _MEMBRES
# qui sont initialisées au démarrage du module.
# À l'étape F (PostgreSQL), elles seront remplacées par des requêtes SQL
# sans toucher au reste de l'application.

from itertools import count as _count

# Compteurs pour générer les nouveaux identifiants
_menage_id_counter = _count(len(_MENAGES) + 1)
_membre_id_counter = _count(len(_MEMBRES) + 1)


def _commune_par_id(id_commune: int) -> tuple:
    """Renvoie (nom, slug) de la commune ou (None, None) si introuvable."""
    for id_c, nom, slug, _, _ in COMMUNES:
        if id_c == id_commune:
            return nom, slug
    return None, None


# ─────────── MÉNAGES ───────────

def creer_menage(donnees: dict) -> dict:
    """
    Crée un nouveau ménage en mémoire.

    `donnees` doit contenir au minimum :
        - nom_menage : str
        - id_commune : int
        - quartier : str

    Champs optionnels (étendus) :
        - type_logement, statut_occupation, nombre_pieces
        - source_eau, type_toilettes, source_eclairage, gestion_ordures
        - biens_durables : liste de str (Frigo, TV, etc.)
        - date_recensement : str (YYYY-MM-DD)

    Renvoie le dict du ménage créé.
    """
    nouveau_id = next(_menage_id_counter)
    nom_commune, _slug = _commune_par_id(donnees["id_commune"])

    menage = {
        "id_menage": nouveau_id,
        "nom_menage": donnees["nom_menage"].strip(),
        "id_commune": donnees["id_commune"],
        "commune": nom_commune or "—",
        "quartier": donnees["quartier"].strip(),
        # Champs étendus
        "type_logement": donnees.get("type_logement", ""),
        "statut_occupation": donnees.get("statut_occupation", ""),
        "nombre_pieces": int(donnees.get("nombre_pieces") or 0),
        "source_eau": donnees.get("source_eau", ""),
        "type_toilettes": donnees.get("type_toilettes", ""),
        "source_eclairage": donnees.get("source_eclairage", ""),
        "gestion_ordures": donnees.get("gestion_ordures", ""),
        "biens_durables": donnees.get("biens_durables", []),
        "date_recensement": donnees.get("date_recensement", ""),
    }
    _MENAGES.append(menage)
    return menage


def modifier_menage(id_menage: int, donnees: dict) -> dict | None:
    """
    Met à jour un ménage existant. Renvoie le ménage modifié ou None.
    Seuls les champs présents dans `donnees` sont mis à jour.
    """
    for menage in _MENAGES:
        if menage["id_menage"] == id_menage:
            if "nom_menage" in donnees:
                menage["nom_menage"] = donnees["nom_menage"].strip()
            if "id_commune" in donnees:
                menage["id_commune"] = donnees["id_commune"]
                nom_commune, _slug = _commune_par_id(donnees["id_commune"])
                menage["commune"] = nom_commune or "—"
            if "quartier" in donnees:
                menage["quartier"] = donnees["quartier"].strip()

            # Champs étendus
            for champ in ("type_logement", "statut_occupation",
                          "source_eau", "type_toilettes",
                          "source_eclairage", "gestion_ordures",
                          "date_recensement"):
                if champ in donnees:
                    menage[champ] = donnees[champ]
            if "nombre_pieces" in donnees:
                menage["nombre_pieces"] = int(donnees["nombre_pieces"] or 0)
            if "biens_durables" in donnees:
                menage["biens_durables"] = donnees["biens_durables"]

            return menage
    return None


def supprimer_menage(id_menage: int) -> bool:
    """
    Supprime un ménage et tous ses membres. Renvoie True si trouvé.
    """
    # On retire d'abord les membres associés
    global _MEMBRES
    _MEMBRES = [m for m in _MEMBRES if m["id_menage"] != id_menage]

    # Puis le ménage lui-même
    for i, menage in enumerate(_MENAGES):
        if menage["id_menage"] == id_menage:
            del _MENAGES[i]
            return True
    return False


# ─────────── MEMBRES ───────────

def creer_membre(donnees: dict) -> dict:
    """
    Crée un nouveau membre dans un ménage existant.

    `donnees` doit contenir :
        - id_menage : int
        - prenom, nom : str
        - sexe : "Masculin" | "Féminin"
        - date_naissance : str (YYYY-MM-DD)

    Champs optionnels (étendus) :
        - lien_chef : str (Chef, Conjoint(e), Enfant, etc.)
        - niveau_instruction : "Aucun" | "Primaire" | "Secondaire" | "Supérieur"
        - sait_lire_ecrire : "Oui" | "Non"
        - situation_matrimoniale, piece_identite, handicap
        - situation_activite : "Actif occupé" | "Chômeur" | "Inactif"
        - type_emploi, secteur_emploi
    """
    nouveau_id = next(_membre_id_counter)
    membre = {
        "id_membre": nouveau_id,
        "id_menage": donnees["id_menage"],
        "prenom": donnees["prenom"].strip(),
        "nom": donnees["nom"].strip(),
        "sexe": donnees["sexe"],
        "date_naissance": donnees["date_naissance"],
        # Champs sociaux
        "lien_chef": donnees.get("lien_chef", ""),
        "niveau_instruction": donnees.get("niveau_instruction", "Aucun"),
        "sait_lire_ecrire": donnees.get("sait_lire_ecrire", "Non"),
        "situation_matrimoniale": donnees.get("situation_matrimoniale", "Célibataire"),
        "piece_identite": donnees.get("piece_identite", "Aucune"),
        "handicap": donnees.get("handicap", "Aucun"),
        # Activité
        "situation_activite": donnees.get("situation_activite", "Inactif"),
        "type_emploi": donnees.get("type_emploi", ""),
        "secteur_emploi": donnees.get("secteur_emploi", ""),
    }
    _MEMBRES.append(membre)
    return membre


def modifier_membre(id_membre: int, donnees: dict) -> dict | None:
    """
    Met à jour un membre. Renvoie le membre modifié ou None.
    """
    for membre in _MEMBRES:
        if membre["id_membre"] == id_membre:
            for champ in ("prenom", "nom", "sexe", "date_naissance",
                          "lien_chef", "niveau_instruction",
                          "sait_lire_ecrire", "situation_matrimoniale",
                          "piece_identite", "handicap",
                          "situation_activite", "type_emploi", "secteur_emploi"):
                if champ in donnees:
                    val = donnees[champ]
                    if isinstance(val, str):
                        val = val.strip()
                    membre[champ] = val
            return membre
    return None


def supprimer_membre(id_membre: int) -> bool:
    """Supprime un membre. Renvoie True si trouvé."""
    for i, membre in enumerate(_MEMBRES):
        if membre["id_membre"] == id_membre:
            del _MEMBRES[i]
            return True
    return False

# ============================================================
# ENRICHISSEMENT DES MÉNAGES AVEC BIENS DURABLES
# ============================================================
# Appelée au démarrage du module pour ajouter aux 120 ménages
# fictifs des biens durables plausibles selon leur commune.

import random as _random_biens

# Niveau d'équipement moyen par commune (sur 8 biens possibles)
# Cocody / Plateau / Marcory = ménages aisés (3-5 biens en moyenne)
# Yopougon / Treichville = classe moyenne (2-3 biens)
# Abobo / Adjamé / Attécoubé = modeste (1-2 biens)
# Anyama / Bingerville / Songon = rural (0-2 biens)
_PROFIL_EQUIPEMENT = {
    "cocody":       {"min": 3, "max": 6, "smartphone_rate": 0.95, "tv_rate": 0.95},
    "plateau":      {"min": 3, "max": 6, "smartphone_rate": 0.95, "tv_rate": 0.90},
    "marcory":      {"min": 2, "max": 5, "smartphone_rate": 0.90, "tv_rate": 0.85},
    "treichville":  {"min": 2, "max": 4, "smartphone_rate": 0.85, "tv_rate": 0.85},
    "yopougon":     {"min": 1, "max": 4, "smartphone_rate": 0.80, "tv_rate": 0.75},
    "koumassi":     {"min": 1, "max": 4, "smartphone_rate": 0.75, "tv_rate": 0.75},
    "port-bouet":   {"min": 1, "max": 3, "smartphone_rate": 0.70, "tv_rate": 0.70},
    "adjame":       {"min": 1, "max": 3, "smartphone_rate": 0.70, "tv_rate": 0.65},
    "abobo":        {"min": 1, "max": 3, "smartphone_rate": 0.65, "tv_rate": 0.60},
    "attecoube":    {"min": 0, "max": 3, "smartphone_rate": 0.60, "tv_rate": 0.55},
    "bingerville":  {"min": 1, "max": 4, "smartphone_rate": 0.70, "tv_rate": 0.65},
    "anyama":       {"min": 0, "max": 3, "smartphone_rate": 0.55, "tv_rate": 0.50},
    "songon":       {"min": 0, "max": 2, "smartphone_rate": 0.45, "tv_rate": 0.40},
}

_AUTRES_BIENS = ["Frigo", "Climatiseur", "Voiture", "Moto", "Internet", "Ordinateur"]


def _enrichir_biens_menages():
    """
    Enrichit les ménages existants avec des biens durables plausibles
    en fonction de leur commune. Utilise une graine déterministe pour
    que les biens soient stables d'un lancement à l'autre.
    """
    # Construit un mapping id_commune → slug
    id_to_slug = {id_c: slug for id_c, _, slug, _, _ in COMMUNES}

    for m in _MENAGES:
        slug = id_to_slug.get(m["id_commune"])
        if not slug:
            continue

        profil = _PROFIL_EQUIPEMENT.get(slug, {"min": 1, "max": 3,
                                                "smartphone_rate": 0.6,
                                                "tv_rate": 0.6})

        # Graine déterministe par ménage
        seed = hash(("biens", m["id_menage"])) & 0x7FFFFFFF
        rng = _random_biens.Random(seed)

        biens = []

        # Smartphone et TV ont leur propre probabilité (très courants)
        if rng.random() < profil["smartphone_rate"]:
            biens.append("Smartphone")
        if rng.random() < profil["tv_rate"]:
            biens.append("TV")

        # Autres biens : on tire un nombre aléatoire dans la fourchette
        nb_autres = rng.randint(profil["min"], profil["max"])
        biens_dispo = _AUTRES_BIENS.copy()
        rng.shuffle(biens_dispo)
        biens.extend(biens_dispo[:nb_autres])

        m["biens_durables"] = biens


# Exécution automatique au chargement du module
_enrichir_biens_menages()
if __name__ == "__main__":
    s = get_stats_globales()
    print(f"Données générées :")
    print(f"  - {s['nb_menages']} ménages")
    print(f"  - {s['nb_membres']} membres")
    print(f"  - {s['nb_communes']} communes")
    print(f"  - {s['nb_quartiers']} quartiers")
    print(f"  - Taille moyenne : {s['nb_membres']/s['nb_menages']:.2f} pers./ménage")