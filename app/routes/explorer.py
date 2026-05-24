"""
Page Explorer — atelier de visualisation libre.

Prépare un JSON optimisé contenant :
  - La liste des variables disponibles avec leurs métadonnées
  - Les ~470 membres enrichis des attributs de leur ménage
  - La liste des communes (pour le filtre)

Tout le calcul d'agrégation et la génération des graphiques
se fait ensuite côté navigateur via JavaScript / Chart.js.
"""
import json
from datetime import date
from flask import Blueprint, render_template

from app.data import get_communes, get_menages, get_membres

explorer_bp = Blueprint('explorer_bp', __name__)


# ============================================================
# DÉFINITION DES VARIABLES
# ============================================================
# Pour chaque variable, on donne :
#   - cle    : nom de la colonne dans le dataset enrichi
#   - label  : libellé affiché à l'utilisateur
#   - type   : "qualitative" | "quantitative"
#   - source : "membre" (sur la personne) | "menage" (sur le ménage)
#   - options (optionnel) : ordre/liste des modalités attendues

VARIABLES = [
    # ─── Sur les personnes ─────────────────────────────────────
    {
        "cle": "sexe", "label": "Sexe",
        "type": "qualitative", "source": "membre",
        "options": ["Masculin", "Féminin"],
    },
    {
        "cle": "age", "label": "Âge",
        "type": "quantitative", "source": "membre",
        "unite": "ans",
    },
    {
        "cle": "tranche_age", "label": "Tranche d'âge",
        "type": "qualitative", "source": "membre",
        "options": ["0-14", "15-29", "30-44", "45-59", "60+"],
    },
    {
        "cle": "niveau_instruction", "label": "Niveau d'instruction",
        "type": "qualitative", "source": "membre",
        "options": ["Aucun", "Primaire", "Secondaire", "Supérieur"],
    },
    {
        "cle": "sait_lire_ecrire", "label": "Sait lire et écrire",
        "type": "qualitative", "source": "membre",
        "options": ["Oui", "Non"],
    },
    {
        "cle": "situation_matrimoniale", "label": "Situation matrimoniale",
        "type": "qualitative", "source": "membre",
        "options": ["Célibataire", "Marié(e)", "Veuf(ve)",
                    "Divorcé(e)", "Union libre"],
    },
    {
        "cle": "situation_activite", "label": "Situation d'activité",
        "type": "qualitative", "source": "membre",
        "options": ["Actif occupé", "Chômeur", "Inactif"],
    },
    {
        "cle": "type_emploi", "label": "Type d'emploi",
        "type": "qualitative", "source": "membre",
        "options": ["Salarié(e)", "Indépendant(e)",
                    "Aide familial(e)", "Apprenti(e)"],
    },
    {
        "cle": "secteur_emploi", "label": "Secteur d'emploi",
        "type": "qualitative", "source": "membre",
        "options": ["Formel", "Informel", "Public"],
    },
    {
        "cle": "lien_chef", "label": "Lien avec le chef",
        "type": "qualitative", "source": "membre",
        "options": ["Chef", "Conjoint(e)", "Enfant", "Parent",
                    "Frère / Sœur", "Autre parent", "Sans lien"],
    },
    {
        "cle": "piece_identite", "label": "Pièce d'identité",
        "type": "qualitative", "source": "membre",
        "options": ["CNI", "Passeport", "Permis de conduire", "Aucune"],
    },
    {
        "cle": "handicap", "label": "Handicap",
        "type": "qualitative", "source": "membre",
        "options": ["Aucun", "Moteur", "Visuel", "Auditif",
                    "Mental", "Autre"],
    },

    # ─── Sur le ménage (héritées) ──────────────────────────────
    {
        "cle": "commune", "label": "Commune du ménage",
        "type": "qualitative", "source": "menage",
    },
    {
        "cle": "type_logement", "label": "Type de logement",
        "type": "qualitative", "source": "menage",
        "options": ["Maison individuelle", "Appartement",
                    "Cour commune", "Studio", "Autre"],
    },
    {
        "cle": "source_eau", "label": "Source d'eau",
        "type": "qualitative", "source": "menage",
        "options": ["Robinet maison", "Robinet cour", "Borne fontaine",
                    "Puits", "Eau en sachet"],
    },
    {
        "cle": "type_toilettes", "label": "Type de toilettes",
        "type": "qualitative", "source": "menage",
        "options": ["WC avec chasse", "Latrine améliorée",
                    "Latrine simple", "Aucune"],
    },
    {
        "cle": "source_eclairage", "label": "Source d'éclairage",
        "type": "qualitative", "source": "menage",
        "options": ["Électricité (CIE)", "Solaire", "Lampe à pétrole",
                    "Bougie", "Aucune"],
    },
    {
        "cle": "nombre_pieces", "label": "Nombre de pièces du logement",
        "type": "quantitative", "source": "menage",
        "unite": "pièces",
    },
    {
        "cle": "nb_biens_durables",
        "label": "Nombre de biens durables (richesse)",
        "type": "quantitative", "source": "menage",
        "unite": "biens",
    },
]


def _calculer_age(date_naissance):
    """Calcule l'âge en années depuis une date."""
    if not date_naissance:
        return None
    if hasattr(date_naissance, 'year'):
        today = date.today()
        return (today - date_naissance).days // 365
    return None


def _tranche_age(age):
    """Renvoie la tranche d'âge correspondante."""
    if age is None:
        return None
    if age < 15:
        return "0-14"
    if age < 30:
        return "15-29"
    if age < 45:
        return "30-44"
    if age < 60:
        return "45-59"
    return "60+"


@explorer_bp.route('/explorer')
def index():
    """Page Explorer — atelier de visualisation libre."""

    # 1. Charge ménages et membres
    menages = get_menages()
    membres = get_membres()

    if not menages or not membres:
        return render_template('explorer.html', vide=True)

    # 2. Indexe les ménages par id (accès rapide)
    menages_par_id = {m["id_menage"]: m for m in menages}

    # 3. Enrichit chaque membre avec les attributs de son ménage
    dataset = []
    for memb in membres:
        menage = menages_par_id.get(memb["id_menage"])
        if not menage:
            continue

        age = _calculer_age(memb.get("date_naissance"))

        # Compte des biens durables (proxy de richesse)
        biens = menage.get("biens_durables") or []
        nb_biens = len(biens)

        ligne = {
            # ── Identité de la personne ──
            "id_membre": memb["id_membre"],
            "id_menage": memb["id_menage"],

            # ── Variables sur la personne ──
            "sexe": memb.get("sexe", ""),
            "age": age,
            "tranche_age": _tranche_age(age),
            "niveau_instruction": memb.get("niveau_instruction", ""),
            "sait_lire_ecrire": memb.get("sait_lire_ecrire", ""),
            "situation_matrimoniale": memb.get("situation_matrimoniale", ""),
            "situation_activite": memb.get("situation_activite", ""),
            "type_emploi": memb.get("type_emploi", ""),
            "secteur_emploi": memb.get("secteur_emploi", ""),
            "lien_chef": memb.get("lien_chef", ""),
            "piece_identite": memb.get("piece_identite", ""),
            "handicap": memb.get("handicap", ""),

            # ── Variables héritées du ménage ──
            "commune": menage.get("commune", ""),
            "commune_slug": menage.get("commune_slug", ""),
            "type_logement": menage.get("type_logement", ""),
            "source_eau": menage.get("source_eau", ""),
            "type_toilettes": menage.get("type_toilettes", ""),
            "source_eclairage": menage.get("source_eclairage", ""),
            "nombre_pieces": menage.get("nombre_pieces", 0) or 0,
            "nb_biens_durables": nb_biens,
        }
        dataset.append(ligne)

    # 4. Récupère les communes pour le filtre
    communes = get_communes()

    return render_template(
        'explorer.html',
        vide=False,
        variables=VARIABLES,
        dataset_json=json.dumps(dataset, ensure_ascii=False),
        variables_json=json.dumps(VARIABLES, ensure_ascii=False),
        communes=communes,
        nb_personnes=len(dataset),
        nb_menages=len(menages),
    )