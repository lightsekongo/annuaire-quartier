"""
Page Territoires — exploration des 13 communes du District d'Abidjan.

Architecture :
  - Une carte interactive (gérée côté navigateur via Leaflet)
  - Un panneau de détail à droite avec la fiche du territoire cliqué
  - Un sélecteur d'indicateur en haut qui recolore la carte en temps réel

La route fournit toutes les données dont la page a besoin sous forme JSON
afin que le JavaScript puisse mettre à jour la carte sans recharger la page.
"""

from flask import Blueprint, render_template
import pandas as pd
import json

from app.data import get_menages, get_membres, get_quartiers
from app.calculs import calculer_par_commune, calculer_stats_quartier

territoires_bp = Blueprint('territoires_bp', __name__)

@territoires_bp.route('/territoires')
def index():
    """Page Territoires avec carte choroplèthe interactive."""

    # 1. Données et calcul par commune
    df_menages = pd.DataFrame(get_menages())
    df_membres = pd.DataFrame(get_membres())

    if df_menages.empty:
        return render_template('territoires.html', vide=True)

    donnees = calculer_par_commune(df_menages, df_membres)

    # 2. Sépare Abidjan (référence) des communes (à afficher sur la carte)
    abidjan = next(t for t in donnees["territoires"] if t["slug"] == "abidjan")
    communes = [t for t in donnees["territoires"] if t["slug"] != "abidjan"]

    # 3. Calcule les bornes (min/max) pour chaque indicateur
    # → utilisées par le JS pour normaliser les couleurs de la carte
    bornes_par_indicateur = {}
    for ind in donnees["indicateurs"]:
        cle = ind["cle"]
        valeurs = [t["valeurs"].get(cle, 0) for t in communes]
        bornes_par_indicateur[cle] = {
            "min": min(valeurs) if valeurs else 0,
            "max": max(valeurs) if valeurs else 0,
            "moyenne_abidjan": abidjan["valeurs"].get(cle, 0),
        }

    # 4. Construit un dict {slug: profil_commune} pour accès rapide en JS
    # 4. Construit un dict {slug: profil_commune} pour accès rapide en JS
    profils_communes = {
        t["slug"]: {
            "id": t["id"],
            "nom": t["nom"],
            "slug": t["slug"],
            "type": t["type"],
            "nb_menages": t["nb_menages"],
            "nb_membres": t["nb_membres"],
            "valeurs": t["valeurs"],
        }
        for t in communes
    }

    # 5. Récupère les quartiers et les regroupe par commune (slug)
    # Format : { "abobo": [ {nom, lat, lng, nb_menages}, ... ], ... }
    # 5. Récupère les quartiers, calcule leurs stats et les regroupe par commune
    # Format : { "abobo": [ {id, nom, lat, lng, stats}, ... ], ... }
    tous_quartiers = get_quartiers()
    quartiers_par_commune = {}
    for q in tous_quartiers:
        slug = q["commune_slug"]
        if slug not in quartiers_par_commune:
            quartiers_par_commune[slug] = []

        # Calcule les stats simples du quartier (volumétrie + composition)
        stats = calculer_stats_quartier(
            df_menages, df_membres,
            q["id_commune"], q["nom"]
        )

        quartiers_par_commune[slug].append({
            "id": q["id_quartier"],
            "nom": q["nom"],
            "lat": q["lat"],
            "lng": q["lng"],
            "nb_menages": q["nb_menages"],
            # Stats embarquées pour le pop-up (pas besoin de requête supplémentaire)
            "stats": stats,
        })

    return render_template(
        'territoires.html',
        vide=False,
        indicateurs_meta=donnees["indicateurs"],
        territoire_initial=abidjan,
        profils_json=json.dumps(profils_communes, ensure_ascii=False),
        bornes_json=json.dumps(bornes_par_indicateur, ensure_ascii=False),
        indicateurs_json=json.dumps(donnees["indicateurs"], ensure_ascii=False),
        abidjan_json=json.dumps(abidjan, ensure_ascii=False),
        quartiers_json=json.dumps(quartiers_par_commune, ensure_ascii=False),
    )