/**
 * Fiche imprimable — Pyramide des âges SVG + sélecteur territoire
 *
 * La pyramide est dessinée en SVG natif (pas Chart.js) car le SVG
 * est mieux préservé à l'impression et au rendu PDF.
 */

(function () {
    'use strict';

    const DATA = window.FICHE_DATA || {};
    const pyramide = DATA.pyramide || { tranches: [], hommes: [], femmes: [] };

    // ============================================================
    // 1. PYRAMIDE DES ÂGES (SVG inline)
    // ============================================================
    function dessinerPyramide() {
        const container = document.getElementById('pyramide-container');
        if (!container) return;
        if (pyramide.tranches.length === 0) return;

        // Calcul de l'échelle : on prend la valeur max de toutes les barres
        const maxVal = Math.max(
            ...pyramide.hommes,
            ...pyramide.femmes,
            1  // évite la division par 0
        );

        // Configuration du SVG
        const w = 600;        // largeur totale
        const h = 220;        // hauteur totale
        const padding = { top: 20, right: 20, bottom: 30, left: 20 };
        const labelWidth = 50; // espace pour les labels d'âge au centre
        const barAreaWidth = (w - padding.left - padding.right - labelWidth) / 2;
        const nbTranches = pyramide.tranches.length;
        const barHeight = (h - padding.top - padding.bottom) / nbTranches;
        const barGap = 4;
        const realBarHeight = barHeight - barGap;

        // Construit le SVG
        const svgNS = 'http://www.w3.org/2000/svg';
        const svg = document.createElementNS(svgNS, 'svg');
        svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
        svg.setAttribute('xmlns', svgNS);
        svg.setAttribute('role', 'img');
        svg.setAttribute('aria-label', 'Pyramide des âges');

        const centerX = padding.left + barAreaWidth;
        const labelCenterX = centerX + labelWidth / 2;

        pyramide.tranches.forEach((tranche, i) => {
            const y = padding.top + i * barHeight;
            const cy = y + realBarHeight / 2;

            // Hommes (à gauche, bleu)
            const wH = (pyramide.hommes[i] / maxVal) * barAreaWidth;
            const rectH = document.createElementNS(svgNS, 'rect');
            rectH.setAttribute('x', centerX - wH);
            rectH.setAttribute('y', y);
            rectH.setAttribute('width', wH);
            rectH.setAttribute('height', realBarHeight);
            rectH.setAttribute('fill', '#1d4ed8');
            rectH.setAttribute('rx', '2');
            svg.appendChild(rectH);

            // Étiquette du compte H (à l'extrémité gauche de la barre)
            if (pyramide.hommes[i] > 0) {
                const textH = document.createElementNS(svgNS, 'text');
                textH.setAttribute('x', centerX - wH - 4);
                textH.setAttribute('y', cy);
                textH.setAttribute('dominant-baseline', 'middle');
                textH.setAttribute('text-anchor', 'end');
                textH.setAttribute('font-size', '11');
                textH.setAttribute('font-family', 'Outfit, sans-serif');
                textH.setAttribute('font-weight', '600');
                textH.setAttribute('fill', '#1d4ed8');
                textH.textContent = pyramide.hommes[i];
                svg.appendChild(textH);
            }

            // Femmes (à droite, rose)
            const wF = (pyramide.femmes[i] / maxVal) * barAreaWidth;
            const rectF = document.createElementNS(svgNS, 'rect');
            rectF.setAttribute('x', centerX + labelWidth);
            rectF.setAttribute('y', y);
            rectF.setAttribute('width', wF);
            rectF.setAttribute('height', realBarHeight);
            rectF.setAttribute('fill', '#db2777');
            rectF.setAttribute('rx', '2');
            svg.appendChild(rectF);

            // Étiquette du compte F (à l'extrémité droite de la barre)
            if (pyramide.femmes[i] > 0) {
                const textF = document.createElementNS(svgNS, 'text');
                textF.setAttribute('x', centerX + labelWidth + wF + 4);
                textF.setAttribute('y', cy);
                textF.setAttribute('dominant-baseline', 'middle');
                textF.setAttribute('text-anchor', 'start');
                textF.setAttribute('font-size', '11');
                textF.setAttribute('font-family', 'Outfit, sans-serif');
                textF.setAttribute('font-weight', '600');
                textF.setAttribute('fill', '#db2777');
                textF.textContent = pyramide.femmes[i];
                svg.appendChild(textF);
            }

            // Label de tranche d'âge au centre
            const textT = document.createElementNS(svgNS, 'text');
            textT.setAttribute('x', labelCenterX);
            textT.setAttribute('y', cy);
            textT.setAttribute('dominant-baseline', 'middle');
            textT.setAttribute('text-anchor', 'middle');
            textT.setAttribute('font-size', '11');
            textT.setAttribute('font-family', 'Outfit, sans-serif');
            textT.setAttribute('font-weight', '600');
            textT.setAttribute('fill', '#3f3f46');
            textT.textContent = tranche;
            svg.appendChild(textT);
        });

        // Légende (en bas)
        const legendY = h - 10;

        // Carré Hommes
        const legHRect = document.createElementNS(svgNS, 'rect');
        legHRect.setAttribute('x', padding.left + 40);
        legHRect.setAttribute('y', legendY - 8);
        legHRect.setAttribute('width', '10');
        legHRect.setAttribute('height', '10');
        legHRect.setAttribute('fill', '#1d4ed8');
        legHRect.setAttribute('rx', '2');
        svg.appendChild(legHRect);

        const legHText = document.createElementNS(svgNS, 'text');
        legHText.setAttribute('x', padding.left + 55);
        legHText.setAttribute('y', legendY);
        legHText.setAttribute('font-size', '11');
        legHText.setAttribute('font-family', 'Outfit, sans-serif');
        legHText.setAttribute('font-weight', '500');
        legHText.setAttribute('fill', '#3f3f46');
        legHText.textContent = 'Hommes';
        svg.appendChild(legHText);

        // Carré Femmes
        const legFRect = document.createElementNS(svgNS, 'rect');
        legFRect.setAttribute('x', w - padding.right - 80);
        legFRect.setAttribute('y', legendY - 8);
        legFRect.setAttribute('width', '10');
        legFRect.setAttribute('height', '10');
        legFRect.setAttribute('fill', '#db2777');
        legFRect.setAttribute('rx', '2');
        svg.appendChild(legFRect);

        const legFText = document.createElementNS(svgNS, 'text');
        legFText.setAttribute('x', w - padding.right - 65);
        legFText.setAttribute('y', legendY);
        legFText.setAttribute('font-size', '11');
        legFText.setAttribute('font-family', 'Outfit, sans-serif');
        legFText.setAttribute('font-weight', '500');
        legFText.setAttribute('fill', '#3f3f46');
        legFText.textContent = 'Femmes';
        svg.appendChild(legFText);

        container.appendChild(svg);
    }

    // ============================================================
    // 2. SÉLECTEUR DE TERRITOIRE
    // ============================================================
    const select = document.getElementById('select-territoire');
    if (select) {
        select.addEventListener('change', () => {
            const slug = select.value;
            if (slug === 'abidjan' || !slug) {
                window.location.href = '/fiche-imprimable';
            } else {
                window.location.href = '/fiche-imprimable?commune=' + encodeURIComponent(slug);
            }
        });
    }

    // ============================================================
    // 3. BOUTON D'IMPRESSION
    // ============================================================
    const btn = document.getElementById('btn-imprimer');
    if (btn) {
        btn.addEventListener('click', () => {
            window.print();
        });
    }

    // Lance le rendu au chargement
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', dessinerPyramide);
    } else {
        dessinerPyramide();
    }
})();