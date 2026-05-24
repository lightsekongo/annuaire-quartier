"""
Page Comparer — confrontation analytique des territoires.

Deux sous-onglets :
  1. Comparaison directe : 2 à 4 territoires affichés côte à côte sur les 18 indicateurs
  2. Classement : 1 indicateur, les 13 communes triées avec moyenne d'Abidjan

Les paramètres de sélection circulent via la query string :
  /comparer?mode=directe&territoires=abobo,cocody,yopougon
  /comparer?mode=classement&indicateur=taux_activite
"""

from flask import Blueprint, render_template, request
import pandas as pd

from app.data import get_menages, get_membres
from app.calculs import calculer_par_commune

comparer_bp = Blueprint('comparer_bp', __name__)

# ============================================================
# CONSTANTES
# ============================================================
# Sélection par défaut quand l'utilisateur arrive sur la page sans paramètres :
# 4 communes contrastées pour montrer immédiatement l'intérêt de l'outil.
TERRITOIRES_DEFAUT = ["cocody", "yopougon", "abobo", "anyama"]

INDICATEUR_DEFAUT = "taux_activite"

MODES_VALIDES = {"directe", "classement"}


# ============================================================
# ROUTE PRINCIPALE
# ============================================================
@comparer_bp.route('/comparer')
def index():
    """Page Comparer avec ses deux sous-onglets."""
    # 1. Récupération des données et calcul par territoire
    df_menages = pd.DataFrame(get_menages())
    df_membres = pd.DataFrame(get_membres())

    if df_menages.empty:
        return render_template('comparer.html', vide=True)

    donnees = calculer_par_commune(df_menages, df_membres)

    # 2. Lecture des paramètres URL
    mode = request.args.get('mode', 'directe')
    if mode not in MODES_VALIDES:
        mode = 'directe'

    # 3. Préparation des données selon le mode
    contexte = {
        "vide": False,
        "mode": mode,
        "indicateurs_meta": donnees["indicateurs"],
        "tous_territoires": donnees["territoires"],
    }

    if mode == "directe":
        contexte.update(_preparer_directe(donnees))
    else:
        contexte.update(_preparer_classement(donnees))

    return render_template('comparer.html', **contexte)


# ============================================================
# MODE 1 : COMPARAISON DIRECTE
# ============================================================
def _preparer_directe(donnees):
    """
    Prépare les données pour la comparaison directe.

    L'utilisateur peut sélectionner 2 à 4 territoires via le paramètre
    `territoires` (slugs séparés par des virgules).
    """
    slugs_demandes = request.args.get('territoires', '').strip()

    if slugs_demandes:
        slugs = [s.strip() for s in slugs_demandes.split(',') if s.strip()]
    else:
        slugs = TERRITOIRES_DEFAUT[:]

    # On limite entre 2 et 4 sélections
    slugs = slugs[:4]

    # Recherche des territoires correspondants
    par_slug = {t["slug"]: t for t in donnees["territoires"]}
    territoires_selectionnes = [par_slug[s] for s in slugs if s in par_slug]

    # Si moins de 2 valides, on retombe sur la sélection par défaut
    if len(territoires_selectionnes) < 2:
        territoires_selectionnes = [par_slug[s] for s in TERRITOIRES_DEFAUT
                                     if s in par_slug]

    # Pour les mini-barres : pour chaque indicateur, on calcule le max
    # parmi les territoires sélectionnés afin de normaliser les barres
    # (la barre la plus pleine = la valeur la plus haute parmi les sélectionnés)
    max_par_indicateur = {}
    for ind in donnees["indicateurs"]:
        cle = ind["cle"]
        valeurs = [t["valeurs"][cle] for t in territoires_selectionnes
                   if cle in t["valeurs"]]
        max_par_indicateur[cle] = max(valeurs) if valeurs else 0

    # Identifie aussi le territoire "leader" pour chaque indicateur
    # (celui qui a la valeur max — utile pour mettre en valeur en ambré)
    leader_par_indicateur = {}
    for ind in donnees["indicateurs"]:
        cle = ind["cle"]
        if not territoires_selectionnes:
            continue
        leader = max(territoires_selectionnes,
                     key=lambda t: t["valeurs"].get(cle, 0))
        leader_par_indicateur[cle] = leader["slug"]

    return {
        "territoires_selectionnes": territoires_selectionnes,
        "slugs_selectionnes": [t["slug"] for t in territoires_selectionnes],
        "max_par_indicateur": max_par_indicateur,
        "leader_par_indicateur": leader_par_indicateur,
    }


# ============================================================
# MODE 2 : CLASSEMENT
# ============================================================
def _preparer_classement(donnees):
    """
    Prépare les données pour le classement.

    L'utilisateur choisit un indicateur, on trie les 13 communes
    et on indique la moyenne d'Abidjan en référence.
    """
    cle_indic = request.args.get('indicateur', INDICATEUR_DEFAUT)

    # Validation : la clé doit exister
    cles_valides = {ind["cle"] for ind in donnees["indicateurs"]}
    if cle_indic not in cles_valides:
        cle_indic = INDICATEUR_DEFAUT

    # Métadonnées de l'indicateur choisi
    indic_meta = next(ind for ind in donnees["indicateurs"]
                      if ind["cle"] == cle_indic)

    # Sépare Abidjan (référence) des communes (à classer)
    abidjan = next(t for t in donnees["territoires"] if t["slug"] == "abidjan")
    communes = [t for t in donnees["territoires"] if t["slug"] != "abidjan"]

    # Trie les communes par valeur décroissante sur l'indicateur choisi
    communes_classees = sorted(
        communes,
        key=lambda t: t["valeurs"].get(cle_indic, 0),
        reverse=True,
    )

    # Calcule la valeur max pour normaliser les barres
    moyenne_abidjan = abidjan["valeurs"].get(cle_indic, 0)
    valeurs = [t["valeurs"].get(cle_indic, 0) for t in communes_classees]
    valeur_max = max(valeurs + [moyenne_abidjan]) if valeurs else 1
    if valeur_max == 0:
        valeur_max = 1  # évite division par zéro

    return {
        "indicateur_actif": indic_meta,
        "communes_classees": communes_classees,
        "moyenne_abidjan": moyenne_abidjan,
        "valeur_max_classement": valeur_max,
    }