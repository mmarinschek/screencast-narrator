(el) => {
    const rect = el.getBoundingClientRect();
    const pad = {{padding}};
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const rx = rect.width / 2 + pad;
    const ry = rect.height / 2 + pad * 0.78;

    const canvas = document.createElement('canvas');
    canvas.id = '_e2e_highlight';
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    canvas.style.cssText = 'position:fixed;top:0;left:0;pointer-events:none;z-index:99999;';
    document.body.appendChild(canvas);

    const ctx = canvas.getContext('2d');
    const minW = {{lineWidthMin}}, maxW = {{lineWidthMax}}, opacity = {{opacity}};
    const segments = {{segments}}, coverage = {{coverage}};
    const startAngle = -Math.PI / 2;

    const points = [];
    for (let i = 0; i <= segments; i++) {
        const t = i / segments;
        const angle = startAngle - t * coverage * Math.PI * 2;
        const x = cx + rx * Math.cos(angle);
        const y = cy + ry * Math.sin(angle);
        const widthT = t < 0.2 ? t / 0.2 : 1.0;
        points.push({ x, y, widthT });
    }

    const speed = {{animationSpeedMs}};
    const start = performance.now();
    function draw(now) {
        const progress = Math.min((now - start) / speed, 1.0);
        const n = Math.floor(progress * (points.length - 1));
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        ctx.globalAlpha = opacity;
        ctx.strokeStyle = '{{color}}';
        if (n > 0) {
            ctx.beginPath();
            ctx.moveTo(points[0].x, points[0].y);
            for (let i = 1; i <= n; i++) {
                ctx.lineWidth = minW + (maxW - minW) * points[i].widthT;
                ctx.lineTo(points[i].x, points[i].y);
            }
            ctx.stroke();
        }
        if (progress < 1.0) requestAnimationFrame(draw);
    }
    requestAnimationFrame(draw);
}
