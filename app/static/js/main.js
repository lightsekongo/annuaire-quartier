document.addEventListener('DOMContentLoaded', () => {

    const overlay    = document.getElementById('modal-confirm');
    const btnAnnuler = document.getElementById('modal-annuler');
    const btnConfirm = document.getElementById('modal-confirmer');
    const msgEl      = document.getElementById('modal-message');

    if (!overlay) return;

    let formEnAttente = null;

    // Intercepte tous les formulaires avec data-confirm
    document.querySelectorAll('form[data-confirm]').forEach(form => {
        form.addEventListener('submit', e => {
            e.preventDefault();
            formEnAttente = form;
            msgEl.textContent = form.dataset.confirm || 'Confirmer la suppression ?';
            overlay.classList.add('visible');
        });
    });

    // Confirmer
    btnConfirm.addEventListener('click', () => {
        if (formEnAttente) {
            overlay.classList.remove('visible');
            formEnAttente.removeEventListener('submit', () => {});
            formEnAttente.submit();
            formEnAttente = null;
        }
    });

    // Annuler
    btnAnnuler.addEventListener('click', fermer);
    overlay.addEventListener('click', e => {
        if (e.target === overlay) fermer();
    });

    document.addEventListener('keydown', e => {
        if (e.key === 'Escape') fermer();
    });

    function fermer() {
        overlay.classList.remove('visible');
        formEnAttente = null;
    }

});