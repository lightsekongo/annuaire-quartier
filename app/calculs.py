"""
Calcul des 18 indicateurs statistiques.

Toutes les fonctions de ce module prennent en entrée des DataFrames pandas
(ménages et membres) et renvoient des indicateurs prêts à afficher.

Aligné sur le schéma PostgreSQL actuel :
  - membre.lien_chef, membre.situation_activite, membre.niveau_instruction,
    membre.sait_lire_ecrire ("Oui"/"Non"), membre.type_emploi, membre.secteur_emploi
  - menage.biens_durables (TEXT[]) au lieu de 6 colonnes booléennes
"""

import pandas as pd
from datetime import date


# ============================================================
# UTILITAIRES
# ============================================================
def _ages(df_membres: pd.DataFrame) -> pd.Series:
    """Calcule l'âge en années depuis la date de naissance."""
    today = date.today()

    def _calc(d):
        if d is None:
            return 0
        # Si c'est déjà un objet date, on l'utilise directement
        if hasattr(d, 'year'):
            return (today - d).days // 365
        return 0

    return df_membres["date_naissance"].apply(_calc)


def _pct(numerateur: int, denominateur: int, decimales: int = 1) -> float:
    """Pourcentage sécurisé (renvoie 0 si dénominateur nul)."""
    if denominateur == 0:
        return 0.0
    return round(numerateur / denominateur * 100, decimales)


def _round(valeur: float, decimales: int = 1) -> float:
    return round(valeur, decimales) if valeur else 0.0


def _possede(df_menages: pd.DataFrame, bien: str) -> pd.Series:
    """Renvoie une série booléenne : True si le ménage possède `bien`."""
    if df_menages.empty or "biens_durables" not in df_menages.columns:
        return pd.Series([False] * len(df_menages), index=df_menages.index)
    return df_menages["biens_durables"].apply(
        lambda lst: bien in (lst or [])
    )


# ============================================================
# 1. INDICATEURS DÉMOGRAPHIQUES
# ============================================================
def population_recensee(df_membres: pd.DataFrame) -> int:
    return len(df_membres)


def taille_moyenne_menages(df_menages: pd.DataFrame,
                            df_membres: pd.DataFrame) -> float:
    if len(df_menages) == 0:
        return 0.0
    return round(len(df_membres) / len(df_menages), 1)


def ratio_dependance(df_membres: pd.DataFrame) -> float:
    """(Jeunes <15 + Âgés 65+) / Population 15-64 × 100"""
    if df_membres.empty:
        return 0.0
    ages = _ages(df_membres)
    jeunes = (ages < 15).sum()
    actifs = ((ages >= 15) & (ages < 65)).sum()
    ages_plus = (ages >= 65).sum()
    return _pct(jeunes + ages_plus, actifs)


def part_moins_15_ans(df_membres: pd.DataFrame) -> float:
    if df_membres.empty:
        return 0.0
    ages = _ages(df_membres)
    return _pct((ages < 15).sum(), len(ages))


def ratio_masculinite(df_membres: pd.DataFrame) -> float:
    """Hommes pour 100 femmes."""
    if df_membres.empty:
        return 0.0
    nb_h = (df_membres["sexe"] == "Masculin").sum()
    nb_f = (df_membres["sexe"] == "Féminin").sum()
    if nb_f == 0:
        return 0.0
    return round(nb_h / nb_f * 100, 1)


def part_menages_diriges_femme(df_membres: pd.DataFrame,
                                df_menages: pd.DataFrame) -> float:
    if df_menages.empty:
        return 0.0
    chefs = df_membres[df_membres["lien_chef"] == "Chef"]
    nb_femmes = (chefs["sexe"] == "Féminin").sum()
    return _pct(nb_femmes, len(df_menages))


# ============================================================
# 2. INDICATEURS ÉCONOMIQUES
# ============================================================
# Valeurs possibles de situation_activite : "Actif occupé", "Chômeur", "Inactif"
INACTIFS = {"Inactif"}

# Valeurs de secteur_emploi : "Formel", "Informel", "Public"
SECTEUR_INFORMEL = {"Informel"}
SECTEUR_SALARIES = {"Formel", "Public"}


def _adultes_15_plus(df_membres: pd.DataFrame) -> pd.DataFrame:
    if df_membres.empty:
        return df_membres
    ages = _ages(df_membres)
    return df_membres[ages >= 15]


def _actifs(df_adultes: pd.DataFrame) -> pd.DataFrame:
    """Population active = adultes non inactifs (donc occupés ou chômeurs)."""
    if df_adultes.empty:
        return df_adultes
    return df_adultes[~df_adultes["situation_activite"].isin(INACTIFS)]


def taux_activite(df_membres: pd.DataFrame) -> float:
    """Actifs (occupés + chômeurs) parmi les 15+."""
    adultes = _adultes_15_plus(df_membres)
    if adultes.empty:
        return 0.0
    actifs = _actifs(adultes)
    return _pct(len(actifs), len(adultes))


def taux_chomage(df_membres: pd.DataFrame) -> float:
    """Chômeurs parmi les actifs."""
    adultes = _adultes_15_plus(df_membres)
    actifs = _actifs(adultes)
    if actifs.empty:
        return 0.0
    chomeurs = (actifs["situation_activite"] == "Chômeur").sum()
    return _pct(chomeurs, len(actifs))


def part_informel(df_membres: pd.DataFrame) -> float:
    """Part dans le secteur informel parmi les actifs occupés."""
    adultes = _adultes_15_plus(df_membres)
    actifs = _actifs(adultes)
    occupes = actifs[actifs["situation_activite"] == "Actif occupé"]
    if occupes.empty:
        return 0.0
    informels = occupes["secteur_emploi"].isin(SECTEUR_INFORMEL).sum()
    return _pct(informels, len(occupes))


def part_salaries(df_membres: pd.DataFrame) -> float:
    """Salariés (formel + public) parmi les actifs occupés."""
    adultes = _adultes_15_plus(df_membres)
    actifs = _actifs(adultes)
    occupes = actifs[actifs["situation_activite"] == "Actif occupé"]
    if occupes.empty:
        return 0.0
    salaries = occupes["secteur_emploi"].isin(SECTEUR_SALARIES).sum()
    return _pct(salaries, len(occupes))


def equipement_numerique(df_menages: pd.DataFrame) -> float:
    """% de ménages possédant smartphone OU ordinateur."""
    if df_menages.empty:
        return 0.0
    a_smartphone = _possede(df_menages, "Smartphone")
    a_ordi = _possede(df_menages, "Ordinateur")
    equipes = (a_smartphone | a_ordi).sum()
    return _pct(equipes, len(df_menages))


def indice_richesse_median(df_menages: pd.DataFrame) -> float:
    """
    Score de richesse simple = nombre de biens durables possédés.
    On renvoie le score médian.

    Méthodologie inspirée de l'indice de richesse EDS.
    Les biens comptés : Frigo, TV, Climatiseur, Voiture, Moto,
    Internet, Smartphone, Ordinateur.
    """
    if df_menages.empty or "biens_durables" not in df_menages.columns:
        return 0.0
    scores = df_menages["biens_durables"].apply(lambda lst: len(lst or []))
    return float(scores.median())


# ============================================================
# 3. INDICATEURS CONDITIONS DE VIE
# ============================================================
# Valeurs de source_eau du formulaire :
# "Robinet maison", "Robinet cour", "Borne fontaine", "Puits", "Eau en sachet"
EAU_POTABLE = {"Robinet maison", "Robinet cour", "Borne fontaine"}

# Valeurs de type_toilettes :
# "WC avec chasse", "Latrine améliorée", "Latrine simple", "Aucune"
TOILETTES_AMELIOREES = {"WC avec chasse", "Latrine améliorée"}

# Valeurs de source_eclairage :
# "Électricité (CIE)", "Solaire", "Lampe à pétrole", "Bougie", "Aucune"
ELECTRICITE = {"Électricité (CIE)", "Solaire"}


def acces_eau_potable(df_menages: pd.DataFrame) -> float:
    if df_menages.empty:
        return 0.0
    nb = df_menages["source_eau"].isin(EAU_POTABLE).sum()
    return _pct(nb, len(df_menages))


def assainissement_ameliore(df_menages: pd.DataFrame) -> float:
    if df_menages.empty:
        return 0.0
    nb = df_menages["type_toilettes"].isin(TOILETTES_AMELIOREES).sum()
    return _pct(nb, len(df_menages))


def acces_electricite(df_menages: pd.DataFrame) -> float:
    if df_menages.empty:
        return 0.0
    nb = df_menages["source_eclairage"].isin(ELECTRICITE).sum()
    return _pct(nb, len(df_menages))


def indice_promiscuite(df_menages: pd.DataFrame,
                        df_membres: pd.DataFrame) -> float:
    """Nombre moyen de personnes par pièce du logement."""
    if df_menages.empty or df_membres.empty:
        return 0.0
    par_menage = df_membres.groupby("id_menage").size().rename("nb_membres")
    fusion = df_menages[["id_menage", "nombre_pieces"]].merge(
        par_menage, left_on="id_menage", right_index=True, how="left"
    )
    fusion["nb_membres"] = fusion["nb_membres"].fillna(0)
    fusion = fusion[fusion["nombre_pieces"] > 0]
    if fusion.empty:
        return 0.0
    ratios = fusion["nb_membres"] / fusion["nombre_pieces"]
    return round(ratios.mean(), 1)


def alphabetisation_adultes(df_membres: pd.DataFrame) -> float:
    """% des 15+ qui savent lire et écrire (sait_lire_ecrire == 'Oui')."""
    adultes = _adultes_15_plus(df_membres)
    if adultes.empty:
        return 0.0
    nb = (adultes["sait_lire_ecrire"] == "Oui").sum()
    return _pct(nb, len(adultes))


def scolarisation_6_15(df_membres: pd.DataFrame) -> float:
    """
    % des enfants 6-15 ans qui ont un niveau d'instruction non nul.
    Approximation : niveau_instruction != "Aucun" → considéré scolarisé.
    """
    if df_membres.empty:
        return 0.0
    ages = _ages(df_membres)
    enfants = df_membres[(ages >= 6) & (ages <= 15)]
    if enfants.empty:
        return 0.0
    nb = (enfants["niveau_instruction"] != "Aucun").sum()
    return _pct(nb, len(enfants))


# ============================================================
# CALCUL PAR TERRITOIRE (utilisé par la page Comparer)
# ============================================================
def calculer_par_commune(df_menages: pd.DataFrame,
                          df_membres: pd.DataFrame) -> dict:
    """
    Calcule les 18 indicateurs pour chaque commune séparément, plus
    une ligne "Abidjan" qui donne la moyenne globale (référence).
    """
    # 1. Métadonnées des 18 indicateurs
    global_calc = calculer_tous_indicateurs(df_menages, df_membres)
    metadonnees = []
    for theme, cartes in global_calc.items():
        for c in cartes:
            metadonnees.append({
                "cle": c["cle"],
                "label": c["label"],
                "unite": c["unite"],
                "theme": theme,
                "icone": c["icone"],
            })

    # 2. Ligne "Abidjan (ensemble)" — moyenne globale
    territoires = []
    territoires.append({
        "id": 0,
        "nom": "Abidjan (ensemble)",
        "slug": "abidjan",
        "type": "ensemble",
        "nb_menages": len(df_menages),
        "nb_membres": len(df_membres),
        "valeurs": {c["cle"]: c["valeur"]
                    for theme in global_calc.values()
                    for c in theme},
    })

    # 3. Une ligne par commune
    if "id_commune" in df_menages.columns:
        ids_communes = sorted(df_menages["id_commune"].unique())
        for id_c in ids_communes:
            df_men_c = df_menages[df_menages["id_commune"] == id_c]
            ids_men = df_men_c["id_menage"].tolist()
            df_mem_c = df_membres[df_membres["id_menage"].isin(ids_men)]

            if df_men_c.empty:
                continue

            ligne = df_men_c.iloc[0]
            calc_c = calculer_tous_indicateurs(df_men_c, df_mem_c)

            # Le slug et le type viennent de get_communes(),
            # qu'on doit éventuellement enrichir.
            # Si pas dispo dans df_menages, on met des valeurs par défaut.
            slug_commune = ligne.get("commune_slug",
                                       ligne["commune"].lower().replace(" ", "-"))
            type_commune = ligne.get("commune_type", "commune_urbaine")

            territoires.append({
                "id": int(id_c),
                "nom": ligne["commune"],
                "slug": slug_commune,
                "type": type_commune,
                "nb_menages": len(df_men_c),
                "nb_membres": len(df_mem_c),
                "valeurs": {c["cle"]: c["valeur"]
                            for theme in calc_c.values()
                            for c in theme},
            })

    # Tri alphabétique des communes (Abidjan reste en tête)
    abidjan = territoires[0]
    autres = sorted(territoires[1:], key=lambda t: t["nom"])
    territoires = [abidjan] + autres

    return {
        "indicateurs": metadonnees,
        "territoires": territoires,
    }


# ============================================================
# CALCUL DES STATS SIMPLES PAR QUARTIER (pour le pop-up)
# ============================================================
def calculer_stats_quartier(df_menages: pd.DataFrame,
                              df_membres: pd.DataFrame,
                              id_commune: int,
                              nom_quartier: str) -> dict:
    """
    Calcule des statistiques descriptives simples pour un quartier précis.
    """
    df_men_q = df_menages[
        (df_menages["id_commune"] == id_commune) &
        (df_menages["quartier"] == nom_quartier)
    ]

    if df_men_q.empty:
        return {
            "nom": nom_quartier,
            "commune": "",
            "volumetrie": {
                "nb_menages": 0,
                "nb_personnes": 0,
                "taille_moyenne": 0,
            },
            "composition": {
                "ratio_masculinite": 0,
                "age_median": 0,
                "part_moins_15": 0,
            },
        }

    ids_men = df_men_q["id_menage"].tolist()
    df_mem_q = df_membres[df_membres["id_menage"].isin(ids_men)]

    nom_commune = df_men_q.iloc[0]["commune"]

    nb_men = len(df_men_q)
    nb_pers = len(df_mem_q)
    taille_moy = round(nb_pers / nb_men, 1) if nb_men else 0

    if df_mem_q.empty:
        ratio_masc = 0
        age_med = 0
        part_15 = 0
    else:
        ages = _ages(df_mem_q)
        nb_h = (df_mem_q["sexe"] == "Masculin").sum()
        nb_f = (df_mem_q["sexe"] == "Féminin").sum()
        ratio_masc = round(nb_h / nb_f * 100) if nb_f > 0 else 0
        age_med = int(ages.median())
        part_15 = _pct((ages < 15).sum(), len(ages))

    return {
        "nom": nom_quartier,
        "commune": nom_commune,
        "volumetrie": {
            "nb_menages": int(nb_men),
            "nb_personnes": int(nb_pers),
            "taille_moyenne": taille_moy,
        },
        "composition": {
            "ratio_masculinite": ratio_masc,
            "age_median": age_med,
            "part_moins_15": part_15,
        },
    }


# ============================================================
# CALCUL GROUPÉ DES 18 INDICATEURS
# ============================================================
def calculer_tous_indicateurs(df_menages: pd.DataFrame,
                               df_membres: pd.DataFrame) -> dict:
    """Calcule les 18 indicateurs structurés pour l'affichage en onglets."""
    nb_men = len(df_menages)

    return {
        "demographie": [
            {"cle": "population", "label": "Population recensée",
             "valeur": population_recensee(df_membres),
             "unite": "", "icone": "users",
             "meta": f"Sur {nb_men} ménages"},
            {"cle": "taille_moyenne", "label": "Taille moyenne des ménages",
             "valeur": taille_moyenne_menages(df_menages, df_membres),
             "unite": "pers.", "icone": "home",
             "meta": "Personnes par foyer"},
            {"cle": "ratio_dependance", "label": "Ratio de dépendance",
             "valeur": ratio_dependance(df_membres),
             "unite": "%", "icone": "balance",
             "meta": "Jeunes + âgés / 15-64 ans"},
            {"cle": "moins_15", "label": "Part des moins de 15 ans",
             "valeur": part_moins_15_ans(df_membres),
             "unite": "%", "icone": "child",
             "meta": "De la population totale"},
            {"cle": "masculinite", "label": "Ratio de masculinité",
             "valeur": ratio_masculinite(df_membres),
             "unite": "", "icone": "gender",
             "meta": "Hommes pour 100 femmes"},
            {"cle": "menages_femmes", "label": "Ménages dirigés par une femme",
             "valeur": part_menages_diriges_femme(df_membres, df_menages),
             "unite": "%", "icone": "leader",
             "meta": "Du total des ménages"},
        ],
        "economie": [
            {"cle": "taux_activite", "label": "Taux d'activité (15+)",
             "valeur": taux_activite(df_membres),
             "unite": "%", "icone": "activity",
             "meta": "Actifs sur population 15+"},
            {"cle": "taux_chomage", "label": "Taux de chômage",
             "valeur": taux_chomage(df_membres),
             "unite": "%", "icone": "briefcase",
             "meta": "Chômeurs sur actifs"},
            {"cle": "informel", "label": "Part dans l'informel",
             "valeur": part_informel(df_membres),
             "unite": "%", "icone": "store",
             "meta": "Des actifs occupés"},
            {"cle": "salaries", "label": "Part des salariés",
             "valeur": part_salaries(df_membres),
             "unite": "%", "icone": "salary",
             "meta": "Public + privé / actifs occupés"},
            {"cle": "numerique", "label": "Équipement numérique",
             "valeur": equipement_numerique(df_menages),
             "unite": "%", "icone": "device",
             "meta": "Smartphone ou ordinateur"},
            {"cle": "richesse", "label": "Indice de richesse médian",
             "valeur": indice_richesse_median(df_menages),
             "unite": "/ 8", "icone": "wealth",
             "meta": "Score sur 8 biens durables"},
        ],
        "conditions": [
            {"cle": "eau", "label": "Accès à l'eau potable",
             "valeur": acces_eau_potable(df_menages),
             "unite": "%", "icone": "water",
             "meta": "Source améliorée — ODD 6.1"},
            {"cle": "assainissement", "label": "Assainissement amélioré",
             "valeur": assainissement_ameliore(df_menages),
             "unite": "%", "icone": "sanitation",
             "meta": "Toilettes améliorées — ODD 6.2"},
            {"cle": "electricite", "label": "Accès à l'électricité",
             "valeur": acces_electricite(df_menages),
             "unite": "%", "icone": "lightning",
             "meta": "Réseau ou solaire — ODD 7.1"},
            {"cle": "promiscuite", "label": "Indice de promiscuité",
             "valeur": indice_promiscuite(df_menages, df_membres),
             "unite": "pers./pièce", "icone": "rooms",
             "meta": "Personnes par pièce d'habitation"},
            {"cle": "alphabetisation", "label": "Alphabétisation des adultes",
             "valeur": alphabetisation_adultes(df_membres),
             "unite": "%", "icone": "book",
             "meta": "Sait lire et écrire (15+)"},
            {"cle": "scolarisation", "label": "Scolarisation des 6-15 ans",
             "valeur": scolarisation_6_15(df_membres),
             "unite": "%", "icone": "school",
             "meta": "Enfants en âge scolaire"},
        ],
    }


# ============================================================
# TEST RAPIDE
# ============================================================
if __name__ == "__main__":
    from app.data import get_menages, get_membres

    df_men = pd.DataFrame(get_menages())
    df_mem = pd.DataFrame(get_membres())

    indicateurs = calculer_tous_indicateurs(df_men, df_mem)

    for theme, cartes in indicateurs.items():
        print(f"\n=== {theme.upper()} ===")
        for c in cartes:
            unite = c["unite"]
            print(f"  {c['label']:.<40} {c['valeur']} {unite}")