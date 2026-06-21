/* ============================================================
   Benagil Cave — Interactions
   Cloned from emeraldcavevegas.com; weather→Open-Meteo MARINE,
   affiliate/booking-map machinery removed (content-only v1).
   ============================================================ */

// ── STICKY HEADER ──────────────────────────────────────────
const header = document.querySelector('.site-header');
if (header) window.addEventListener('scroll', () => {
  header.classList.toggle('scrolled', window.scrollY > 60);
}, { passive: true });

// ── MOBILE NAV ─────────────────────────────────────────────
const toggle = document.querySelector('.nav-toggle');
const mobileNav = document.querySelector('.mobile-nav');

if (toggle && mobileNav) {
  toggle.addEventListener('click', () => {
    const open = mobileNav.classList.toggle('open');
    toggle.setAttribute('aria-expanded', String(open));
    toggle.querySelectorAll('span').forEach((s, i) => {
      if (open) {
        if (i === 0) s.style.transform = 'rotate(45deg) translate(6px,6px)';
        if (i === 1) s.style.opacity = '0';
        if (i === 2) s.style.transform = 'rotate(-45deg) translate(6px,-6px)';
      } else {
        s.style.transform = '';
        s.style.opacity = '';
      }
    });
  });

  mobileNav.querySelectorAll('a').forEach(a =>
    a.addEventListener('click', () => {
      mobileNav.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
      toggle.querySelectorAll('span').forEach(s => {
        s.style.transform = '';
        s.style.opacity = '';
      });
    })
  );
}

// ── FAQ ACCORDION ──────────────────────────────────────────
document.querySelectorAll('.faq-q').forEach(btn => {
  btn.addEventListener('click', () => {
    const item   = btn.closest('.faq-item');
    const answer = item.querySelector('.faq-a');
    const open   = btn.getAttribute('aria-expanded') === 'true';

    document.querySelectorAll('.faq-q[aria-expanded="true"]').forEach(other => {
      if (other !== btn) {
        other.setAttribute('aria-expanded', 'false');
        other.closest('.faq-item').querySelector('.faq-a').classList.remove('open');
      }
    });

    btn.setAttribute('aria-expanded', String(!open));
    answer.classList.toggle('open', !open);
  });
});

// ── TABLE SORT ─────────────────────────────────────────────
const table = document.getElementById('compTable');
if (table) {
  const headers = table.querySelectorAll('th.sortable');
  headers.forEach(th => {
    th.style.cursor = 'pointer';
    th.addEventListener('click', () => {
      const col  = parseInt(th.dataset.col, 10);
      const asc  = th.getAttribute('aria-sort') !== 'ascending';
      const tbody = table.querySelector('tbody');
      const rows  = Array.from(tbody.querySelectorAll('tr'));

      rows.sort((a, b) => {
        const aCell = a.cells[col];
        const bCell = b.cells[col];
        const aVal  = aCell.dataset.val !== undefined ? parseFloat(aCell.dataset.val) : aCell.textContent.replace(/[^0-9.]/g, '');
        const bVal  = bCell.dataset.val !== undefined ? parseFloat(bCell.dataset.val) : bCell.textContent.replace(/[^0-9.]/g, '');
        const aN = isNaN(aVal) ? 0 : aVal;
        const bN = isNaN(bVal) ? 0 : bVal;
        return asc ? bN - aN : aN - bN;
      });

      headers.forEach(h => h.removeAttribute('aria-sort'));
      th.setAttribute('aria-sort', asc ? 'ascending' : 'descending');
      rows.forEach(r => tbody.appendChild(r));
    });
  });
}

// ── SCROLL REVEAL ──────────────────────────────────────────
const observer = new IntersectionObserver(entries => {
  entries.forEach(e => {
    if (e.isIntersecting) { e.target.classList.add('visible'); observer.unobserve(e.target); }
  });
}, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });

document.querySelectorAll(['.gem-card', '.season-item', '.op-entry'].join(',')).forEach((el, i) => {
  el.classList.add('reveal');
  el.style.transitionDelay = `${(i % 4) * 0.08}s`;
  observer.observe(el);
});

// ── OPEN-METEO MARINE WIDGET ───────────────────────────────
// Significant wave height is the access gate for a sea cave: the algar closes
// on Atlantic swell over ~1.5 m regardless of tide (operator rule of thumb).
const LAT = 37.0868, LON = -8.4238;            // Algar de Benagil
const weatherEl = document.getElementById('weatherWidget');
const pill      = document.getElementById('conditionsPill');

if (pill) {
  const cond = pill.querySelector('.pill-conditions');
  if (cond) cond.addEventListener('click', () => {
    const safety = document.getElementById('safety');
    if (safety) safety.scrollIntoView({ behavior: 'smooth' });
    else window.location.href = 'index.html#safety';
  });
}

function degToCompass(d) {
  const dirs = ['N','NE','E','SE','S','SW','W','NW'];
  return dirs[Math.round(d / 45) % 8];
}
// verdict keyed on significant wave height (metres)
function verdictClass(h) { return h < 0.5 ? 'go' : h < 1.5 ? 'caution' : 'hold'; }
function verdictText(h) {
  if (h < 0.5) return '✓ Calm — cave likely accessible';
  if (h < 1.5) return '⚠ Choppy — confirm with your operator';
  return '✗ Heavy swell — the cave is likely closed';
}

const WMO = {
  0:'Clear sky', 1:'Mainly clear', 2:'Partly cloudy', 3:'Overcast',
  45:'Fog', 48:'Icy fog', 51:'Light drizzle', 53:'Drizzle', 55:'Heavy drizzle',
  61:'Light rain', 63:'Rain', 65:'Heavy rain', 80:'Light showers', 81:'Showers',
  82:'Heavy showers', 95:'Thunderstorm', 96:'Thunderstorm + hail', 99:'Thunderstorm + heavy hail'
};

if (weatherEl || pill) {
  const marineURL = 'https://marine-api.open-meteo.com/v1/marine?latitude=' + LAT + '&longitude=' + LON +
    '&current=wave_height,wave_period,wave_direction,swell_wave_height,sea_surface_temperature' +
    '&hourly=wave_height&timezone=Europe%2FLisbon&forecast_days=1';
  const airURL = 'https://api.open-meteo.com/v1/forecast?latitude=' + LAT + '&longitude=' + LON +
    '&current=temperature_2m,wind_speed_10m,weather_code&timezone=Europe%2FLisbon&forecast_days=1';

  Promise.all([
    fetch(marineURL).then(r => r.json()),
    fetch(airURL).then(r => r.json()).catch(() => null),
  ]).then(([m, a]) => {
    const c       = m.current;
    const waveH   = +c.wave_height;
    const swellH  = c.swell_wave_height != null ? +c.swell_wave_height : null;
    const period  = c.wave_period != null ? Math.round(c.wave_period) : null;
    const seaT    = c.sea_surface_temperature != null ? Math.round(c.sea_surface_temperature) : null;
    const dir     = degToCompass(c.wave_direction || 0);
    const airC    = a && a.current ? Math.round(a.current.temperature_2m) : null;
    const wind    = a && a.current ? Math.round(a.current.wind_speed_10m) : null;
    const desc    = a && a.current ? (WMO[a.current.weather_code] || 'Variable') : '';
    const now     = new Date().toLocaleTimeString('en-GB', { hour: 'numeric', minute: '2-digit', timeZone: 'Europe/Lisbon' });
    const vCls    = verdictClass(waveH);
    const vTxt    = verdictText(waveH);

    // hourly wave-height bars — next 7 hours from current hour
    const curHour = new Date(c.time).getHours();
    const hWaves  = m.hourly.wave_height;
    const hours   = [];
    for (let i = 0; i < 7; i++) {
      const idx = curHour + i;
      if (idx < hWaves.length) hours.push({ h: +hWaves[idx], hr: idx });
    }
    const maxW = Math.max(...hours.map(h => h.h), 1);
    const fmtH = hr => (hr % 24).toString().padStart(2, '0') + 'h';
    const hourBars = hours.map((h, i) => {
      const pct   = Math.max(6, Math.round((h.h / maxW) * 100));
      const cls   = verdictClass(h.h);
      const label = i === 0 ? 'Now' : fmtH(h.hr);
      return '<div class="wind-hour">' +
        '<div class="wind-bar-wrap"><div class="wind-bar ' + cls + '" style="height:' + pct + '%"></div></div>' +
        '<span class="wind-hour-val">' + h.h.toFixed(1) + '</span>' +
        '<span class="wind-hour-time">' + label + '</span></div>';
    }).join('');

    if (weatherEl) {
      const stats = [];
      if (swellH != null) stats.push(['<span class="weather-stat-n">' + swellH.toFixed(1) + ' m</span>', 'Swell']);
      if (period != null) stats.push(['<span class="weather-stat-n">' + period + ' s</span>', 'Period']);
      if (airC != null)   stats.push(['<span class="weather-stat-n">' + airC + '°C</span>', 'Air']);
      if (wind != null)   stats.push(['<span class="weather-stat-n">' + wind + ' km/h</span>', 'Wind']);
      const statsHtml = stats.map(s =>
        '<div class="weather-stat">' + s[0] + '<span class="weather-stat-l">' + s[1] + '</span></div>').join('');

      weatherEl.classList.add('loaded');
      weatherEl.innerHTML =
        '<div class="weather-header">' +
          '<span class="weather-title">Sea conditions off Benagil' +
            '<span class="live-badge"><span class="live-dot"></span> Live</span></span>' +
          '<span class="weather-updated">Updated ' + now + '</span>' +
        '</div>' +
        '<div class="weather-body">' +
          '<div class="weather-main">' +
            '<span class="weather-temp">' + waveH.toFixed(1) + ' m <span class="weather-temp-c">wave ' + dir + '</span></span>' +
            (desc ? '<span class="weather-desc">' + desc + '</span>' : '') +
            '<span class="weather-verdict verdict-' + vCls + '">' + vTxt + '</span>' +
          '</div>' +
          '<div>' +
            '<div class="weather-stats">' + statsHtml + '</div>' +
            '<p class="wind-hours-label">Wave height — next 7 hours (m)</p>' +
            '<div class="wind-hours">' + hourBars + '</div>' +
          '</div>' +
        '</div>' +
        '<div class="sea-note">' +
          '<strong>The algar closes on swell over ~1.5 m</strong> regardless of tide — sea state, not tide, decides whether boats and kayaks can enter. ' +
          'November–March, operators run calm days only.' +
          (seaT != null ? ' Sea temperature today ≈ ' + seaT + '°C.' : '') +
        '</div>';
    }

    if (pill) {
      pill.querySelector('.pill-dot').className = 'pill-dot ' + vCls;
      pill.querySelector('.pill-wind').textContent = waveH.toFixed(1) + ' m';
      pill.style.display = 'flex';
    }
  }).catch(() => {
    if (weatherEl) weatherEl.innerHTML = '<span class="weather-loading">Live sea data unavailable — ' +
      'check a marine forecast (e.g. <a href="https://www.windguru.cz/" target="_blank" rel="noopener noreferrer">Windguru</a>) ' +
      'for Benagil swell before booking.</span>';
  });
}

// reveal pill after the hero scrolls out of view
if (pill) {
  const heroEnd = document.querySelector('.facts-bar') || document.querySelector('.hero');
  const obs = new IntersectionObserver(([e]) => {
    pill.style.display = e.isIntersecting ? 'none' : 'flex';
  }, { threshold: 0 });
  if (heroEnd) obs.observe(heroEnd);
}

// ── GALLERY DRAG-SCROLL ─────────────────────────────────────
document.querySelectorAll('.scroll-gallery').forEach(g => {
  let isDown = false, startX, scrollLeft;
  g.addEventListener('mousedown', e => { isDown = true; startX = e.pageX - g.offsetLeft; scrollLeft = g.scrollLeft; });
  g.addEventListener('mouseleave', () => isDown = false);
  g.addEventListener('mouseup',    () => isDown = false);
  g.addEventListener('mousemove',  e => {
    if (!isDown) return;
    e.preventDefault();
    g.scrollLeft = scrollLeft - (e.pageX - g.offsetLeft - startX);
  });
});

// ── SMOOTH SCROLL (in-page anchors) ─────────────────────────
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', e => {
    const target = document.querySelector(a.getAttribute('href'));
    if (!target) return;
    e.preventDefault();
    window.scrollTo({ top: target.getBoundingClientRect().top + window.scrollY - 72, behavior: 'smooth' });
  });
});

// ── BENAGIL ORIENTATION MAP (Leaflet — cave + departure towns) ──
// Non-affiliate: plain place popups showing where tours leave from and how
// far each town is. Lazy-loads Leaflet from CDN only when scrolled into view.
(function () {
  const el = document.getElementById('benagilMap');
  if (!el) return;

  const LEAFLET_CSS = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
  const LEAFLET_JS  = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';

  const POIS = [
    { lat: 37.0868, lon: -8.4238, kind: 'cave', icon: '◉',
      title: 'Algar de Benagil', sub: 'The sea cave with the oculus. Reached only by boat, guided kayak/SUP — no landing, no swimming in (Edital 019/2024).' },
    { lat: 37.0978, lon: -8.4675, kind: 'town', icon: '⚓',
      title: 'Carvoeiro', sub: 'Closest motorized launch — ~15–20 min by small boat. High supply.' },
    { lat: 37.1010, lon: -8.3530, kind: 'town', icon: '⚓',
      title: 'Armação de Pêra', sub: 'Praia dos Pescadores — beach-launched small boats, ~15–25 min. High supply.' },
    { lat: 37.1185, lon: -8.5237, kind: 'town', icon: '⚓',
      title: 'Portimão', sub: 'Marina de Portimão — the big catamaran hub, ~30–45 min.' },
    { lat: 37.0890, lon: -8.2660, kind: 'town', icon: '⚓',
      title: 'Albufeira', sub: 'Marina de Albufeira — ~45–60 min catamaran, often bundled with dolphin watching.' },
    { lat: 37.1028, lon: -8.6710, kind: 'town', icon: '⚓',
      title: 'Lagos', sub: 'Marina de Lagos — ~45–60 min speedboat, past Ponta da Piedade. Scenic, longest west run.' },
  ];

  function loadLeaflet() {
    if (window.L) return Promise.resolve(window.L);
    return new Promise((resolve, reject) => {
      const css = document.createElement('link');
      css.rel = 'stylesheet'; css.href = LEAFLET_CSS; document.head.appendChild(css);
      const s = document.createElement('script');
      s.src = LEAFLET_JS;
      s.onload = () => resolve(window.L);
      s.onerror = () => reject(new Error('Leaflet failed to load'));
      document.head.appendChild(s);
    });
  }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, c => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c]));
  }
  function initMap() {
    if (el.dataset.initialized) return;
    el.dataset.initialized = '1';
    loadLeaflet().then(L => {
      const map = L.map(el, { scrollWheelZoom: false }).setView([37.10, -8.49], 11);
      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>', maxZoom: 18,
      }).addTo(map);
      const group = L.featureGroup();
      POIS.forEach(p => {
        L.marker([p.lat, p.lon], {
          icon: L.divIcon({ className: '',
            html: '<span class="ec-pin ec-pin-' + p.kind + '">' + p.icon + '</span>',
            iconSize: [30, 30], iconAnchor: [15, 15], popupAnchor: [0, -16] }),
        }).bindPopup('<div class="ec-pop"><strong class="ec-pop-title">' + esc(p.title) + '</strong>' +
          '<span class="ec-pop-sub">' + esc(p.sub) + '</span></div>', { maxWidth: 250, minWidth: 200 })
          .addTo(group);
      });
      group.addTo(map);
      const b = group.getBounds();
      if (b.isValid()) map.fitBounds(b.pad(0.15), { maxZoom: 12 });
      map.once('click', () => map.scrollWheelZoom.enable());
    }).catch(() => {
      el.innerHTML = '<p class="tm-mapfail">Map unavailable — Benagil cave is at 37.0868°N, 8.4238°W, ' +
        'on the Lagoa coast between Carvoeiro and Armação de Pêra.</p>';
    });
  }
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver(entries => {
      entries.forEach(e => { if (e.isIntersecting) { initMap(); io.unobserve(e.target); } });
    }, { rootMargin: '200px' });
    io.observe(el);
  } else { initMap(); }
})();
