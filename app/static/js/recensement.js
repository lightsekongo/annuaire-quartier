/**
 * Page Recensement — Liste des ménages
 *
 * Gère :
 *  - La recherche en temps réel (filtre client-side sur le nom du ménage)
 *  - Les filtres commune / quartier (avec sélecteur dépendant)
 *  - Le bouton "effacer la recherche"
 *  - La mise à jour dynamique du compteur
 *
 * Les filtres commune/quartier déclenchent une navigation serveur
 * (URL avec paramètres GET) pour conserver l'état dans l'URL.
 * Seule la recherche par nom se fait entièrement côté client.
 */

(function () {
    'use strict';

    const DATA = window.RECENSEMENT_DATA || {};
    const quartiersParCommune = DATA.quartiers_par_commune || {};

    // ============================================================
    // 1. RECHERCHE EN TEMPS RÉEL
    // ============================================================
    const inputRecherche = document.getElementById('recherche-menage');
    const btnEffacer = document.getElementById('effacer-recherche');
    const compteur = document.getElementById('compteur-resultats');
    const cartes = document.querySelectorAll('.menage-card');

    function filtrerCartes() {
        if (!inputRecherche) return;
        const terme = inputRecherche.value.trim().toLowerCase();
        let visibles = 0;

        cartes.forEach(carte => {
            const nom = carte.dataset.nom || '';
            const match = !terme || nom.includes(terme);

            if (match) {
                carte.classList.remove('is-hidden');
                visibles++;
            } else {
                carte.classList.add('is-hidden');
            }
        });

        // Met à jour le compteur
        if (compteur) {
            compteur.textContent = visibles;
        }
    }

    if (inputRecherche) {
        // Debounce simple pour ne pas spammer à chaque touche
        let timer;
        inputRecherche.addEventListener('input', () => {
            clearTimeout(timer);
            timer = setTimeout(filtrerCartes, 120);
        });

        // Touche Échap pour vider
        inputRecherche.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                inputRecherche.value = '';
                filtrerCartes();
            }
        });
    }

    // Bouton "✕" pour effacer la recherche
    if (btnEffacer && inputRecherche) {
        btnEffacer.addEventListener('click', () => {
            inputRecherche.value = '';
            filtrerCartes();
            inputRecherche.focus();
        });
    }

    // ============================================================
    // 2. FILTRES COMMUNE / QUARTIER (avec navigation serveur)
    // ============================================================
    const filtreCommune = document.getElementById('filtre-commune');
    const filtreQuartier = document.getElementById('filtre-quartier');

    /**
     * Met à jour les options du sélecteur quartier en fonction
     * de la commune sélectionnée.
     */
    function rafraichirQuartiers(idCommune) {
        if (!filtreQuartier) return;

        // Vide les options actuelles (sauf la première)
        filtreQuartier.innerHTML = '<option value="">Tous les quartiers</option>';

        if (!idCommune) {
            filtreQuartier.disabled = true;
            return;
        }

        const quartiers = quartiersParCommune[idCommune] || [];
        if (quartiers.length === 0) {
            filtreQuartier.disabled = true;
            return;
        }

        quartiers.forEach(nom => {
            const opt = document.createElement('option');
            opt.value = nom;
            opt.textContent = nom;
            filtreQuartier.appendChild(opt);
        });

        filtreQuartier.disabled = false;
    }

    /**
     * Construit l'URL avec les paramètres et navigue dessus.
     */
    function appliquerFiltres() {
        const params = new URLSearchParams();
        const q = inputRecherche ? inputRecherche.value.trim() : '';
        const commune = filtreCommune ? filtreCommune.value : '';
        const quartier = filtreQuartier ? filtreQuartier.value : '';

        if (q) params.set('q', q);
        if (commune) params.set('commune', commune);
        if (quartier) params.set('quartier', quartier);

        const url = window.location.pathname + (params.toString() ? '?' + params.toString() : '');
        window.location.href = url;
    }

    if (filtreCommune) {
        filtreCommune.addEventListener('change', () => {
            // Réinitialise le quartier quand on change de commune
            rafraichirQuartiers(filtreCommune.value);
            appliquerFiltres();
        });
    }

    if (filtreQuartier) {
        filtreQuartier.addEventListener('change', appliquerFiltres);
    }
})();