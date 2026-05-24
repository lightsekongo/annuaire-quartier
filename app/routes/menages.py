"""
Routes pour la gestion des ménages.

Utilise les fixtures Python (en mémoire) en attendant le branchement
PostgreSQL à l'étape F. L'interface des fonctions de manipulation
(creer_menage, modifier_menage, supprimer_menage) est conçue pour être
remplaçable sans toucher aux templates ni aux routes.
"""
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, abort
)
import pandas as pd

from app.data import (
    get_communes, get_menages, get_membres, get_quartiers,
    get_menage_by_id, get_membres_by_menage, get_stats_globales,
    creer_menage, modifier_menage, supprimer_menage,
)
from app.calculs import calculer_tous_indicateurs

menages_bp = Blueprint('menages_bp', __name__)


# ============================================================
# PAGE D'ACCUEIL (statistiques globales)
# ============================================================
@menages_bp.route('/')
def index():
    """Tableau de bord avec les 18 indicateurs."""
    df_menages = pd.DataFrame(get_menages())
    df_membres = pd.DataFrame(get_membres())
    stats_globales = get_stats_globales()

    indicateurs = []
    if not df_menages.empty:
        indicateurs = calculer_tous_indicateurs(df_menages, df_membres)

    return render_template(
        'index.html',
        vide=df_menages.empty,
        stats_globales=stats_globales,
        indicateurs=indicateurs,
    )


# ============================================================
# LISTE DES MÉNAGES (page Recensement)
# ============================================================
@menages_bp.route('/menages')
def liste():
    """
    Liste tous les ménages avec recherche et filtres.

    Paramètres GET :
      - q : terme de recherche (cherche dans nom_menage)
      - commune : id_commune pour filtrer (vide = toutes)
      - quartier : nom du quartier pour filtrer (vide = tous)
    """
    # Récupération des paramètres
    q = (request.args.get('q') or '').strip()
    id_commune_str = request.args.get('commune') or ''
    nom_quartier = (request.args.get('quartier') or '').strip()

    # Données brutes
    tous_menages = get_menages()
    tous_membres = get_membres()
    communes = get_communes()
    quartiers = get_quartiers()

    # Compte le nombre de membres par ménage (pour l'afficher dans la liste)
    membres_par_menage = {}
    for m in tous_membres:
        id_m = m["id_menage"]
        membres_par_menage[id_m] = membres_par_menage.get(id_m, 0) + 1

    # Application des filtres
    menages_filtres = tous_menages

    if q:
        q_lower = q.lower()
        menages_filtres = [
            m for m in menages_filtres
            if q_lower in m["nom_menage"].lower()
        ]

    if id_commune_str:
        try:
            id_commune = int(id_commune_str)
            menages_filtres = [
                m for m in menages_filtres if m["id_commune"] == id_commune
            ]
        except ValueError:
            id_commune_str = ''

    if nom_quartier:
        menages_filtres = [
            m for m in menages_filtres
            if m["quartier"] == nom_quartier
        ]

    # Enrichit chaque ménage avec son nombre de membres
    for m in menages_filtres:
        m["_nb_membres"] = membres_par_menage.get(m["id_menage"], 0)

    # Tri par nom de ménage
    menages_filtres = sorted(menages_filtres, key=lambda x: x["nom_menage"].lower())

    # Prépare la liste des quartiers par commune (pour le sélecteur dépendant)
    quartiers_par_commune = {}
    for q_item in quartiers:
        id_c = q_item["id_commune"]
        if id_c not in quartiers_par_commune:
            quartiers_par_commune[id_c] = []
        quartiers_par_commune[id_c].append(q_item["nom"])

    return render_template(
        'menages/liste.html',
        menages=menages_filtres,
        total=len(tous_menages),
        nb_filtres=len(menages_filtres),
        # Filtres actifs
        q=q,
        id_commune_actif=id_commune_str,
        nom_quartier_actif=nom_quartier,
        # Données pour les sélecteurs
        communes=communes,
        quartiers_par_commune=quartiers_par_commune,
    )


# ============================================================
# FICHE DÉTAILLÉE D'UN MÉNAGE
# ============================================================
@menages_bp.route('/menages/<int:id_menage>')
def fiche(id_menage):
    """Affiche le détail d'un ménage et la liste de ses membres."""
    menage = get_menage_by_id(id_menage)
    if not menage:
        abort(404)

    membres = get_membres_by_menage(id_menage)
    # Tri : chef d'abord, puis par âge décroissant
    membres = sorted(
        membres,
        key=lambda m: (
            0 if m.get("lien_chef") == "Chef" else 1,
            m.get("date_naissance", ""),
        )
    )

    return render_template(
        'menages/fiche.html',
        menage=menage,
        membres=membres,
        nb_membres=len(membres),
    )


# ============================================================
# CRÉATION D'UN MÉNAGE
# ============================================================
@menages_bp.route('/menages/nouveau', methods=['GET', 'POST'])
def nouveau():
    """Formulaire de création d'un ménage."""
    communes = get_communes()
    quartiers = get_quartiers()

    # Pour le sélecteur dépendant commune → quartier
    quartiers_par_commune = {}
    for q_item in quartiers:
        id_c = q_item["id_commune"]
        if id_c not in quartiers_par_commune:
            quartiers_par_commune[id_c] = []
        quartiers_par_commune[id_c].append(q_item["nom"])

    if request.method == 'POST':
        # Validation minimale
        nom = (request.form.get('nom_menage') or '').strip()
        id_commune_str = request.form.get('id_commune') or ''
        quartier = (request.form.get('quartier') or '').strip()

        erreurs = []
        if not nom:
            erreurs.append("Le nom du ménage est requis.")
        if not id_commune_str:
            erreurs.append("La commune est requise.")
        if not quartier:
            erreurs.append("Le quartier est requis.")

        if erreurs:
            for e in erreurs:
                flash(e, 'error')
            return render_template(
                'menages/formulaire.html',
                menage=None,
                communes=communes,
                quartiers_par_commune=quartiers_par_commune,
                # On renvoie les valeurs saisies pour ne pas perdre le formulaire
                form_data=request.form,
            )

        # Construction du dict pour creer_menage
        donnees = {
            'nom_menage': nom,
            'id_commune': int(id_commune_str),
            'quartier': quartier,
            'type_logement': request.form.get('type_logement') or '',
            'statut_occupation': request.form.get('statut_occupation') or '',
            'nombre_pieces': request.form.get('nombre_pieces') or 0,
            'source_eau': request.form.get('source_eau') or '',
            'type_toilettes': request.form.get('type_toilettes') or '',
            'source_eclairage': request.form.get('source_eclairage') or '',
            'gestion_ordures': request.form.get('gestion_ordures') or '',
            'biens_durables': request.form.getlist('biens_durables'),
            'date_recensement': request.form.get('date_recensement') or '',
        }

        nouveau_menage = creer_menage(donnees)
        flash(f'Ménage "{nouveau_menage["nom_menage"]}" créé avec succès.', 'success')
        return redirect(url_for('menages_bp.fiche', id_menage=nouveau_menage["id_menage"]))

    return render_template(
        'menages/formulaire.html',
        menage=None,
        communes=communes,
        quartiers_par_commune=quartiers_par_commune,
        form_data={},
    )


# ============================================================
# MODIFICATION D'UN MÉNAGE
# ============================================================
@menages_bp.route('/menages/<int:id_menage>/modifier', methods=['GET', 'POST'])
def modifier(id_menage):
    """Formulaire d'édition d'un ménage existant."""
    menage = get_menage_by_id(id_menage)
    if not menage:
        abort(404)

    communes = get_communes()
    quartiers = get_quartiers()

    quartiers_par_commune = {}
    for q_item in quartiers:
        id_c = q_item["id_commune"]
        if id_c not in quartiers_par_commune:
            quartiers_par_commune[id_c] = []
        quartiers_par_commune[id_c].append(q_item["nom"])

    if request.method == 'POST':
        nom = (request.form.get('nom_menage') or '').strip()
        id_commune_str = request.form.get('id_commune') or ''
        quartier = (request.form.get('quartier') or '').strip()

        erreurs = []
        if not nom:
            erreurs.append("Le nom du ménage est requis.")
        if not id_commune_str:
            erreurs.append("La commune est requise.")
        if not quartier:
            erreurs.append("Le quartier est requis.")

        if erreurs:
            for e in erreurs:
                flash(e, 'error')
            return render_template(
                'menages/formulaire.html',
                menage=menage,
                communes=communes,
                quartiers_par_commune=quartiers_par_commune,
                form_data=request.form,
            )

        donnees = {
            'nom_menage': nom,
            'id_commune': int(id_commune_str),
            'quartier': quartier,
            'type_logement': request.form.get('type_logement') or '',
            'statut_occupation': request.form.get('statut_occupation') or '',
            'nombre_pieces': request.form.get('nombre_pieces') or 0,
            'source_eau': request.form.get('source_eau') or '',
            'type_toilettes': request.form.get('type_toilettes') or '',
            'source_eclairage': request.form.get('source_eclairage') or '',
            'gestion_ordures': request.form.get('gestion_ordures') or '',
            'biens_durables': request.form.getlist('biens_durables'),
            'date_recensement': request.form.get('date_recensement') or '',
        }

        modifier_menage(id_menage, donnees)
        flash(f'Ménage "{nom}" mis à jour.', 'success')
        return redirect(url_for('menages_bp.fiche', id_menage=id_menage))

    # GET : on pré-remplit avec les données actuelles
    return render_template(
        'menages/formulaire.html',
        menage=menage,
        communes=communes,
        quartiers_par_commune=quartiers_par_commune,
        form_data=menage,
    )


# ============================================================
# SUPPRESSION D'UN MÉNAGE
# ============================================================
@menages_bp.route('/menages/<int:id_menage>/supprimer', methods=['POST'])
def supprimer(id_menage):
    """Supprime un ménage et tous ses membres."""
    menage = get_menage_by_id(id_menage)
    if not menage:
        abort(404)

    nom = menage["nom_menage"]
    ok = supprimer_menage(id_menage)

    if ok:
        flash(f'Ménage "{nom}" supprimé.', 'success')
    else:
        flash('Erreur lors de la suppression.', 'error')

    return redirect(url_for('menages_bp.liste'))