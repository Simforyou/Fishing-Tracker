// FishMap – Leichtgewichtige Tile-Karte ohne externe Abhängigkeiten
// Lädt OSM-Tiles direkt über Canvas

class FishMap {
  constructor(containerId, opts = {}) {
    this.container = document.getElementById(containerId);
    if (!this.container) return;

    this.lat = opts.lat || 52.476;
    this.lng = opts.lng || 9.800;
    this.zoom = opts.zoom || 13;
    this.markers = [];
    this.onMarkerClick = opts.onMarkerClick || null;
    this.tileCache = {};
    this.dragging = false;
    this.lastX = 0;
    this.lastY = 0;
    this.offsetX = 0;
    this.offsetY = 0;

    this._build();
  }

  _build() {
    this.container.style.position = 'relative';
    this.container.style.overflow = 'hidden';
    this.container.style.background = '#1a2a3a';
    this.container.style.borderRadius = '14px';

    this.canvas = document.createElement('canvas');
    this.canvas.style.cssText = 'position:absolute;top:0;left:0;cursor:grab';
    this.container.appendChild(this.canvas);

    this.markerLayer = document.createElement('div');
    this.markerLayer.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none';
    this.container.appendChild(this.markerLayer);

    // Zoom-Buttons
    const zoomDiv = document.createElement('div');
    zoomDiv.style.cssText = 'position:absolute;top:10px;right:10px;z-index:10;display:flex;flex-direction:column;gap:4px';
    ['+','−'].forEach((label, i) => {
      const btn = document.createElement('button');
      btn.textContent = label;
      btn.style.cssText = 'width:32px;height:32px;border:none;border-radius:8px;background:rgba(10,24,38,.9);color:#fff;font-size:18px;font-weight:700;cursor:pointer;border:1px solid rgba(255,255,255,.2)';
      btn.onclick = () => { this.zoom += i === 0 ? 1 : -1; this.zoom = Math.max(10, Math.min(18, this.zoom)); this.offsetX = 0; this.offsetY = 0; this._render(); };
      zoomDiv.appendChild(btn);
    });
    this.container.appendChild(zoomDiv);

    // Attribution
    const attr = document.createElement('div');
    attr.innerHTML = '© <a href="https://openstreetmap.org" style="color:#4af">OpenStreetMap</a>';
    attr.style.cssText = 'position:absolute;bottom:4px;right:8px;font-size:10px;color:rgba(255,255,255,.5);z-index:10;background:rgba(0,0,0,.3);padding:2px 6px;border-radius:4px';
    this.container.appendChild(attr);

    this._setupEvents();
    this._resize();
    this._render();
    window.addEventListener('resize', () => { this._resize(); this._render(); });
  }

  _resize() {
    const w = this.container.clientWidth || 360;
    const h = this.container.clientHeight || 300;
    this.canvas.width = w;
    this.canvas.height = h;
    this.w = w;
    this.h = h;
  }

  _tile(x, y, z) {
    return `https://tile.openstreetmap.org/${z}/${x}/${y}.png`;
  }

  _latLngToPixel(lat, lng) {
    const z = this.zoom;
    const scale = Math.pow(2, z) * 256;
    const x = (lng + 180) / 360 * scale;
    const sinLat = Math.sin(lat * Math.PI / 180);
    const y = (0.5 - Math.log((1 + sinLat) / (1 - sinLat)) / (4 * Math.PI)) * scale;
    return { x, y };
  }

  _centerPixel() {
    return this._latLngToPixel(this.lat, this.lng);
  }

  _render() {
    const ctx = this.canvas.getContext('2d');
    const cp = this._centerPixel();
    const tileSize = 256;
    const z = this.zoom;

    // Tile-Koordinaten des Centers
    const centerTileX = cp.x / tileSize;
    const centerTileY = cp.y / tileSize;

    // Pixel-Offset des Centers auf dem Canvas
    const canvasCenterX = this.w / 2 + this.offsetX;
    const canvasCenterY = this.h / 2 + this.offsetY;

    // Anzahl Tiles die wir brauchen
    const tilesX = Math.ceil(this.w / tileSize) + 2;
    const tilesY = Math.ceil(this.h / tileSize) + 2;

    ctx.fillStyle = '#1a2a3a';
    ctx.fillRect(0, 0, this.w, this.h);

    for (let dx = -Math.floor(tilesX / 2); dx <= Math.ceil(tilesX / 2); dx++) {
      for (let dy = -Math.floor(tilesY / 2); dy <= Math.ceil(tilesY / 2); dy++) {
        const tileX = Math.floor(centerTileX) + dx;
        const tileY = Math.floor(centerTileY) + dy;

        if (tileX < 0 || tileY < 0 || tileX >= Math.pow(2, z) || tileY >= Math.pow(2, z)) continue;

        const pixX = canvasCenterX + (tileX - centerTileX) * tileSize;
        const pixY = canvasCenterY + (tileY - centerTileY) * tileSize;

        const key = `${z}/${tileX}/${tileY}`;
        if (this.tileCache[key]) {
          if (this.tileCache[key].complete && this.tileCache[key].naturalWidth > 0) {
            ctx.drawImage(this.tileCache[key], Math.round(pixX), Math.round(pixY), tileSize, tileSize);
          }
        } else {
          const img = new Image();
          img.crossOrigin = 'anonymous';
          img.src = this._tile(tileX, tileY, z);
          img.onload = () => this._render();
          img.onerror = () => {};
          this.tileCache[key] = img;
        }
      }
    }

    this._updateMarkers(cp, canvasCenterX, canvasCenterY);
  }

  _updateMarkers(cp, canvasCenterX, canvasCenterY) {
    const tileSize = 256;
    this.markerLayer.innerHTML = '';

    this.markers.forEach((m, i) => {
      const mp = this._latLngToPixel(m.lat, m.lng);
      const px = Math.round(canvasCenterX + (mp.x - cp.x));
      const py = Math.round(canvasCenterY + (mp.y - cp.y));

      if (px < -20 || px > this.w + 20 || py < -20 || py > this.h + 20) return;

      const el = document.createElement('div');
      const color = m.score >= 80 ? '#67d33f' : m.score >= 65 ? '#ffd23f' : '#ff9d18';
      el.style.cssText = `position:absolute;left:${px - 22}px;top:${py - 22}px;width:44px;height:44px;pointer-events:all;cursor:pointer;z-index:5`;
      el.innerHTML = `
        <div style="width:44px;height:44px;border-radius:50%;background:${color};border:3px solid #fff;box-shadow:0 3px 12px rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center;flex-direction:column;transition:.15s" 
             onmouseenter="this.style.transform='scale(1.15)'" 
             onmouseleave="this.style.transform='scale(1)'">
          <div style="font-size:11px;font-weight:900;color:#000;line-height:1">${m.score}%</div>
        </div>
        <div style="position:absolute;bottom:-18px;left:50%;transform:translateX(-50%);white-space:nowrap;font-size:10px;font-weight:700;color:#fff;text-shadow:0 1px 3px rgba(0,0,0,.9);background:rgba(0,0,0,.5);border-radius:4px;padding:1px 5px">${m.name.length > 12 ? m.name.slice(0,11)+'…' : m.name}</div>`;
      el.addEventListener('click', () => this.onMarkerClick && this.onMarkerClick(i));
      el.addEventListener('touchend', (e) => { e.preventDefault(); this.onMarkerClick && this.onMarkerClick(i); });
      this.markerLayer.appendChild(el);
    });
  }

  _setupEvents() {
    const el = this.canvas;

    // Mouse
    el.addEventListener('mousedown', e => { this.dragging = true; this.lastX = e.clientX; this.lastY = e.clientY; el.style.cursor = 'grabbing'; });
    window.addEventListener('mousemove', e => {
      if (!this.dragging) return;
      this.offsetX += e.clientX - this.lastX;
      this.offsetY += e.clientY - this.lastY;
      this.lastX = e.clientX;
      this.lastY = e.clientY;
      this._render();
    });
    window.addEventListener('mouseup', () => { this.dragging = false; el.style.cursor = 'grab'; });

    // Touch
    let lastTouchX, lastTouchY, lastDist;
    el.addEventListener('touchstart', e => {
      if (e.touches.length === 1) {
        lastTouchX = e.touches[0].clientX;
        lastTouchY = e.touches[0].clientY;
      } else if (e.touches.length === 2) {
        lastDist = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
      }
    }, { passive: true });

    el.addEventListener('touchmove', e => {
      e.preventDefault();
      if (e.touches.length === 1) {
        this.offsetX += e.touches[0].clientX - lastTouchX;
        this.offsetY += e.touches[0].clientY - lastTouchY;
        lastTouchX = e.touches[0].clientX;
        lastTouchY = e.touches[0].clientY;
        this._render();
      } else if (e.touches.length === 2) {
        const dist = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
        if (Math.abs(dist - lastDist) > 10) {
          this.zoom += dist > lastDist ? 1 : -1;
          this.zoom = Math.max(10, Math.min(18, this.zoom));
          this.offsetX = 0; this.offsetY = 0;
          lastDist = dist;
          this._render();
        }
      }
    }, { passive: false });

    // Wheel zoom
    el.addEventListener('wheel', e => {
      e.preventDefault();
      this.zoom += e.deltaY < 0 ? 1 : -1;
      this.zoom = Math.max(10, Math.min(18, this.zoom));
      this.offsetX = 0; this.offsetY = 0;
      this._render();
    }, { passive: false });
  }

  addMarker(lat, lng, score, name) {
    this.markers.push({ lat, lng, score, name });
    this._render();
  }

  flyTo(lat, lng, zoom) {
    this.lat = lat;
    this.lng = lng;
    if (zoom) this.zoom = zoom;
    this.offsetX = 0;
    this.offsetY = 0;
    this._render();
  }

  fitMarkers() {
    if (!this.markers.length) return;
    const lats = this.markers.map(m => m.lat);
    const lngs = this.markers.map(m => m.lng);
    this.lat = (Math.max(...lats) + Math.min(...lats)) / 2;
    this.lng = (Math.max(...lngs) + Math.min(...lngs)) / 2;
    this.offsetX = 0;
    this.offsetY = 0;
    this._render();
  }
}
