/* Service worker del recetario (https://brauliopastran.github.io/recetario/).
 *
 * Sirve para que la web instalada como app abra rápido y funcione sin conexión.
 * Es un fichero fijo: no hay que tocarlo al añadir recetas (generate.py no lo cambia).
 *
 * El origen brauliopastran.github.io lo comparten otros proyectos de GitHub Pages, así que:
 *  - solo se atienden peticiones dentro de /recetario/ (el alcance de este fichero);
 *  - las cachés se llaman «recetario-…» y solo se borran cachés con ese prefijo.
 *
 * Estrategias:
 *  - La página (./ e index.html): primero la red, revalidando con el servidor
 *    (cache: 'no-cache'; GitHub Pages manda max-age=600 y si no se vería la versión
 *    de hace 10 min). Sin red, o si tarda más de 3 s, la última copia guardada
 *    (y la red, si llega, la actualiza para la próxima vez).
 *  - Fotos (images/…): primero la caché. La página pide cada foto con ?v=<huella del
 *    contenido>, así que una foto cambiada es otra URL. Se guardan unas 150 como mucho:
 *    al pasar de ahí salen las que entraron antes.
 *  - Google Fonts: se usa lo guardado y se actualiza por detrás.
 *  - Manifiesto e iconos: primero la caché. Si algún día cambian, sube STATIC a
 *    'recetario-static-v2' para que se descarguen de nuevo.
 *  - sw.js y todo lo demás: directo a la red, sin guardar nada.
 *
 * Interruptor de emergencia: si alguna vez este service worker da problemas, sustituye
 * TODO este fichero por estas líneas y publícalo:
 *
 *   self.addEventListener('install', () => self.skipWaiting());
 *   self.addEventListener('activate', event => event.waitUntil((async () => {
 *     const names = await caches.keys();
 *     await Promise.all(names.filter(n => n.startsWith('recetario-')).map(n => caches.delete(n)));
 *     await self.registration.unregister();
 *   })()));
 *
 * No tiene manejador de «fetch», así que todo va directo a la red. La página registra sw.js
 * con updateViaCache: 'none', de modo que el navegador recoge el cambio en la siguiente
 * visita. No recargues las pestañas desde el interruptor: mientras generate.py siga
 * registrando sw.js, cada visita lo instalaría y recargaría otra vez, sin fin. Para quitarlo
 * del todo, borra también el registro (registerServiceWorker) en generate.py.
 */
'use strict';

const PAGES = 'recetario-pages-v1';
const IMAGES = 'recetario-img-v1';
const FONTS = 'recetario-fonts-v1';
const STATIC = 'recetario-static-v1';
const KEEP = [PAGES, IMAGES, FONTS, STATIC];
const PREFIX = 'recetario-';
const MAX_IMAGES = 150;
const MAX_FONTS = 20;
const PAGE_TIMEOUT_MS = 3000;
const FONT_HOSTS = ['fonts.googleapis.com', 'fonts.gstatic.com'];

const SCOPE = new URL(self.registration.scope); // p. ej. https://brauliopastran.github.io/recetario/
const BASE = SCOPE.pathname;                     // «/recetario/»
const PAGE_KEY = SCOPE.href;                      // la página se guarda siempre con esta clave

self.addEventListener('install', event => {
  self.skipWaiting();
  // Guarda ya la página: así funciona sin conexión desde la primera visita. Si falla, da igual.
  event.waitUntil(
    fetch(new Request(PAGE_KEY, { cache: 'no-cache', credentials: 'same-origin' }))
      .then(res => (cacheablePage(res) ? caches.open(PAGES).then(c => c.put(PAGE_KEY, res)) : null))
      .catch(() => {})
  );
});

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(names.filter(n => n.startsWith(PREFIX) && !KEEP.includes(n)).map(n => caches.delete(n)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;
  let url;
  try { url = new URL(req.url); } catch (e) { return; }

  if (url.origin === self.location.origin) {
    if (!url.pathname.startsWith(BASE)) return; // otro proyecto del mismo origen
    const rest = url.pathname.slice(BASE.length);
    if (rest === 'sw.js') return;
    if (rest === '' || rest === 'index.html') {
      if (req.mode === 'navigate') pageNetworkFirst(event);
      return;
    }
    if (rest.startsWith('images/')) {
      if (!req.headers.has('range')) event.respondWith(imageCacheFirst(event));
      return;
    }
    if (rest === 'manifest.webmanifest' || rest.startsWith('icons/')) {
      event.respondWith(staticCacheFirst(event));
    }
    return;
  }

  if (url.protocol === 'https:' && FONT_HOSTS.includes(url.hostname)) {
    event.respondWith(fontStaleWhileRevalidate(event));
  }
});

const cacheablePage = res => !!res && res.ok && res.type === 'basic' && !res.redirected;
const offlineResponse = () => new Response('', { status: 504, statusText: 'Offline' });

/* ---------- Página: red primero ---------- */
function pageNetworkFirst(event) {
  let settle;
  // Mantiene vivo el service worker hasta guardar la copia nueva, aunque se responda antes con la guardada.
  event.waitUntil(new Promise(resolve => { settle = resolve; }));
  const net = fetch(event.request, { cache: 'no-cache' }).then(res => {
    if (cacheablePage(res)) {
      const copy = res.clone();
      settle(caches.open(PAGES).then(c => c.put(PAGE_KEY, copy)).catch(() => {}));
    } else settle();
    return res;
  }, err => { settle(); throw err; });

  event.respondWith((async () => {
    const cached = await caches.open(PAGES).then(c => c.match(PAGE_KEY)).catch(() => undefined);
    if (!cached) {
      try { return await net; } catch (e) { return offlinePage(); }
    }
    try {
      const res = await Promise.race([net, new Promise(r => setTimeout(r, PAGE_TIMEOUT_MS, null))]);
      if (!res) return cached;                                   // la red tarda: la copia guardada
      if (res.ok || res.type === 'opaqueredirect') return res;   // lo nuevo (o una redirección)
      return cached;                                             // error del servidor: mejor la copia
    } catch (e) {
      return cached;                                             // sin conexión
    }
  })());
}

function offlinePage() {
  const html = '<!doctype html><html lang="es"><head><meta charset="utf-8">' +
    '<meta name="viewport" content="width=device-width, initial-scale=1"><title>Recetario</title></head>' +
    '<body style="margin:0;min-height:100vh;display:grid;place-items:center;padding:24px;box-sizing:border-box;' +
    'background:#F3F5F8;color:#121A24;font:16px/1.5 system-ui,-apple-system,sans-serif;text-align:center">' +
    '<div><p style="margin:0 0 8px;font-size:1.5rem;font-weight:800">Sin conexión</p>' +
    '<p style="margin:0 0 20px">El recetario estará disponible sin internet después de abrirlo una vez con conexión.</p>' +
    '<button type="button" onclick="location.reload()" style="min-height:44px;padding:0 20px;border:0;' +
    'border-radius:999px;background:#0C7A56;color:#fff;font:inherit;font-weight:700">Reintentar</button></div></body></html>';
  return new Response(html, { status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8' } });
}

/* ---------- Fotos: caché primero ---------- */
async function imageCacheFirst(event) {
  const req = event.request;
  const cache = await caches.open(IMAGES);
  const hit = await cache.match(req);
  if (hit) return hit;
  let res;
  try { res = await fetch(req); } catch (e) { return offlineResponse(); }
  if (res.ok && res.type === 'basic') event.waitUntil(saveImage(cache, req, res.clone()).catch(() => {}));
  return res;
}
async function saveImage(cache, req, res) {
  // Las otras versiones de la misma foto (otro ?v=) ya no se van a pedir.
  const u = new URL(req.url);
  await cache.delete(u.origin + u.pathname, { ignoreSearch: true });
  await cache.put(req, res);
  await trim(cache, MAX_IMAGES);
}
// Cache Storage devuelve las claves en orden de entrada: se borran las más antiguas.
async function trim(cache, max) {
  const keys = await cache.keys();
  for (let i = 0; i < keys.length - max; i++) await cache.delete(keys[i]);
}

/* ---------- Google Fonts: lo guardado y actualizar por detrás ---------- */
async function fontStaleWhileRevalidate(event) {
  const req = event.request;
  const cache = await caches.open(FONTS);
  const hit = await cache.match(req);
  let saved = null;
  const refresh = fetch(req).then(res => {
    if (res.ok) {
      const copy = res.clone();
      saved = cache.put(req, copy).then(() => trim(cache, MAX_FONTS));
    }
    return res;
  });
  event.waitUntil(refresh.then(() => saved).catch(() => {}));
  if (hit) return hit;
  try { return await refresh; } catch (e) { return offlineResponse(); }
}

/* ---------- Manifiesto e iconos: caché primero ---------- */
async function staticCacheFirst(event) {
  const req = event.request;
  const cache = await caches.open(STATIC);
  const hit = await cache.match(req);
  if (hit) return hit;
  let res;
  try { res = await fetch(req); } catch (e) { return offlineResponse(); }
  if (res.ok && res.type === 'basic') event.waitUntil(cache.put(req, res.clone()).catch(() => {}));
  return res;
}
