/**
 * Page Explorer — Atelier de visualisation libre
 *
 * Logique : à chaque changement de sélecteur,
 *   1. Filtrer le dataset selon les filtres actifs
 *   2. Déterminer le type de graphique selon les variables choisies
 *   3. Calculer les données agrégées
 *   4. Dessiner le graphique Chart.js + remplir le tableau
 */

(function () {
    'use strict';

    // ============================================================
    // 0. CONSTANTES & ÉTAT GLOBAL
    // ============================================================
    const DATA = window.EXPLORER_DATA || {};
    const DATASET = DATA.dataset || [];
    const VARIABLES = DATA.variables || [];

    // Index des variables par clé pour accès rapide
    const VAR_INDEX = {};
    VARIABLES.forEach(v => { VAR_INDEX[v.cle] = v; });

    // Palette de couleurs cohérente avec le reste du site
    const PALETTE = [
        '#1d4ed8', '#7c3aed', '#db2777', '#ea580c',
        '#ca8a04', '#16a34a', '#0891b2', '#4f46e5',
        '#be123c', '#15803d', '#a16207', '#9333ea'
    ];
    const BRAND = '#1d4ed8';
    const PINK = '#db2777';
    const FONT = "'Outfit', sans-serif";

    // Configuration Chart.js globale
    if (typeof Chart !== 'undefined') {
        Chart.defaults.font.family = FONT;
        Chart.defaults.color = '#71717a';
    }

    // Instance Chart.js courante (pour pouvoir la détruire avant de redessiner)
    let chartInstance = null;

    // ============================================================
    // 1. FILTRAGE DU DATASET
    // ============================================================
    function appliquerFiltres(dataset) {
        const commune = document.getElementById('filtre-commune').value;
        const sexe = document.getElementById('filtre-sexe').value;
        const trancheAge = document.getElementById('filtre-age').value;

        return dataset.filter(row => {
            if (commune && row.commune !== commune) return false;
            if (sexe && row.sexe !== sexe) return false;
            if (trancheAge && row.tranche_age !== trancheAge) return false;
            return true;
        });
    }

    // ============================================================
    // 2. AGRÉGATION
    // ============================================================

    /**
     * Comptage simple d'une variable qualitative.
     * Renvoie : [{label: 'Masculin', count: 230}, ...]
     */
    function agregerQualitatif(dataset, cleVar) {
        const variable = VAR_INDEX[cleVar];
        const compteur = {};

        dataset.forEach(row => {
            const val = row[cleVar];
            if (val !== null && val !== undefined && val !== '') {
                compteur[val] = (compteur[val] || 0) + 1;
            }
        });

        // Si la variable a un ordre prédéfini (options), on l'utilise
        let labels;
        if (variable.options) {
            labels = variable.options.filter(opt => compteur[opt] !== undefined);
            // Ajoute les valeurs hors options à la fin
            Object.keys(compteur).forEach(k => {
                if (!labels.includes(k)) labels.push(k);
            });
        } else {
            labels = Object.keys(compteur).sort();
        }

        return labels.map(label => ({
            label: label,
            count: compteur[label] || 0
        }));
    }

    /**
     * Tableau croisé qualitatif × qualitatif.
     * Renvoie une matrice : { rows: [...], cols: [...], data: {row -> col -> count} }
     */
    function agregerCroiseQualQual(dataset, cleVar1, cleVar2) {
        const var1 = VAR_INDEX[cleVar1];
        const var2 = VAR_INDEX[cleVar2];
        const matrice = {};

        dataset.forEach(row => {
            const v1 = row[cleVar1];
            const v2 = row[cleVar2];
            if (!v1 || !v2) return;

            if (!matrice[v1]) matrice[v1] = {};
            matrice[v1][v2] = (matrice[v1][v2] || 0) + 1;
        });

        // Ordonne les modalités selon les options si disponibles
        const ordonner = (clesPresentes, options) => {
            if (!options) return clesPresentes.sort();
            const ordonnes = options.filter(o => clesPresentes.includes(o));
            clesPresentes.forEach(k => {
                if (!ordonnes.includes(k)) ordonnes.push(k);
            });
            return ordonnes;
        };

        const rows = ordonner(Object.keys(matrice), var1.options);
        const colsSet = new Set();
        rows.forEach(r => Object.keys(matrice[r]).forEach(c => colsSet.add(c)));
        const cols = ordonner(Array.from(colsSet), var2.options);

        return { rows, cols, matrice };
    }

    /**
     * Histogramme — variable quantitative.
     * Découpe en classes égales (règle de Sturges adaptée).
     */
    function agregerQuantitatif(dataset, cleVar) {
        const valeurs = dataset
            .map(r => r[cleVar])
            .filter(v => v !== null && v !== undefined && !isNaN(v));

        if (valeurs.length === 0) {
            return { classes: [], counts: [], stats: null };
        }

        const min = Math.min(...valeurs);
        const max = Math.max(...valeurs);

        // Cas particulier : valeurs entières petites (nombre de pièces, biens)
        const tousEntiers = valeurs.every(v => Number.isInteger(v));
        const etendue = max - min;

        let bornes;
        if (tousEntiers && etendue <= 12) {
            // Une classe par valeur entière
            bornes = [];
            for (let v = min; v <= max + 1; v++) bornes.push(v);
        } else {
            // Règle de Sturges : nb_classes ≈ 1 + log2(n)
            const nbClasses = Math.min(
                Math.max(5, Math.ceil(1 + Math.log2(valeurs.length))),
                12
            );
            const largeur = etendue / nbClasses;
            bornes = [];
            for (let i = 0; i <= nbClasses; i++) {
                bornes.push(min + i * largeur);
            }
        }

        // Compte par classe
        const counts = new Array(bornes.length - 1).fill(0);
        valeurs.forEach(v => {
            for (let i = 0; i < bornes.length - 1; i++) {
                if (v >= bornes[i] && (v < bornes[i + 1] || i === bornes.length - 2)) {
                    counts[i]++;
                    break;
                }
            }
        });

        // Labels des classes
        const classes = [];
        for (let i = 0; i < bornes.length - 1; i++) {
            if (tousEntiers && etendue <= 12) {
                classes.push(String(bornes[i]));
            } else {
                classes.push(
                    bornes[i].toFixed(1) + ' – ' + bornes[i + 1].toFixed(1)
                );
            }
        }

        // Statistiques descriptives
        const triees = [...valeurs].sort((a, b) => a - b);
        const moyenne = valeurs.reduce((s, v) => s + v, 0) / valeurs.length;
        const mediane = triees[Math.floor(triees.length / 2)];

        return {
            classes, counts,
            stats: {
                n: valeurs.length,
                min: min, max: max,
                moyenne: moyenne.toFixed(2),
                mediane: mediane
            }
        };
    }

    /**
     * Moyenne d'une variable quantitative par groupe qualitatif.
     */
    function agregerMoyenneParGroupe(dataset, cleQual, cleQuant) {
        const variable = VAR_INDEX[cleQual];
        const groupes = {};

        dataset.forEach(row => {
            const cle = row[cleQual];
            const val = row[cleQuant];
            if (!cle || val === null || val === undefined || isNaN(val)) return;

            if (!groupes[cle]) groupes[cle] = [];
            groupes[cle].push(val);
        });

        let labels = Object.keys(groupes);
        if (variable.options) {
            labels = variable.options.filter(o => groupes[o]);
            Object.keys(groupes).forEach(k => {
                if (!labels.includes(k)) labels.push(k);
            });
        } else {
            labels.sort();
        }

        return labels.map(label => {
            const vals = groupes[label];
            const moy = vals.reduce((s, v) => s + v, 0) / vals.length;
            return {
                label: label,
                moyenne: moy,
                effectif: vals.length
            };
        });
    }

    /**
     * Nuage de points — deux variables quantitatives.
     */
    function agregerScatter(dataset, cleX, cleY) {
        const points = [];
        dataset.forEach(row => {
            const x = row[cleX];
            const y = row[cleY];
            if (x === null || x === undefined || isNaN(x)) return;
            if (y === null || y === undefined || isNaN(y)) return;
            points.push({ x, y });
        });
        return points;
    }

    // ============================================================
    // 3. DÉCISION DU TYPE DE GRAPHIQUE
    // ============================================================
    function determinerTypeGraphique(cleVar1, cleVar2) {
        const v1 = VAR_INDEX[cleVar1];
        if (!v1) return null;

        if (!cleVar2) {
            // Univarié
            return v1.type === 'quantitative' ? 'histogramme' : 'barres_simples';
        }

        const v2 = VAR_INDEX[cleVar2];
        if (!v2) return null;

        // Bivarié — 4 cas
        if (v1.type === 'qualitative' && v2.type === 'qualitative') {
            return 'barres_groupees';
        }
        if (v1.type === 'qualitative' && v2.type === 'quantitative') {
            return 'moyenne_par_groupe';
        }
        if (v1.type === 'quantitative' && v2.type === 'qualitative') {
            return 'moyenne_par_groupe_inverse';
        }
        // quantitative × quantitative
        return 'nuage_points';
    }

    // ============================================================
    // 4. RENDU CHART.JS + TABLEAU
    // ============================================================
    const LIBELLES_TYPES = {
        'barres_simples':           'Barres',
        'barres_groupees':          'Barres groupées',
        'histogramme':              'Histogramme',
        'moyenne_par_groupe':       'Moyennes par groupe',
        'moyenne_par_groupe_inverse': 'Moyennes par groupe',
        'nuage_points':             'Nuage de points'
    };

    function dessinerGraphique(type, donnees, v1, v2) {
        const ctx = document.getElementById('explorer-chart').getContext('2d');
        if (chartInstance) chartInstance.destroy();

        let config;

        if (type === 'barres_simples') {
            config = {
                type: 'bar',
                data: {
                    labels: donnees.map(d => d.label),
                    datasets: [{
                        label: v1.label,
                        data: donnees.map(d => d.count),
                        backgroundColor: BRAND,
                        borderRadius: 4
                    }]
                },
                options: configBarres(false)
            };
        }
        else if (type === 'barres_groupees') {
            const datasets = donnees.cols.map((col, idx) => ({
                label: col,
                data: donnees.rows.map(r => (donnees.matrice[r] || {})[col] || 0),
                backgroundColor: PALETTE[idx % PALETTE.length],
                borderRadius: 4
            }));
            config = {
                type: 'bar',
                data: { labels: donnees.rows, datasets: datasets },
                options: configBarres(true)
            };
        }
        else if (type === 'histogramme') {
            config = {
                type: 'bar',
                data: {
                    labels: donnees.classes,
                    datasets: [{
                        label: v1.label,
                        data: donnees.counts,
                        backgroundColor: BRAND,
                        borderRadius: 2,
                        barPercentage: 1.0,
                        categoryPercentage: 0.95
                    }]
                },
                options: configBarres(false)
            };
        }
        else if (type === 'moyenne_par_groupe' || type === 'moyenne_par_groupe_inverse') {
            config = {
                type: 'bar',
                data: {
                    labels: donnees.map(d => d.label),
                    datasets: [{
                        label: 'Moyenne',
                        data: donnees.map(d => parseFloat(d.moyenne.toFixed(2))),
                        backgroundColor: PALETTE,
                        borderRadius: 4
                    }]
                },
                options: configBarres(false)
            };
        }
        else if (type === 'nuage_points') {
            config = {
                type: 'scatter',
                data: {
                    datasets: [{
                        label: v1.label + ' × ' + v2.label,
                        data: donnees,
                        backgroundColor: 'rgba(29, 78, 216, 0.55)',
                        borderColor: BRAND,
                        pointRadius: 4
                    }]
                },
                options: configScatter(v1, v2)
            };
        }

        chartInstance = new Chart(ctx, config);
    }

    function configBarres(grouped) {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: grouped,
                    position: 'bottom',
                    labels: { font: { family: FONT, size: 12 }, padding: 12 }
                },
                tooltip: {
                    backgroundColor: 'rgba(24, 24, 27, 0.95)',
                    titleFont: { family: FONT, weight: '700' },
                    bodyFont: { family: FONT },
                    padding: 10,
                    cornerRadius: 6
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { font: { family: FONT, size: 11 }, maxRotation: 35 }
                },
                y: {
                    beginAtZero: true,
                    grid: { color: '#f4f4f5' },
                    ticks: { font: { family: FONT, size: 11 } }
                }
            }
        };
    }

    function configScatter(v1, v2) {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(24, 24, 27, 0.95)',
                    titleFont: { family: FONT, weight: '700' },
                    bodyFont: { family: FONT },
                    padding: 10,
                    cornerRadius: 6,
                    callbacks: {
                        label: (ctx) =>
                            `${v1.label}: ${ctx.parsed.x} · ${v2.label}: ${ctx.parsed.y}`
                    }
                }
            },
            scales: {
                x: {
                    title: { display: true, text: v1.label,
                             font: { family: FONT, size: 12, weight: '600' } },
                    grid: { color: '#f4f4f5' }
                },
                y: {
                    title: { display: true, text: v2.label,
                             font: { family: FONT, size: 12, weight: '600' } },
                    grid: { color: '#f4f4f5' }
                }
            }
        };
    }

    /**
     * Remplit le tableau sous le graphique.
     */
    function remplirTableau(type, donnees, v1, v2) {
        const thead = document.querySelector('#explorer-table thead');
        const tbody = document.querySelector('#explorer-table tbody');
        thead.innerHTML = '';
        tbody.innerHTML = '';

        if (type === 'barres_simples') {
            thead.innerHTML = `
                <tr>
                    <th>${v1.label}</th>
                    <th class="text-right">Effectif</th>
                    <th class="text-right">Part (%)</th>
                </tr>`;
            const total = donnees.reduce((s, d) => s + d.count, 0);
            donnees.forEach(d => {
                const pct = total ? (d.count / total * 100).toFixed(1) : 0;
                tbody.innerHTML += `
                    <tr>
                        <td>${d.label}</td>
                        <td class="text-right">${d.count}</td>
                        <td class="text-right text-muted">${pct} %</td>
                    </tr>`;
            });
        }
        else if (type === 'barres_groupees') {
            let header = `<tr><th>${v1.label}</th>`;
            donnees.cols.forEach(c => { header += `<th class="text-right">${c}</th>`; });
            header += '<th class="text-right">Total</th></tr>';
            thead.innerHTML = header;

            donnees.rows.forEach(r => {
                let row = `<tr><td>${r}</td>`;
                let totalLigne = 0;
                donnees.cols.forEach(c => {
                    const v = (donnees.matrice[r] || {})[c] || 0;
                    row += `<td class="text-right">${v}</td>`;
                    totalLigne += v;
                });
                row += `<td class="text-right text-bold">${totalLigne}</td></tr>`;
                tbody.innerHTML += row;
            });
        }
        else if (type === 'histogramme') {
            thead.innerHTML = `
                <tr>
                    <th>Classe</th>
                    <th class="text-right">Effectif</th>
                </tr>`;
            donnees.classes.forEach((cl, i) => {
                tbody.innerHTML += `
                    <tr>
                        <td>${cl}</td>
                        <td class="text-right">${donnees.counts[i]}</td>
                    </tr>`;
            });
            if (donnees.stats) {
                tbody.innerHTML += `
                    <tr class="explorer-table-stat">
                        <td class="text-bold">Statistiques</td>
                        <td class="text-right text-muted">
                            n=${donnees.stats.n} ·
                            moy=${donnees.stats.moyenne} ·
                            méd=${donnees.stats.mediane} ·
                            min=${donnees.stats.min} ·
                            max=${donnees.stats.max}
                        </td>
                    </tr>`;
            }
        }
        else if (type === 'moyenne_par_groupe' || type === 'moyenne_par_groupe_inverse') {
            const colQual = (type === 'moyenne_par_groupe') ? v1.label : v2.label;
            const colQuant = (type === 'moyenne_par_groupe') ? v2.label : v1.label;
            thead.innerHTML = `
                <tr>
                    <th>${colQual}</th>
                    <th class="text-right">Moyenne (${colQuant})</th>
                    <th class="text-right">Effectif</th>
                </tr>`;
            donnees.forEach(d => {
                tbody.innerHTML += `
                    <tr>
                        <td>${d.label}</td>
                        <td class="text-right">${d.moyenne.toFixed(2)}</td>
                        <td class="text-right text-muted">${d.effectif}</td>
                    </tr>`;
            });
        }
        else if (type === 'nuage_points') {
            thead.innerHTML = `
                <tr>
                    <th>${v1.label}</th>
                    <th class="text-right">${v2.label}</th>
                </tr>`;
            // Limite à 100 lignes pour ne pas saturer le DOM
            const aAfficher = donnees.slice(0, 100);
            aAfficher.forEach(p => {
                tbody.innerHTML += `
                    <tr>
                        <td>${p.x}</td>
                        <td class="text-right">${p.y}</td>
                    </tr>`;
            });
            if (donnees.length > 100) {
                tbody.innerHTML += `
                    <tr class="explorer-table-stat">
                        <td colspan="2" class="text-muted text-center">
                            … et ${donnees.length - 100} autres observations
                        </td>
                    </tr>`;
            }
        }
    }

    // ============================================================
    // 5. ORCHESTRATION
    // ============================================================
    function rafraichir() {
        const cleVar1 = document.getElementById('var-principale').value;
        const cleVar2 = document.getElementById('var-croisement').value;

        const emptyEl = document.getElementById('explorer-empty');
        const outputEl = document.getElementById('explorer-output');

        if (!cleVar1) {
            emptyEl.style.display = '';
            outputEl.style.display = 'none';
            return;
        }

        // Filtrage
        const filtered = appliquerFiltres(DATASET);

        if (filtered.length === 0) {
            emptyEl.style.display = '';
            emptyEl.innerHTML = `
                <div class="explorer-empty-icon">📭</div>
                <h3 class="explorer-empty-title">Aucune donnée</h3>
                <p class="explorer-empty-desc">
                    Les filtres appliqués ne renvoient aucune observation.
                    Essayez de relâcher un filtre.
                </p>`;
            outputEl.style.display = 'none';
            return;
        }

        // Type de graphique
        const type = determinerTypeGraphique(cleVar1, cleVar2);
        if (!type) return;

        const v1 = VAR_INDEX[cleVar1];
        const v2 = cleVar2 ? VAR_INDEX[cleVar2] : null;

        // Agrégation
        let donnees;
        if (type === 'barres_simples') {
            donnees = agregerQualitatif(filtered, cleVar1);
        } else if (type === 'barres_groupees') {
            donnees = agregerCroiseQualQual(filtered, cleVar1, cleVar2);
        } else if (type === 'histogramme') {
            donnees = agregerQuantitatif(filtered, cleVar1);
        } else if (type === 'moyenne_par_groupe') {
            donnees = agregerMoyenneParGroupe(filtered, cleVar1, cleVar2);
        } else if (type === 'moyenne_par_groupe_inverse') {
            donnees = agregerMoyenneParGroupe(filtered, cleVar2, cleVar1);
        } else if (type === 'nuage_points') {
            donnees = agregerScatter(filtered, cleVar1, cleVar2);
        }

        // Mise à jour de l'en-tête
        document.getElementById('output-type').textContent = LIBELLES_TYPES[type];
        document.getElementById('output-count').textContent =
            filtered.length + ' observation' + (filtered.length > 1 ? 's' : '');

        let titre, sub;
        if (!v2) {
            titre = v1.label;
            sub = type === 'histogramme'
                ? `Distribution de ${v1.label.toLowerCase()}`
                : `Répartition selon ${v1.label.toLowerCase()}`;
        } else {
            titre = `${v1.label} × ${v2.label}`;
            sub = `Analyse croisée de ${v1.label.toLowerCase()} ` +
                  `et ${v2.label.toLowerCase()}`;
        }
        document.getElementById('output-title').textContent = titre;
        document.getElementById('output-sub').textContent = sub;

        // Affichage
        emptyEl.style.display = 'none';
        outputEl.style.display = '';

        dessinerGraphique(type, donnees, v1, v2);
        remplirTableau(type, donnees, v1, v2);
    }

    // ============================================================
    // 6. EXPORT CSV
    // ============================================================
    function exporterCSV() {
        const table = document.getElementById('explorer-table');
        const lignes = [];

        // En-têtes
        const thead = table.querySelector('thead tr');
        if (thead) {
            lignes.push(
                Array.from(thead.children).map(th => `"${th.textContent.trim()}"`).join(',')
            );
        }
        // Corps
        table.querySelectorAll('tbody tr').forEach(tr => {
            lignes.push(
                Array.from(tr.children).map(td => `"${td.textContent.trim()}"`).join(',')
            );
        });

        const csv = '\uFEFF' + lignes.join('\n'); // BOM pour Excel
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);

        const link = document.createElement('a');
        const date = new Date().toISOString().slice(0, 10);
        link.href = url;
        link.download = `explorer_${date}.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    // ============================================================
    // 7. ÉVÉNEMENTS
    // ============================================================
    const idsAEcouter = [
        'var-principale', 'var-croisement',
        'filtre-commune', 'filtre-sexe', 'filtre-age'
    ];
    idsAEcouter.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', rafraichir);
    });

    // Bouton réinitialiser
    const btnReset = document.getElementById('btn-reset');
    if (btnReset) {
        btnReset.addEventListener('click', () => {
            idsAEcouter.forEach(id => {
                const el = document.getElementById(id);
                if (el) el.value = '';
            });
            rafraichir();
        });
    }

    // Bouton export CSV
    const btnCsv = document.getElementById('btn-export-csv');
    if (btnCsv) btnCsv.addEventListener('click', exporterCSV);

})();