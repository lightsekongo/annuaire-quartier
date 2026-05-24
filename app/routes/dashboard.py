from flask import Blueprint, render_template
from app.models import query_df
from datetime import date
import pandas as pd

dashboard_bp = Blueprint('dashboard_bp', __name__)

def _calculs():
    """Calculs communs au dashboard et à la fiche imprimable."""
    df_menages = query_df("SELECT * FROM menage")
    df_membres = query_df("SELECT * FROM membre")

    if df_membres.empty:
        return None, None

    aujourd_hui = date.today()
    df_membres['age'] = df_membres['date_naissance'].apply(
        lambda d: (aujourd_hui - d).days // 365
    )

    nb_menages     = len(df_menages)
    nb_membres     = len(df_membres)
    taille_moyenne = round(nb_membres / nb_menages, 1) if nb_menages > 0 else 0

    df_scol            = df_membres[df_membres['statut_scolaire'] != 'Sans objet']
    nb_scolarises      = len(df_membres[df_membres['statut_scolaire'] == 'Scolarisé'])
    taux_scolarisation = round(nb_scolarises / len(df_scol) * 100, 1) if len(df_scol) > 0 else 0

    inactifs      = ['Chômeur', 'Au foyer', 'Retraité', 'Élève / Étudiant']
    df_adultes    = df_membres[df_membres['age'] >= 15]
    nb_actifs     = len(df_adultes[~df_adultes['activite_principale'].isin(inactifs)])
    taux_activite = round(nb_actifs / len(df_adultes) * 100, 1) if len(df_adultes) > 0 else 0

    return df_menages, df_membres, {
        'nb_menages'        : nb_menages,
        'nb_membres'        : nb_membres,
        'taille_moyenne'    : taille_moyenne,
        'nb_scolarises'     : nb_scolarises,
        'taux_scolarisation': taux_scolarisation,
        'taux_activite'     : taux_activite,
    }


@dashboard_bp.route('/statistiques')
def index():
    result = _calculs()
    if result[0] is None:
        return render_template('dashboard.html', vide=True)

    df_menages, df_membres, kpis = result

    # Graphiques
    sexe      = df_membres['sexe'].value_counts()
    activites = df_membres['activite_principale'].value_counts()
    statuts   = df_membres['statut_scolaire'].value_counts()

    bins   = [0, 5, 10, 15, 20, 30, 40, 50, 60, 200]
    labels = ['0-4','5-9','10-14','15-19','20-29','30-39','40-49','50-59','60+']
    df_membres['tranche'] = pd.cut(df_membres['age'], bins=bins, labels=labels, right=False)
    pyramide = df_membres.groupby(['tranche','sexe'], observed=True).size().unstack(fill_value=0)

    pyramide_masculin = [int(pyramide.get('Masculin', pd.Series(0, index=labels)).get(l, 0)) for l in labels]
    pyramide_feminin  = [int(pyramide.get('Féminin',  pd.Series(0, index=labels)).get(l, 0)) for l in labels]

    quartiers = df_menages['quartier'].value_counts()

    return render_template('dashboard.html',
        vide              = False,
        **kpis,
        sexe_labels       = sexe.index.tolist(),
        sexe_data         = sexe.values.tolist(),
        activites_labels  = activites.index.tolist(),
        activites_data    = activites.values.tolist(),
        statuts_labels    = statuts.index.tolist(),
        statuts_data      = statuts.values.tolist(),
        pyramide_labels   = labels,
        pyramide_masculin = pyramide_masculin,
        pyramide_feminin  = pyramide_feminin,
        quartiers_labels  = quartiers.index.tolist(),
        quartiers_data    = quartiers.values.tolist(),
    )


@dashboard_bp.route('/statistiques/fiche')
def fiche_imprimable():
    result = _calculs()
    if result[0] is None:
        return render_template('fiche_imprimable.html',
            vide=True, date_generation=date.today().strftime('%d %B %Y'))

    df_menages, df_membres, kpis = result

    # Synthèse par quartier
    rows = []
    for q in df_menages['quartier'].unique():
        ids_q    = df_menages[df_menages['quartier'] == q]['id_menage'].tolist()
        mb_q     = df_membres[df_membres['id_menage'].isin(ids_q)]
        nb_m     = len(ids_q)
        nb_mb    = len(mb_q)
        nb_scol  = len(mb_q[mb_q['statut_scolaire'] == 'Scolarisé'])
        rows.append({
            'quartier'      : q,
            'nb_menages'    : nb_m,
            'nb_membres'    : nb_mb,
            'taille_moyenne': round(nb_mb / nb_m, 1) if nb_m > 0 else 0,
            'nb_scolarises' : nb_scol,
        })

    # Activités des chefs
    df_chefs   = df_membres[df_membres['lien_parente'] == 'Chef de ménage']
    act_chefs  = df_chefs['activite_principale'].value_counts()
    total_chefs = len(df_chefs)
    activites_chefs = [
        {'activite_principale': a, 'nb': n,
         'pct': round(n / total_chefs * 100, 1) if total_chefs > 0 else 0}
        for a, n in act_chefs.items()
    ]

    return render_template('fiche_imprimable.html',
        vide             = False,
        date_generation  = date.today().strftime('%d %B %Y'),
        synthese_quartiers = rows,
        activites_chefs    = activites_chefs,
        **kpis,
    )