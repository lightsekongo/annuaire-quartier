/**
 * Page d'accueil — interactions
 *
 * 1. Onglets thématiques avec trait blanc glissant
 * 2. Carrousel infini avec glissement fluide (transform translateX)
 * 3. Compteurs animés
 *
 * Mécanique du carrousel infini :
 *   On clone les N premières cartes en fin de piste.
 *   On translate la piste de -1 carte à la fois.
 *   Quand on dépasse la dernière vraie carte, on saute en arrière
 *   sans transition (effet imperceptible) pour reprendre la boucle.
 */

(function () {
    'use strict';

    // ============================================================
    // 1. ONGLETS — TRAIT GLISSANT
    // ============================================================
    const tabsContainer = document.getElementById('theme-tabs');
    if (!tabsContainer) return;

    const tabs = tabsContainer.querySelectorAll('.tab');
    const indicator = tabsContainer.querySelector('.tab-indicator');
    const panels = document.querySelectorAll('.tab-panel');

    function moveIndicator(activeTab) {
        if (!activeTab || !indicator) return;
        const rect = activeTab.getBoundingClientRect();
        const parentRect = tabsContainer.getBoundingClientRect();
        indicator.style.left = (rect.left - parentRect.left) + 'px';
        indicator.style.width = rect.width + 'px';
    }

    function activateTab(targetTab) {
        tabs.forEach(t => t.classList.remove('tab-active'));
        targetTab.classList.add('tab-active');

        const target = targetTab.dataset.tab;
        panels.forEach(p => {
            p.classList.toggle('tab-panel-active', p.dataset.panel === target);
        });

        moveIndicator(targetTab);

        const activePanel = document.querySelector(
            `.tab-panel[data-panel="${target}"]`
        );
        if (activePanel) {
            animateCounters(activePanel);
            startCarousel(activePanel);
        }

        document.querySelectorAll('.tab-panel:not(.tab-panel-active)').forEach(p => {
            stopCarousel(p);
        });
    }

    tabs.forEach(tab => tab.addEventListener('click', () => activateTab(tab)));

    window.addEventListener('load', () => {
        moveIndicator(tabsContainer.querySelector('.tab-active'));
    });
    window.addEventListener('resize', () => {
        moveIndicator(tabsContainer.querySelector('.tab-active'));
        document.querySelectorAll('.tab-panel-active').forEach(panel => {
            stopCarousel(panel);
            startCarousel(panel);
        });
    });

    // ============================================================
    // 2. COMPTEURS ANIMÉS
    // ============================================================
    function animateCounters(scope) {
        const counters = scope.querySelectorAll('.counter');
        counters.forEach(el => {
            const target = parseFloat(el.dataset.target) || 0;
            const decimal = parseInt(el.dataset.decimal || 0, 10);
            const duration = 1400;
            const startTime = performance.now();
            const ease = t => 1 - Math.pow(1 - t, 4);

            function tick(now) {
                const progress = Math.min((now - startTime) / duration, 1);
                const value = ease(progress) * target;
                el.textContent = formatNumber(value, decimal);
                if (progress < 1) {
                    requestAnimationFrame(tick);
                } else {
                    el.textContent = formatNumber(target, decimal);
                }
            }
            requestAnimationFrame(tick);
        });
    }

    function formatNumber(value, decimal) {
        const fixed = value.toFixed(decimal);
        const [intPart, decPart] = fixed.split('.');
        const withSpaces = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, '\u202F');
        return decPart !== undefined ? `${withSpaces},${decPart}` : withSpaces;
    }

    // ============================================================
    // 3. CARROUSEL INFINI AVEC GLISSEMENT FLUIDE
    // ============================================================
    const AUTOPLAY_INTERVAL = 3500;
    const RESUME_DELAY = 5000;

    const carouselData = new WeakMap();

    function getVisibleCount() {
        if (window.matchMedia('(max-width: 600px)').matches) return 1;
        if (window.matchMedia('(max-width: 900px)').matches) return 1;
        return 4;
    }

    function startCarousel(panel) {
        stopCarousel(panel);

        const track = panel.querySelector('[data-track]');
        if (!track) return;

        // Nettoie d'éventuels clones précédents
        track.querySelectorAll('[data-clone]').forEach(c => c.remove());

        const originalCards = Array.from(track.querySelectorAll('[data-card]'));
        if (originalCards.length === 0) return;

        const visibleCount = getVisibleCount();

        // Mobile : on laisse le scroll natif horizontal, pas de carrousel JS
        const isMobile = window.matchMedia('(max-width: 900px)').matches;
        if (isMobile) {
            track.style.transform = '';
            track.style.transition = 'none';
            track.style.overflowX = 'auto';
            track.style.scrollSnapType = 'x mandatory';
            originalCards.forEach(c => c.style.scrollSnapAlign = 'start');
            return;
        }

        track.style.overflowX = '';
        track.style.scrollSnapType = '';

        // Clone les `visibleCount` premières cartes en fin de piste
        // pour pouvoir scroller au-delà sans laisser de vide
        const clones = [];
        for (let i = 0; i < visibleCount; i++) {
            const clone = originalCards[i].cloneNode(true);
            clone.setAttribute('data-clone', 'true');
            // Les compteurs des clones doivent afficher la valeur finale directement
            clone.querySelectorAll('.counter').forEach(c => {
                const target = parseFloat(c.dataset.target) || 0;
                const dec = parseInt(c.dataset.decimal || 0, 10);
                c.textContent = formatNumber(target, dec);
            });
            track.appendChild(clone);
            clones.push(clone);
        }

        const state = {
            position: 0,             // index logique de la carte de gauche
            total: originalCards.length,
            visible: visibleCount,
            autoTimer: null,
            resumeTimer: null,
            track: track,
            isAnimating: false,
        };

        carouselData.set(panel, state);

        // Position initiale
        applyTransform(track, 0, false);

        function next() {
            if (state.isAnimating) return;
            state.isAnimating = true;
            state.position++;
            applyTransform(track, state.position, true);

            // Quand on atteint la zone clonée, on saute en arrière sans transition
            if (state.position >= state.total) {
                setTimeout(() => {
                    state.position = 0;
                    applyTransform(track, 0, false);
                    state.isAnimating = false;
                }, 700);  // doit dépasser la durée de transition CSS (650ms)
            } else {
                setTimeout(() => { state.isAnimating = false; }, 700);
            }
        }

        function prev() {
            if (state.isAnimating) return;
            state.isAnimating = true;

            // Si on est au début, on saute d'abord à la fin (sans transition)
            // puis on glisse en arrière
            if (state.position === 0) {
                state.position = state.total;
                applyTransform(track, state.position, false);
                // Force le reflow pour que le saut soit appliqué avant la transition
                void track.offsetWidth;
            }
            state.position--;
            applyTransform(track, state.position, true);
            setTimeout(() => { state.isAnimating = false; }, 700);
        }

        function startAuto() {
            stopAuto();
            state.autoTimer = setInterval(next, AUTOPLAY_INTERVAL);
        }
        function stopAuto() {
            if (state.autoTimer) {
                clearInterval(state.autoTimer);
                state.autoTimer = null;
            }
        }
        function pauseAuto() {
            stopAuto();
            if (state.resumeTimer) clearTimeout(state.resumeTimer);
            state.resumeTimer = setTimeout(startAuto, RESUME_DELAY);
        }

        state._startAuto = startAuto;
        state._stopAuto = stopAuto;
        state._next = next;
        state._prev = prev;

        // Pause au survol de la zone (incluant les flèches qui sont dehors :
        // on cible la stats-band, l'ancêtre commun)
        const band = panel.closest('.stats-band');
        if (band) {
            band.addEventListener('mouseenter', stopAuto);
            band.addEventListener('mouseleave', startAuto);
        }

        // Pause si onglet en arrière-plan
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) stopAuto();
            else if (panel.classList.contains('tab-panel-active')) startAuto();
        });

        // Boutons (les boutons sont au niveau de stats-band, pas du panel)
        if (band) {
            const btnNext = band.querySelector('[data-next]');
            const btnPrev = band.querySelector('[data-prev]');

            if (btnNext) {
                const fresh = btnNext.cloneNode(true);
                btnNext.parentNode.replaceChild(fresh, btnNext);
                fresh.addEventListener('click', () => { next(); pauseAuto(); });
            }
            if (btnPrev) {
                const fresh = btnPrev.cloneNode(true);
                btnPrev.parentNode.replaceChild(fresh, btnPrev);
                fresh.addEventListener('click', () => { prev(); pauseAuto(); });
            }
        }

        startAuto();
    }

    function applyTransform(track, position, animated) {
        // Calcule la translation : largeur d'une carte + le gap
        const card = track.querySelector('[data-card]');
        if (!card) return;
        const cardWidth = card.getBoundingClientRect().width;
        const gap = parseFloat(getComputedStyle(track).gap) || 16;
        const offset = position * (cardWidth + gap);

        track.style.transition = animated
            ? 'transform 0.65s cubic-bezier(0.45, 0.05, 0.25, 1)'
            : 'none';
        track.style.transform = `translateX(-${offset}px)`;
    }

    function stopCarousel(panel) {
        const state = carouselData.get(panel);
        if (!state) return;
        if (state.autoTimer) clearInterval(state.autoTimer);
        if (state.resumeTimer) clearTimeout(state.resumeTimer);
        if (state.track) {
            state.track.style.transform = '';
            state.track.style.transition = '';
            state.track.querySelectorAll('[data-clone]').forEach(c => c.remove());
        }
        carouselData.delete(panel);
    }

    // ============================================================
    // 4. INITIALISATION
    // ============================================================
    function init() {
        const initialPanel = document.querySelector('.tab-panel-active');
        if (initialPanel) {
            animateCounters(initialPanel);
            startCarousel(initialPanel);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();