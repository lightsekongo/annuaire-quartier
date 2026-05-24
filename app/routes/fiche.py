"""
Route de la fiche imprimable.

URL :
    /fiche-imprimable                  → Abidjan ensemble
    /fiche-imprimable?commune=cocody   → Fiche d'une commune précise

La page est conçue pour s'imprimer proprement via Ctrl+P
(format A4, marges optimisées via @media print).
"""
from datetime import date
from flask import Blueprint, render_template, request
import pandas as pd

from app.data import get_communes, get_menages, get_membres, get_quartiers
from app.calculs import calculer_par_commune, calculer_stats_quartier

fiche_bp = Blueprint('fiche_bp', __name__)


@fiche_bp.route('/fiche-imprimable')
def index():
    """Fiche imprimable d'Abidjan ou d'une commune au choix."""
    # 1. Lecture du paramètre (commune ou ensemble)
    slug_actif = request.args.get('commune', '').strip().lower()

    # 2. Données globales
    df_menages = pd.DataFrame(get_menages())
    df_membres = pd.DataFrame(get_membres())
    communes = get_communes()

    if df_menages.empty:
        return render_template('fiche.html', vide=True)

    # 3. Calcule les 18 indicateurs pour chaque commune + Abidjan ensemble
    donnees = calculer_par_commune(df_menages, df_membres)

    # 4. Cherche le territoire actif
    territoire = None
    type_fiche = "ensemble"

    if slug_actif and slug_actif != "abidjan":
        # Cherche une commune par son slug
        for t in donnees["territoires"]:
            if t["slug"] == slug_actif:
                territoire = t
                type_fiche = "commune"
                break

    if territoire is None:
        # Abidjan ensemble (par défaut)
        territoire = next(t for t in donnees["territoires"]
                           if t["slug"] == "abidjan")
        type_fiche = "ensemble"

    # 5. Quartiers de la commune (si type_fiche == "commune")
    quartiers_commune = []
    if type_fiche == "commune":
        tous_quartiers = get_quartiers()
        for q in tous_quartiers:
            if q["commune_slug"] == territoire["slug"]:
                stats_q = calculer_stats_quartier(
                    df_menages, df_membres,
                    q["id_commune"], q["nom"]
                )
                quartiers_commune.append({
                    "nom": q["nom"],
                    "nb_menages": q["nb_menages"],
                    "nb_personnes": stats_q["volumetrie"]["nb_personnes"],
                })
        # Tri par nombre de ménages décroissant
        quartiers_commune.sort(key=lambda q: q["nb_menages"], reverse=True)

    # 6. Données pour la pyramide des âges (mini-graphique)
    # On filtre les membres concernés selon le territoire
    if type_fiche == "commune":
        ids_menages = df_menages[
            df_menages["id_commune"] == territoire["id"]
        ]["id_menage"].tolist()
        df_mem_filtre = df_membres[df_membres["id_menage"].isin(ids_menages)]
    else:
        df_mem_filtre = df_membres

    # Calcule la pyramide (5 tranches d'âge, H/F)
    pyramide = _calculer_pyramide(df_mem_filtre)

    # Répartition par sexe
    if len(df_mem_filtre) > 0:
        nb_h = (df_mem_filtre["sexe"] == "Masculin").sum()
        nb_f = (df_mem_filtre["sexe"] == "Féminin").sum()
    else:
        nb_h = nb_f = 0

    return render_template(
        'fiche.html',
        vide=False,
        type_fiche=type_fiche,
        territoire=territoire,
        indicateurs_meta=donnees["indicateurs"],
        quartiers_commune=quartiers_commune,
        communes=communes,
        slug_actif=territoire["slug"],
        date_extraction=date.today(),
        pyramide=pyramide,
        nb_h=int(nb_h),
        nb_f=int(nb_f),
    )


def _calculer_pyramide(df_membres):
    """
    Calcule la pyramide des âges en 5 tranches.
    Renvoie un dict avec les comptes par tranche et par sexe.
    """
    from datetime import date
    if df_membres.empty:
        return {
            "tranches": ["0-14", "15-29", "30-44", "45-59", "60+"],
            "hommes":   [0, 0, 0, 0, 0],
            "femmes":   [0, 0, 0, 0, 0],
        }

    today = date.today()
    ages = df_membres["date_naissance"].apply(
        lambda d: (today - d).days // 365 if d else 0
    )

    bornes = [(0, 14), (15, 29), (30, 44), (45, 59), (60, 200)]
    tranches = ["0-14", "15-29", "30-44", "45-59", "60+"]
    hommes = []
    femmes = []

    for borne_min, borne_max in bornes:
        mask_age = (ages >= borne_min) & (ages <= borne_max)
        sous_df = df_membres[mask_age]
        hommes.append(int((sous_df["sexe"] == "Masculin").sum()))
        femmes.append(int((sous_df["sexe"] == "Féminin").sum()))

    return {
        "tranches": tranches,
        "hommes": hommes,
        "femmes": femmes,
    }