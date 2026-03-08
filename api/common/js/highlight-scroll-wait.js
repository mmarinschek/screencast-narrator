() => new Promise(resolve => {
    const initial = window.scrollY;
    let last = initial;
    let moved = false;
    let settled = 0;
    const check = () => {
        const cur = window.scrollY;
        if (cur !== initial) moved = true;
        if (moved && cur === last) {
            settled++;
            if (settled >= 3) { resolve(); return; }
        } else {
            settled = 0;
        }
        last = cur;
        requestAnimationFrame(check);
    };
    requestAnimationFrame(check);
    setTimeout(() => resolve(), 2000);
})
