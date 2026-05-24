/**
 * Formulaire ménage — Sélecteur dépendant commune → quartier
 *
 * Quand l'utilisateur change la commune dans le formulaire,
 * la liste des quartiers se met à jour automatiquement.
 * Si on est en mode édition, on préselectionne le quartier actuel.
 */

(function () {
    'use strict';

    const DATA = window.FORMULAIRE_DATA || {};
    const quartiersParCommune = DATA.quartiers_par_commune || {};
    const quartierInitial = DATA.quartier_initial || '';

    const selectCommune = document.getElementById('id_commune');
    const selectQuartier = document.getElementById('quartier');

    if (!selectCommune || !selectQuartier) return;

    /**
     * Remplit le sélecteur quartier selon la commune choisie.
     * @param {string} quartierSelectionne - nom du quartier à présélectionner
     */
    function remplirQuartiers(quartierSelectionne) {
        const idCommune = selectCommune.value;

        // Vide les options
        selectQuartier.innerHTML = '';

        if (!idCommune) {
            selectQuartier.innerHTML =
                '<option value="">— Choisir d\'abord une commune —</option>';
            selectQuartier.disabled = true;
            return;
        }

        const quartiers = quartiersParCommune[idCommune] || [];

        if (quartiers.length === 0) {
            selectQuartier.innerHTML =
                '<option value="">— Aucun quartier disponible —</option>';
            selectQuartier.disabled = true;
            return;
        }

        // Option par défaut
        const optDefaut = document.createElement('option');
        optDefaut.value = '';
        optDefaut.textContent = '— Choisir un quartier —';
        selectQuartier.appendChild(optDefaut);

        // Options des quartiers
        quartiers.forEach(nom => {
            const opt = document.createElement('option');
            opt.value = nom;
            opt.textContent = nom;
            if (nom === quartierSelectionne) {
                opt.selected = true;
            }
            selectQuartier.appendChild(opt);
        });

        selectQuartier.disabled = false;
    }

    // Au changement de commune, on rafraîchit les quartiers
    selectCommune.addEventListener('change', () => {
        remplirQuartiers('');  // pas de quartier préselectionné en cas de changement
    });

    // Au chargement initial : si une commune est déjà sélectionnée
    // (mode édition ou re-soumission après erreur), on remplit
    if (selectCommune.value) {
        remplirQuartiers(quartierInitial);
    }
})();