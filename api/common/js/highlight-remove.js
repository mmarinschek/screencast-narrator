document.getElementById('_e2e_highlight')?.remove();
if (document.body.dataset.e2eScrollPad) {
    document.body.style.paddingBottom = '';
    delete document.body.dataset.e2eScrollPad;
}
