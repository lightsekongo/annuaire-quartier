/**
 * Page Comparer — interactions
 *
 * 1. Mode classement : positionne la ligne pointillée "moyenne d'Abidjan"
 *    et anime les barres à l'arrivée
 * 2. Mode comparaison directe : compteur dynamique de territoires
 *    sélectionnés + limite à 4
 */

(function () {
    'use strict';

    // ============================================================
    // 1. CLASSEMENT — POSITION DE LA LIGNE DE RÉFÉRENCE
    // ============================================================
    /**
     * La ligne pointillée "moyenne d'Abidjan" doit être placée précisément
     * au-dessus des barres, à la position correspondant à la valeur de
     * la moyenne. Comme les barres sont dans une grille avec d'autres
     * colonnes (rang, nom, valeur), on ne peut pas se baser sur un
     * pourcentage de la largeur totale du conteneur.
     *
     * Solution : calculer la position en pixels en se basant sur la
     * largeur réelle d'une .ranking-bar-wrap au moment du rendu.
     */
    function placerLigneReference() {
        const chart = document.querySelector('.ranking-chart');
        if (!chart) return;

        const refPos = parseFloat(chart.dataset.refPos);
        if (isNaN(refPos)) return;

        const refLine = chart.querySelector('.ranking-ref-line');
        const firstBarWrap = chart.querySelector('.ranking-bar-wrap');
        if (!refLine || !firstBarWrap) return;

        // Calcule la position de la zone des barres dans le conteneur
        const chartRect = chart.getBoundingClientRect();
        const barRect = firstBarWrap.getBoundingClientRect();

        const offsetLeft = barRect.left - chartRect.left;
        const barWidth = barRect.width;

        // Position absolue de la ligne en pixels depuis le bord gauche du chart
        const positionPx = offsetLeft + (barWidth * refPos / 100);

        // On applique en utilisant les propriétés directement
        // (et on retire les styles parasites du CSS qui essayaient un calcul approximatif)
        refLine.style.left = positionPx + 'px';
        refLine.style.marginLeft = '0';
        refLine.style.width = '2px';

        // Le label "Abidjan" reste dans la ligne, donc déjà bien positionné
        const label = refLine.querySelector('.ranking-ref-line-label');
        if (label) {
            label.style.left = '0';
            label.style.transform = 'translateX(-50%)';
        }
    }

    // ============================================================
    // 2. CLASSEMENT — ANIMATION DES BARRES À L'ARRIVÉE
    // ============================================================
    function animerBarresClassement() {
        const bars = document.querySelectorAll('.ranking-bar');
        bars.forEach((bar, i) => {
            const target = bar.style.width;
            // Réinitialise à 0
            bar.style.width = '0';
            // Petit décalage en cascade pour effet de flux
            setTimeout(() => {
                bar.style.width = target;
            }, 100 + i * 60);
        });
    }

    // ============================================================
    // 3. COMPARAISON DIRECTE — ANIMATION DES MINI-BARRES
    // ============================================================
    function animerBarresComparaison() {
        const fills = document.querySelectorAll('.ct-cell-fill');
        fills.forEach((fill, i) => {
            const target = fill.style.width;
            fill.style.width = '0';
            setTimeout(() => {
                fill.style.width = target;
            }, 200 + i * 15);
        });
    }

    // ============================================================
    // 4. COMPARAISON DIRECTE — GESTION DES SÉLECTIONS
    // ============================================================
    function gererSelectionTerritoires() {
        const form = document.getElementById('territory-form');
        if (!form) return;

        const checkboxes = form.querySelectorAll('input[type="checkbox"]');
        const counter = form.querySelector('[data-counter]');
        const submitBtn = form.querySelector('button[type="submit"]');

        function actualiserCompteur() {
            const cochees = form.querySelectorAll('input[type="checkbox"]:checked');
            const nb = cochees.length;

            // Met à jour le label visuel "X / 4 sélectionnés"
            if (counter) {
                counter.textContent = `${nb} / 4 sélectionné${nb > 1 ? 's' : ''}`;
                counter.classList.toggle('territory-counter-warning',
                                          nb < 2 || nb > 4);
            }

            // Désactive les autres cases si on atteint 4
            checkboxes.forEach(cb => {
                const chip = cb.closest('.territory-chip');
                if (!cb.checked && nb >= 4) {
                    cb.disabled = true;
                    chip.style.opacity = '0.4';
                    chip.style.cursor = 'not-allowed';
                } else {
                    cb.disabled = false;
                    chip.style.opacity = '';
                    chip.style.cursor = 'pointer';
                }
            });

            // Désactive le bouton si moins de 2 sélectionnés
            if (submitBtn) {
                submitBtn.disabled = nb < 2;
                submitBtn.style.opacity = nb < 2 ? '0.5' : '';
                submitBtn.style.cursor = nb < 2 ? 'not-allowed' : '';
            }

            // Met à jour la classe visuelle des chips
            checkboxes.forEach(cb => {
                const chip = cb.closest('.territory-chip');
                if (chip) {
                    chip.classList.toggle('territory-chip-active', cb.checked);
                }
            });
        }

        // Branche les événements
        checkboxes.forEach(cb => {
            cb.addEventListener('change', actualiserCompteur);
        });

        // État initial
        actualiserCompteur();
    }

    // ============================================================
    // 5. INITIALISATION
    // ============================================================
    function init() {
        // Détecte le mode (présence des éléments propres à chaque vue)
        if (document.querySelector('.ranking-chart')) {
            // Mode classement
            placerLigneReference();
            animerBarresClassement();
            // Repositionne la ligne au resize
            window.addEventListener('resize', placerLigneReference);
        }

        if (document.querySelector('#territory-form')) {
            // Mode comparaison directe
            gererSelectionTerritoires();
            animerBarresComparaison();
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();