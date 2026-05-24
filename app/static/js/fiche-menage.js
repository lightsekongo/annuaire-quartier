/**
 * Fiche ménage — Modals de confirmation de suppression
 *
 * Deux modals indépendantes :
 *  - #modal-suppression-menage : confirme la suppression du ménage entier
 *  - #modal-suppression-membre : confirme la suppression d'un membre
 *    (avec nom personnalisé selon le membre cliqué)
 */

(function () {
    'use strict';

    // ============================================================
    // 1. SUPPRESSION DU MÉNAGE
    // ============================================================
    const modalMenage = document.getElementById('modal-suppression-menage');
    const btnOuvrirMenage = document.getElementById('btn-supprimer');
    const btnAnnulerMenage = document.getElementById('btn-annuler-suppression');

    function ouvrirModal(modal) {
        if (modal) {
            modal.classList.add('visible');
        }
    }

    function fermerModal(modal) {
        if (modal) {
            modal.classList.remove('visible');
        }
    }

    if (btnOuvrirMenage && modalMenage) {
        btnOuvrirMenage.addEventListener('click', () => {
            ouvrirModal(modalMenage);
        });
    }

    if (btnAnnulerMenage && modalMenage) {
        btnAnnulerMenage.addEventListener('click', () => {
            fermerModal(modalMenage);
        });
    }

    // Fermeture au clic sur l'arrière-plan
    if (modalMenage) {
        modalMenage.addEventListener('click', (e) => {
            if (e.target === modalMenage) {
                fermerModal(modalMenage);
            }
        });
    }

    // ============================================================
    // 2. SUPPRESSION D'UN MEMBRE
    // ============================================================
    const modalMembre = document.getElementById('modal-suppression-membre');
    const btnsSupprimerMembre = document.querySelectorAll('.btn-supprimer-membre');
    const btnAnnulerMembre = document.getElementById('btn-annuler-suppr-membre');
    const messageMembre = document.getElementById('modal-membre-message');
    const formSupprMembre = document.getElementById('form-suppr-membre');

    // URL de base pour la suppression (avec un id factice de 0 à remplacer)
    const URL_BASE = window.URL_SUPPR_MEMBRE || '';

    btnsSupprimerMembre.forEach(btn => {
        btn.addEventListener('click', () => {
            const id = btn.dataset.id;
            const nom = btn.dataset.nom || '';

            // Met à jour le message
            if (messageMembre) {
                messageMembre.innerHTML =
                    'Cette action supprimera définitivement le membre ' +
                    '<strong>« ' + nom + ' »</strong>. ' +
                    'Cette action est irréversible.';
            }

            // Met à jour l'URL de soumission du formulaire
            if (formSupprMembre && id) {
                // URL_BASE se termine par "/0", on remplace par le vrai id
                formSupprMembre.action = URL_BASE.replace(/\/0$/, '/' + id);
            }

            ouvrirModal(modalMembre);
        });
    });

    if (btnAnnulerMembre && modalMembre) {
        btnAnnulerMembre.addEventListener('click', () => {
            fermerModal(modalMembre);
        });
    }

    if (modalMembre) {
        modalMembre.addEventListener('click', (e) => {
            if (e.target === modalMembre) {
                fermerModal(modalMembre);
            }
        });
    }

    // ============================================================
    // 3. TOUCHE ÉCHAP POUR FERMER N'IMPORTE QUELLE MODAL
    // ============================================================
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            fermerModal(modalMenage);
            fermerModal(modalMembre);
        }
    });
})();