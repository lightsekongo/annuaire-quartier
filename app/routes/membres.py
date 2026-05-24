"""
Routes pour la gestion des membres d'un ménage.

Utilise les fixtures Python (en mémoire) en attendant le branchement
PostgreSQL à l'étape F.
"""
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, abort
)

from app.data import (
    get_menage_by_id, get_membres_by_menage,
    creer_membre, modifier_membre, supprimer_membre,
)

membres_bp = Blueprint('membres_bp', __name__)


def _trouver_membre(id_membre: int) -> dict | None:
    """Helper : trouve un membre par son id (depuis PostgreSQL)."""
    from app.models import query_one
    return query_one(
        "SELECT id_menage, prenom, nom FROM membre WHERE id_membre = %s",
        (id_membre,)
    )

# ============================================================
# AJOUT D'UN MEMBRE À UN MÉNAGE
# ============================================================
@membres_bp.route('/menages/<int:id_menage>/membres/nouveau',
                   methods=['GET', 'POST'])
def nouveau(id_menage):
    """Formulaire de création d'un membre dans un ménage."""
    menage = get_menage_by_id(id_menage)
    if not menage:
        abort(404)

    if request.method == 'POST':
        # Validation
        prenom = (request.form.get('prenom') or '').strip()
        nom = (request.form.get('nom') or '').strip()
        sexe = request.form.get('sexe') or ''
        date_naissance = request.form.get('date_naissance') or ''

        erreurs = []
        if not prenom:
            erreurs.append("Le prénom est requis.")
        if not nom:
            erreurs.append("Le nom est requis.")
        if sexe not in ('Masculin', 'Féminin'):
            erreurs.append("Le sexe doit être renseigné.")
        if not date_naissance:
            erreurs.append("La date de naissance est requise.")

        if erreurs:
            for e in erreurs:
                flash(e, 'error')
            return render_template(
                'menages/form_membre.html',
                menage=menage,
                membre=None,
                form_data=request.form,
            )

        donnees = {
            'id_menage': id_menage,
            'prenom': prenom,
            'nom': nom,
            'sexe': sexe,
            'date_naissance': date_naissance,
            'lien_chef': request.form.get('lien_chef') or '',
            'niveau_instruction': request.form.get('niveau_instruction') or 'Aucun',
            'sait_lire_ecrire': request.form.get('sait_lire_ecrire') or 'Non',
            'situation_matrimoniale': request.form.get('situation_matrimoniale') or 'Célibataire',
            'piece_identite': request.form.get('piece_identite') or 'Aucune',
            'handicap': request.form.get('handicap') or 'Aucun',
            'situation_activite': request.form.get('situation_activite') or 'Inactif',
            'type_emploi': request.form.get('type_emploi') or '',
            'secteur_emploi': request.form.get('secteur_emploi') or '',
        }

        nouveau_membre = creer_membre(donnees)
        flash(f'Membre "{nouveau_membre["prenom"]} {nouveau_membre["nom"]}" ajouté.',
              'success')
        return redirect(url_for('menages_bp.fiche', id_menage=id_menage))

    return render_template(
        'menages/form_membre.html',
        menage=menage,
        membre=None,
        form_data={},
    )


# ============================================================
# MODIFICATION D'UN MEMBRE
# ============================================================
@membres_bp.route('/membres/<int:id_membre>/modifier', methods=['GET', 'POST'])
def modifier(id_membre):
    """Formulaire d'édition d'un membre existant."""
    membre = _trouver_membre(id_membre)
    if not membre:
        abort(404)

    menage = get_menage_by_id(membre["id_menage"])
    if not menage:
        abort(404)

    if request.method == 'POST':
        prenom = (request.form.get('prenom') or '').strip()
        nom = (request.form.get('nom') or '').strip()
        sexe = request.form.get('sexe') or ''
        date_naissance = request.form.get('date_naissance') or ''

        erreurs = []
        if not prenom:
            erreurs.append("Le prénom est requis.")
        if not nom:
            erreurs.append("Le nom est requis.")
        if sexe not in ('Masculin', 'Féminin'):
            erreurs.append("Le sexe doit être renseigné.")
        if not date_naissance:
            erreurs.append("La date de naissance est requise.")

        if erreurs:
            for e in erreurs:
                flash(e, 'error')
            return render_template(
                'menages/form_membre.html',
                menage=menage,
                membre=membre,
                form_data=request.form,
            )

        donnees = {
            'prenom': prenom,
            'nom': nom,
            'sexe': sexe,
            'date_naissance': date_naissance,
            'lien_chef': request.form.get('lien_chef') or '',
            'niveau_instruction': request.form.get('niveau_instruction') or 'Aucun',
            'sait_lire_ecrire': request.form.get('sait_lire_ecrire') or 'Non',
            'situation_matrimoniale': request.form.get('situation_matrimoniale') or 'Célibataire',
            'piece_identite': request.form.get('piece_identite') or 'Aucune',
            'handicap': request.form.get('handicap') or 'Aucun',
            'situation_activite': request.form.get('situation_activite') or 'Inactif',
            'type_emploi': request.form.get('type_emploi') or '',
            'secteur_emploi': request.form.get('secteur_emploi') or '',
        }

        modifier_membre(id_membre, donnees)
        flash(f'Membre "{prenom} {nom}" mis à jour.', 'success')
        return redirect(url_for('menages_bp.fiche', id_menage=menage["id_menage"]))

    return render_template(
        'menages/form_membre.html',
        menage=menage,
        membre=membre,
        form_data=membre,
    )


# ============================================================
# SUPPRESSION D'UN MEMBRE
# ============================================================
@membres_bp.route('/membres/<int:id_membre>/supprimer', methods=['POST'])
def supprimer(id_membre):
    """Supprime un membre."""
    membre = _trouver_membre(id_membre)
    if not membre:
        abort(404)

    id_menage = membre["id_menage"]
    nom_complet = f'{membre["prenom"]} {membre["nom"]}'
    ok = supprimer_membre(id_membre)

    if ok:
        flash(f'Membre "{nom_complet}" supprimé.', 'success')
    else:
        flash('Erreur lors de la suppression.', 'error')

    return redirect(url_for('menages_bp.fiche', id_menage=id_menage))