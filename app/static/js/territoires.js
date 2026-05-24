/**
 * Page Territoires — carte interactive Leaflet
 */

(function () {
    'use strict';

    const DATA = window.TERRITOIRES_DATA;
    if (!DATA) return;

    const URL_COMMUNES = '/static/data/abidjan_communes.geojson';
    const URL_PAYS     = '/static/data/cote_ivoire.geojson';

    const CENTRE_ABIDJAN = [5.36, -4.02];
    const ZOOM_INITIAL = 10;
    const ZOOM_MIN = 10;
    const ZOOM_MAX = 10;

    const PALETTE = [
        '#1d4ed8', '#60a5fa', '#bfdbfe',
        '#fef3c7', '#fbbf24', '#d97706',
    ];

    // --- État global ---
    let map = null;
    let geojsonCommunes = null;
    let geojsonPays = null;
    let indicateurActif = DATA.indicateurs[0].cle;
    let layersBySlug = {};
    let slugSelectionne = null;
    let slugSousCurseur = null;
    let quartiersLayer = null;
    let quartierMarkerHighlight = null;

    // ============================================================
    // 1. INITIALISATION DE LA CARTE
    // ============================================================
    function initialiserCarte() {
        map = L.map('map', {
            center: CENTRE_ABIDJAN,
            zoom: ZOOM_INITIAL,
            minZoom: ZOOM_MIN,
            maxZoom: ZOOM_MAX,
            zoomControl: false,
            attributionControl: true,
            scrollWheelZoom: false,
            doubleClickZoom: false,
            dragging: false,
            touchZoom: false,
            keyboard: false,
            boxZoom: false,
        });

        map.attributionControl.setPrefix('');
        map.attributionControl.addAttribution(
            'Données : OpenStreetMap, Natural Earth'
        );

        chargerCouches();
    }

    // ============================================================
    // 2. CHARGEMENT DES COUCHES
    // ============================================================
    function chargerCouches() {
        fetch(URL_PAYS)
            .then(r => r.ok ? r.json() : null)
            .catch(() => null)
            .then(paysData => {
                if (paysData) {
                    geojsonPays = L.geoJSON(paysData, {
                        interactive: false,
                        style: {
                            color: '#94a3b8',
                            weight: 1,
                            opacity: 0.6,
                            fillColor: '#e2e8f0',
                            fillOpacity: 0.4,
                            className: 'pays-shape',
                        },
                    }).addTo(map);
                }
                return fetch(URL_COMMUNES);
            })
            .then(r => r ? r.json() : null)
            .then(communesData => {
                if (!communesData) return;

                geojsonCommunes = L.geoJSON(communesData, {
                    style: styleCommune,
                    onEachFeature: brancherInteractions,
                }).addTo(map);

                appliquerCouleurs();

                map.fitBounds(geojsonCommunes.getBounds(), {
                    padding: [60, 60],
                    maxZoom: 10,
                });
            })
            .catch(err => {
                console.error('Erreur de chargement des couches :', err);
            });
    }

    function styleCommune(feature) {
        return {
            color: '#ffffff',
            weight: 1.5,
            opacity: 1,
            fillColor: PALETTE[0],
            fillOpacity: 0.9,
            className: 'commune-shape',
        };
    }

    function brancherInteractions(feature, layer) {
        const slug = feature.properties.slug;
        layersBySlug[slug] = layer;

        layer.on({
            mouseover: e => onSurvol(e, feature),
            mouseout:  e => onSortieSurvol(e),
            mousemove: e => onMouvementSurvol(e),
            click:     e => onClic(e, feature),
        });
    }

    // ============================================================
    // 3. COLORATION CHOROPLÈTHE
    // ============================================================
    function appliquerCouleurs() {
        if (!geojsonCommunes) return;

        const bornes = DATA.bornes[indicateurActif];
        if (!bornes) return;

        const min = bornes.min;
        const max = bornes.max;
        const range = max - min || 1;

        geojsonCommunes.eachLayer(layer => {
            const slug = layer.feature.properties.slug;
            if (slug === slugSousCurseur) return;

            const profil = DATA.profils[slug];
            if (!profil) return;

            const valeur = profil.valeurs[indicateurActif] || 0;
            const ratio = (valeur - min) / range;
            const couleur = couleurDepuisRatio(ratio);

            // setStyle Leaflet pour mettre à jour son état interne
            layer.setStyle({
                fillColor: couleur,
                fillOpacity: slug === slugSelectionne ? 1 : 0.9,
                weight: slug === slugSelectionne ? 2.5 : 1.5,
                color: '#ffffff',
            });

            // ⚡ Force l'écriture directe des attributs SVG.
            // Indispensable car setStyle() ne propage pas correctement les
            // changements quand le path est dans un état "hover fantôme"
            // (mouseenter sans mouseleave correspondant).
            forcerStyleSVG(layer, {
                stroke: '#ffffff',
                'stroke-width': slug === slugSelectionne ? 2.5 : 1.5,
                fill: couleur,
                'fill-opacity': slug === slugSelectionne ? 1 : 0.9,
            });
        });
    }

    // Helper : force directement les attributs SVG d'un layer Leaflet
    // Court-circuite les bugs de Leaflet sur les paths en état hover fantôme.
    function forcerStyleSVG(layer, attributs) {
        if (!layer || !layer._path) return;
        const path = layer._path;
        Object.entries(attributs).forEach(([attr, val]) => {
            path.setAttribute(attr, val);
        });
    }

    function couleurDepuisRatio(ratio) {
        ratio = Math.max(0, Math.min(1, ratio));
        const idx = Math.min(
            Math.floor(ratio * PALETTE.length),
            PALETTE.length - 1
        );
        return PALETTE[idx];
    }

    // ============================================================
    // 4. INTERACTIONS HOVER
    // ============================================================
    const hoverInfo = document.getElementById('map-hover');
    const hoverName = hoverInfo ? hoverInfo.querySelector('.map-hover-name') : null;
    const hoverValue = hoverInfo ? hoverInfo.querySelector('.map-hover-value') : null;

    function ramenerQuartiersAuPremierPlan() {
        if (!quartiersLayer) return;
        quartiersLayer.eachLayer(marker => {
            if (marker.bringToFront) marker.bringToFront();
        });
    }

function onSurvol(e, feature) {
        const layer = e.target;
        slugSousCurseur = feature.properties.slug;

        // Plus de setStyle au hover : on évite tout bug de re-rendering SVG.
        // L'utilisateur sait quelle commune est sous sa souris grâce au
        // tooltip noir flottant qui s'affiche juste à côté.

        if (hoverInfo && hoverName && hoverValue) {
            const slug = feature.properties.slug;
            const profil = DATA.profils[slug];
            const indMeta = DATA.indicateurs.find(i => i.cle === indicateurActif);

            if (profil && indMeta) {
                const valeur = profil.valeurs[indicateurActif];
                hoverName.textContent = profil.nom;
                hoverValue.textContent = indMeta.label + ' : ' +
                                          formatValeur(valeur, indMeta.unite);
                hoverInfo.removeAttribute('hidden');
                hoverInfo.style.display = 'block';
            }
        }
    }

function onSortieSurvol(e) {
        slugSousCurseur = null;

        // Plus de reset de style ici : comme onSurvol ne change rien,
        // il n'y a rien à remettre à zéro.

        if (hoverInfo) {
            hoverInfo.setAttribute('hidden', '');
            hoverInfo.style.display = 'none';
        }
    }

    function onMouvementSurvol(e) {
        if (!hoverInfo) return;
        const mapEl = document.getElementById('map');
        const mapRect = mapEl.getBoundingClientRect();
        const x = e.originalEvent.clientX - mapRect.left + 14;
        const y = e.originalEvent.clientY - mapRect.top + 14;
        const tooltipWidth = hoverInfo.offsetWidth || 200;
        const maxX = mapRect.width - tooltipWidth - 10;
        hoverInfo.style.left = Math.min(x, maxX) + 'px';
        hoverInfo.style.top = y + 'px';
    }

    // ============================================================
    // 5. CLIC SUR UNE COMMUNE
    // ============================================================
    function onClic(e, feature) {
        const slug = feature.properties.slug;
        const profil = DATA.profils[slug];
        if (!profil) return;

        slugSelectionne = slug;
        afficherTerritoire(profil, false);
        afficherQuartiers(slug);

        // Reset propre de toutes les communes SAUF celle sous le curseur
        const bornes = DATA.bornes[indicateurActif];
        const range = (bornes.max - bornes.min) || 1;

        geojsonCommunes.eachLayer(layer => {
            const sl = layer.feature.properties.slug;
            if (sl === slugSousCurseur) return;

            const profil2 = DATA.profils[sl];
            if (!profil2) return;

            const valeur = profil2.valeurs[indicateurActif] || 0;
            const ratio = (valeur - bornes.min) / range;
            const couleur = couleurDepuisRatio(ratio);

            layer.setStyle({
                fillColor: couleur,
                fillOpacity: sl === slugSelectionne ? 1 : 0.9,
                weight: sl === slugSelectionne ? 2.5 : 1.5,
                color: '#ffffff',
            });

            // ⚡ Force directement les attributs SVG
            forcerStyleSVG(layer, {
                stroke: '#ffffff',
                'stroke-width': sl === slugSelectionne ? 2.5 : 1.5,
                fill: couleur,
                'fill-opacity': sl === slugSelectionne ? 1 : 0.9,
            });
        });
    }

    // ============================================================
    // 6. AFFICHAGE / MASQUAGE DES QUARTIERS
    // ============================================================
    function afficherQuartiers(slugCommune) {
        masquerQuartiers();

        const quartiers = DATA.quartiers[slugCommune];
        if (!quartiers || quartiers.length === 0) return;

        quartiersLayer = L.layerGroup();

        quartiers.forEach((q, idx) => {
            const marker = L.circleMarker([q.lat, q.lng], {
                radius: 9,
                weight: 2.5,
                color: '#ffffff',
                fillColor: '#d97706',
                fillOpacity: 1,
                className: 'quartier-marker',
                interactive: true,
            });

            marker._quartierData = q;

            marker.on('add', function () {
                const path = marker._path;
                if (path) {
                    path.style.animationDelay = (idx * 60) + 'ms';
                }
            });

            marker.on('mouseover', function (e) {
                L.DomEvent.stopPropagation(e);
                afficherTooltipQuartier(q, e.originalEvent);
            });
            marker.on('mousemove', function (e) {
                L.DomEvent.stopPropagation(e);
                deplacerTooltipQuartier(e.originalEvent);
            });
            marker.on('mouseout', function (e) {
                L.DomEvent.stopPropagation(e);
                masquerTooltipQuartier();
            });
            marker.on('click', function (e) {
                L.DomEvent.stopPropagation(e);
                surlignerLigneQuartier(q.id);
                ouvrirPopupQuartier(q, e);
            });

            quartiersLayer.addLayer(marker);
        });

        quartiersLayer.addTo(map);
    }

    function masquerQuartiers() {
        if (quartiersLayer) {
            map.removeLayer(quartiersLayer);
            quartiersLayer = null;
        }
        masquerTooltipQuartier();
    }

    // ============================================================
    // 7. TOOLTIP DES QUARTIERS
    // ============================================================
    let tooltipQuartier = null;

    function afficherTooltipQuartier(quartier, evt) {
        if (!tooltipQuartier) {
            tooltipQuartier = document.createElement('div');
            tooltipQuartier.className = 'quartier-tooltip';
            document.querySelector('.map-wrap').appendChild(tooltipQuartier);
        }
        tooltipQuartier.textContent = quartier.nom +
            ' · ' + quartier.nb_menages + ' mén.';
        tooltipQuartier.style.display = 'block';
        deplacerTooltipQuartier(evt);
    }

    function deplacerTooltipQuartier(evt) {
        if (!tooltipQuartier) return;
        const mapRect = document.getElementById('map').getBoundingClientRect();
        const x = evt.clientX - mapRect.left + 14;
        const y = evt.clientY - mapRect.top + 14;
        tooltipQuartier.style.left = x + 'px';
        tooltipQuartier.style.top = y + 'px';
    }

    function masquerTooltipQuartier() {
        if (tooltipQuartier) tooltipQuartier.style.display = 'none';
    }

    // ============================================================
    // 8. PANNEAU DE DÉTAIL
    // ============================================================
    const panel = document.getElementById('territory-panel');
    const panelType = document.getElementById('panel-type');
    const panelName = document.getElementById('panel-name');
    const panelMeta = document.getElementById('panel-meta');
    const panelHint = document.getElementById('panel-hint');
    const panelQuartiers = document.getElementById('panel-quartiers');
    const quartiersListEl = document.getElementById('quartiers-list');
    const quartiersCountEl = document.getElementById('quartiers-count');

    function afficherTerritoire(profil, isAbidjan) {
        if (panel) {
            panel.classList.add('panel-loading');
            setTimeout(() => panel.classList.remove('panel-loading'), 220);
        }

        if (panelName) panelName.textContent = profil.nom;

        if (panelType) {
            panelType.textContent = isAbidjan
                ? 'Vue d\'ensemble'
                : (profil.type === 'commune_urbaine'
                    ? 'Commune urbaine'
                    : 'Sous-préfecture');
        }

        if (panelHint) {
            if (isAbidjan) {
                panelHint.textContent =
                    'Cliquez sur une commune de la carte pour voir ses quartiers et son détail.';
            } else {
                panelHint.innerHTML =
                    '<a href="#" id="back-to-overview" ' +
                    'style="color:var(--brand);text-decoration:none;font-weight:600">' +
                    '← Revenir à la vue d\'ensemble</a>';
                const lien = document.getElementById('back-to-overview');
                if (lien) {
                    lien.addEventListener('click', e => {
                        e.preventDefault();
                        slugSelectionne = null;
                        afficherTerritoire(DATA.abidjan, true);
                        masquerQuartiers();
                        appliquerCouleurs();
                    });
                }
            }
        }

        if (panelMeta) {
            panelMeta.innerHTML =
                '<span class="text-bold numeric">' +
                formatNombre(profil.nb_membres) +
                '</span> personnes recensées dans ' +
                '<span class="text-bold numeric">' +
                formatNombre(profil.nb_menages) +
                '</span> ménages';
        }

        remplirBlocs(profil);

        if (panelQuartiers) {
            if (isAbidjan) {
                panelQuartiers.setAttribute('hidden', '');
            } else {
                panelQuartiers.removeAttribute('hidden');
                remplirListeQuartiers(profil.slug);
            }
        }
    }

    function remplirBlocs(profil) {
        if (!panel) return;

        const parTheme = { demographie: [], economie: [], conditions: [] };
        DATA.indicateurs.forEach(ind => {
            if (parTheme[ind.theme]) parTheme[ind.theme].push(ind);
        });

        Object.entries(parTheme).forEach(([theme, indicateurs]) => {
            const conteneur = panel.querySelector(`[data-stats="${theme}"]`);
            if (!conteneur) return;
            conteneur.innerHTML = '';

            indicateurs.forEach(ind => {
                const valeur = profil.valeurs[ind.cle];
                const estActif = ind.cle === indicateurActif;

                const row = document.createElement('div');
                row.className = 'panel-stat-row' +
                    (estActif ? ' panel-stat-row-active' : '');
                row.innerHTML =
                    '<span class="panel-stat-label">' + ind.label + '</span>' +
                    '<span class="panel-stat-value">' +
                    formatValeur(valeur, ind.unite) +
                    '</span>';
                conteneur.appendChild(row);
            });
        });
    }

    // ============================================================
    // 9. LISTE DES QUARTIERS DANS LE PANNEAU
    // ============================================================
    function remplirListeQuartiers(slugCommune) {
        if (!quartiersListEl || !quartiersCountEl) return;

        const quartiers = DATA.quartiers[slugCommune] || [];
        quartiersCountEl.textContent = '(' + quartiers.length + ')';
        quartiersListEl.innerHTML = '';

        quartiers.forEach(q => {
            const row = document.createElement('button');
            row.type = 'button';
            row.className = 'quartier-row';
            row.dataset.quartierId = q.id;
            row.innerHTML =
                '<span class="quartier-row-dot"></span>' +
                '<span class="quartier-row-name">' + q.nom + '</span>' +
                '<span class="quartier-row-meta">' + q.nb_menages + ' mén.</span>';

            row.addEventListener('click', () => {
                surlignerMarqueurQuartier(q);
                ouvrirPopupQuartier(q, null);
            });

            quartiersListEl.appendChild(row);
        });
    }

    // ============================================================
    // 10. INTERACTIONS CROISÉES LISTE ↔ CARTE
    // ============================================================
    function surlignerMarqueurQuartier(quartier) {
        if (!quartiersLayer) return;

        if (quartierMarkerHighlight) {
            quartierMarkerHighlight.setStyle({ radius: 7 });
            quartierMarkerHighlight = null;
        }

        quartiersLayer.eachLayer(marker => {
            if (marker._quartierData && marker._quartierData.id === quartier.id) {
                marker.setStyle({ radius: 12 });
                marker.bringToFront();
                quartierMarkerHighlight = marker;

                setTimeout(() => {
                    if (quartierMarkerHighlight === marker) {
                        marker.setStyle({ radius: 8 });
                    }
                }, 600);
            }
        });
    }

    function surlignerLigneQuartier(idQuartier) {
        if (!quartiersListEl) return;
        const lignes = quartiersListEl.querySelectorAll('.quartier-row');
        lignes.forEach(l => {
            const id = parseInt(l.dataset.quartierId, 10);
            if (id === idQuartier) {
                l.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                l.style.background = 'var(--amber-light)';
                l.style.borderColor = 'var(--amber)';
                setTimeout(() => {
                    l.style.background = '';
                    l.style.borderColor = '';
                }, 1500);
            }
        });
    }

    // ============================================================
    // 11. POP-UP DE DÉTAIL D'UN QUARTIER
    // ============================================================
    const popup = document.getElementById('quartier-popup');
    const popupClose = document.getElementById('quartier-popup-close');

    function ouvrirPopupQuartier(quartier, evt) {
        if (!popup || !quartier.stats) return;

        const stats = quartier.stats;

        document.getElementById('qp-commune').textContent =
            stats.commune || quartier.commune_nom || '';
        document.getElementById('qp-name').textContent = quartier.nom;

        document.getElementById('qp-nb-menages').textContent =
            formatNombre(stats.volumetrie.nb_menages);
        document.getElementById('qp-nb-personnes').textContent =
            formatNombre(stats.volumetrie.nb_personnes);
        document.getElementById('qp-taille-moyenne').textContent =
            formatValeur(stats.volumetrie.taille_moyenne, '');

        const masc = stats.composition.ratio_masculinite;
        document.getElementById('qp-masculinite').textContent =
            (masc && masc > 0) ? masc : '—';

        const ageMed = stats.composition.age_median;
        document.getElementById('qp-age-median').textContent =
            (ageMed && ageMed > 0) ? ageMed + ' ans' : '—';

        const moins15 = stats.composition.part_moins_15;
        document.getElementById('qp-moins-15').textContent =
            (moins15 !== undefined && moins15 !== null)
                ? formatValeur(moins15, '%')
                : '—';

        let pointX, pointY;
        if (evt && evt.containerPoint) {
            pointX = evt.containerPoint.x;
            pointY = evt.containerPoint.y;
        } else {
            const point = map.latLngToContainerPoint([quartier.lat, quartier.lng]);
            pointX = point.x;
            pointY = point.y;
        }

        popup.removeAttribute('hidden');
        popup.style.display = 'block';

        const popupRect = popup.getBoundingClientRect();
        const mapRect = document.getElementById('map').getBoundingClientRect();

        let posX = pointX + 18;
        let posY = pointY - 30;

        if (posX + popupRect.width > mapRect.width - 10) {
            posX = pointX - popupRect.width - 18;
        }
        if (posX < 10) posX = 10;
        if (posY + popupRect.height > mapRect.height - 10) {
            posY = mapRect.height - popupRect.height - 10;
        }
        if (posY < 10) posY = 10;

        popup.style.left = posX + 'px';
        popup.style.top = posY + 'px';

        popup.style.animation = 'none';
        void popup.offsetWidth;
        popup.style.animation = '';
    }

    function fermerPopupQuartier() {
        if (!popup) return;
        popup.setAttribute('hidden', '');
        popup.style.display = 'none';
    }

    if (popupClose) {
        popupClose.addEventListener('click', fermerPopupQuartier);
    }

    setTimeout(() => {
        if (map) {
            map.on('click', () => {
                fermerPopupQuartier();
            });
        }
    }, 500);

    const masquerQuartiersOriginal = masquerQuartiers;
    masquerQuartiers = function () {
        masquerQuartiersOriginal();
        fermerPopupQuartier();
    };

    // ============================================================
    // 12. SÉLECTEUR D'INDICATEUR
    // ============================================================
    const selecteur = document.getElementById('map-indicator');
    if (selecteur) {
        selecteur.addEventListener('change', () => {
            indicateurActif = selecteur.value;
            appliquerCouleurs();
            const profilCourant = slugSelectionne
                ? DATA.profils[slugSelectionne]
                : DATA.abidjan;
            afficherTerritoire(profilCourant, !slugSelectionne);
        });
    }

    // ============================================================
    // 13. UTILITAIRES
    // ============================================================
    function formatNombre(n) {
        return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '\u202F');
    }

    function formatValeur(valeur, unite) {
        if (valeur === null || valeur === undefined) return '—';
        const aDecimales = valeur % 1 !== 0;
        const formatted = aDecimales
            ? valeur.toFixed(1).replace('.', ',')
            : formatNombre(valeur);
        if (!unite) return formatted;
        if (unite === '%') return formatted + ' %';
        return formatted + ' ' + unite;
    }

    // ============================================================
    // 14. INITIALISATION
    // ============================================================
    function init() {
        afficherTerritoire(DATA.abidjan, true);
        initialiserCarte();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();