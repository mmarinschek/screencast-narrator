(function() {
    const overlay = document.createElement('div');
    overlay.id = '_e2e_sync';
    overlay.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;'
        + 'background:#00FF00;display:flex;align-items:center;justify-content:center;'
        + 'z-index:999999;';
    const img = document.createElement('img');
    img.src = '{{dataUrl}}';
    img.style.cssText = 'width:400px;height:400px;image-rendering:pixelated;';
    overlay.appendChild(img);
    document.body.appendChild(overlay);
})()
