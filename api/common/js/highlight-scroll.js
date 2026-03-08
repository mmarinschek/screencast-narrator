(el) => {
    const rect = el.getBoundingClientRect();
    const absoluteTop = rect.top + window.scrollY;
    const visibleHeight = window.innerHeight;
    const targetScroll = absoluteTop - (visibleHeight - rect.height) / 2;
    const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
    if (targetScroll > maxScroll) {
        document.body.style.paddingBottom = '600px';
        document.body.dataset.e2eScrollPad = '1';
        void document.body.offsetHeight;
    }
    window.scrollTo({ top: Math.max(0, targetScroll), behavior: 'smooth' });
}
