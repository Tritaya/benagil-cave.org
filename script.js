/* ============================================================
   Benagil Cave: interactions
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

// -- SEA CONDITIONS (Open-Meteo marine model, open water off the cave) --------
// The cave rules carry no wave-height limit: the skipper decides at the cave and the
// Capitania closes the caves by notice to mariners. So the strip states the numbers (wave
// height and period) and says where the current wave height sits among the last 30 days of
// hourly values at the SAME grid point (lower, middle or upper third), printing the cut-offs.
// It never says "open", "closed", "calm" or "rough", and the booking ask is always the calendar.
// Why not the cave's own coordinates: the marine grid cell that contains the cave (centre
// 37.125 N, 8.458 W, 35 m elevation) is land about 5 km inland and reads lower than the sea.
// The nearest open-water cell is centred at 37.0417 N, 8.4583 W (about 6 km south-south-west).
// Fetch failure leaves the static CHECK FIRST default in place.
const LAT = 37.0868, LON = -8.4238;            // Algar de Benagil (wind and weather)
const SEA_LAT = 37.0417, SEA_LON = -8.4583;    // open-water marine grid cell off the cave
const weatherEl = document.getElementById('weatherWidget');
const pill      = document.getElementById('conditionsPill');

// The pill is the booking nudge once the reading is in: it lands on the page's own
// pinned calendar (#availability).
if (pill) {
  const cond = pill.querySelector('.pill-conditions');
  if (cond) cond.addEventListener('click', () => {
    const el = document.getElementById('availability');
    if (el) window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - 72, behavior: 'smooth' });
    else window.location.href = '/#availability';
  });
}

function degToCompass(d) {
  const dirs = ['N','NE','E','SE','S','SW','W','NW'];
  return dirs[Math.round(d / 45) % 8];
}
function quantile(sorted, q) {
  if (!sorted.length) return null;
  const pos = (sorted.length - 1) * q, lo = Math.floor(pos), hi = Math.ceil(pos);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo);
}
// where a wave height sits against the 30-day cut points: 'lower' | 'middle' | 'upper' | null
function thirdOf(h, cuts) {
  if (!cuts || h == null) return null;
  return h <= cuts.p33 ? 'lower' : h <= cuts.p66 ? 'middle' : 'upper';
}
const THIRD = {
  lower:  { word: 'LOWER THIRD',  sentence: 'in the lower third of the last 30 days' },
  middle: { word: 'MIDDLE THIRD', sentence: 'in the middle third of the last 30 days' },
  upper:  { word: 'UPPER THIRD',  sentence: 'in the upper third of the last 30 days' },
};

const WMO = {
  0:'Clear sky', 1:'Mainly clear', 2:'Partly cloudy', 3:'Overcast',
  45:'Fog', 48:'Icy fog', 51:'Light drizzle', 53:'Drizzle', 55:'Heavy drizzle',
  61:'Light rain', 63:'Rain', 65:'Heavy rain', 80:'Light showers', 81:'Showers',
  82:'Heavy showers', 95:'Thunderstorm', 96:'Thunderstorm with hail', 99:'Thunderstorm with heavy hail'
};

if (weatherEl || pill || document.getElementById('strip-verdict-word')) {
  const marineURL = 'https://marine-api.open-meteo.com/v1/marine?latitude=' + SEA_LAT + '&longitude=' + SEA_LON +
    '&current=wave_height,wave_period,wave_direction,sea_surface_temperature' +
    '&hourly=wave_height&past_days=30&forecast_days=1&timezone=Europe%2FLisbon';
  const airURL = 'https://api.open-meteo.com/v1/forecast?latitude=' + LAT + '&longitude=' + LON +
    '&current=temperature_2m,wind_speed_10m,wind_direction_10m,wind_gusts_10m,weather_code&timezone=Europe%2FLisbon&forecast_days=1';

  try {
    Promise.all([
      fetch(marineURL).then(r => r.json()),
      fetch(airURL).then(r => r.json()).catch(() => null),
    ]).then(([m, a]) => {
      try {
        const c = m && m.current;
        if (!c || typeof c.wave_height !== 'number') return;
        const waveH  = +c.wave_height;
        const period = c.wave_period != null ? Math.round(c.wave_period) : null;
        const seaT   = c.sea_surface_temperature != null ? Math.round(c.sea_surface_temperature) : null;
        const dir    = degToCompass(c.wave_direction || 0);
        const ac     = a && a.current ? a.current : null;
        const wind   = ac && ac.wind_speed_10m != null ? Math.round(ac.wind_speed_10m) : null;
        const gust   = ac && ac.wind_gusts_10m != null ? Math.round(ac.wind_gusts_10m) : null;
        const wdir   = ac && ac.wind_direction_10m != null ? degToCompass(ac.wind_direction_10m) : '';
        const airC   = ac && ac.temperature_2m != null ? Math.round(ac.temperature_2m) : null;
        const desc   = ac ? (WMO[ac.weather_code] || '') : '';
        const now    = new Date().toLocaleTimeString('en-GB', { hour: 'numeric', minute: '2-digit', timeZone: 'Europe/Lisbon' });

        // 30-day cut points from the hourly values before the current hour
        const times = (m.hourly && m.hourly.time) || [];
        const hw = (m.hourly && m.hourly.wave_height) || [];
        const nowKey = String(c.time || '').slice(0, 13);
        let iNow = times.findIndex(t => String(t).slice(0, 13) === nowKey);
        if (iNow < 0) iNow = times.length;
        const past = hw.slice(0, iNow).filter(v => typeof v === 'number').sort((x, y) => x - y);
        const cuts = past.length >= 200 ? { p33: quantile(past, 1 / 3), p66: quantile(past, 2 / 3) } : null;
        const th = thirdOf(waveH, cuts);
        const T = th ? THIRD[th] : null;
        const cutText = cuts ? 'lower third up to ' + cuts.p33.toFixed(1) + ' m, middle third ' + cuts.p33.toFixed(1) + ' to ' + cuts.p66.toFixed(1) + ' m, upper third above ' + cuts.p66.toFixed(1) + ' m' : '';

        // -- the home page strip
        const stripWord = document.getElementById('strip-verdict-word');
        if (stripWord) {
          const sw = document.getElementById('strip-wave');   if (sw) sw.textContent = waveH.toFixed(1) + ' m';
          const sp = document.getElementById('strip-period'); if (sp) sp.textContent = period != null ? period + ' s' : '-';
          const sd = document.getElementById('strip-wind');   if (sd) sd.innerHTML = wind != null ? wind + ' km/h' + (wdir ? ' ' + wdir : '') : '-';
          if (T) {
            stripWord.textContent = T.word;
            const wl = document.getElementById('strip-verdict-label'); if (wl) wl.textContent = 'Wave height now, ranked against the last 30 days at this point';
          }
          const hon = document.getElementById('strip-honest');
          if (hon && cuts) hon.innerHTML = 'Open-water marine model cell at 37.04&deg; N, 8.46&deg; W, about 6 km south-south-west of the cave: ' + cutText + ' (last 30 days of hourly values)';
          const tm = document.getElementById('verdict-time'), live = document.getElementById('verdict-live');
          if (tm && live) { tm.textContent = now; live.hidden = false; }
        }

        // -- the sea-conditions section: numbers, next hours, what the rules say
        if (weatherEl) {
          const stats = [];
          if (period != null) stats.push([period + ' s', 'Wave period']);
          if (wind != null)   stats.push([wind + ' km/h' + (wdir ? ' ' + wdir : ''), 'Wind at the cave']);
          if (gust != null)   stats.push([gust + ' km/h', 'Gusts']);
          if (seaT != null)   stats.push([seaT + '&deg;C', 'Sea']);
          if (airC != null)   stats.push([airC + '&deg;C', 'Air']);
          const statsHtml = stats.map(s => '<div class="weather-stat"><span class="weather-stat-n">' + s[0] +
            '</span><span class="weather-stat-l">' + s[1] + '</span></div>').join('');
          const hours = [];
          for (let i = 0; i < 7; i++) {
            const idx = iNow + i;
            if (idx < hw.length && typeof hw[idx] === 'number') hours.push({ h: +hw[idx], t: String(times[idx]).slice(11, 13) });
          }
          const maxW = Math.max(...hours.map(h => h.h), 1);
          const bars = hours.map((h, i) => {
            const pct = Math.max(6, Math.round((h.h / maxW) * 100));
            return '<div class="wind-hour"><div class="wind-bar-wrap"><div class="wind-bar neutral" style="height:' + pct + '%"></div></div>' +
              '<span class="wind-hour-val">' + h.h.toFixed(1) + '</span><span class="wind-hour-time">' + (i === 0 ? 'Now' : h.t + 'h') + '</span></div>';
          }).join('');
          weatherEl.classList.add('loaded');
          weatherEl.innerHTML =
            '<div class="weather-header"><span class="weather-title">Sea off Benagil Cave</span>' +
            '<span class="weather-updated">checked ' + now + ' in Benagil</span></div>' +
            '<div class="weather-body"><div class="weather-main">' +
              '<span class="weather-temp">' + waveH.toFixed(1) + ' m <span class="weather-temp-c">waves from the ' + dir + '</span></span>' +
              (desc ? '<span class="weather-desc">' + desc + '</span>' : '') +
              (T ? '<span class="weather-verdict verdict-neutral">' + T.sentence + '</span>' : '') +
            '</div><div><div class="weather-stats">' + statsHtml + '</div>' +
            (bars ? '<p class="wind-hours-label">Wave height, next hours (m)</p><div class="wind-hours">' + bars + '</div>' : '') +
            '</div></div>' +
            '<div class="sea-note">No wave height is written into the cave rules. The skipper or guide decides at the cave, and the Capitania do Porto de Portim&atilde;o closes the caves by a notice to mariners when the sea does not allow visits. ' +
            'Wave figures are the Open-Meteo marine model for open water about 6 km south-south-west of the cave' + (cutText ? ' (' + cutText + ', last 30 days)' : '') + '; they are not an operator&rsquo;s cut-off.</div>';
        }

        if (pill) {
          pill.querySelector('.pill-dot').className = 'pill-dot neutral';
          pill.querySelector('.pill-wind').textContent = waveH.toFixed(1) + ' m';
          const pc = pill.querySelector('.pill-cta');
          if (pc) pc.innerHTML = '&middot; ' + (pill.dataset.cta || 'Book a boat') + ' &rarr;';
          pill.style.display = 'flex';
        }
      } catch (e) { /* keep the static default */ }
    }).catch(() => {
      if (weatherEl) weatherEl.innerHTML = '<span class="weather-loading">Live sea data unavailable. Check a marine forecast for Benagil before booking; ' +
        'the skipper decides on the day.</span>';
    });
  } catch (e) { /* keep the static default */ }
}

// reveal pill after the hero scrolls out of view
if (pill) {
  const heroEnd = document.querySelector('.facts-bar') || document.querySelector('.hero');
  const obs = new IntersectionObserver(([e]) => {
    pill.style.display = e.isIntersecting ? 'none' : 'flex';
  }, { threshold: 0 });
  if (heroEnd) obs.observe(heroEnd);
}

// ── AFFILIATE LINK HANDLER (.vlink) ─────────────────────────
// Booking URLs are base64-encoded in data-vurl rather than written as plain
// hrefs. The whole card is clickable;
// this decodes and opens the GetYourGuide page in a new tab.
function openVlink(target) {
  if (!target || !target.dataset || !target.dataset.vurl) return;
  try {
    window.open(atob(target.dataset.vurl), '_blank', 'noopener,noreferrer');
  } catch (e) { /* malformed token — do nothing */ }
}
document.addEventListener('click', e => {
  const link = e.target.closest && e.target.closest('.vlink');
  if (!link) return;
  e.preventDefault();
  openVlink(link);
});
document.addEventListener('keydown', e => {
  if (e.key !== 'Enter' && e.key !== ' ') return;
  const link = e.target.closest && e.target.closest('.vlink');
  if (!link) return;
  e.preventDefault();
  openVlink(link);
});

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
