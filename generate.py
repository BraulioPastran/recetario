#!/usr/bin/env python3
"""Genera index.html a partir de recipes.json para el recetario.

Uso: python generate.py [recipes.json] [index.html]

Toda la web (HTML, CSS y JS) vive en TEMPLATE, una cadena normal (no un
f-string) con marcadores __ASI__ que se sustituyen con str.replace().
Las llaves de CSS y JS se escriben tal cual, sin doblarlas.

Salida: la línea «✅ Generated …» va por stdout; los AVISO, por stderr.
La salida es determinista: con los mismos datos, el mismo index.html.
"""

import hashlib
import json
import math
import os
import re
import struct
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

# Fuente única de las etiquetas: también se inyecta en la web.
TAG_LABEL = {
    'rapida': 'Rápida', 'cena': 'Cena', 'horno': 'Horno', 'postre': 'Postre',
    'pescado': 'Pescado', 'merienda': 'Merienda', 'verdura': 'Verdura',
    'pasta': 'Pasta', 'huevo': 'Huevo', 'pollo': 'Pollo', 'arroz': 'Arroz',
    'desayuno': 'Desayuno', 'carne': 'Carne', 'ensalada': 'Ensalada',
    'sopa': 'Sopa', 'asiatica': 'Asiática', 'vegetariano': 'Vegetariano',
}
# Icono (emoji) y tono de color (0-360) de cada etiqueta, para chips, tarjetas y ficha.
TAG_ICON = {
    'rapida': '⚡', 'cena': '🌙', 'horno': '🔥', 'postre': '🍰', 'pescado': '🐟',
    'merienda': '🧁', 'verdura': '🥦', 'pasta': '🍝', 'huevo': '🥚', 'pollo': '🍗',
    'arroz': '🍚', 'desayuno': '🥐', 'carne': '🥩', 'ensalada': '🥗', 'sopa': '🍲',
    'asiatica': '🥢', 'vegetariano': '🌱',
}
TAG_HUE = {
    'rapida': 48, 'cena': 245, 'horno': 12, 'postre': 335, 'pescado': 205,
    'merienda': 285, 'verdura': 115, 'pasta': 40, 'huevo': 52, 'pollo': 26,
    'arroz': 185, 'desayuno': 32, 'carne': 0, 'ensalada': 95, 'sopa': 18,
    'asiatica': 352, 'vegetariano': 140,
}
CHIP_ORDER = ['postre', 'pescado', 'pasta', 'pollo', 'carne', 'verdura', 'vegetariano',
              'huevo', 'arroz', 'asiatica', 'horno', 'desayuno', 'merienda']
HIDDEN_TAGS = ['rapida', 'cena']  # se buscan y se ven en el detalle, pero no generan chip
# Reglas de etiquetas (ver TAGS.md): «rapida» = preparación + cocción ≤ RAPIDA_MAX_MIN; airfryer cuenta como «horno».
RAPIDA_MAX_MIN = 30
MAX_IMAGE_KB = 500
MIN_IMAGE_WIDTH = 540  # por debajo, la foto se ve borrosa a todo el ancho del móvil
# Títulos en Bricolage Grotesque y texto en Plus Jakarta Sans.
FONTS_CSS = ('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500..800'
             '&family=Plus+Jakarta+Sans:wght@400..800&display=swap')

TEMPLATE = r'''<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<script>try{var t=localStorage.getItem('recetario:theme');if(t==='light'||t==='dark')document.documentElement.dataset.theme=t}catch(e){}</script>
<title>Recetario</title>
<meta name="description" content="Recetario familiar: __COUNT__ recetas">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#F3F5F8" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0D1117" media="(prefers-color-scheme: dark)">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Ccircle cx='32' cy='32' r='30' fill='%230C7A56'/%3E%3Ctext x='32' y='44' font-family='Arial,sans-serif' font-size='34' font-weight='800' text-anchor='middle' fill='%23fff'%3ER%3C/text%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<!-- Fuentes sin bloquear el primer pintado: mientras llegan se usa la del sistema. -->
<link rel="stylesheet" href="__FONTS_CSS__" media="print" onload="this.media='all'">
<noscript><link rel="stylesheet" href="__FONTS_CSS__"></noscript>
<style>
/* ---------- Tokens ---------- */
:root{
  color-scheme:light;
  --paper:#F3F5F8;
  --surface:#FFFFFF;
  --surface-2:#E8ECF1;
  --ink:#121A24;
  --ink-2:#4A5666;
  --ink-3:#647082;
  --line:#E0E5EB;
  --line-strong:#8C97A6;
  --accent:#0C7A56;
  --on-accent:#FFFFFF;
  --accent-soft:#DDF3E9;
  --olive:#0C7A56;
  --on-olive:#FFFFFF;
  --gold:#B26B00;
  --focus:#121A24;
  --focus-halo:#FFFFFF;
  --scrim:rgba(10,16,24,.42);
  --on-scrim:#FFFFFF;
  --heart-on-photo:#FF5A6E;
  /* Texto blanco sobre foto:el degradado empieza pronto para que la línea de categorías también se lea. */
  --photo-fade:linear-gradient(180deg,rgba(10,7,5,0) 0%,rgba(10,7,5,.55) 30%,rgba(10,7,5,.85) 100%);
  --feat-fade:linear-gradient(180deg,rgba(6,10,16,0) 30%,rgba(6,10,16,.6) 60%,rgba(6,10,16,.86) 100%);
  --photo-text-shadow:0 1px 2px rgba(0,0,0,.5);
  --mark-bg:#BFEBD7;
  --bar-bg:rgba(243,245,248,.86);
  --toast-bg:#121A24;
  --toast-ink:#F3F5F8;
  --toast-action:#5EE0A6;
  --cook-bg:#FFFFFF;
  --cook-ink:#000000;
  --shadow-1:0 1px 2px rgba(16,24,40,.06),0 4px 14px rgba(16,24,40,.07);
  --shadow-2:0 20px 50px rgba(16,24,40,.2);
  --img-y:55%;
  --font-display:"Bricolage Grotesque","Plus Jakarta Sans",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  --font-ui:"Plus Jakarta Sans",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  --ease:cubic-bezier(.2,.8,.2,1);
  --spring:cubic-bezier(.34,1.56,.64,1);
  --heart:#E5484D;
  --photo-fade:linear-gradient(180deg,rgba(6,10,16,0) 0%,rgba(6,10,16,.5) 30%,rgba(6,10,16,.84) 100%);
  --tint-s:72%;
  --tint-l:92%;
  --tint-ink:30%;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
  color-scheme:dark;
  --paper:#0D1117;
  --surface:#161C24;
  --surface-2:#212934;
  --ink:#E8EDF3;
  --ink-2:#A3AEBB;
  --ink-3:#8A96A4;
  --line:#28313D;
  --line-strong:#6B7684;
  --accent:#43D69A;
  --on-accent:#05271A;
  --accent-soft:#12352A;
  --olive:#43D69A;
  --on-olive:#05271A;
  --gold:#F2B544;
  --focus:#E8EDF3;
  --focus-halo:#0D1117;
  --scrim:rgba(0,0,0,.55);
  --mark-bg:#1F5A43;
  --bar-bg:rgba(13,17,23,.86);
  --toast-bg:#E8EDF3;
  --toast-ink:#0D1117;
  --toast-action:#0C7A56;
  --cook-bg:#07090C;
  --cook-ink:#F5F8FB;
  --shadow-1:0 0 0 1px var(--line);
  --shadow-2:0 0 0 1px var(--line);
  --heart:#FF6B70;
  --tint-s:30%;
  --tint-l:21%;
  --tint-ink:82%;
}
}
:root[data-theme="dark"]{
  color-scheme:dark;
  --paper:#0D1117;
  --surface:#161C24;
  --surface-2:#212934;
  --ink:#E8EDF3;
  --ink-2:#A3AEBB;
  --ink-3:#8A96A4;
  --line:#28313D;
  --line-strong:#6B7684;
  --accent:#43D69A;
  --on-accent:#05271A;
  --accent-soft:#12352A;
  --olive:#43D69A;
  --on-olive:#05271A;
  --gold:#F2B544;
  --focus:#E8EDF3;
  --focus-halo:#0D1117;
  --scrim:rgba(0,0,0,.55);
  --mark-bg:#1F5A43;
  --bar-bg:rgba(13,17,23,.86);
  --toast-bg:#E8EDF3;
  --toast-ink:#0D1117;
  --toast-action:#0C7A56;
  --cook-bg:#07090C;
  --cook-ink:#F5F8FB;
  --shadow-1:0 0 0 1px var(--line);
  --shadow-2:0 0 0 1px var(--line);
  --heart:#FF6B70;
  --tint-s:30%;
  --tint-l:21%;
  --tint-ink:82%;
}

/* ---------- Base ---------- */
*,*::before,*::after{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;text-size-adjust:100%;background:var(--paper);scroll-padding-top:80px}
body{margin:0;min-height:100vh;min-height:100dvh;background:var(--paper);color:var(--ink);font:400 1rem/1.55 var(--font-ui);-webkit-font-smoothing:antialiased;overflow-x:hidden}
html:has(dialog[open]),html.is-locked{overflow:hidden}
img{display:block;max-width:100%}
button,input,select,textarea{font:inherit;color:inherit;letter-spacing:inherit}
button{cursor:pointer;-webkit-tap-highlight-color:transparent;touch-action:manipulation}
button:disabled{cursor:default}
h1,h2,h3,p,ul,ol,figure{margin:0}
ul,ol{padding:0;list-style:none}
a{color:var(--accent)}
[hidden]{display:none!important}
.visually-hidden{position:absolute!important;width:1px;height:1px;margin:-1px;padding:0;overflow:hidden;clip:rect(0 0 0 0);clip-path:inset(50%);white-space:nowrap;border:0}
:focus-visible{outline:3px solid var(--focus);outline-offset:2px;box-shadow:0 0 0 2px var(--focus-halo)}
.sprite{position:absolute;width:0;height:0;overflow:hidden}
.ico{width:20px;height:20px;flex:none;fill:none;stroke:currentColor;stroke-width:1.75;stroke-linecap:round;stroke-linejoin:round}
.tnum{font-variant-numeric:tabular-nums}
.skip{position:absolute;left:16px;top:-200px;z-index:100;padding:12px 16px;border-radius:999px;background:var(--ink);color:var(--paper);font-weight:700;text-decoration:none}
.skip:focus{top:12px}
.wrap{width:100%;max-width:1240px;margin-inline:auto;padding-left:max(16px,env(safe-area-inset-left));padding-right:max(16px,env(safe-area-inset-right))}
@media (min-width:600px){.wrap{padding-left:24px;padding-right:24px}}
@media (min-width:1024px){.wrap{padding-left:32px;padding-right:32px}}

/* ---------- Botones comunes ---------- */
.icon-btn{position:relative;width:44px;height:44px;flex:none;display:inline-grid;place-items:center;padding:0;border:0;border-radius:999px;background:transparent;color:var(--ink)}
.icon-btn:hover{background:var(--surface-2)}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-height:44px;padding:0 16px;border:1px solid var(--line-strong);border-radius:999px;background:transparent;color:var(--ink);font-size:.9375rem;font-weight:700;text-decoration:none;white-space:nowrap;transition:background-color .2s,color .2s}
.btn:hover{background:var(--surface-2)}
.btn-primary{background:var(--accent);border-color:transparent;color:var(--on-accent)}
.btn-primary:hover{background:var(--accent);filter:brightness(1.06)}
.btn.is-armed{background:var(--accent);border-color:transparent;color:var(--on-accent)}
.linkbtn{display:inline-flex;align-items:center;min-height:44px;padding:0 8px;border:0;background:none;color:var(--accent);font-size:.875rem;font-weight:700;text-decoration:underline;text-underline-offset:3px}

/* ---------- Cabecera ---------- */
.masthead{padding-top:calc(16px + env(safe-area-inset-top));padding-bottom:8px}
.dateline{min-height:44px;display:flex;align-items:center;font-size:.875rem;line-height:1.2;font-weight:600;letter-spacing:0;text-transform:none;color:var(--ink-2)}
.dateline a{display:inline-flex;align-items:center;min-height:44px;color:inherit;text-decoration:none}
.dateline a:hover{text-decoration:underline;text-underline-offset:3px}
.mast-row{display:flex;align-items:flex-end;justify-content:space-between;gap:16px}
.wordmark{font-family:var(--font-display);font-optical-sizing:auto;font-weight:800;font-size:clamp(2.25rem,5vw + 1rem,3.75rem);line-height:1;letter-spacing:-.04em}
.wordmark::after,.mini-mark::after{content:".";color:var(--accent)}

/* ---------- Barra de búsqueda fija ---------- */
.bar{position:sticky;top:0;z-index:20;padding-block:8px;background:var(--bar-bg);-webkit-backdrop-filter:saturate(160%) blur(16px);backdrop-filter:saturate(160%) blur(16px);transition:box-shadow .2s}
@supports not ((backdrop-filter:blur(1px)) or (-webkit-backdrop-filter:blur(1px))){.bar{background:var(--paper)}}
.bar.is-stuck{box-shadow:0 1px 0 var(--line),var(--shadow-1)}
.bar-inner{display:flex;align-items:center;gap:20px}
.mini-mark{display:none;font-family:var(--font-display);font-weight:800;font-size:1.25rem;line-height:1;white-space:nowrap;letter-spacing:-.03em}
@media (min-width:1024px){.bar.is-stuck .mini-mark{display:block;animation:fade .2s var(--ease)}}
.search{position:relative;flex:1;max-width:640px}
.search>.ico{position:absolute;left:14px;top:50%;transform:translateY(-50%);color:var(--ink-2);pointer-events:none}
#q{width:100%;height:48px;padding:0 48px 0 44px;border:1px solid var(--line-strong);border-radius:14px;background:var(--surface);font-size:1rem;-webkit-appearance:none;appearance:none;border-color:var(--line);box-shadow:var(--shadow-1)}
#q::placeholder{color:var(--ink-3);opacity:1}
#q::-webkit-search-cancel-button,#q::-webkit-search-decoration{-webkit-appearance:none;appearance:none}
.search .clear{position:absolute;right:2px;top:2px}
.search kbd{display:none;position:absolute;right:14px;top:50%;transform:translateY(-50%);min-width:24px;height:24px;padding:0 6px;border:1px solid var(--line-strong);border-radius:6px;font:700 .8125rem/22px var(--font-ui);text-align:center;color:var(--ink-2);pointer-events:none}
@media (pointer:fine){.search.is-empty kbd{display:block}}

/* ---------- Filtros ---------- */
.filters{display:grid;grid-template-columns:minmax(0,1fr);gap:4px;padding-top:12px}
.chip-row{display:flex;align-items:center;gap:8px;overflow-x:auto;scroll-snap-type:x proximity;scrollbar-width:none;padding-block:4px;-webkit-overflow-scrolling:touch}
.chip-row::-webkit-scrollbar{display:none}
.chip-row.has-more{-webkit-mask-image:linear-gradient(90deg,black calc(100% - 32px),transparent);mask-image:linear-gradient(90deg,black calc(100% - 32px),transparent)}
.chip{flex:none;scroll-snap-align:start;display:inline-flex;align-items:center;gap:6px;height:44px;padding:0 16px;border:1px solid var(--line);border-radius:999px;background:var(--surface);color:var(--ink);font-size:.9375rem;font-weight:600;white-space:nowrap;transition:background-color .2s,color .2s,opacity .2s}
.chip .ico{width:16px;height:16px}
.chip .n{font-size:.8125rem;font-weight:700;color:var(--ink-2);font-variant-numeric:tabular-nums}
.chip .n:empty{display:none}
.chip .chk{display:none}
.chip:hover:not([aria-disabled="true"]){border-color:var(--line-strong)}
.chip[aria-pressed="true"]{background:var(--accent);border-color:transparent;color:var(--on-accent)}
.chip[aria-pressed="true"] .n{color:inherit;opacity:.75}
.chip[aria-pressed="true"] .chk{display:block}
/* aria-disabled y no disabled: el chip conserva el foco aunque se quede sin recetas. */
.chip[aria-disabled="true"]{opacity:.45;cursor:default}
/* Iconos de etiqueta (emoji): fuente de color del sistema, sin heredar mayúsculas ni sombras. */
.emo{display:inline-block;font-family:"Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji",sans-serif;font-style:normal;font-weight:400;line-height:1;letter-spacing:0;text-transform:none;text-shadow:none}
.sep{flex:none;width:1px;height:24px;background:var(--line-strong)}
/* Con ratón no hay barra de scroll visible: en pantallas anchas los chips pasan a varias líneas
   (en ventanas estrechas, la rueda vertical desplaza la fila; ver buildChips). */
@media (min-width:768px) and (pointer:fine){
  .chip-row{flex-wrap:wrap;overflow:visible}
  .chip-row,.chip-row.has-more{-webkit-mask-image:none;mask-image:none}
}
/* Categorías (fila de arriba): icono redondo de color con el nombre debajo. */
#row-a{gap:2px;align-items:flex-start;padding-block:6px 10px}
#row-a .sep{align-self:flex-start;height:58px;margin:0 6px;background:var(--line)}
#row-a .chip{position:relative;flex-direction:column;justify-content:flex-start;gap:6px;width:78px;height:auto;min-height:44px;padding:2px 0 4px;border:0;border-radius:16px;background:none;color:var(--ink-2);font-size:.8125rem;font-weight:600;line-height:1.2;white-space:normal;text-align:center}
#row-a .chip .emo,#row-a .chip .own{display:grid;place-items:center;width:58px;height:58px;border-radius:50%;background:hsl(var(--h,150) var(--tint-s) var(--tint-l));font-size:28px;transition:transform .2s var(--spring),box-shadow .2s}
#row-a .chip .own{display:block;padding:17px;color:hsl(var(--h,150) 60% var(--tint-ink))}
#row-a .chip .n{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}
#row-a .chip .chk{position:absolute;top:0;right:6px;z-index:1;width:22px;height:22px;padding:4px;border-radius:50%;background:var(--accent);color:var(--on-accent);stroke-width:3;box-shadow:0 0 0 2px var(--paper)}
#row-a .chip[aria-pressed="true"]{background:none;color:var(--ink);font-weight:800}
#row-a .chip[aria-pressed="true"] .emo,#row-a .chip[aria-pressed="true"] .own{box-shadow:0 0 0 3px var(--paper),0 0 0 5px var(--accent)}
/* En pantalla ancha, una sola fila: los iconos se estrechan hasta 64 px y, si aun así no caben, la fila se desliza. */
@media (min-width:768px){
  #row-a{flex-wrap:nowrap;overflow-x:auto;overflow-y:hidden;gap:4px;margin-inline:-8px;padding-inline:8px}
  #row-a .chip{flex:1 1 64px;width:auto;min-width:64px;max-width:84px;font-size:.75rem}
  #row-a.has-more{-webkit-mask-image:linear-gradient(90deg,black calc(100% - 48px),transparent);mask-image:linear-gradient(90deg,black calc(100% - 48px),transparent)}
}
@media (hover:hover) and (pointer:fine){#row-a .chip:hover:not([aria-disabled="true"]) :is(.emo,.own){transform:translateY(-3px)}}
.resbar{display:flex;align-items:center;flex-wrap:wrap;gap:4px 8px;min-height:44px;margin-top:8px}
#count{font-size:.875rem;color:var(--ink-2);font-variant-numeric:tabular-nums}
#count .cnt-s{display:none}
.resbar .spacer{flex:1}
.sort,#random{flex:none}
@media (max-width:479px){
  .resbar{flex-wrap:nowrap}
  #count{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  #count .cnt-l{display:none}
  #count .cnt-s{display:inline}
  .sort select{padding-left:12px}
}
/* Resumen de filtros activos (el chip pulsado puede quedar fuera de la vista en la fila). */
.active-row{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-top:4px}
.act-pill{display:inline-flex;align-items:center;gap:6px;min-height:44px;padding:0 12px 0 16px;border:1px solid var(--line-strong);border-radius:999px;background:var(--surface);color:var(--ink);font-size:.875rem;font-weight:700;white-space:nowrap}
.act-pill:hover{background:var(--surface-2)}
.act-pill .ico{width:16px;height:16px}
.sort{position:relative;display:inline-flex}
.sort select{height:44px;padding:0 36px 0 16px;border:1px solid var(--line-strong);border-radius:999px;background:var(--surface);color:var(--ink);font-size:.875rem;font-weight:700;-webkit-appearance:none;appearance:none;cursor:pointer}
.sort .ico{position:absolute;right:12px;top:50%;width:16px;height:16px;transform:translateY(-50%);pointer-events:none}
#random .lbl{display:none}
@media (min-width:480px){#random .lbl{display:inline}}
#random.spin .ico{animation:spin .5s var(--ease)}

/* ---------- Rejilla y tarjetas ---------- */
.grid{display:grid;grid-template-columns:minmax(0,1fr);column-gap:12px;row-gap:14px;padding-block:12px 48px}
@media (min-width:360px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (min-width:768px){.grid{grid-template-columns:repeat(3,minmax(0,1fr));column-gap:20px;row-gap:22px}}
@media (min-width:1100px){.grid{grid-template-columns:repeat(4,minmax(0,1fr))}}
.grid.intro>:nth-child(-n+8){animation:rise .24s var(--ease) both}
.grid.intro>:nth-child(2){animation-delay:40ms}.grid.intro>:nth-child(3){animation-delay:80ms}
.grid.intro>:nth-child(4){animation-delay:120ms}.grid.intro>:nth-child(5){animation-delay:160ms}
.grid.intro>:nth-child(6){animation-delay:200ms}.grid.intro>:nth-child(7){animation-delay:240ms}
.grid.intro>:nth-child(8){animation-delay:280ms}
.card{position:relative;display:flex;flex-direction:column;gap:4px;min-width:0;transition:opacity .2s}
.card.is-stale{opacity:.5}
/* Ficha blanca con la foto dentro (la portada va sin ficha). */
.card:not(.card--feature){gap:3px;padding:6px 6px 12px;border-radius:20px;background:var(--surface);box-shadow:var(--shadow-1)}
.card:not(.card--feature)>:not(.card-media){padding-inline:6px}
.card-media{position:relative;aspect-ratio:4/5;margin-bottom:6px;overflow:hidden;border-radius:15px;background:linear-gradient(100deg,transparent 30%,rgb(255 255 255/.35) 50%,transparent 70%) var(--surface-2);background-size:200% 100%;animation:shimmer 1.2s linear infinite;transition:transform .12s var(--ease)}
.card-media.is-done{animation:none;background:var(--surface-2)}
.card-media img{width:100%;height:100%;object-fit:cover;object-position:50% var(--img-y);opacity:0;transition:opacity .2s,transform .3s var(--ease)}
.card-media img.is-loaded{opacity:1}
.card-media.is-broken,.d-hero.is-broken{animation:none;background:var(--accent-soft)}
.card-media.is-broken img,.d-hero.is-broken img{opacity:0}
.card-media.is-broken::before,.d-hero.is-broken::before{content:attr(data-initial);position:absolute;inset:0;display:grid;place-items:center;font-family:var(--font-display);font-size:4rem;font-weight:600;color:var(--accent)}
.card:has(.card-link:active) .card-media{transform:scale(.98)}
@media (hover:hover) and (pointer:fine){.card:hover .card-media img{transform:scale(1.03)}}
.card-link{color:inherit;text-decoration:none}
.card-link::after{content:"";position:absolute;inset:0;z-index:1}
.card-link:focus-visible{outline:none;box-shadow:none}
.card-link:focus-visible::after{outline:3px solid var(--focus);outline-offset:4px;border-radius:22px;box-shadow:0 0 0 2px var(--focus-halo)}
.badge-new{position:absolute;top:8px;left:8px;display:inline-flex;align-items:center;height:24px;padding:0 10px;border-radius:8px;background:var(--accent);color:var(--on-accent);font-size:.75rem;font-weight:700}
/* Iconos de las etiquetas sobre la foto */
.card-tags{display:flex;position:absolute;left:8px;bottom:8px;gap:4px;pointer-events:none}
.card-tags .emo{width:30px;height:30px;display:grid;place-items:center;border-radius:50%;background:rgba(255,255,255,.9);box-shadow:0 1px 3px rgba(0,0,0,.2);font-size:16px}
.fav-btn{position:absolute;top:6px;right:6px;z-index:2;width:44px;height:44px;display:grid;place-items:center;padding:0;border:0;border-radius:999px;background:none;color:var(--on-scrim)}
.fav-btn::before{content:"";position:absolute;inset:4px;border-radius:50%;background:var(--scrim);-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px)}
.fav-btn .ico,.tb-btn .ico{position:relative}
/* Sobre foto, el corazón activo lleva borde blanco para destacar también sobre fondos claros. */
.fav-btn[aria-pressed="true"] .ico,.tb-btn[aria-pressed="true"] .ico{fill:var(--heart-on-photo);stroke:#fff;stroke-width:1.5}
/* Sobre superficie sólida, el acento (contraste ≥ 3:1). */
.d-topbar.is-solid .tb-btn[aria-pressed="true"] .ico{fill:var(--heart);stroke:var(--heart);stroke-width:1.75}
.pop .ico{animation:pop .28s var(--spring)}
.card-kicker{font-size:.8125rem;line-height:1.2;font-weight:700;letter-spacing:0;text-transform:none;color:var(--accent)}
.card-kicker:empty{display:none}
.card-title{font-family:var(--font-display);font-optical-sizing:auto;font-weight:700;font-size:1rem;line-height:1.25;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:3;overflow:hidden;overflow-wrap:break-word;letter-spacing:-.01em}
@media (min-width:768px){.card-title{font-size:1.125rem;-webkit-line-clamp:2}}
mark{background:var(--mark-bg);color:inherit;border-radius:3px;box-shadow:inset 0 -2px var(--accent);-webkit-box-decoration-break:clone;box-decoration-break:clone}
.card-meta{display:flex;flex-wrap:wrap;align-items:center;gap:4px;font-size:.8125rem;color:var(--ink-2);font-variant-numeric:tabular-nums}
.card-meta .ico{width:14px;height:14px}
.card-mine{display:flex;flex-wrap:wrap;align-items:center;gap:4px 10px;font-size:.8125rem;color:var(--ink-2);font-variant-numeric:tabular-nums}
.card-mine .done{display:inline-flex;align-items:center;gap:4px;color:var(--olive);font-weight:700}
.card-mine .rate{display:inline-flex;align-items:center;gap:3px}
.card-mine .ico{width:14px;height:14px}
.card-mine .rate .ico{color:var(--gold);fill:currentColor}
.card-match{font-size:.8125rem;color:var(--ink-2)}

/* Portada */
.card--feature{grid-column:1/-1}
.card--feature .card-media{aspect-ratio:1/1;margin:0;border-radius:24px}
.feat-text{position:absolute;inset:0;z-index:1;display:flex;flex-direction:column;justify-content:flex-end;gap:6px;padding:16px;background:var(--feat-fade);color:var(--on-scrim);text-shadow:var(--photo-text-shadow)}
.feat-text .card-kicker,.feat-text .card-meta{color:var(--on-scrim)}
.feat-text .card-title{font-size:clamp(1.5rem,3vw + 1rem,2.25rem);line-height:1.1;-webkit-line-clamp:4;text-wrap:balance;font-weight:800;letter-spacing:-.025em}
/* El contorno de foco se dibuja por dentro: .card-media recorta lo que sale (overflow:hidden). */
.card--feature .card-link:focus-visible::after{outline-offset:-4px;border-radius:12px;box-shadow:inset 0 0 0 6px var(--focus-halo)}
@media (min-width:768px){
  /* Una sola fila y la foto en absoluto: la altura la marcan las tarjetas vecinas, no la proporción de la foto (9:16). */
  .card--feature{grid-column:span 2;grid-row:span 1}
  .card--feature .card-media{flex:1;aspect-ratio:auto;min-height:320px}
  .card--feature .card-media img{position:absolute;inset:0}
  .feat-text{padding:24px}
}

/* ---------- Estados vacíos y pie ---------- */
.empty{max-width:420px;margin:0 auto;padding:48px 0;display:flex;flex-direction:column;align-items:center;gap:12px;text-align:center}
.empty h3{font-family:var(--font-display);font-weight:800;font-size:1.75rem;line-height:1.2;letter-spacing:-.02em}
.empty p{color:var(--ink-2)}
.empty-icon{width:96px;height:96px;display:grid;place-items:center;border-radius:50%;background:var(--accent-soft);color:var(--accent)}
.empty-icon .ico{width:40px;height:40px}
.empty-icon.olive{color:var(--olive)}
.empty .actions{display:flex;flex-wrap:wrap;justify-content:center;gap:8px;margin-top:8px}
.foot{padding-top:24px;padding-bottom:calc(32px + env(safe-area-inset-bottom));border-top:1px solid var(--line);font-size:.875rem;color:var(--ink-2);text-align:center}
.foot .linkbtn{font-size:inherit}

/* ---------- Detalle ---------- */
dialog{color:var(--ink)}
.detail{width:100%;max-width:100%;height:100dvh;max-height:100dvh;margin:0;padding:0;border:0;background:var(--paper);overflow:hidden}
.detail::backdrop{background:var(--scrim)}
.detail[open]{animation:dlg-in .32s var(--ease)}
.detail.no-anim[open]{animation:none}
.detail.is-closing{animation:dlg-out .24s var(--ease) forwards}
.d-scroll{height:100%;overflow-y:auto;overscroll-behavior:contain;padding-bottom:calc(88px + env(safe-area-inset-bottom));scroll-padding-top:64px;scroll-padding-bottom:calc(96px + env(safe-area-inset-bottom))}
.d-topbar{position:absolute;top:0;left:0;right:0;z-index:5;display:flex;align-items:center;gap:2px;height:calc(56px + env(safe-area-inset-top));padding:env(safe-area-inset-top) 6px 0;border-bottom:1px solid transparent;transition:background-color .2s,border-color .2s}
.d-short{flex:1;min-width:0;padding:0 8px;font-family:var(--font-display);font-weight:600;font-size:1.0625rem;text-align:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;opacity:0;transition:opacity .2s}
.tb-btn{position:relative;width:44px;height:44px;flex:none;display:grid;place-items:center;padding:0;border:0;border-radius:999px;background:none;color:var(--on-scrim)}
.tb-btn::before{content:"";position:absolute;inset:4px;border-radius:50%;background:var(--scrim);transition:opacity .2s}
.tb-btn.close-d{display:none}
.d-topbar.is-solid{background:var(--bar-bg);-webkit-backdrop-filter:blur(16px);backdrop-filter:blur(16px);border-bottom-color:var(--line)}
.d-topbar.is-solid .tb-btn{color:var(--ink)}
.d-topbar.is-solid .tb-btn::before{opacity:0}
.d-topbar.is-solid .d-short{opacity:1}
.d-hero{position:relative;background:var(--surface-2)}
.d-hero img{width:100%;aspect-ratio:4/5;max-height:60svh;object-fit:cover;object-position:50% var(--img-y)}
.d-hero.is-broken{aspect-ratio:4/5;max-height:60svh;min-height:240px}
.d-hero.is-broken img{position:absolute;inset:0;height:100%}
.d-hero-text{position:absolute;left:0;right:0;bottom:0;padding:96px 16px 16px;background:var(--photo-fade);color:var(--on-scrim);text-shadow:var(--photo-text-shadow)}
.d-hero-text:empty{display:none}
.d-kicker{font-size:.8125rem;line-height:1.2;font-weight:700;letter-spacing:0;text-transform:none;margin-bottom:8px;display:flex;flex-wrap:wrap;gap:6px}
.d-kicker .tg{display:inline-flex;align-items:center;gap:.35em;height:30px;padding:0 11px 0 7px;border-radius:999px;background:hsl(var(--h,150) var(--tint-s) var(--tint-l));color:hsl(var(--h,150) 55% var(--tint-ink));font-weight:700}
.d-kicker .emo{font-size:15px}
.d-hero-text .d-kicker .tg{background:rgba(255,255,255,.2);color:#fff;-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px)}
.d-title{font-family:var(--font-display);font-optical-sizing:auto;font-weight:800;font-size:clamp(1.875rem,4vw + 1rem,3rem);line-height:1.08;text-wrap:balance;overflow-wrap:break-word;letter-spacing:-.03em}
.d-title:focus{outline:none}
.d-title:focus-visible{outline:3px solid var(--focus);outline-offset:2px}
.d-right{padding:16px}
.d-head{margin-bottom:16px}
.d-right .d-kicker{color:var(--accent)}
.d-random{display:flex;flex-wrap:wrap;align-items:center;gap:0 4px;margin-bottom:12px;font-size:.9375rem;color:var(--ink-2)}
.d-pills{display:flex;flex-wrap:wrap;gap:8px}
.pill{display:inline-flex;align-items:center;gap:6px;height:36px;padding:0 12px;border-radius:999px;background:var(--surface);font-size:.875rem;font-variant-numeric:tabular-nums;box-shadow:inset 0 0 0 1px var(--line)}
.pill .ico{width:16px;height:16px}
.pill--done{background:var(--olive);color:var(--on-olive);font-weight:700;box-shadow:none}
.d-split{margin-top:8px;font-size:.875rem;color:var(--ink-2)}
.mine{display:grid;gap:12px;margin-block:20px;padding:16px;border-radius:14px;background:var(--surface);box-shadow:var(--shadow-1)}
.rate-row{display:flex;flex-wrap:wrap;align-items:center;gap:4px 8px}
.rate-row .lbl{font-weight:700;min-width:4.5rem}
.stars{display:flex}
.star-btn{width:44px;height:44px;display:grid;place-items:center;padding:0;border:0;border-radius:999px;background:none;color:var(--ink-2)}
.star-btn .ico{width:28px;height:28px}
.star-btn.on{color:var(--gold)}
.star-btn.on .ico{fill:currentColor}
.rate-txt{color:var(--ink-2);font-variant-numeric:tabular-nums}
.done-btn{width:100%;min-height:48px;display:flex;align-items:center;justify-content:center;gap:8px;padding:0 16px;border:1px solid var(--line-strong);border-radius:999px;background:transparent;font-weight:700;transition:background-color .2s,color .2s}
.done-btn[aria-pressed="true"]{background:var(--olive);border-color:transparent;color:var(--on-olive)}
.draw{stroke-dasharray:24;animation:draw .25s var(--ease) both}
.switch-row{width:100%;min-height:48px;display:flex;align-items:center;justify-content:space-between;gap:12px;padding:0;border:0;background:none;text-align:left}
.switch{position:relative;flex:none;width:52px;height:32px;border:1px solid var(--line-strong);border-radius:999px;background:var(--surface-2);transition:background-color .2s}
.switch::after{content:"";position:absolute;top:3px;left:3px;width:24px;height:24px;border-radius:50%;background:var(--ink-2);transition:transform .2s var(--ease),background-color .2s}
.switch-row[aria-checked="true"] .switch{background:var(--olive);border-color:var(--olive)}
.switch-row[aria-checked="true"] .switch::after{transform:translateX(20px);background:var(--on-olive)}
.wake-row{margin-top:8px;color:var(--ink-2);font-size:.9375rem}
.sec-head{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 12px;margin:28px 0 4px}
.sec-head h3{font-family:var(--font-display);font-weight:800;font-size:1.375rem;line-height:1.2;letter-spacing:-.02em}
.prog{font-size:.9375rem;color:var(--ink-2);font-variant-numeric:tabular-nums}
.sec-head .linkbtn{margin-left:auto}
.d-ingr .sec-head{margin-top:8px}
/* Con subgrid, la columna de cantidades se ajusta a la más ancha (con tope) y queda alineada en todas las filas. */
.ingr{display:grid;grid-template-columns:28px 5.5rem minmax(0,1fr);column-gap:12px}
@supports (grid-template-columns:subgrid){.ingr{grid-template-columns:28px fit-content(7rem) minmax(0,1fr)}}
@media (min-width:600px){@supports (grid-template-columns:subgrid){.ingr{grid-template-columns:28px fit-content(9rem) minmax(0,1fr)}}}
.ingr>li{grid-column:1/-1;display:grid;grid-template-columns:subgrid}
.ingr-row{grid-column:1/-1;position:relative;display:grid;grid-template-columns:28px 5.5rem minmax(0,1fr);grid-template-columns:subgrid;gap:12px;align-items:baseline;min-height:48px;padding-block:10px;border-bottom:1px solid var(--line);font-size:1.0625rem;cursor:pointer}
.box{align-self:center;width:24px;height:24px;display:grid;place-items:center;border:2px solid var(--line-strong);border-radius:6px;color:var(--on-olive);transition:background-color .2s,border-color .2s}
.box .ico{width:16px;height:16px;stroke-width:2.5;stroke-dasharray:24;stroke-dashoffset:24;transition:stroke-dashoffset .2s var(--ease)}
input:checked+.box{background:var(--olive);border-color:var(--olive)}
input:checked+.box .ico{stroke-dashoffset:0}
input:focus-visible+.box{outline:3px solid var(--focus);outline-offset:2px;box-shadow:0 0 0 2px var(--focus-halo)}
.ingr-row .q{font-weight:700;font-variant-numeric:tabular-nums;overflow-wrap:break-word;min-width:0}
.ingr-row .n{overflow-wrap:break-word}
.note{color:var(--ink-3)}
input:checked~.q,input:checked~.n{text-decoration:line-through;color:var(--ink-2)}
/* La casilla oculta ocupa toda la fila: al tabular, el navegador desplaza hasta la fila entera. */
.ingr-row>input.visually-hidden,.step>input.visually-hidden{inset:0;width:auto;height:auto}
/* Columna estrecha (móvil pequeño, o la columna izquierda de la ficha en escritorio):
   la cantidad va en línea antes del nombre, sin columna propia que deje huecos. */
@media (max-width:419px){
  .ingr,.ingr>li{display:block}
  .ingr-row{display:block;padding-left:40px}
  .ingr-row .box{position:absolute;left:0;top:11px}
  .ingr-row .q{display:inline;margin-right:.3em}
  .ingr-row .q:empty{display:none}
  .ingr-row .n{display:inline}
}
@media (min-width:900px){
  .d-left .ingr,.d-left .ingr>li{display:block}
  .d-left .ingr-row{display:block;padding-left:40px}
  .d-left .ingr-row .box{position:absolute;left:0;top:11px}
  .d-left .ingr-row .q{display:inline;margin-right:.3em}
  .d-left .ingr-row .q:empty{display:none}
  .d-left .ingr-row .n{display:inline}
}
.step{position:relative;display:grid;grid-template-columns:2.5rem minmax(0,1fr);gap:12px;padding:16px 12px;border-bottom:1px solid var(--line);border-radius:14px;font-size:1.125rem;line-height:1.6;cursor:pointer;transition:background-color .2s}
.step .num{font-family:var(--font-ui);font-weight:800;font-size:1rem;line-height:1;color:var(--accent);font-variant-numeric:tabular-nums;width:36px;height:36px;display:grid;place-items:center;border-radius:50%;background:var(--accent-soft)}
.step .ok{display:none;width:24px;height:24px;margin-top:4px;color:var(--olive);stroke-width:2.25}
.step input:checked~.num{display:none}
.step input:checked~.ok{display:block}
.step input:checked~.txt{color:var(--ink-2)}
.step input:focus-visible~.txt{outline:3px solid var(--focus);outline-offset:4px;border-radius:4px}
.step.is-next{background:var(--surface);box-shadow:inset 0 0 0 2px var(--accent)}
.step.is-next .num{background:var(--accent);color:var(--on-accent)}
.d-cta{position:absolute;left:0;right:0;bottom:0;z-index:4;padding:12px 16px calc(12px + env(safe-area-inset-bottom));background:linear-gradient(transparent,var(--paper) 30%)}
.cta-btn{width:100%;height:56px;display:flex;align-items:center;justify-content:center;gap:10px;padding:0 28px;border:0;border-radius:999px;background:var(--accent);color:var(--on-accent);font-size:1.0625rem;font-weight:700}
.cta-btn .ico{width:22px;height:22px}
.d-foot{display:grid;justify-items:start;gap:8px;margin-top:28px;padding-top:16px;border-top:1px solid var(--line)}
.d-src{display:inline-flex;align-items:center;gap:6px;min-height:44px;font-weight:700;text-underline-offset:3px}
.d-src .ico{width:16px;height:16px}
.d-added{font-size:.875rem;color:var(--ink-2)}
@media (min-width:768px) and (max-width:899px){.d-left,.d-right{max-width:720px;margin-inline:auto}.d-hero img{max-height:60svh}}
@media (min-width:900px){
  .detail{width:min(1080px,100vw - 64px);max-width:none;height:min(92dvh,960px);max-height:none;margin:auto;border-radius:22px;box-shadow:var(--shadow-2)}
  .detail::backdrop{background:rgba(20,14,10,.5);-webkit-backdrop-filter:blur(2px);backdrop-filter:blur(2px)}
  .d-topbar,.d-topbar.is-solid{height:56px;padding:0 12px;background:var(--surface);border-bottom-color:var(--line)}
  .d-topbar .tb-btn{color:var(--ink)}
  .d-topbar .tb-btn::before{opacity:0}
  .d-topbar .tb-btn:hover{background:var(--surface-2)}
  .d-topbar .tb-btn[aria-pressed="true"] .ico{fill:var(--heart);stroke:var(--heart);stroke-width:1.75}
  .d-topbar .d-short,.d-topbar.is-solid .d-short{opacity:0}
  .tb-btn.close-m{display:none}
  .tb-btn.close-d{display:grid}
  .d-scroll{display:grid;grid-template-columns:400px minmax(0,1fr);height:100%;padding:56px 0 0;overflow:hidden}
  .d-left,.d-right{min-height:0;overflow-y:auto;overscroll-behavior:contain}
  .d-left{padding:24px;border-right:1px solid var(--line)}
  /* Sin padding inferior: el sticky de .d-cta se mide desde el borde del padding y dejaría
     ver los pasos por debajo del botón. El hueco final lo pone .d-foot. */
  .d-right{padding:24px 32px 0;scroll-padding-bottom:96px}
  .d-right .d-foot{padding-bottom:32px}
  .d-hero{border-radius:18px;overflow:hidden}
  .d-hero img,.d-hero.is-broken{max-height:42vh}
  .d-ingr .sec-head{margin-top:20px}
  /* «Empezar a cocinar» queda fijo al pie de la columna mientras se leen los pasos. */
  .d-cta{position:sticky;bottom:0;z-index:2;margin-top:8px;padding:24px 0 16px;background:linear-gradient(transparent,var(--paper) 40%)}
  .cta-btn{display:inline-flex;width:auto}
}

#lista:focus,#grid:focus,#count:focus{outline:none;box-shadow:none}

/* ---------- Modo cocina ---------- */
.cook{width:100%;max-width:100%;height:100dvh;max-height:100dvh;margin:0;padding:0;border:0;background:var(--cook-bg);color:var(--cook-ink);--cook-scale:1}
.cook[open]{display:flex;flex-direction:column;animation:fade .2s var(--ease)}
.cook::backdrop{background:var(--cook-bg)}
.c-top{display:flex;align-items:center;gap:8px;min-height:56px;padding:calc(6px + env(safe-area-inset-top)) 8px 6px}
#c-label{flex:1;min-width:0;text-align:center;font-size:.9375rem;font-weight:700;font-variant-numeric:tabular-nums}
.c-btn{min-width:44px;height:44px;display:inline-flex;align-items:center;justify-content:center;gap:6px;padding:0 10px;border:1px solid var(--line-strong);border-radius:999px;background:transparent;color:inherit;font-weight:700}
.c-btn:disabled{opacity:.4}
.c-btn .lbl{display:none}
@media (min-width:480px){.c-btn .lbl{display:inline}}
.c-prog{display:flex;gap:4px;padding:4px 16px 0}
.c-prog span{flex:1;height:4px;border-radius:2px;background:var(--line-strong);transition:background-color .2s}
.c-prog span.on{background:var(--accent)}
.c-body{flex:1;min-height:0;display:flex;flex-direction:column;overflow-y:auto;padding:24px;touch-action:pan-y;-webkit-user-select:none;user-select:none}
.c-step,.c-final{margin-block:auto;width:100%;max-width:44rem;margin-inline:auto}
.c-num{font-family:var(--font-display);font-weight:800;font-size:4rem;line-height:1;color:var(--accent);font-variant-numeric:tabular-nums}
.c-txt{max-width:30ch;margin-top:16px;font-size:calc(clamp(1.5rem,5.5vw,2.5rem) * var(--cook-scale));line-height:1.45;overflow-wrap:break-word}
.c-step.go-next{animation:step-next .2s var(--ease)}
.c-step.go-prev{animation:step-prev .2s var(--ease)}
.c-final{display:flex;flex-direction:column;align-items:flex-start;gap:12px}
.c-final h2{font-family:var(--font-display);font-weight:800;font-size:2.5rem;line-height:1.1;letter-spacing:-.02em}
.c-final p{font-size:1.25rem}
.c-final .star-btn{color:currentColor}
.c-final .star-btn.on{color:var(--gold)}
.c-final .actions{display:flex;flex-wrap:wrap;gap:12px;margin-top:8px}
.c-final .btn{min-height:56px;padding:0 24px;font-size:1.0625rem;color:inherit}
.c-final .btn-primary{color:var(--on-accent)}
.c-nav{display:grid;grid-template-columns:1fr 2fr;gap:12px;padding:12px 16px calc(12px + env(safe-area-inset-bottom))}
.c-nav button{height:64px;display:flex;align-items:center;justify-content:center;gap:8px;border-radius:999px;font-size:1.125rem;font-weight:700}
.c-prev{border:2px solid var(--line-strong);background:transparent;color:inherit}
.c-prev:disabled{opacity:.4}
.c-next{border:0;background:var(--accent);color:var(--on-accent)}
@media (min-width:900px){.c-top,.c-prog,.c-nav{width:100%;max-width:760px;margin-inline:auto}}

/* ---------- Hojas (ajustes, ingredientes en cocina) ---------- */
.sheet{width:100%;max-width:100%;max-height:75dvh;margin:auto 0 0;padding:0;border:0;border-radius:22px 22px 0 0;background:var(--surface);color:var(--ink);box-shadow:var(--shadow-2)}
.sheet[open]{display:flex;flex-direction:column;animation:sheet-in .32s var(--ease)}
.sheet::backdrop{background:var(--scrim)}
#settings{max-height:85dvh}
.sheet-head{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:8px 8px 4px 20px;touch-action:none}
.sheet-head h2{font-family:var(--font-display);font-weight:600;font-size:1.5rem}
.sheet-body{flex:1;min-height:0;overflow-y:auto;overscroll-behavior:contain;padding:0 20px calc(24px + env(safe-area-inset-bottom))}
.sheet-body h3{margin:20px 0 8px;font-size:1rem;font-weight:700}
.sheet-body p{color:var(--ink-2);font-size:.9375rem}
@media (min-width:900px){#settings{width:480px;margin:auto;border-radius:22px}#settings[open]{animation:dlg-in .32s var(--ease)}}
.seg-wrap{margin:0;padding:0;border:0}
.seg-wrap legend{padding:0;margin:12px 0 8px;font-weight:700}
.seg{display:grid;grid-template-columns:repeat(3,1fr);gap:4px;padding:4px;border:1px solid var(--line-strong);border-radius:999px}
.seg label{position:relative;display:flex;align-items:center;justify-content:center;gap:6px;min-height:44px;border-radius:999px;font-weight:700;cursor:pointer;transition:background-color .2s,color .2s}
.seg input{position:absolute;inset:0;margin:0;opacity:0;cursor:pointer}
.seg label:has(input:checked){background:var(--ink);color:var(--paper)}
.seg label:has(input:focus-visible){outline:3px solid var(--focus);outline-offset:2px}
.s-actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
.s-build{margin-top:24px}
kbd.k{display:inline-block;min-width:22px;padding:0 6px;border:1px solid var(--line-strong);border-radius:6px;font:700 .8125rem/20px var(--font-ui);text-align:center;color:var(--ink)}
@media (hover:none) and (pointer:coarse){.s-keys{display:none}}

/* ---------- Toast ---------- */
#toast{position:fixed;left:50%;bottom:calc(16px + env(safe-area-inset-bottom) + var(--cta-h,0px));z-index:1000;display:flex;align-items:center;gap:8px;width:max-content;min-height:48px;max-width:min(92vw,420px);margin:0;padding:0 8px 0 20px;border-radius:999px;background:var(--toast-bg);color:var(--toast-ink);font-size:.9375rem;box-shadow:var(--shadow-2);opacity:0;visibility:hidden;transform:translate(-50%,8px);transition:opacity .2s,transform .2s var(--ease),visibility 0s .2s}
#toast.show{opacity:1;visibility:visible;transform:translate(-50%,0);transition:opacity .2s,transform .2s var(--ease)}
#toast .t-msg{padding-block:12px}
#toast.no-act{padding-right:20px}
.toast-act{flex:none;min-height:44px;padding:0 12px;border:0;border-radius:999px;background:none;color:var(--toast-action);font-weight:700}

/* ---------- Animaciones ---------- */
@keyframes shimmer{from{background-position:150% 0}to{background-position:-50% 0}}
@keyframes fade{from{opacity:0}to{opacity:1}}
@keyframes rise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
@keyframes pop{0%{transform:scale(1)}50%{transform:scale(1.25)}100%{transform:scale(1)}}
@keyframes spin{from{transform:rotate(0)}to{transform:rotate(360deg)}}
@keyframes dlg-in{from{opacity:0;transform:translateY(24px)}to{opacity:1;transform:none}}
@keyframes dlg-out{from{opacity:1;transform:none}to{opacity:0;transform:translateY(24px)}}
@keyframes sheet-in{from{transform:translateY(100%)}to{transform:none}}
@keyframes step-next{from{opacity:0;transform:translateX(24px)}to{opacity:1;transform:none}}
@keyframes step-prev{from{opacity:0;transform:translateX(-24px)}to{opacity:1;transform:none}}
@keyframes draw{from{stroke-dashoffset:24}to{stroke-dashoffset:0}}
::view-transition-old(hero),::view-transition-new(hero){animation-duration:.32s;animation-timing-function:var(--ease)}

@media (prefers-reduced-motion: reduce){
  *,*::before,*::after{animation-duration:.01ms!important;animation-iteration-count:1!important;animation-delay:0s!important;transition-duration:.1s!important;scroll-behavior:auto!important}
  .card-media{animation:none;background:var(--surface-2)}
  .card:has(.card-link:active) .card-media,.card:hover .card-media img{transform:none!important}
  .detail[open],.detail.is-closing,.sheet[open],#settings[open],.c-step.go-next,.c-step.go-prev{animation-name:fade!important;animation-duration:.1s!important}
  .detail.is-closing{opacity:0}
  #toast,#toast.show{transform:translate(-50%,0)}
  ::view-transition-group(*),::view-transition-old(*),::view-transition-new(*){animation:none!important}
}
@media (forced-colors: active){
  .chip[aria-pressed="true"]{border:2px solid Highlight}
  :focus-visible,.card-link:focus-visible::after{outline-color:Highlight}
  .box,.switch{border-color:CanvasText}
}
</style>
</head>
<body>
<!-- Iconos: Lucide (https://lucide.dev), licencia ISC. Copyright (c) Lucide Contributors -->
<svg class="sprite" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false">
<symbol id="i-search" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></symbol>
<symbol id="i-x" viewBox="0 0 24 24"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></symbol>
<symbol id="i-heart" viewBox="0 0 24 24"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/></symbol>
<symbol id="i-clock" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></symbol>
<symbol id="i-star" viewBox="0 0 24 24"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></symbol>
<symbol id="i-check" viewBox="0 0 24 24"><path d="M20 6 9 17l-5-5"/></symbol>
<symbol id="i-share" viewBox="0 0 24 24"><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/><path d="m16 6-4-4-4 4"/><path d="M12 2v13"/></symbol>
<symbol id="i-arrow-left" viewBox="0 0 24 24"><path d="m12 19-7-7 7-7"/><path d="M19 12H5"/></symbol>
<symbol id="i-arrow-right" viewBox="0 0 24 24"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></symbol>
<symbol id="i-chevron-down" viewBox="0 0 24 24"><path d="m6 9 6 6 6-6"/></symbol>
<symbol id="i-dices" viewBox="0 0 24 24"><rect width="12" height="12" x="2" y="10" rx="2" ry="2"/><path d="m17.92 14 3.5-3.5a2.24 2.24 0 0 0 0-3l-5-4.92a2.24 2.24 0 0 0-3 0L10 6"/><path d="M6 18h.01"/><path d="M10 14h.01"/><path d="M15 6h.01"/><path d="M18 9h.01"/></symbol>
<symbol id="i-more-horizontal" viewBox="0 0 24 24"><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/></symbol>
<symbol id="i-list" viewBox="0 0 24 24"><path d="M8 6h13"/><path d="M8 12h13"/><path d="M8 18h13"/><path d="M3 6h.01"/><path d="M3 12h.01"/><path d="M3 18h.01"/></symbol>
<symbol id="i-chef-hat" viewBox="0 0 24 24"><path d="M17 21a1 1 0 0 0 1-1v-5.35c0-.457.316-.844.727-1.041a4 4 0 0 0-2.134-7.589 5 5 0 0 0-9.186 0 4 4 0 0 0-2.134 7.588c.411.198.727.585.727 1.041V20a1 1 0 0 0 1 1Z"/><path d="M6 17h12"/></symbol>
<symbol id="i-external-link" viewBox="0 0 24 24"><path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/></symbol>
<symbol id="i-copy" viewBox="0 0 24 24"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></symbol>
<symbol id="i-minus" viewBox="0 0 24 24"><path d="M5 12h14"/></symbol>
<symbol id="i-plus" viewBox="0 0 24 24"><path d="M5 12h14"/><path d="M12 5v14"/></symbol>
<symbol id="i-download" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5"/><path d="M12 15V3"/></symbol>
<symbol id="i-upload" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m17 8-5-5-5 5"/><path d="M12 3v12"/></symbol>
<symbol id="i-trash" viewBox="0 0 24 24"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></symbol>
<symbol id="i-sun" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/></symbol>
<symbol id="i-moon" viewBox="0 0 24 24"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></symbol>
<symbol id="i-monitor" viewBox="0 0 24 24"><rect width="20" height="14" x="2" y="3" rx="2"/><path d="M8 21h8"/><path d="M12 17v4"/></symbol>
<symbol id="i-leaf" viewBox="0 0 24 24"><path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"/><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/></symbol>
</svg>

<a class="skip" href="#grid" data-action="skip">Saltar a las recetas</a>
<p class="visually-hidden live" id="live" role="status"></p>

<header class="masthead wrap" id="masthead">
  <p class="dateline" id="dateline" data-latest="__LATEST__"><a id="dateline-link" href="#lista">__COUNT__ recetas</a></p>
  <div class="mast-row">
    <h1 class="wordmark">Recetario</h1>
    <button type="button" class="icon-btn" data-action="settings" aria-label="Ajustes y mis datos"><svg class="ico" aria-hidden="true" focusable="false"><use href="#i-more-horizontal"/></svg></button>
  </div>
</header>

<div class="bar" id="bar">
  <div class="wrap bar-inner">
    <span class="mini-mark" aria-hidden="true">Recetario</span>
    <div class="search is-empty" id="search">
      <svg class="ico" aria-hidden="true" focusable="false"><use href="#i-search"/></svg>
      <input type="search" id="q" enterkeyhint="search" autocomplete="off" autocapitalize="off" spellcheck="false" aria-label="Buscar recetas" placeholder="Plato o ingredientes: pollo limón">
      <button type="button" class="icon-btn clear" data-action="clear-q" aria-label="Borrar búsqueda" hidden><svg class="ico" aria-hidden="true" focusable="false"><use href="#i-x"/></svg></button>
      <kbd aria-hidden="true">/</kbd>
    </div>
  </div>
</div>

<main id="lista" class="wrap" tabindex="-1">
  <h2 class="visually-hidden">Recetas</h2>
  <div class="filters">
    <div class="chip-row" id="row-a" role="group" aria-label="Mías y categorías"></div>
    <div class="chip-row" id="row-b" role="group" aria-label="Tiempo y tipo"></div>
  </div>
  <div class="resbar" id="resbar">
    <p id="count" aria-live="polite" tabindex="-1">__COUNT__ recetas</p>
    <span class="spacer"></span>
    <label class="sort"><span class="visually-hidden">Ordenar</span>
      <select id="sort">
        <option value="recent">Recientes</option>
        <option value="quick">Más rápidas</option>
        <option value="healthy">Más sanas</option>
        <option value="rating">Mejor valoradas</option>
        <option value="az">A–Z</option>
        <option value="random">Aleatorio</option>
      </select>
      <svg class="ico" aria-hidden="true" focusable="false"><use href="#i-chevron-down"/></svg>
    </label>
    <button type="button" class="btn" id="random" data-action="random" aria-label="¿Qué cocino hoy? Elegir una receta al azar"><svg class="ico" aria-hidden="true" focusable="false"><use href="#i-dices"/></svg><span class="lbl">¿Qué cocino hoy?</span></button>
  </div>
  <div class="active-row" id="active-row" role="group" aria-label="Filtros activos" hidden></div>
  <div class="grid" id="grid" tabindex="-1"></div>
  <div class="empty" id="empty" hidden></div>
  <noscript><p>Esta web necesita JavaScript para mostrar las recetas.</p></noscript>
</main>

<footer class="foot wrap">
  <p><span id="foot-txt">Tus favoritas se guardan solo en este dispositivo</span> · <button type="button" class="linkbtn" data-action="settings" data-focus="data">Mis datos</button></p>
</footer>

<template id="tpl-card">
<article class="card" data-id="">
  <div class="card-media" data-initial="">
    <img alt="" width="400" height="500" decoding="async">
    <span class="badge-new" hidden>Nueva</span>
    <span class="card-tags" aria-hidden="true"></span>
    <button type="button" class="fav-btn" data-action="fav" data-fav="" aria-pressed="false" aria-label=""><svg class="ico" aria-hidden="true" focusable="false"><use href="#i-heart"/></svg></button>
  </div>
  <p class="card-kicker"></p>
  <h3 class="card-title"><a class="card-link" data-action="open" href=""></a></h3>
  <p class="card-meta"></p>
  <p class="card-mine" hidden></p>
  <p class="card-match" hidden></p>
</article>
</template>

<template id="tpl-feature">
<article class="card card--feature" data-id="">
  <div class="card-media" data-initial="">
    <img alt="" width="800" height="800" decoding="async">
    <div class="feat-text">
      <p class="card-kicker"></p>
      <h3 class="card-title"><a class="card-link" data-action="open" href=""></a></h3>
      <p class="card-meta"></p>
    </div>
    <button type="button" class="fav-btn" data-action="fav" data-fav="" aria-pressed="false" aria-label=""><svg class="ico" aria-hidden="true" focusable="false"><use href="#i-heart"/></svg></button>
  </div>
</article>
</template>

<dialog id="detail" class="detail" aria-labelledby="d-title">
  <div class="d-topbar" id="d-topbar">
    <button type="button" class="tb-btn close-m" data-action="close" aria-label="Cerrar receta"><svg class="ico" aria-hidden="true" focusable="false"><use href="#i-arrow-left"/></svg></button>
    <p class="d-short" id="d-short" aria-hidden="true"></p>
    <button type="button" class="tb-btn" id="d-fav" data-action="fav" data-fav="" aria-pressed="false" aria-label="Favorita"><svg class="ico" aria-hidden="true" focusable="false"><use href="#i-heart"/></svg></button>
    <button type="button" class="tb-btn" data-action="share" aria-label="Compartir receta"><svg class="ico" aria-hidden="true" focusable="false"><use href="#i-share"/></svg></button>
    <button type="button" class="tb-btn close-d" data-action="close" aria-label="Cerrar receta"><svg class="ico" aria-hidden="true" focusable="false"><use href="#i-x"/></svg></button>
  </div>
  <div class="d-scroll" id="d-scroll">
    <div class="d-left" id="d-left">
      <div class="d-hero" id="d-hero" data-initial="">
        <img id="d-img" alt="" width="800" height="1000" decoding="async">
        <div class="d-hero-text" id="d-hero-text"></div>
      </div>
    </div>
    <div class="d-right" id="d-right">
      <div class="d-head" id="d-head">
        <p class="d-kicker" id="d-kicker"></p>
        <h2 class="d-title" id="d-title" tabindex="-1"></h2>
      </div>
      <p class="d-random" id="d-random" hidden><span id="d-random-txt"></span><span aria-hidden="true">·</span><button type="button" class="linkbtn" data-action="random-again">Otra</button></p>
      <div class="d-pills" id="d-pills"></div>
      <p class="d-split" id="d-split" hidden></p>
      <section class="d-ingr" id="d-ingr" aria-labelledby="h-ingr">
        <div class="sec-head"><h3 id="h-ingr" tabindex="-1">Ingredientes</h3><span class="prog" id="d-ingr-prog"></span><button type="button" class="linkbtn" id="d-uncheck" data-action="uncheck-all" hidden>Desmarcar todo</button></div>
        <ul class="ingr" id="d-ingr-list"></ul>
        <button type="button" class="switch-row wake-row" id="d-wake" role="switch" aria-checked="false" data-action="wake" hidden><span>Mantener la pantalla encendida</span><span class="switch" aria-hidden="true"></span></button>
      </section>
      <section class="d-steps" aria-labelledby="h-steps">
        <div class="sec-head"><h3 id="h-steps">Preparación</h3><span class="prog" id="d-steps-prog"></span></div>
        <ol class="steps" id="d-steps"></ol>
      </section>
      <section class="mine" aria-label="Tu receta">
        <div class="rate-row">
          <span class="lbl" aria-hidden="true">Tu nota</span>
          <div class="stars" id="d-stars" role="radiogroup" aria-label="Tu nota"></div>
          <span class="rate-txt" id="d-rate-txt"></span>
        </div>
        <button type="button" class="done-btn" id="d-done" data-action="done" aria-pressed="false">La he hecho</button>
      </section>
      <div class="d-cta" id="d-cta"><button type="button" class="cta-btn" data-action="cook"><svg class="ico" aria-hidden="true" focusable="false"><use href="#i-chef-hat"/></svg><span id="d-cta-txt">Empezar a cocinar</span></button></div>
      <footer class="d-foot">
        <button type="button" class="btn" data-action="copy-text"><svg class="ico" aria-hidden="true" focusable="false"><use href="#i-copy"/></svg>Copiar receta como texto</button>
        <a class="d-src" id="d-src" href="#" target="_blank" rel="noopener noreferrer" data-action="src" hidden><span id="d-src-txt">Ver receta original</span><svg class="ico" aria-hidden="true" focusable="false"><use href="#i-external-link"/></svg></a>
        <p class="d-added" id="d-added"></p>
      </footer>
    </div>
  </div>
  <p class="visually-hidden live" role="status"></p>
</dialog>

<dialog id="cook" class="cook" aria-label="Modo cocina">
  <p class="visually-hidden live" id="c-live" role="status"></p>
  <div class="c-top">
    <button type="button" class="c-btn" data-action="cook-close" aria-label="Salir del modo cocina"><svg class="ico" aria-hidden="true" focusable="false"><use href="#i-x"/></svg></button>
    <p id="c-label">Paso 1 de 1</p>
    <button type="button" class="c-btn" data-action="cook-ingr" aria-label="Ingredientes"><svg class="ico" aria-hidden="true" focusable="false"><use href="#i-list"/></svg><span class="lbl">Ingredientes</span></button>
    <button type="button" class="c-btn" id="c-dec" data-action="font-dec" aria-label="Letra más pequeña">A−</button>
    <button type="button" class="c-btn" id="c-inc" data-action="font-inc" aria-label="Letra más grande">A+</button>
  </div>
  <div class="c-prog" id="c-prog" role="progressbar" aria-label="Progreso" aria-valuemin="1" aria-valuemax="1" aria-valuenow="1"></div>
  <div class="c-body" id="c-body">
    <div class="c-step" id="c-step"><p class="c-num" id="c-num" aria-hidden="true">01</p><p class="c-txt" id="c-txt"></p></div>
    <div class="c-final" id="c-final" hidden>
      <h2>¡Listo!</h2>
      <p>¿Qué tal ha salido?</p>
      <div class="stars" id="c-stars" role="radiogroup" aria-label="Tu nota"></div>
      <div class="actions">
        <button type="button" class="btn btn-primary" id="c-mark" data-action="cook-mark">Marcar como hecha</button>
        <button type="button" class="btn" data-action="cook-skip">Ahora no</button>
      </div>
    </div>
  </div>
  <div class="c-nav" id="c-nav">
    <button type="button" class="c-prev" id="c-prev" data-action="cook-prev"><svg class="ico" aria-hidden="true" focusable="false"><use href="#i-arrow-left"/></svg>Anterior</button>
    <button type="button" class="c-next" id="c-next" data-action="cook-next"><span id="c-next-txt">Siguiente</span><svg class="ico" aria-hidden="true" focusable="false"><use href="#i-arrow-right"/></svg></button>
  </div>
</dialog>

<dialog id="cook-ingr" class="sheet" aria-labelledby="ci-title">
  <div class="sheet-head"><h2 id="ci-title">Ingredientes</h2><button type="button" class="icon-btn" data-action="close-sheet" aria-label="Cerrar ingredientes"><svg class="ico" aria-hidden="true" focusable="false"><use href="#i-x"/></svg></button></div>
  <div class="sheet-body"><ul class="ingr" id="ci-list"></ul></div>
  <p class="visually-hidden live" role="status"></p>
</dialog>

<dialog id="settings" class="sheet" aria-labelledby="s-title">
  <div class="sheet-head"><h2 id="s-title">Ajustes</h2><button type="button" class="icon-btn" data-action="close-sheet" aria-label="Cerrar ajustes"><svg class="ico" aria-hidden="true" focusable="false"><use href="#i-x"/></svg></button></div>
  <div class="sheet-body">
    <fieldset class="seg-wrap">
      <legend>Apariencia</legend>
      <div class="seg">
        <label><input type="radio" name="theme" value="auto"><svg class="ico" aria-hidden="true" focusable="false"><use href="#i-monitor"/></svg>Auto</label>
        <label><input type="radio" name="theme" value="light"><svg class="ico" aria-hidden="true" focusable="false"><use href="#i-sun"/></svg>Claro</label>
        <label><input type="radio" name="theme" value="dark"><svg class="ico" aria-hidden="true" focusable="false"><use href="#i-moon"/></svg>Oscuro</label>
      </div>
    </fieldset>
    <section aria-labelledby="s-data">
      <h3 id="s-data" tabindex="-1">Mis datos</h3>
      <p id="s-data-txt">Tus favoritas, notas y recetas hechas se guardan solo en este navegador. Descarga una copia para pasarlas a otro dispositivo.</p>
      <div class="s-actions">
        <button type="button" class="btn" data-action="export"><svg class="ico" aria-hidden="true" focusable="false"><use href="#i-download"/></svg>Descargar copia</button>
        <button type="button" class="btn" data-action="import"><svg class="ico" aria-hidden="true" focusable="false"><use href="#i-upload"/></svg>Importar copia</button>
        <input type="file" id="import-file" accept="application/json,.json" hidden>
        <button type="button" class="btn" id="wipe" data-action="wipe"><svg class="ico" aria-hidden="true" focusable="false"><use href="#i-trash"/></svg><span id="wipe-txt">Borrar mis datos</span></button>
      </div>
    </section>
    <section class="s-keys" aria-labelledby="s-keys">
      <h3 id="s-keys">Atajos</h3>
      <p><kbd class="k">/</kbd> buscar · <kbd class="k">←</kbd> <kbd class="k">→</kbd> en el modo cocina · <kbd class="k">Ctrl</kbd>+<kbd class="k">Z</kbd> deshacer el último aviso</p>
    </section>
    <p class="s-build" id="s-build" data-version="__VERSION__"></p>
  </div>
  <p class="visually-hidden live" role="status"></p>
</dialog>

<!-- Aviso visual; lo que se lee en voz alta va a la región .live del diálogo de arriba. -->
<div id="toast"></div>

<script type="application/json" id="config-data">__CONFIG_JSON__</script>
<script type="application/json" id="recipes-data">__RECIPES_JSON__</script>
<script>
(function () {
'use strict';

/* =========================================================
   Utilidades
   ========================================================= */
const $ = (sel, root) => (root || document).querySelector(sel);
const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));
const SVGNS = 'http://www.w3.org/2000/svg';
const mq = q => (window.matchMedia ? window.matchMedia(q) : { matches: false, addEventListener() {} });
const MQ_DESK = mq('(min-width: 900px)');
const MQ_REDUCE = mq('(prefers-reduced-motion: reduce)');
const MQ_COARSE = mq('(pointer: coarse)');
const reduced = () => MQ_REDUCE.matches;
const onMQ = (m, fn) => { try { m.addEventListener('change', fn); } catch (e) { try { m.addListener(fn); } catch (e2) {} } };

function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
function ssGet(k) { try { return sessionStorage.getItem(k); } catch (e) { return null; } }
function ssSet(k, v) { try { sessionStorage.setItem(k, v); } catch (e) {} }
function ssDel(k) { try { sessionStorage.removeItem(k); } catch (e) {} }
function readJSON(str, fallback) {
  if (!str) return fallback;
  try { const v = JSON.parse(str); return v == null ? fallback : v; } catch (e) { return fallback; }
}
function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
}
function icon(name, cls) {
  const s = document.createElementNS(SVGNS, 'svg');
  s.setAttribute('class', 'ico' + (cls ? ' ' + cls : ''));
  s.setAttribute('aria-hidden', 'true');
  s.setAttribute('focusable', 'false');
  const u = document.createElementNS(SVGNS, 'use');
  u.setAttribute('href', '#i-' + name);
  s.appendChild(u);
  return s;
}
const pad2 = n => (n < 10 ? '0' : '') + n;
const toInt = (v, max) => {
  const n = Math.round(Number(v));
  if (!isFinite(n) || n < 0) return 0;
  return max != null ? Math.min(n, max) : n;
};
const isTyping = t => !!t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName));

/* Normaliza carácter a carácter (misma longitud que el original) para poder resaltar. */
function norm(s) {
  s = String(s == null ? '' : s);
  let out = '';
  for (let i = 0; i < s.length; i++) {
    const c = (s[i].normalize('NFD')[0] || ' ').toLowerCase()[0];
    out += /[a-z0-9]/.test(c) ? c : ' ';
  }
  return out;
}

const DIFF = { easy: 'Fácil', medium: 'Media', hard: 'Difícil' };
function fmtTime(min) {
  if (min < 60) return min + ' min';
  const h = Math.floor(min / 60), m = min % 60;
  return m ? h + ' h ' + m + ' min' : h + ' h';
}
function fmtShort(ts) {
  try { return new Date(ts).toLocaleDateString('es-ES', { day: 'numeric', month: 'short' }).replace(/\.$/, ''); } catch (e) { return ''; }
}
function fmtLong(ts) {
  try { return new Date(ts).toLocaleDateString('es-ES', { day: 'numeric', month: 'long', year: 'numeric' }); } catch (e) { return ''; }
}
let RTF = null;
try { RTF = new Intl.RelativeTimeFormat('es', { numeric: 'auto' }); } catch (e) {}
function relTime(ts) {
  const diff = (ts - Date.now()) / 1000, abs = Math.abs(diff);
  const units = [['year', 31536000], ['month', 2592000], ['week', 604800], ['day', 86400], ['hour', 3600], ['minute', 60]];
  for (const [unit, secs] of units) {
    if (abs >= secs) return RTF ? RTF.format(Math.round(diff / secs), unit) : fmtShort(ts);
  }
  return 'ahora mismo';
}

/* =========================================================
   Datos
   ========================================================= */
// Si los datos no se pueden leer, se avisa en pantalla en lugar de mostrar una lista vacía.
let DATA_ERROR = false;
const RAW = (function () {
  try {
    const v = JSON.parse($('#recipes-data').textContent);
    if (Array.isArray(v)) return v;
  } catch (e) { console.error(e); }
  DATA_ERROR = true;
  return [];
})();
const CONFIG = readJSON($('#config-data').textContent, {});
const TAG_LABEL = CONFIG.tagLabel || {};
const CHIP_ORDER = CONFIG.chipOrder || [];
const HIDDEN_TAGS = new Set(CONFIG.hiddenTags || []);
const IMG_RE = /^images\/[\w.\-]+$/;
const URL_RE = /^https?:\/\//i;
const tagLabel = t => (Object.prototype.hasOwnProperty.call(TAG_LABEL, t) ? TAG_LABEL[t] : (t.charAt(0).toUpperCase() + t.slice(1)));
const TAG_ICON = CONFIG.tagIcon || {}, TAG_HUE = CONFIG.tagHue || {};
const own = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
// Emoji decorativo de la etiqueta (el nombre siempre va en texto al lado o en la etiqueta accesible).
function tagEmo(t) {
  if (!own(TAG_ICON, t)) return null;
  const s = el('span', 'emo', TAG_ICON[t]);
  s.setAttribute('aria-hidden', 'true');
  return s;
}
function setHue(node, t) { if (own(TAG_HUE, t)) node.style.setProperty('--h', String(TAG_HUE[t])); }

// Ids únicos y estables: la 1.ª aparición conserva el suyo (y sus favoritas);
// las repetidas reciben «~2», «~3»… Sin id, se deriva de título y fecha, no de la posición.
const seenIds = new Map();
function uniqueId(r, title, idx) {
  let id = r.id == null ? '' : String(r.id).trim();
  if (!id) id = (norm(title).trim().replace(/\s+/g, '-') || 'receta') + '@' + (String(r.created_at || '').trim() || idx);
  const n = (seenIds.get(id) || 0) + 1;
  seenIds.set(id, n);
  return n > 1 ? id + '~' + n : id;
}

const DATA = RAW.filter(r => r && typeof r === 'object').map((r, idx) => {
  const title = String(r.title || '').trim() || 'Receta sin título';
  const tags = Array.isArray(r.tags) ? r.tags.map(t => String(t).trim()).filter(Boolean) : [];
  const ingredients = (Array.isArray(r.ingredients) ? r.ingredients : []).filter(i => i && typeof i === 'object');
  const steps = (Array.isArray(r.steps) ? r.steps : []).map(s => String(s == null ? '' : s).trim()).filter(Boolean);
  const prep = toInt(r.prep_time_min), cook = toInt(r.cook_time_min);
  const ts = Date.parse(r.created_at);
  const image = typeof r.image === 'string' && IMG_RE.test(r.image) ? r.image : '';
  const source = typeof r.source === 'string' && URL_RE.test(r.source.trim()) ? r.source.trim() : '';
  // Encuadre vertical opcional de la foto (0 = arriba, 100 = abajo).
  const fy = r.image_focus_y;
  const focusY = typeof fy === 'number' && isFinite(fy) && fy >= 0 && fy <= 100 ? fy : null;
  return {
    id: uniqueId(r, title, idx), title, displayTitle: title, a11yTitle: title, dupNote: '', tags, ingredients, steps,
    prep, cook, total: prep + cook, ts: isNaN(ts) ? 0 : ts,
    diff: String(r.difficulty || ''), health: toInt(r.health_score, 10), image, focusY, source,
    nTitle: norm(title),
    nTags: norm(tags.map(t => t + ' ' + tagLabel(t)).join(' | ')),
    nIngr: ingredients.map(i => norm(i.name)),
  };
});
const BY_ID = new Map(DATA.map(d => [d.id, d]));

// Títulos repetidos: el título no cambia; la fecha va en la línea de categoría y en las etiquetas accesibles.
(function () {
  const groups = new Map();
  DATA.forEach(d => {
    const k = d.nTitle.replace(/\s+/g, ' ').trim();
    if (!groups.has(k)) groups.set(k, []);
    groups.get(k).push(d);
  });
  groups.forEach(list => {
    if (list.length < 2) return;
    list.forEach(d => {
      if (!d.ts) return;
      d.dupNote = 'añadida ' + fmtShort(d.ts).replace(/\s+/g, ' ');
      d.a11yTitle = d.title + ' (' + d.dupNote + ')';
    });
  });
})();

// Etiquetas: primero CHIP_ORDER, después el resto por número de recetas.
const TAG_COUNT = new Map();
DATA.forEach(d => d.tags.forEach(t => TAG_COUNT.set(t, (TAG_COUNT.get(t) || 0) + 1)));
const CHIP_TAGS = CHIP_ORDER.filter(t => TAG_COUNT.has(t)).concat(
  Array.from(TAG_COUNT.keys())
    .filter(t => !CHIP_ORDER.includes(t) && !HIDDEN_TAGS.has(t))
    .sort((a, b) => (TAG_COUNT.get(b) - TAG_COUNT.get(a)) || a.localeCompare(b, 'es'))
);
const CHIP_TAG_SET = new Set(CHIP_TAGS);
function kickerTag(d) {
  for (const t of CHIP_ORDER) if (d.tags.includes(t)) return t;
  return d.tags.find(t => !HIDDEN_TAGS.has(t)) || '';
}
const LATEST = DATA.reduce((a, d) => (!a || d.ts > a.ts ? d : a), null);

/* =========================================================
   Store: datos personales (favoritas, nota, hecha).
   Ahora en localStorage; mañana, un backend (p. ej. Supabase)
   sin tocar la interfaz. Getters síncronos, setters asíncronos.
   ========================================================= */
const STORE_KEY = 'recetario:v1';
const Store = (function () {
  // Mapas sin prototipo: un id como «constructor» o «__proto__» no hereda nada de Object.prototype.
  const map = () => Object.create(null);
  const blank = () => ({ fav: map(), rating: map(), cooked: map() });
  const copy = m => Object.assign(map(), m);
  const has = (m, k) => Object.prototype.hasOwnProperty.call(m, k);
  let data = blank();
  const subs = new Set();
  const obj = x => (x && typeof x === 'object' && !Array.isArray(x) ? x : {});
  function sanitize(o) {
    const out = blank();
    o = obj(o);
    const fav = obj(o.fav), rating = obj(o.rating), cooked = obj(o.cooked);
    Object.keys(fav).forEach(k => { if (k && fav[k] === true) out.fav[k] = true; });
    Object.keys(rating).forEach(k => {
      const v = rating[k];
      if (k && Number.isInteger(v) && v >= 1 && v <= 5) out.rating[k] = v;
    });
    Object.keys(cooked).forEach(k => {
      const v = cooked[k];
      if (k && typeof v === 'string' && !isNaN(Date.parse(v))) out.cooked[k] = v;
    });
    return out;
  }
  function load() { data = sanitize(readJSON(lsGet(STORE_KEY), null)); }
  function save() {
    try { localStorage.setItem(STORE_KEY, JSON.stringify({ v: 1, fav: data.fav, rating: data.rating, cooked: data.cooked })); } catch (e) { /* sigue en memoria */ }
  }
  function emit(ev) { subs.forEach(fn => { try { fn(ev); } catch (e) { console.error(e); } }); }
  return {
    user: null, // reservado para el usuario autenticado
    persistent: true, // false si el navegador no deja guardar (datos de sitios bloqueados)
    async init() {
      try {
        localStorage.setItem('recetario:probe', '1');
        localStorage.removeItem('recetario:probe');
        this.persistent = true;
      } catch (e) { this.persistent = false; }
      load();
      window.addEventListener('storage', e => { if (e.key === STORE_KEY) { load(); emit({ type: 'all' }); } });
    },
    isFavorite(id) { return has(data.fav, id) && data.fav[id] === true; },
    async setFavorite(id, on) {
      if (on) data.fav[id] = true; else delete data.fav[id];
      save(); emit({ type: 'fav', id });
    },
    getRating(id) { return has(data.rating, id) ? data.rating[id] : 0; },
    async setRating(id, n) {
      n = Math.max(0, Math.min(5, Math.round(Number(n) || 0)));
      if (n) data.rating[id] = n; else delete data.rating[id];
      save(); emit({ type: 'rating', id });
    },
    // Devuelve la fecha ISO de la última vez (verdadero) o null (falso).
    getCooked(id) { return has(data.cooked, id) ? data.cooked[id] : null; },
    // Acepta una fecha ISO, true (ahora) o false/null (desmarcar).
    async setCooked(id, v) {
      const iso = v === true ? new Date().toISOString() : (typeof v === 'string' && !isNaN(Date.parse(v)) ? v : null);
      if (iso) data.cooked[id] = iso; else delete data.cooked[id];
      save(); emit({ type: 'cooked', id });
    },
    onChange(fn) { subs.add(fn); return () => subs.delete(fn); },
    exportData() {
      return { app: 'recetario', exported_at: new Date().toISOString(), v: 1,
        fav: copy(data.fav), rating: copy(data.rating), cooked: copy(data.cooked) };
    },
    // Fusiona una copia: la nota local gana y de «hecha» se queda la fecha más reciente.
    // Solo cuenta lo que cambia de verdad; isKnown(id) permite ignorar recetas que ya no existen.
    async importData(o, isKnown) {
      if (!o || typeof o !== 'object' || o.v !== 1) throw new Error('Formato no válido');
      const inc = sanitize(o);
      const ok = k => !isKnown || isKnown(k);
      const n = { fav: 0, rating: 0, cooked: 0 };
      Object.keys(inc.fav).forEach(k => {
        if (ok(k) && !has(data.fav, k)) { data.fav[k] = true; n.fav++; }
      });
      Object.keys(inc.rating).forEach(k => {
        if (ok(k) && !has(data.rating, k)) { data.rating[k] = inc.rating[k]; n.rating++; }
      });
      Object.keys(inc.cooked).forEach(k => {
        if (ok(k) && (!has(data.cooked, k) || Date.parse(inc.cooked[k]) > Date.parse(data.cooked[k]))) {
          data.cooked[k] = inc.cooked[k]; n.cooked++;
        }
      });
      if (n.fav + n.rating + n.cooked) { save(); emit({ type: 'all' }); }
      return n;
    },
    async clear() { data = blank(); save(); emit({ type: 'all' }); },
  };
})();

/* =========================================================
   Cantidades
   ========================================================= */
const NOTE_RE = /^(al gusto|opcional|seg[uú]n receta|un poco|para .+)$/i;
const NUM_RE = /^\d+(?:[.,]\d+)?$/;
const FRAC_RE = /^\d+\/\d+$/;
const RANGE_RE = /^\d+(?:[.,]\d+)?\s*-\s*\d+(?:[.,]\d+)?$/;
const OMIT_UNITS = new Set(['unidad', 'unidades']);
const GLYPH = { 0.25: '¼', 0.5: '½', 0.75: '¾' };
function fmtNum(s) {
  if (RANGE_RE.test(s)) return s.replace(/\s+/g, '');
  let v;
  if (FRAC_RE.test(s)) {
    const p = s.split('/').map(Number);
    if (!p[1]) return s;
    v = p[0] / p[1];
  } else v = parseFloat(s.replace(',', '.'));
  if (!isFinite(v)) return s;
  const whole = Math.floor(v), frac = Math.round((v - whole) * 100) / 100;
  if (GLYPH[frac]) return (whole ? whole : '') + GLYPH[frac];
  if (Number.isInteger(v)) return String(v);
  return String(Math.round(v * 100) / 100).replace('.', ',');
}
function formatQty(quantity, unit) {
  const qs = String(quantity == null ? '' : quantity).trim();
  let u = String(unit == null ? '' : unit).trim();
  let extra = '';
  // «cucharada (para la salsa)» → unidad «cucharada» y nota «para la salsa»
  const par = u.match(/^(.*?)\s*\(([^()]+)\)$/);
  if (par) { u = par[1].trim(); extra = par[2].trim(); }
  const join = (a, b) => [a, b].filter(Boolean).join(' · ');
  const omit = OMIT_UNITS.has(u.toLowerCase());
  if (NUM_RE.test(qs) || FRAC_RE.test(qs) || RANGE_RE.test(qs)) {
    const num = fmtNum(qs);
    if (!u || omit) return { q: num, note: extra };
    if (NOTE_RE.test(u)) return { q: num, note: join(u, extra) };
    return { q: num + ' ' + u, note: extra };
  }
  if (!qs) return { q: '', note: join(omit ? '' : u, extra) };
  if (NOTE_RE.test(qs) || qs.length > 12) return { q: '', note: join(omit ? qs : [qs, u].filter(Boolean).join(' '), extra) };
  return { q: omit || !u ? qs : qs + ' ' + u, note: extra };
}

/* =========================================================
   Búsqueda, filtros y orden
   ========================================================= */
const STOP = new Set('de del con y la el los las al a en un una para'.split(' '));
function stem(t) {
  if (t.length > 4 && t.endsWith('es')) return t.slice(0, -2);
  if (t.length > 3 && t.endsWith('s')) return t.slice(0, -1);
  return t;
}
function tokenize(q) {
  let toks = norm(q).split(/\s+/).filter(t => t.length >= 2);
  const content = toks.filter(t => !STOP.has(t));
  if (content.length) toks = content;
  return Array.from(new Set(toks.map(stem)));
}
function matchRecipe(d, toks) {
  let score = 0;
  const hits = [];
  for (const t of toks) {
    if (d.nTitle.includes(t)) score += 3;
    else if (d.nTags.includes(t)) score += 2;
    else {
      let found = false;
      d.nIngr.forEach((n, i) => { if (n.includes(t)) { found = true; if (!hits.includes(i)) hits.push(i); } });
      if (!found) return null;
      score += 1;
    }
  }
  return { score, hits };
}

const SORTS = {
  recent: (a, b) => b.ts - a.ts,
  quick: (a, b) => (a.total - b.total) || (b.ts - a.ts),
  healthy: (a, b) => (b.health - a.health) || (a.total - b.total),
  rating: (a, b) => (Store.getRating(b.id) - Store.getRating(a.id)) ||
    ((Store.isFavorite(b.id) ? 1 : 0) - (Store.isFavorite(a.id) ? 1 : 0)) || (b.ts - a.ts),
  az: (a, b) => a.displayTitle.localeCompare(b.displayTitle, 'es', { sensitivity: 'base' }) || (b.ts - a.ts),
  random: (a, b) => (randKey.get(a.id) || 0) - (randKey.get(b.id) || 0),
};
const SORT_KEYS = Object.keys(SORTS);

// Orden aleatorio estable dentro de la sesión (mulberry32).
let randKey = new Map();
function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function setSeed(seed) {
  const rnd = mulberry32(seed);
  randKey = new Map(DATA.map(d => [d.id, rnd()]));
}
function newSeed() {
  const seed = (Math.random() * 4294967296) >>> 0;
  ssSet('recetario:seed', String(seed));
  setSeed(seed);
}
(function () {
  const s = parseInt(ssGet('recetario:seed'), 10);
  if (isFinite(s)) setSeed(s); else newSeed();
})();

const defaultState = () => ({ q: '', tags: [], mine: null, max: null, easy: false, sano: false, sort: 'recent' });
const state = defaultState();
const hasFilters = s => !!(s.q.trim() || s.tags.length || s.mine || s.max || s.easy || s.sano);

function passes(d, s) {
  if (s.mine === 'fav' && !Store.isFavorite(d.id)) return false;
  if (s.mine === 'done' && !Store.getCooked(d.id)) return false;
  for (const t of s.tags) if (!d.tags.includes(t)) return false;
  if (s.max && d.total > s.max) return false;
  if (s.easy && d.diff !== 'easy') return false;
  if (s.sano && d.health < 8) return false;
  return true;
}
function compute(s) {
  const toks = tokenize(s.q);
  const list = [];
  for (const d of DATA) {
    if (!passes(d, s)) continue;
    let m = null;
    if (toks.length) { m = matchRecipe(d, toks); if (!m) continue; }
    list.push({ d, m });
  }
  return { list, toks };
}
// byScore: la relevancia de la búsqueda solo manda con el orden por defecto («Relevancia»).
function sortList(list, sort, byScore) {
  const cmp = SORTS[sort] || SORTS.recent;
  list.sort((a, b) => (byScore ? (b.m.score - a.m.score) : 0) || cmp(a.d, b.d));
  return list;
}

/* =========================================================
   Toasts
   ========================================================= */
const toastEl = $('#toast');
let toastTimer = 0, toastLeft = 0, toastStarted = 0, toastFn = null, toastReturn = null;
const DIALOGS = ['cook-ingr', 'settings', 'cook', 'detail'].map(id => document.getElementById(id));
const topDialog = () => DIALOGS.find(d => d && d.open) || null;

// Regiones vivas fijas (una por diálogo): un modal deja inerte lo de fuera.
const liveRegion = host => (host && host !== document.body ? $('.live', host) : $('#live'));
function say(region, msg) {
  if (!region) return;
  clearTimeout(region._t);
  region.textContent = '';
  // En otra tarea, para que el lector lo anuncie aunque la región acabe de hacerse visible.
  region._t = setTimeout(() => { region.textContent = msg; }, 60);
}

// El aviso vive dentro del diálogo de arriba (fuera de él sería inerte).
function placeToast() {
  const host = topDialog() || document.body;
  if (toastEl.parentNode !== host) host.appendChild(toastEl);
  const ctaH = host.id === 'detail' && !MQ_DESK.matches && !$('#d-cta').hidden ? '80px' : '0px';
  toastEl.style.setProperty('--cta-h', ctaH);
  return host;
}
// Tras cerrar un diálogo, el aviso baja al siguiente; si le queda poco, se le da tiempo para «Deshacer».
function rehostToast() {
  if (toastEl.parentNode === (topDialog() || document.body)) return;
  placeToast();
  if (toastFn && toastEl.classList.contains('show') && toastLeft - (Date.now() - toastStarted) < 2000) armToast(3000);
}
function hideToast() {
  clearTimeout(toastTimer);
  toastEl.classList.remove('show');
  toastFn = null;
  setTimeout(() => { if (!toastEl.classList.contains('show')) toastEl.textContent = ''; }, 250);
}
function armToast(ms) {
  clearTimeout(toastTimer);
  toastLeft = ms; toastStarted = Date.now();
  toastTimer = setTimeout(hideToast, ms);
}
function toast(msg, actionLabel, action) {
  const host = placeToast();
  const ae = document.activeElement;
  toastReturn = ae && ae !== document.body && !toastEl.contains(ae) ? ae : null;
  toastEl.textContent = '';
  toastEl.appendChild(el('span', 't-msg', msg));
  toastFn = typeof action === 'function' ? action : null;
  toastEl.classList.toggle('no-act', !toastFn);
  if (toastFn) {
    const b = el('button', 'toast-act', actionLabel || 'Deshacer');
    b.type = 'button';
    b.dataset.action = 'toast-act';
    toastEl.appendChild(b);
  }
  void toastEl.offsetWidth;
  toastEl.classList.add('show');
  say(liveRegion(host), toastFn ? msg + '. ' + (actionLabel || 'Deshacer') + ' disponible.' : msg);
  armToast(toastFn ? 10000 : 4000);
}
// Ejecuta la acción del aviso y devuelve el foco a donde estaba si estaba en el aviso.
function runToastAction() {
  const fn = toastFn, back = toastReturn, hadFocus = toastEl.contains(document.activeElement);
  hideToast();
  if (fn) fn();
  if (!hadFocus) return;
  const dlg = topDialog();
  const target = back && back.isConnected && back.offsetParent !== null ? back
    : (dlg ? dlg.querySelector('h2[tabindex="-1"], button') : $('#count'));
  if (target) { try { target.focus({ preventScroll: true }); } catch (e) {} }
}
const pauseToast = () => {
  if (!toastEl.classList.contains('show')) return;
  clearTimeout(toastTimer);
  toastLeft = Math.max(1200, toastLeft - (Date.now() - toastStarted));
};
const resumeToast = () => { if (toastEl.classList.contains('show')) armToast(toastLeft); };
toastEl.addEventListener('mouseenter', pauseToast);
toastEl.addEventListener('mouseleave', resumeToast);
toastEl.addEventListener('focusin', pauseToast);
toastEl.addEventListener('focusout', resumeToast);
// Ctrl/Cmd+Z deshace mientras hay un aviso con acción (llegar al botón con Tab puede costar mucho).
document.addEventListener('keydown', e => {
  if (!(e.ctrlKey || e.metaKey) || e.shiftKey || e.altKey || (e.key !== 'z' && e.key !== 'Z')) return;
  if (!toastFn || !toastEl.classList.contains('show') || isTyping(e.target)) return;
  e.preventDefault();
  runToastAction();
});

/* =========================================================
   Tarjetas
   ========================================================= */
const grid = $('#grid');
const tplCard = $('#tpl-card');
const tplFeature = $('#tpl-feature');
const cardNodes = new Map();
let FEATURE = null;
const DAY = 864e5;

function initialOf(d) { return (Array.from(d.displayTitle.trim())[0] || 'R').toUpperCase(); }
function fillMeta(p, d) {
  p.textContent = '';
  const parts = [fmtTime(d.total)];
  if (DIFF[d.diff]) parts.push(DIFF[d.diff]);
  parts.push('Salud ' + d.health);
  p.append(icon('clock'), document.createTextNode(parts.join(' · ')));
}
function setTitle(node, text, toks) {
  node.textContent = '';
  const ranges = [];
  if (toks && toks.length) {
    const n = norm(text);
    toks.forEach(t => { let i = n.indexOf(t); while (i > -1) { ranges.push([i, i + t.length]); i = n.indexOf(t, i + 1); } });
  }
  if (!ranges.length) { node.textContent = text; return; }
  ranges.sort((a, b) => a[0] - b[0]);
  const merged = [];
  ranges.forEach(r => {
    const last = merged[merged.length - 1];
    if (last && r[0] <= last[1]) last[1] = Math.max(last[1], r[1]); else merged.push(r.slice());
  });
  let pos = 0;
  merged.forEach(([a, b]) => {
    if (a > pos) node.appendChild(document.createTextNode(text.slice(pos, a)));
    node.appendChild(el('mark', null, text.slice(a, b)));
    pos = b;
  });
  if (pos < text.length) node.appendChild(document.createTextNode(text.slice(pos)));
}
function buildCard(d, tpl) {
  const node = tpl.content.firstElementChild.cloneNode(true);
  node.dataset.id = d.id;
  const media = $('.card-media', node);
  const img = $('img', media);
  img.addEventListener('load', () => imgLoaded(img));
  img.addEventListener('error', () => imgBroken(img));
  media.dataset.initial = initialOf(d);
  if (!d.image) media.classList.add('is-broken');
  if (d.focusY != null) img.style.setProperty('--img-y', d.focusY + '%');
  const link = $('.card-link', node);
  link.setAttribute('href', '#r=' + encodeURIComponent(d.id));
  link.dataset.id = d.id;
  link.textContent = d.displayTitle;
  const kt = kickerTag(d);
  $('.card-kicker', node).textContent = [kt ? tagLabel(kt) : '', d.dupNote].filter(Boolean).join(' · ');
  const tagBox = $('.card-tags', node);
  if (tagBox) {
    d.tags.filter(t => !HIDDEN_TAGS.has(t)).slice(0, 4).forEach(t => {
      const e = tagEmo(t);
      if (e) tagBox.appendChild(e);
    });
  }
  fillMeta($('.card-meta', node), d);
  const fav = $('.fav-btn', node);
  fav.dataset.fav = d.id;
  fav.dataset.id = d.id;
  fav.setAttribute('aria-label', 'Favorita: ' + d.a11yTitle);
  fav.setAttribute('aria-pressed', String(Store.isFavorite(d.id)));
  const badge = $('.badge-new', node);
  if (badge && d.ts && Date.now() - d.ts < 14 * DAY) badge.hidden = false;
  return node;
}
// Asigna la foto la primera vez que la tarjeta se pinta.
function ensureImg(node, d, eager) {
  const img = $('img', node);
  if (!d.image || img.dataset.set) return syncImg(node);
  img.dataset.set = '1';
  img.setAttribute('loading', eager ? 'eager' : 'lazy');
  if (eager) img.setAttribute('fetchpriority', 'high');
  img.src = d.image;
  syncImg(node);
}
// Solo marca como cargada: «complete» no es fiable para detectar fotos rotas con loading=lazy.
function syncImg(node) {
  const img = $('img', node);
  if (img.dataset.set && img.complete && img.naturalWidth > 0) imgLoaded(img);
}
function imgLoaded(img) {
  img.classList.add('is-loaded');
  const m = img.closest('.card-media, .d-hero');
  if (m) { m.classList.add('is-done'); m.classList.remove('is-broken'); }
}
function imgBroken(img) {
  const m = img.closest('.card-media, .d-hero');
  if (m && img.getAttribute('src')) m.classList.add('is-broken');
}
// Carga y error de imágenes, en captura porque estos eventos no burbujean.
document.addEventListener('load', e => { if (e.target && e.target.tagName === 'IMG') imgLoaded(e.target); }, true);
document.addEventListener('error', e => { if (e.target && e.target.tagName === 'IMG') imgBroken(e.target); }, true);

function fillMine(p, id) {
  const c = Store.getCooked(id), r = Store.getRating(id);
  p.textContent = '';
  p.hidden = !c && !r;
  if (c) {
    const s = el('span', 'done');
    s.append(icon('check'), document.createTextNode('Hecha'));
    p.appendChild(s);
  }
  if (r) {
    const s = el('span', 'rate');
    s.append(el('span', 'visually-hidden', 'Tu nota'), icon('star'), document.createTextNode(String(r)), el('span', 'visually-hidden', ' de 5'));
    p.appendChild(s);
  }
}
function updateCard(node, d, m, toks) {
  node.classList.remove('is-stale');
  setTitle($('.card-link', node), d.displayTitle, toks);
  const mine = $('.card-mine', node);
  if (mine) fillMine(mine, d.id);
  const match = $('.card-match', node);
  if (match) {
    const names = [];
    if (m && m.hits.length) m.hits.forEach(i => {
      const n = String(d.ingredients[i].name || '').trim();
      if (n && !names.includes(n) && names.length < 3) names.push(n);
    });
    match.hidden = !names.length;
    match.textContent = names.length ? 'Lleva: ' + names.join(', ') : '';
  }
  $('.fav-btn', node).setAttribute('aria-pressed', String(Store.isFavorite(d.id)));
}
function updateFeatureKicker() {
  if (!FEATURE) return;
  $('.card-kicker', FEATURE).textContent = 'Lo último' + (LATEST.ts ? ' · ' + relTime(LATEST.ts) : '');
}
// La portada no está en cardNodes: su corazón se sincroniza aparte (también estando fuera del DOM).
function syncFeatureFav() {
  if (FEATURE && LATEST) $('.fav-btn', FEATURE).setAttribute('aria-pressed', String(Store.isFavorite(LATEST.id)));
}

/* =========================================================
   Chips
   ========================================================= */
const rowA = $('#row-a'), rowB = $('#row-b');
const chips = [];
function chip(kind, value, label, ownIcon, hue) {
  const b = el('button', 'chip');
  b.type = 'button';
  b.dataset.action = 'chip';
  b.dataset.kind = kind;
  b.dataset.value = value;
  b.dataset.label = label;
  b.setAttribute('aria-pressed', 'false');
  b.appendChild(icon('check', 'chk'));
  if (ownIcon) b.appendChild(icon(ownIcon, 'own'));
  if (kind === 'tag') {
    const e = tagEmo(value);
    if (e) b.appendChild(e);
    setHue(b, value);
  }
  if (hue != null) b.style.setProperty('--h', String(hue));
  b.appendChild(el('span', 'l', label));
  b.appendChild(el('span', 'n'));
  chips.push(b);
  return b;
}
const sep = () => { const s = el('span', 'sep'); s.setAttribute('aria-hidden', 'true'); return s; };
function buildChips() {
  rowA.append(chip('mine', 'fav', 'Favoritas', 'heart', 350), chip('mine', 'done', 'Hechas', 'check', 150), sep());
  CHIP_TAGS.forEach(t => rowA.appendChild(chip('tag', t, tagLabel(t))));
  // Sin chip «Cualquier tiempo»: se quita el límite volviendo a pulsar el chip activo.
  rowB.append(chip('max', '15', '≤15 min'), chip('max', '30', '≤30 min'),
    chip('max', '45', '≤45 min'), sep(), chip('easy', '1', 'Solo fáciles'), chip('sano', '1', 'Sanas ≥8'));
  [rowA, rowB].forEach(row => {
    const upd = () => row.classList.toggle('has-more', row.scrollLeft + row.clientWidth < row.scrollWidth - 2);
    row.addEventListener('scroll', upd, { passive: true });
    window.addEventListener('resize', upd);
    upd();
    // Rueda vertical del ratón → desplazamiento horizontal de la fila (si desborda y no está en un extremo).
    row.addEventListener('wheel', e => {
      if (e.deltaX || e.ctrlKey || e.shiftKey || row.scrollWidth <= row.clientWidth) return;
      const dy = e.deltaY * (e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? row.clientWidth : 1);
      const next = Math.max(0, Math.min(row.scrollWidth - row.clientWidth, row.scrollLeft + dy));
      if (next === row.scrollLeft) return;
      e.preventDefault();
      row.scrollLeft = next;
    }, { passive: false });
  });
}
// Lleva a la vista el primer chip activo de cada fila desplazable (al cargar o volver con Atrás).
function revealActiveChips() {
  [rowA, rowB].forEach(row => {
    if (row.scrollWidth <= row.clientWidth) return;
    const a = row.querySelector('.chip[aria-pressed="true"]');
    if (a) row.scrollLeft = Math.max(0, a.offsetLeft - row.offsetLeft - 16);
  });
}
const favCount = () => DATA.reduce((n, d) => n + (Store.isFavorite(d.id) ? 1 : 0), 0);
const doneCount = () => DATA.reduce((n, d) => n + (Store.getCooked(d.id) ? 1 : 0), 0);
function setChip(b, active, n) {
  b.setAttribute('aria-pressed', String(active));
  const label = b.dataset.label;
  $('.n', b).textContent = n == null ? '' : String(n);
  // aria-disabled (no disabled): un chip desactivado no pierde el foco ni sale del orden de tabulación.
  if (!active && n === 0 && b.dataset.kind !== 'mine') b.setAttribute('aria-disabled', 'true');
  else b.removeAttribute('aria-disabled');
  b.setAttribute('aria-label', n == null ? label : label + ', ' + n + (n === 1 ? ' receta' : ' recetas'));
}
function updateMineChips() {
  chips.forEach(b => {
    if (b.dataset.kind !== 'mine') return;
    const v = b.dataset.value;
    setChip(b, state.mine === v, v === 'fav' ? favCount() : doneCount());
  });
}
function updateChips(list) {
  const count = s => compute(s).list.length;
  chips.forEach(b => {
    const k = b.dataset.kind, v = b.dataset.value;
    if (k === 'tag') {
      const on = state.tags.includes(v);
      setChip(b, on, on ? list.length : list.reduce((n, x) => n + (x.d.tags.includes(v) ? 1 : 0), 0));
    } else if (k === 'max') {
      const M = Number(v);
      setChip(b, state.max === M, count(Object.assign({}, state, { max: M })));
    } else if (k === 'easy' || k === 'sano') {
      setChip(b, state[k], state[k] ? list.length : count(Object.assign({}, state, { [k]: true })));
    }
  });
  updateMineChips();
}

/* =========================================================
   Render de la lista
   ========================================================= */
const countEl = $('#count'), emptyEl = $('#empty'), activeRow = $('#active-row');
const sortRecentOpt = $('#sort option[value="recent"]');
let current = [];
const recetas = n => n + (n === 1 ? ' receta' : ' recetas');
function renderCount(n, total, filtered) {
  countEl.textContent = '';
  if (!filtered) { countEl.textContent = recetas(total); return; }
  // Texto completo para lectores de pantalla; versión corta solo visual en móvil estrecho.
  const long = el('span', 'cnt-l', n + ' de ' + recetas(total)), short = el('span', 'cnt-s', n + ' de ' + total);
  long.setAttribute('aria-hidden', 'true');
  short.setAttribute('aria-hidden', 'true');
  countEl.append(el('span', 'visually-hidden', n + ' de ' + recetas(total)), long, short);
}
// Fila con los filtros activos («Merienda ×») y «Limpiar».
function renderActive() {
  activeRow.textContent = '';
  const items = [];
  if (state.mine) items.push(['mine', state.mine === 'fav' ? 'Favoritas' : 'Hechas']);
  state.tags.forEach(t => items.push(['tag:' + t, tagLabel(t)]));
  if (state.max) items.push(['max', '≤' + state.max + ' min']);
  if (state.easy) items.push(['easy', 'Solo fáciles']);
  if (state.sano) items.push(['sano', 'Sanas ≥8']);
  activeRow.hidden = !items.length;
  if (!items.length) return;
  items.forEach(([key, label]) => {
    const b = el('button', 'act-pill');
    b.type = 'button';
    b.dataset.action = 'remove-filter';
    b.dataset.value = key;
    b.setAttribute('aria-label', 'Quitar filtro ' + label);
    b.append(document.createTextNode(label), icon('x'));
    activeRow.appendChild(b);
  });
  const clr = el('button', 'linkbtn', 'Limpiar');
  clr.type = 'button';
  clr.dataset.action = 'clear-filters';
  clr.setAttribute('aria-label', 'Quitar todos los filtros');
  activeRow.appendChild(clr);
}
function render(intro) {
  const res = compute(state);
  const searching = res.toks.length > 0;
  // Con búsqueda, la relevancia solo manda con el orden por defecto; si eliges otro orden, se respeta.
  const list = sortList(res.list, state.sort, searching && state.sort === 'recent');
  sortRecentOpt.textContent = searching ? 'Relevancia' : 'Recientes';
  current = list;
  const isDefault = !hasFilters(state) && state.sort === 'recent' && !!FEATURE;
  const frag = document.createDocumentFragment();
  let k = 0;
  if (isDefault) { ensureImg(FEATURE, LATEST, true); syncFeatureFav(); k++; frag.appendChild(FEATURE); }
  list.forEach(({ d, m }) => {
    if (isDefault && d === LATEST) return;
    const node = cardNodes.get(d.id);
    updateCard(node, d, m, res.toks);
    ensureImg(node, d, k++ < 4);
    frag.appendChild(node);
  });
  grid.textContent = '';
  grid.appendChild(frag);
  if (intro && !reduced()) { grid.classList.add('intro'); setTimeout(() => grid.classList.remove('intro'), 900); }

  renderCount(list.length, DATA.length, hasFilters(state));
  renderActive();
  updateChips(list);
  renderEmpty(list.length);
}

function filterLabel(key) {
  if (key === 'q') return '«' + state.q.trim() + '»';
  if (key.startsWith('tag:')) return '«' + tagLabel(key.slice(4)) + '»';
  return { mine: state.mine === 'fav' ? '«Favoritas»' : '«Hechas»', max: '«≤' + state.max + ' min»', easy: '«Solo fáciles»', sano: '«Sanas ≥8»' }[key];
}
function withoutFilter(s, key) {
  const c = Object.assign({}, s, { tags: s.tags.slice() });
  if (key === 'q') c.q = '';
  else if (key.startsWith('tag:')) c.tags = c.tags.filter(t => t !== key.slice(4));
  else if (key === 'mine') c.mine = null;
  else if (key === 'max') c.max = null;
  else c[key] = false;
  return c;
}
function emptyBlock(iconName, cls, title, text) {
  const ic = el('div', 'empty-icon' + (cls ? ' ' + cls : ''));
  ic.appendChild(icon(iconName));
  emptyEl.append(ic, el('h3', null, title), el('p', null, text));
}
function renderEmpty(n) {
  emptyEl.textContent = '';
  if (DATA_ERROR) {
    emptyEl.hidden = false;
    emptyBlock('x', '', 'No se pudieron cargar las recetas.', 'Prueba a recargar la página. Si sigue igual, avisa a quien mantiene el recetario.');
    return;
  }
  emptyEl.hidden = n > 0;
  if (n > 0) return;
  const actions = el('div', 'actions');
  if (state.mine === 'fav' && favCount() === 0) {
    emptyBlock('heart', '', 'Aún no tienes favoritas.', 'Toca el corazón de una receta para guardarla aquí. Se guardan solo en este dispositivo.');
  } else if (state.mine === 'done' && doneCount() === 0) {
    emptyBlock('check', 'olive', 'Aún no has hecho ninguna.', 'Cuando cocines una receta, pulsa «La he hecho» y aparecerá aquí.');
  } else {
    emptyEl.appendChild(el('h3', null, 'Nada por aquí.'));
    let why = 'Ninguna receta';
    if (state.tags.length) {
      const labels = state.tags.map(tagLabel);
      why += ' de ' + (labels.length > 1 ? labels.slice(0, -1).join(', ') + ' y ' + labels[labels.length - 1] : labels[0]);
    }
    if (state.easy) why += ' fácil';
    if (state.sano) why += ', sana';
    if (state.max) why += ' en ≤' + state.max + ' min';
    if (state.q.trim()) why += ' con «' + state.q.trim() + '»';
    if (state.mine === 'fav') why += ' entre tus favoritas';
    if (state.mine === 'done') why += ' entre las hechas';
    emptyEl.appendChild(el('p', null, why + '.'));
    const keys = [];
    if (state.q.trim()) keys.push('q');
    state.tags.forEach(t => keys.push('tag:' + t));
    ['mine', 'max', 'easy', 'sano'].forEach(k => { if (state[k]) keys.push(k); });
    keys.map(key => ({ key, n: compute(withoutFilter(state, key)).list.length }))
      .sort((a, b) => b.n - a.n)
      .forEach(({ key, n }) => {
        const b = el('button', 'btn', 'Quitar ' + filterLabel(key) + (n ? ' · hay ' + n : ''));
        b.type = 'button'; b.dataset.action = 'remove-filter'; b.dataset.value = key;
        actions.appendChild(b);
      });
  }
  const all = el('button', 'btn btn-primary', state.mine && emptyEl.querySelector('.empty-icon') ? 'Ver todas' : 'Quitar todos los filtros');
  all.type = 'button'; all.dataset.action = 'clear-filters';
  actions.appendChild(all);
  emptyEl.appendChild(actions);
}

/* =========================================================
   Hash e historial
   ========================================================= */
const basePath = () => location.pathname + location.search;
function listHash(extra) {
  const parts = [];
  const add = (k, v) => parts.push(k + '=' + encodeURIComponent(v).replace(/%2C/gi, ','));
  if (state.q.trim()) add('q', state.q.trim());
  if (state.tags.length) add('t', state.tags.join(','));
  if (state.mine) add('mine', state.mine);
  if (state.max) add('max', state.max);
  if (state.easy) add('easy', '1');
  if (state.sano) add('sano', '1');
  if (state.sort !== 'recent') add('sort', state.sort);
  if (extra) Object.keys(extra).forEach(k => add(k, extra[k]));
  return parts.length ? '#' + parts.join('&') : '';
}
function parseHash() {
  const h = location.hash.slice(1);
  const s = defaultState();
  const legacy = h.match(/^receta\/(.+)$/); // compatibilidad con #receta/<id>
  if (legacy) { let id = legacy[1]; try { id = decodeURIComponent(id); } catch (e) {} return { list: s, r: id, cook: false }; }
  let p;
  try { p = new URLSearchParams(h); } catch (e) { p = new URLSearchParams(''); }
  s.q = (p.get('q') || '').slice(0, 120);
  s.tags = Array.from(new Set((p.get('t') || '').split(',').filter(t => CHIP_TAG_SET.has(t))));
  const mine = p.get('mine'); if (mine === 'fav' || mine === 'done') s.mine = mine;
  const max = Number(p.get('max')); if (max === 15 || max === 30 || max === 45) s.max = max;
  s.easy = p.get('easy') === '1';
  s.sano = p.get('sano') === '1';
  const sort = p.get('sort'); if (SORT_KEYS.includes(sort)) s.sort = sort;
  return { list: s, r: p.get('r'), cook: p.get('cook') === '1' };
}
const sameState = (a, b) => a.q === b.q && a.tags.join(',') === b.tags.join(',') && a.mine === b.mine &&
  a.max === b.max && a.easy === b.easy && a.sano === b.sano && a.sort === b.sort;
let hashTimer = 0;
function writeListHash() {
  clearTimeout(hashTimer);
  hashTimer = 0;
  try { history.replaceState(history.state, '', basePath() + listHash()); } catch (e) {}
}
function scheduleHash(ms) { clearTimeout(hashTimer); hashTimer = setTimeout(writeListHash, ms); }
function flushHash() { if (hashTimer) writeListHash(); }
function saveScroll() {
  ssSet('recetario:scroll', JSON.stringify({ hash: listHash(), y: Math.round(window.scrollY) }));
}

/* =========================================================
   Detalle
   ========================================================= */
const detail = $('#detail'), dScroll = $('#d-scroll'), dTopbar = $('#d-topbar');
const dLeft = $('#d-left'), dRight = $('#d-right'), dHero = $('#d-hero'), dHeroText = $('#d-hero-text');
const dHead = $('#d-head'), dImg = $('#d-img'), dTitle = $('#d-title'), dIngr = $('#d-ingr');
const dStars = $('#d-stars'), cStars = $('#c-stars');
const BASE_TITLE = document.title;
let openId = null, opener = null, randomInfo = null, lastRandom = null, closingDetail = false;

// Coloca título e ingredientes según el ancho: en móvil el título va sobre la foto.
function placeLayout() {
  if (MQ_DESK.matches) {
    if (dHead.parentNode !== dRight) dRight.insertBefore(dHead, dRight.firstChild);
    if (dIngr.parentNode !== dLeft) dLeft.appendChild(dIngr);
  } else {
    if (dHead.parentNode !== dHeroText) dHeroText.appendChild(dHead);
    if (dIngr.parentNode !== dRight) dRight.insertBefore(dIngr, $('.d-steps', dRight));
  }
}
placeLayout();
onMQ(MQ_DESK, placeLayout);

// Barra superior sólida cuando la foto sale de la vista.
if ('IntersectionObserver' in window) {
  new IntersectionObserver(es => es.forEach(e => dTopbar.classList.toggle('is-solid', !e.isIntersecting)),
    { root: dScroll, rootMargin: '-56px 0px 0px 0px', threshold: 0 }).observe(dImg);
}

const checksKey = id => 'recetario:checks:' + id;
function getChecks(id) {
  const c = readJSON(ssGet(checksKey(id)), {});
  return { i: Array.isArray(c.i) ? c.i.filter(Number.isInteger) : [], s: Array.isArray(c.s) ? c.s.filter(Number.isInteger) : [] };
}
function setChecks(id, c) {
  if (!c.i.length && !c.s.length) ssDel(checksKey(id));
  else ssSet(checksKey(id), JSON.stringify(c));
}

function buildIngrList(ul, d, checks) {
  ul.textContent = '';
  d.ingredients.forEach((ing, i) => {
    const f = formatQty(ing.quantity, ing.unit);
    const li = el('li');
    const lab = el('label', 'ingr-row');
    const cb = el('input', 'visually-hidden');
    cb.type = 'checkbox';
    cb.dataset.check = 'i';
    cb.dataset.idx = String(i);
    cb.checked = checks.i.includes(i);
    const box = el('span', 'box');
    box.setAttribute('aria-hidden', 'true');
    box.appendChild(icon('check'));
    const n = el('span', 'n', String(ing.name || '').trim());
    if (f.note) n.appendChild(el('span', 'note', ' · ' + f.note));
    lab.append(cb, box, el('span', 'q', f.q), n);
    li.appendChild(lab);
    ul.appendChild(li);
  });
}
function buildSteps(ol, d, checks) {
  ol.textContent = '';
  d.steps.forEach((s, i) => {
    const li = el('li');
    const lab = el('label', 'step');
    const cb = el('input', 'visually-hidden');
    cb.type = 'checkbox';
    cb.dataset.check = 's';
    cb.dataset.idx = String(i);
    cb.checked = checks.s.includes(i);
    const num = el('span', 'num', pad2(i + 1));
    num.setAttribute('aria-hidden', 'true');
    lab.append(cb, num, icon('check', 'ok'), el('span', 'txt', s));
    li.appendChild(lab);
    ol.appendChild(li);
  });
}
// Sincroniza casillas, progreso y «paso siguiente» en el detalle y en la hoja de cocina.
function syncChecks() {
  if (!openId) return;
  const d = BY_ID.get(openId), c = getChecks(openId);
  $$('input[data-check]').forEach(cb => {
    const list = cb.dataset.check === 'i' ? c.i : c.s;
    cb.checked = list.includes(Number(cb.dataset.idx));
  });
  $('#d-ingr-prog').textContent = c.i.length + '/' + d.ingredients.length;
  $('#d-steps-prog').textContent = c.s.length + '/' + d.steps.length;
  $('#d-uncheck').hidden = !c.i.length && !c.s.length;
  const next = c.s.length ? d.steps.findIndex((_, i) => !c.s.includes(i)) : -1;
  $$('#d-steps .step').forEach((s, i) => s.classList.toggle('is-next', i === next));
}
document.addEventListener('change', e => {
  const cb = e.target;
  if (!cb.matches || !cb.matches('input[data-check]') || !openId) return;
  const c = getChecks(openId), key = cb.dataset.check, idx = Number(cb.dataset.idx);
  c[key] = c[key].filter(x => x !== idx);
  if (cb.checked) c[key].push(idx);
  c[key].sort((a, b) => a - b);
  setChecks(openId, c);
  syncChecks();
});

function pill(iconName, text, cls) {
  const p = el('span', 'pill' + (cls ? ' ' + cls : ''));
  if (iconName) p.appendChild(icon(iconName));
  p.appendChild(document.createTextNode(text));
  return p;
}
function buildStars(box) {
  box.textContent = '';
  for (let i = 1; i <= 5; i++) {
    const b = el('button', 'star-btn');
    b.type = 'button';
    b.setAttribute('role', 'radio');
    b.dataset.action = 'rate';
    b.dataset.value = String(i);
    b.setAttribute('aria-label', i === 1 ? '1 estrella' : i + ' estrellas');
    b.appendChild(icon('star'));
    box.appendChild(b);
  }
}
function syncStars(box, id) {
  const r = Store.getRating(id);
  box.dataset.id = id;
  Array.from(box.children).forEach((b, i) => {
    const v = i + 1;
    b.classList.toggle('on', v <= r);
    b.setAttribute('aria-checked', String(v === r));
    b.tabIndex = (r ? v === r : v === 1) ? 0 : -1;
  });
}
function syncDetailMine() {
  if (!openId) return;
  const d = BY_ID.get(openId), r = Store.getRating(openId), c = Store.getCooked(openId);
  syncStars(dStars, openId);
  $('#d-rate-txt').textContent = r ? r + ' de 5' : 'Sin nota';
  const done = $('#d-done');
  done.setAttribute('aria-pressed', String(!!c));
  done.textContent = '';
  if (c) done.append(icon('check', 'draw'), document.createTextNode('Hecha el ' + fmtShort(Date.parse(c))));
  else done.textContent = 'La he hecho';
  const pills = $('#d-pills');
  pills.textContent = '';
  pills.appendChild(pill('clock', fmtTime(d.total)));
  if (DIFF[d.diff]) pills.appendChild(pill(null, DIFF[d.diff]));
  pills.appendChild(pill('leaf', 'Salud ' + d.health + '/10'));
  if (c) pills.appendChild(pill('check', 'Hecha el ' + fmtShort(Date.parse(c)), 'pill--done'));
  const fav = $('#d-fav');
  fav.setAttribute('aria-pressed', String(Store.isFavorite(openId)));
  if (cook.open) syncCookFinal();
}
function updateCta() {
  if (!openId) return;
  const d = BY_ID.get(openId);
  const saved = parseInt(ssGet('recetario:cook:' + openId), 10);
  $('#d-cta').hidden = !d.steps.length;
  $('#d-cta-txt').textContent = isFinite(saved) && saved > 0 && saved < d.steps.length
    ? 'Seguir cocinando · paso ' + (saved + 1) : 'Empezar a cocinar';
}

function fillDetail(d) {
  openId = d.id;
  dHero.dataset.initial = initialOf(d);
  dHero.classList.toggle('is-broken', !d.image);
  if (d.image) { if (dImg.getAttribute('src') !== d.image) dImg.src = d.image; }
  else dImg.removeAttribute('src');
  if (d.focusY != null) dImg.style.setProperty('--img-y', d.focusY + '%'); else dImg.style.removeProperty('--img-y');
  const dKicker = $('#d-kicker');
  dKicker.textContent = '';
  d.tags.forEach(t => {
    const s = el('span', 'tg');
    setHue(s, t);
    const e = tagEmo(t);
    if (e) s.appendChild(e);
    s.appendChild(document.createTextNode(tagLabel(t)));
    dKicker.appendChild(s);
  });
  dTitle.textContent = d.displayTitle;
  $('#d-short').textContent = d.displayTitle;
  document.title = d.displayTitle + ' · ' + BASE_TITLE;
  const fav = $('#d-fav');
  fav.dataset.fav = d.id;
  fav.dataset.id = d.id;
  fav.setAttribute('aria-label', 'Favorita: ' + d.a11yTitle);
  const rnd = $('#d-random');
  rnd.hidden = !randomInfo;
  if (randomInfo) $('#d-random-txt').textContent = 'Elegida al azar entre ' + randomInfo.n;
  const parts = [];
  if (d.prep) parts.push(fmtTime(d.prep) + ' de preparación');
  if (d.cook) parts.push(fmtTime(d.cook) + ' de cocción');
  const split = $('#d-split');
  split.hidden = parts.length < 2;
  split.textContent = parts.join(' · ');
  const checks = getChecks(d.id);
  buildIngrList($('#d-ingr-list'), d, checks);
  buildSteps($('#d-steps'), d, checks);
  $('#d-ingr').hidden = !d.ingredients.length;
  $('.d-steps').hidden = !d.steps.length;
  const src = $('#d-src');
  src.hidden = !d.source;
  if (d.source) {
    src.href = d.source;
    let host = '';
    try { host = new URL(d.source).hostname; } catch (e) {}
    $('#d-src-txt').textContent = /(^|\.)tiktok\.com$/i.test(host) ? 'Ver vídeo en TikTok' : 'Ver receta original';
  } else src.removeAttribute('href');
  $('#d-added').textContent = d.ts ? 'Añadida el ' + fmtLong(d.ts) : '';
  $('#d-wake').hidden = !('wakeLock' in navigator);
  syncWakeSwitch();
  syncDetailMine();
  syncChecks();
  updateCta();
  dScroll.scrollTop = 0; dLeft.scrollTop = 0; dRight.scrollTop = 0;
}

function showDetail(d, from) {
  if (from !== undefined) opener = from;
  const firstOpen = !detail.open;
  const doOpen = () => {
    fillDetail(d);
    if (!detail.open) {
      detail.classList.remove('is-closing');
      try { detail.showModal(); } catch (e) { detail.setAttribute('open', ''); }
      document.documentElement.classList.add('is-locked');
    }
    try { dTitle.focus({ preventScroll: true }); } catch (e) { dTitle.focus(); }
  };
  // Transición de la foto de la tarjeta a la del detalle, si el navegador la admite.
  const fromImg = firstOpen && from && from.closest ? $('.card-media img.is-loaded', from.closest('.card') || document.createElement('div')) : null;
  if (fromImg && document.startViewTransition && !reduced()) {
    try {
      fromImg.style.viewTransitionName = 'hero';
      const vt = document.startViewTransition(() => {
        fromImg.style.viewTransitionName = '';
        detail.classList.add('no-anim');
        doOpen();
        dImg.style.viewTransitionName = 'hero';
      });
      vt.finished.finally(() => { dImg.style.viewTransitionName = ''; detail.classList.remove('no-anim'); });
      return;
    } catch (e) { fromImg.style.viewTransitionName = ''; }
  }
  doOpen();
}
function openRecipe(id, opts) {
  opts = opts || {};
  const d = BY_ID.get(id);
  if (!d) return;
  flushHash();
  randomInfo = opts.random || null;
  if (opts.push !== false) {
    try { history.pushState({ r: id, pushed: true }, '', basePath() + listHash({ r: id })); } catch (e) {}
  }
  showDetail(d, opts.from === undefined ? null : opts.from);
}
function afterDetailClosed() {
  const id = openId;
  openId = null;
  randomInfo = null;
  document.title = BASE_TITLE;
  document.documentElement.classList.remove('is-locked');
  detail.style.transform = ''; detail.style.transition = '';
  WL.wantSwitch = false; WL.wantCook = false; wakeUpdate();
  let target = opener && opener.isConnected && opener.offsetParent !== null ? opener : null;
  if (!target && id) { const node = cardNodes.get(id); target = node && node.isConnected ? $('.card-link', node) : null; }
  if (!target) target = $('#q');
  opener = null;
  try { target.focus({ preventScroll: true }); } catch (e) {}
  rehostToast();
}
function hideDetail() {
  if (!detail.open || closingDetail) { if (!detail.open) openId = null; return; }
  if (cook.open) closeCookUI(true);
  closingDetail = true;
  let done = false;
  const finish = () => {
    if (done) return;
    done = true;
    detail.classList.remove('is-closing');
    detail.close();
    closingDetail = false;
    afterDetailClosed();
  };
  if (reduced()) return finish();
  if (detail.style.transform) {
    detail.style.transition = 'transform .2s var(--ease)';
    detail.style.transform = 'translateY(100%)';
    setTimeout(finish, 210);
    return;
  }
  detail.classList.add('is-closing');
  detail.addEventListener('animationend', finish, { once: true });
  setTimeout(finish, 320);
}
function requestCloseDetail() {
  if (history.state && history.state.pushed) { history.back(); return; }
  try { history.replaceState(null, '', basePath() + listHash()); } catch (e) {}
  hideDetail();
}
// Si Chrome no deja cancelar (Esc repetido sin activación de usuario), cierra él y el
// listener de «close» es el único que ajusta el historial: así no hay dos history.back().
detail.addEventListener('cancel', e => { if (!e.cancelable) return; e.preventDefault(); requestCloseDetail(); });
// Cierre que no hemos pedido (p. ej. gesto Atrás de Android): se ajusta el historial.
detail.addEventListener('close', () => {
  if (closingDetail || !openId) return;
  const wasPushed = history.state && history.state.pushed;
  afterDetailClosed();
  if (wasPushed) history.back();
  else { try { history.replaceState(null, '', basePath() + listHash()); } catch (e) {} }
});
detail.addEventListener('click', e => { if (e.target === detail) requestCloseDetail(); });

// Deslizar hacia abajo para cerrar (pantallas táctiles).
let sw = null;
detail.addEventListener('touchstart', e => {
  sw = null;
  if (!MQ_COARSE.matches || MQ_DESK.matches || e.touches.length !== 1) return;
  if (!e.target.closest('.d-hero, .d-topbar') || dScroll.scrollTop > 0) return;
  const t = e.touches[0];
  sw = { x0: t.clientX, y0: t.clientY, y: t.clientY, t: performance.now(), v: 0, dy: 0, active: false };
}, { passive: true });
detail.addEventListener('touchmove', e => {
  if (!sw) return;
  const t = e.touches[0], dx = t.clientX - sw.x0, dy = t.clientY - sw.y0;
  if (!sw.active) {
    if (dy > 8 && dy > Math.abs(dx)) sw.active = true;
    else { if (dy < -4 || Math.abs(dx) > 8) sw = null; return; }
  }
  e.preventDefault();
  const now = performance.now();
  sw.v = (t.clientY - sw.y) / Math.max(1, now - sw.t);
  sw.y = t.clientY; sw.t = now; sw.dy = Math.max(0, dy);
  detail.style.transition = 'none';
  detail.style.transform = 'translateY(' + (sw.dy * 0.6) + 'px)';
}, { passive: false });
detail.addEventListener('touchend', () => {
  const s = sw;
  sw = null;
  if (!s || !s.active) return;
  if (s.dy > 120 || s.v > 0.5) { requestCloseDetail(); return; }
  detail.style.transition = reduced() ? 'none' : 'transform .2s var(--ease)';
  detail.style.transform = '';
});
// Gesto interrumpido por el sistema (llamada, gesto de sistema…): vuelve a su sitio.
detail.addEventListener('touchcancel', () => {
  if (!sw) return;
  sw = null;
  detail.style.transition = reduced() ? 'none' : 'transform .2s var(--ease)';
  detail.style.transform = '';
});

/* =========================================================
   Pantalla encendida (Wake Lock)
   ========================================================= */
const WL = { lock: null, wantCook: false, wantSwitch: false };
function wakeWarn() {
  if (ssGet('recetario:wakewarned')) return;
  ssSet('recetario:wakewarned', '1');
  toast('Tu navegador no permite mantener la pantalla encendida');
}
async function wakeAcquire() {
  if (!('wakeLock' in navigator)) { wakeWarn(); return false; }
  if (WL.lock) return true;
  try {
    WL.lock = await navigator.wakeLock.request('screen');
    WL.lock.addEventListener('release', () => { WL.lock = null; });
    return true;
  } catch (e) { wakeWarn(); return false; }
}
function wakeRelease() {
  const l = WL.lock;
  WL.lock = null;
  if (l) { try { l.release(); } catch (e) {} }
}
async function wakeUpdate() {
  if (WL.wantCook || WL.wantSwitch) {
    const ok = await wakeAcquire();
    if (!ok && WL.wantSwitch) { WL.wantSwitch = false; syncWakeSwitch(); }
  } else wakeRelease();
}
function syncWakeSwitch() { $('#d-wake').setAttribute('aria-checked', String(WL.wantSwitch)); }
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible' && (WL.wantCook || WL.wantSwitch)) { WL.lock = null; wakeAcquire(); }
  if (document.visibilityState === 'hidden') saveScroll();
});

/* =========================================================
   Compartir y copiar
   ========================================================= */
function recipeUrl(id) {
  const base = location.protocol === 'file:' ? location.href.split('#')[0] : location.origin + location.pathname;
  return base + '#r=' + encodeURIComponent(id);
}
async function copyText(text) {
  try {
    if (navigator.clipboard && window.isSecureContext) { await navigator.clipboard.writeText(text); return true; }
  } catch (e) {}
  try {
    const ta = el('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.position = 'fixed'; ta.style.top = '0'; ta.style.left = '0'; ta.style.opacity = '0';
    (topDialog() || document.body).appendChild(ta);
    ta.select();
    const ok = document.execCommand('copy');
    ta.remove();
    return !!ok;
  } catch (e) { return false; }
}
async function shareRecipe(d) {
  const url = recipeUrl(d.id);
  if (navigator.share) {
    try { await navigator.share({ title: d.displayTitle, text: d.displayTitle, url }); return; }
    catch (e) { if (e && e.name === 'AbortError') return; }
  }
  toast((await copyText(url)) ? 'Enlace copiado' : 'No se pudo copiar el enlace');
}
function recipeText(d) {
  const lines = [d.displayTitle, [fmtTime(d.total), DIFF[d.diff]].filter(Boolean).join(' · '), '', 'INGREDIENTES'];
  d.ingredients.forEach(i => {
    const f = formatQty(i.quantity, i.unit);
    lines.push('- ' + [f.q, String(i.name || '').trim()].filter(Boolean).join(' ') + (f.note ? ' (' + f.note + ')' : ''));
  });
  lines.push('', 'PASOS');
  d.steps.forEach((s, k) => lines.push((k + 1) + '. ' + s));
  lines.push('', recipeUrl(d.id));
  return lines.join('\n');
}

/* =========================================================
   «¿Qué cocino hoy?»
   ========================================================= */
function pickRandom() {
  let pool = current.map(x => x.d);
  if (!pool.length) { toast('No hay recetas con estos filtros'); return null; }
  const n = pool.length;
  const weekAgo = Date.now() - 7 * DAY;
  const notRecent = pool.filter(d => { const c = Store.getCooked(d.id); return !(c && Date.parse(c) >= weekAgo); });
  if (notRecent.length) pool = notRecent;
  const notLast = pool.filter(d => d.id !== lastRandom);
  if (notLast.length) pool = notLast;
  const weights = pool.map(d => 1 + (Store.isFavorite(d.id) ? 2 : 0) + Store.getRating(d.id) * 0.5);
  let r = Math.random() * weights.reduce((a, b) => a + b, 0);
  let pick = pool[pool.length - 1];
  for (let i = 0; i < pool.length; i++) { r -= weights[i]; if (r <= 0) { pick = pool[i]; break; } }
  lastRandom = pick.id;
  return { d: pick, n };
}

/* =========================================================
   Modo cocina
   ========================================================= */
const cookDlg = $('#cook'), cookIngr = $('#cook-ingr');
const cBody = $('#c-body'), cStep = $('#c-step'), cFinal = $('#c-final'), cNav = $('#c-nav'), cProg = $('#c-prog');
const cook = { open: false, id: null, idx: 0, n: 0, finished: false, after: null };
let closingCook = false;
const SCALES = [0.85, 1, 1.15, 1.3, 1.5];
let scaleIdx = (function () { const v = parseInt(lsGet('recetario:cookScale'), 10); return v >= 0 && v < SCALES.length ? v : 1; })();
function applyScale() {
  cookDlg.style.setProperty('--cook-scale', String(SCALES[scaleIdx]));
  $('#c-dec').disabled = scaleIdx === 0;
  $('#c-inc').disabled = scaleIdx === SCALES.length - 1;
}
applyScale();

function startCook(push) {
  const d = BY_ID.get(openId);
  if (!d || !d.steps.length || cook.open) return;
  let idx = parseInt(ssGet('recetario:cook:' + d.id), 10);
  if (!(idx >= 0 && idx < d.steps.length)) idx = 0;
  Object.assign(cook, { open: true, id: d.id, idx, n: d.steps.length, finished: false, after: null });
  if (push !== false) {
    try { history.pushState({ r: d.id, cook: true, pushed: true }, '', basePath() + listHash({ r: d.id, cook: '1' })); } catch (e) {}
  }
  cookDlg.setAttribute('aria-label', 'Modo cocina: ' + d.a11yTitle);
  cProg.textContent = '';
  for (let i = 0; i < cook.n; i++) cProg.appendChild(el('span'));
  cProg.setAttribute('aria-valuemax', String(cook.n));
  cStep.hidden = false; cFinal.hidden = true; cNav.hidden = false;
  showStep(idx, 0);
  try { cookDlg.showModal(); } catch (e) { cookDlg.setAttribute('open', ''); }
  try { $('#c-next').focus({ preventScroll: true }); } catch (e) {}
  WL.wantCook = true;
  wakeUpdate();
}
function showStep(i, dir) {
  const d = BY_ID.get(cook.id);
  cook.idx = i;
  ssSet('recetario:cook:' + cook.id, String(i));
  $('#c-label').textContent = 'Paso ' + (i + 1) + ' de ' + cook.n;
  Array.from(cProg.children).forEach((s, k) => s.classList.toggle('on', k <= i));
  cProg.setAttribute('aria-valuenow', String(i + 1));
  $('#c-num').textContent = pad2(i + 1);
  $('#c-txt').textContent = d.steps[i];
  // El lector anuncia el paso entero, no solo «Paso N de M».
  say($('#c-live'), 'Paso ' + (i + 1) + ' de ' + cook.n + '. ' + d.steps[i]);
  document.title = 'Paso ' + (i + 1) + ' · ' + d.displayTitle;
  $('#c-prev').disabled = i === 0;
  $('#c-next-txt').textContent = i === cook.n - 1 ? 'Terminar' : 'Siguiente';
  cBody.scrollTop = 0;
  cStep.classList.remove('go-next', 'go-prev');
  if (dir) { void cStep.offsetWidth; cStep.classList.add(dir > 0 ? 'go-next' : 'go-prev'); }
}
function markStepDone(i) {
  const c = getChecks(cook.id);
  if (!c.s.includes(i)) { c.s.push(i); c.s.sort((a, b) => a - b); setChecks(cook.id, c); syncChecks(); }
}
function cookNext() {
  if (!cook.open || cook.finished) return;
  markStepDone(cook.idx);
  if (cook.idx < cook.n - 1) showStep(cook.idx + 1, 1);
  else showFinal();
}
function cookPrev() { if (cook.open && !cook.finished && cook.idx > 0) showStep(cook.idx - 1, -1); }
function syncCookFinal() {
  syncStars(cStars, cook.id);
  $('#c-mark').textContent = Store.getCooked(cook.id) ? 'Actualizar a hoy' : 'Marcar como hecha';
}
function showFinal() {
  cook.finished = true;
  cStep.hidden = true; cNav.hidden = true; cFinal.hidden = false;
  $('#c-label').textContent = 'Receta terminada';
  say($('#c-live'), 'Receta terminada. ¿Qué tal ha salido?');
  Array.from(cProg.children).forEach(s => s.classList.add('on'));
  syncCookFinal();
  try { $('#c-mark').focus(); } catch (e) {}
}
function closeCookUI(silent) {
  if (!cook.open) return;
  cook.open = false;
  closingCook = true;
  if (cookIngr.open) cookIngr.close();
  if (cookDlg.open) cookDlg.close();
  closingCook = false;
  WL.wantCook = false;
  wakeUpdate();
  updateCta();
  const d = BY_ID.get(openId);
  document.title = d ? d.displayTitle + ' · ' + BASE_TITLE : BASE_TITLE;
  // «close» es asíncrono: el aviso se recoloca ya, para que «Deshacer» siga visible.
  rehostToast();
  if (!silent) { try { $('.cta-btn').focus({ preventScroll: true }); } catch (e) {} }
  const after = cook.after;
  cook.after = null;
  if (after) after();
}
function requestCloseCook(after) {
  if (after) cook.after = after;
  if (history.state && history.state.cook && history.state.pushed) { history.back(); return; }
  try { history.replaceState({ r: cook.id, pushed: !!(history.state && history.state.pushed) }, '', basePath() + listHash({ r: cook.id })); } catch (e) {}
  closeCookUI();
}
function finishCook(mark) {
  const id = cook.id;
  ssDel('recetario:cook:' + id);
  if (!mark) { requestCloseCook(); return; }
  const prev = Store.getCooked(id);
  Store.setCooked(id, new Date().toISOString());
  requestCloseCook(() => toast('Marcada como hecha', 'Deshacer', () => Store.setCooked(id, prev)));
}
cookDlg.addEventListener('cancel', e => { if (!e.cancelable) return; e.preventDefault(); requestCloseCook(); });
cookDlg.addEventListener('close', () => {
  rehostToast();
  if (closingCook || !cook.open) return;
  const wasCook = history.state && history.state.cook && history.state.pushed;
  closeCookUI();
  if (wasCook) history.back();
});
cookDlg.addEventListener('keydown', e => {
  if (cookIngr.open || e.altKey || e.ctrlKey || e.metaKey) return;
  const onButton = e.target.closest && e.target.closest('button');
  if (['ArrowRight', 'PageDown', ' '].includes(e.key)) {
    if (e.key === ' ' && onButton) return;
    e.preventDefault(); cookNext();
  } else if (['ArrowLeft', 'PageUp'].includes(e.key)) {
    e.preventDefault(); cookPrev();
  }
});
// Toque por zonas (tercio izquierdo = atrás) y deslizamiento horizontal.
let cp = null;
cBody.addEventListener('pointerdown', e => {
  cp = null;
  if ((e.pointerType === 'mouse' && e.button !== 0) || cook.finished) return;
  if (e.target.closest('button, a, input')) return;
  cp = { x: e.clientX, y: e.clientY, t: performance.now() };
});
cBody.addEventListener('pointercancel', () => { cp = null; });
cBody.addEventListener('pointerup', e => {
  if (!cp) return;
  const dx = e.clientX - cp.x, dy = e.clientY - cp.y, dt = performance.now() - cp.t;
  cp = null;
  if (Math.abs(dx) > 60 && Math.abs(dx) > 1.5 * Math.abs(dy)) { if (dx < 0) cookNext(); else cookPrev(); return; }
  if (Math.abs(dx) < 10 && Math.abs(dy) < 10 && dt < 300) {
    const r = cBody.getBoundingClientRect();
    if (e.clientX - r.left < r.width / 3) cookPrev(); else cookNext();
  }
});
function openCookIngr() {
  const d = BY_ID.get(cook.id);
  buildIngrList($('#ci-list'), d, getChecks(cook.id));
  try { cookIngr.showModal(); } catch (e) { cookIngr.setAttribute('open', ''); }
}

/* =========================================================
   Hojas: cierre con fondo y deslizando
   ========================================================= */
const settingsDlg = $('#settings');
[cookIngr, settingsDlg].forEach(sh => {
  sh.addEventListener('click', e => { if (e.target === sh) sh.close(); });
  let y0 = null;
  const head = $('.sheet-head', sh);
  head.addEventListener('touchstart', e => { y0 = e.touches.length === 1 ? e.touches[0].clientY : null; }, { passive: true });
  head.addEventListener('touchmove', e => {
    if (y0 == null) return;
    const dy = Math.max(0, e.touches[0].clientY - y0);
    sh.style.transform = dy ? 'translateY(' + dy + 'px)' : '';
  }, { passive: true });
  head.addEventListener('touchend', e => {
    if (y0 == null) return;
    const dy = (e.changedTouches[0] ? e.changedTouches[0].clientY : y0) - y0;
    y0 = null;
    sh.style.transform = '';
    if (dy > 80) sh.close();
  });
  head.addEventListener('touchcancel', () => { y0 = null; sh.style.transform = ''; });
  sh.addEventListener('close', () => { sh.style.transform = ''; rehostToast(); });
});

/* =========================================================
   Ajustes: tema y «Mis datos»
   ========================================================= */
const themeMetas = $$('meta[name="theme-color"]').map(m => ({ m, content: m.getAttribute('content'), media: m.getAttribute('media') }));
function applyTheme(t) {
  const root = document.documentElement;
  if (t === 'light' || t === 'dark') root.dataset.theme = t; else { delete root.dataset.theme; t = 'auto'; }
  lsSet('recetario:theme', t);
  if (t === 'auto') themeMetas.forEach(x => { x.m.setAttribute('content', x.content); x.m.setAttribute('media', x.media); });
  else {
    const paper = getComputedStyle(root).getPropertyValue('--paper').trim();
    themeMetas.forEach(x => { x.m.setAttribute('content', paper); x.m.removeAttribute('media'); });
  }
}
function currentTheme() { const t = lsGet('recetario:theme'); return t === 'light' || t === 'dark' ? t : 'auto'; }
$$('input[name="theme"]').forEach(r => r.addEventListener('change', () => { if (r.checked) applyTheme(r.value); }));
function openSettings(focusData) {
  $$('input[name="theme"]').forEach(r => { r.checked = r.value === currentTheme(); });
  try { settingsDlg.showModal(); } catch (e) { settingsDlg.setAttribute('open', ''); }
  if (focusData) { const h = $('#s-data'); try { h.focus(); h.scrollIntoView({ block: 'nearest' }); } catch (e) {} }
}
// Versión = huella del contenido publicado (determinista: no cambia si no cambian los datos ni la web).
(function () {
  const b = $('#s-build'), v = b.dataset.version || '';
  b.textContent = 'Versión ' + v + (LATEST && LATEST.ts ? ' · última receta añadida el ' + fmtLong(LATEST.ts) : '');
})();
function exportData() {
  try {
    const blob = new Blob([JSON.stringify(Store.exportData(), null, 2)], { type: 'application/json' });
    const a = el('a');
    const t = new Date();
    a.href = URL.createObjectURL(blob);
    a.download = 'recetario-mis-datos-' + t.getFullYear() + '-' + pad2(t.getMonth() + 1) + '-' + pad2(t.getDate()) + '.json';
    settingsDlg.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  } catch (e) { toast('No se pudo descargar la copia'); }
}
const importFile = $('#import-file');
importFile.addEventListener('change', async () => {
  const f = importFile.files && importFile.files[0];
  importFile.value = '';
  if (!f) return;
  try {
    const text = await f.text();
    const n = await Store.importData(JSON.parse(text), id => BY_ID.has(id));
    toast(n.fav + n.rating + n.cooked === 0 ? 'No había nada nuevo que importar'
      : 'Importadas: ' + n.fav + ' favoritas, ' + n.rating + ' notas, ' + n.cooked + ' hechas');
  } catch (e) { toast('Ese archivo no es una copia del recetario'); }
});
let wipeTimer = 0;
function disarmWipe() {
  clearTimeout(wipeTimer); wipeTimer = 0;
  $('#wipe').classList.remove('is-armed');
  $('#wipe-txt').textContent = 'Borrar mis datos';
}
settingsDlg.addEventListener('close', disarmWipe);

// Sin almacenamiento (datos de sitios bloqueados): se avisa en el pie, en Ajustes y la primera vez que se marca algo.
let persistWarned = false;
function applyPersistNotice() {
  if (Store.persistent) return;
  $('#foot-txt').textContent = 'Este navegador no deja guardar tus favoritas: se perderán al cerrar';
  $('#s-data-txt').textContent = 'Este navegador no deja guardar datos de esta web (puede que los tengas bloqueados). Tus favoritas, notas y recetas hechas se perderán al cerrar la página.';
}
function warnNotPersistent() {
  if (Store.persistent || persistWarned) return;
  persistWarned = true;
  toast('Este navegador no deja guardar tus datos: se perderán al cerrar');
}

/* =========================================================
   Acciones (un único listener delegado)
   ========================================================= */
function setQuery(v) {
  const q = $('#q');
  q.value = v;
  syncSearchUI();
  state.q = v;
}
function syncSearchUI() {
  const q = $('#q');
  $('#search').classList.toggle('is-empty', !q.value);
  $('.search .clear').hidden = !q.value;
}
function onListChange(hashDelay) {
  render();
  scheduleHash(hashDelay || 0);
}
function clearFilters() {
  setQuery('');
  Object.assign(state, { tags: [], mine: null, max: null, easy: false, sano: false });
  onListChange();
}
function vibrate() { if (!reduced() && navigator.vibrate) { try { navigator.vibrate(10); } catch (e) {} } }
// Si el botón pulsado ha desaparecido al repintar, el foco no se queda en <body>:
// pasa al botón equivalente que quede en su contenedor o, si no hay, al recuento.
function keepFocus(container, idx) {
  const ae = document.activeElement;
  if (ae && ae !== document.body && ae.isConnected) return;
  let target = null;
  if (container && !container.hidden) {
    const btns = $$('button', container);
    if (btns.length) target = btns[Math.min(idx, btns.length - 1)];
  }
  try { (target || countEl).focus({ preventScroll: true }); } catch (e) {}
}

document.addEventListener('click', e => {
  const t = e.target.closest ? e.target.closest('[data-action]') : null;
  if (!t || t.disabled || t.getAttribute('aria-disabled') === 'true') return;
  const a = t.dataset.action;
  const id = t.dataset.id || openId;
  switch (a) {
    case 'open': {
      if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      if (!BY_ID.has(t.dataset.id)) return;
      e.preventDefault();
      openRecipe(t.dataset.id, { from: t });
      break;
    }
    case 'fav': {
      e.preventDefault();
      if (!id || !BY_ID.has(id)) return;
      const on = !Store.isFavorite(id);
      Store.setFavorite(id, on);
      vibrate();
      if (on) { t.classList.remove('pop'); void t.offsetWidth; t.classList.add('pop'); }
      else toast('Quitada de favoritas', 'Deshacer', () => Store.setFavorite(id, true));
      break;
    }
    case 'chip': {
      const k = t.dataset.kind, v = t.dataset.value;
      if (k === 'tag') state.tags = state.tags.includes(v) ? state.tags.filter(x => x !== v) : state.tags.concat(v);
      else if (k === 'mine') state.mine = state.mine === v ? null : v;
      else if (k === 'max') state.max = state.max === Number(v) ? null : Number(v);
      else state[k] = !state[k];
      onListChange();
      break;
    }
    case 'clear-q': setQuery(''); onListChange(); $('#q').focus(); break;
    case 'clear-filters': clearFilters(); keepFocus(null, 0); break;
    case 'remove-filter': {
      const key = t.dataset.value, box = t.parentNode, idx = $$('button', box).indexOf(t);
      if (key === 'q') setQuery('');
      Object.assign(state, withoutFilter(state, key));
      onListChange();
      keepFocus(box === activeRow ? activeRow : emptyEl.querySelector('.actions'), Math.max(0, idx));
      break;
    }
    case 'random': {
      const pick = pickRandom();
      if (!pick) return;
      if (!reduced()) { t.classList.remove('spin'); void t.offsetWidth; t.classList.add('spin'); }
      openRecipe(pick.d.id, { from: t, random: { n: pick.n } });
      break;
    }
    case 'random-again': {
      const pick = pickRandom();
      if (!pick) return;
      randomInfo = { n: pick.n };
      try { history.replaceState({ r: pick.d.id, pushed: !!(history.state && history.state.pushed) }, '', basePath() + listHash({ r: pick.d.id })); } catch (err) {}
      fillDetail(pick.d);
      try { dTitle.focus({ preventScroll: true }); } catch (err) {}
      break;
    }
    case 'close': requestCloseDetail(); break;
    // Salta los filtros: el siguiente Tab ya es la primera receta.
    case 'skip': { e.preventDefault(); grid.focus({ preventScroll: true }); $('#resbar').scrollIntoView(); break; }
    case 'share': if (openId) shareRecipe(BY_ID.get(openId)); break;
    case 'copy-text':
      if (openId) copyText(recipeText(BY_ID.get(openId))).then(ok => toast(ok ? 'Receta copiada' : 'No se pudo copiar la receta'));
      break;
    case 'src': saveScroll(); break;
    case 'rate': {
      const box = t.closest('.stars'), rid = box && box.dataset.id;
      if (!rid) return;
      const cur = Store.getRating(rid), v = Number(t.dataset.value);
      if (v === cur) { Store.setRating(rid, 0); toast('Nota borrada', 'Deshacer', () => Store.setRating(rid, cur)); }
      else Store.setRating(rid, v);
      break;
    }
    case 'done': {
      if (!openId) return;
      const prev = Store.getCooked(openId), rid = openId;
      if (prev) { Store.setCooked(rid, null); toast('Desmarcada', 'Deshacer', () => Store.setCooked(rid, prev)); }
      else Store.setCooked(rid, new Date().toISOString());
      break;
    }
    case 'wake': WL.wantSwitch = !WL.wantSwitch; syncWakeSwitch(); wakeUpdate(); break;
    case 'uncheck-all':
      if (openId) {
        setChecks(openId, { i: [], s: [] });
        syncChecks();
        ssDel('recetario:cook:' + openId); // el modo cocina vuelve a empezar por el paso 1
        updateCta();
        try { $('#h-ingr').focus({ preventScroll: true }); } catch (err) {}
      }
      break;
    case 'cook': startCook(true); break;
    case 'cook-close': requestCloseCook(); break;
    case 'cook-next': cookNext(); break;
    case 'cook-prev': cookPrev(); break;
    case 'cook-ingr': openCookIngr(); break;
    case 'cook-mark': finishCook(true); break;
    case 'cook-skip': finishCook(false); break;
    case 'font-dec': case 'font-inc':
      scaleIdx = Math.max(0, Math.min(SCALES.length - 1, scaleIdx + (a === 'font-inc' ? 1 : -1)));
      lsSet('recetario:cookScale', String(scaleIdx));
      applyScale();
      break;
    case 'settings': openSettings(t.dataset.focus === 'data'); break;
    case 'close-sheet': { const dlg = t.closest('dialog'); if (dlg) dlg.close(); break; }
    case 'export': exportData(); break;
    case 'import': importFile.click(); break;
    case 'wipe':
      if (!wipeTimer) {
        t.classList.add('is-armed');
        $('#wipe-txt').textContent = 'Pulsa otra vez para borrar todo';
        wipeTimer = setTimeout(disarmWipe, 4000);
      } else { disarmWipe(); Store.clear(); toast('Datos borrados'); }
      break;
    case 'toast-act': runToastAction(); break;
  }
});

// Estrellas: radiogroup con flechas, Inicio y Fin.
document.addEventListener('keydown', e => {
  const b = e.target.closest ? e.target.closest('.star-btn') : null;
  if (!b) return;
  const box = b.closest('.stars'), rid = box.dataset.id;
  const cur = Store.getRating(rid);
  let v = null;
  if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') v = Math.max(1, (cur || 1) - 1);
  else if (e.key === 'ArrowRight' || e.key === 'ArrowUp') v = Math.min(5, cur + 1);
  else if (e.key === 'Home') v = 1;
  else if (e.key === 'End') v = 5;
  if (v == null) return;
  e.preventDefault();
  e.stopPropagation();
  Store.setRating(rid, v).then(() => { const nb = box.children[v - 1]; if (nb) nb.focus(); });
}, true);

// Buscador
const qInput = $('#q');
let qTimer = 0;
qInput.addEventListener('input', () => {
  syncSearchUI();
  clearTimeout(qTimer);
  qTimer = setTimeout(() => { state.q = qInput.value; render(); scheduleHash(300); }, 80);
});
qInput.addEventListener('keydown', e => {
  if (e.key === 'Enter') {
    e.preventDefault();
    clearTimeout(qTimer);
    if (state.q !== qInput.value) { state.q = qInput.value; render(); scheduleHash(0); }
    // En táctil se cierra el teclado; con teclado físico el foco sigue en el campo.
    if (MQ_COARSE.matches) qInput.blur();
  }
  else if (e.key === 'Escape' && qInput.value) { e.preventDefault(); setQuery(''); onListChange(); }
});
document.addEventListener('keydown', e => {
  if (e.key !== '/' || e.ctrlKey || e.metaKey || e.altKey || isTyping(e.target) || topDialog()) return;
  e.preventDefault();
  qInput.focus();
});
$('#sort').addEventListener('change', e => {
  state.sort = SORT_KEYS.includes(e.target.value) ? e.target.value : 'recent';
  if (state.sort === 'random') newSeed();
  onListChange();
  const bar = $('#resbar');
  if (bar.getBoundingClientRect().top < 0) bar.scrollIntoView({ block: 'start', behavior: reduced() ? 'auto' : 'smooth' });
});

/* =========================================================
   Reacción a cambios del Store (sin repintar la rejilla)
   ========================================================= */
function markStale(id, cond) {
  const node = cardNodes.get(id);
  if (node && node.isConnected) node.classList.toggle('is-stale', cond);
}
Store.onChange(ev => {
  if (ev.type === 'all') {
    const y = window.scrollY;
    render();
    window.scrollTo(0, y);
    if (openId) { syncDetailMine(); }
    return;
  }
  warnNotPersistent();
  const id = ev.id, node = cardNodes.get(id);
  if (ev.type === 'fav') {
    const on = Store.isFavorite(id);
    $$('[data-fav]').forEach(b => { if (b.dataset.fav === id) b.setAttribute('aria-pressed', String(on)); });
    // También las tarjetas que no están en el DOM (filtradas o la portada fuera de la vista por defecto).
    if (node) $('.fav-btn', node).setAttribute('aria-pressed', String(on));
    syncFeatureFav();
    updateMineChips();
    if (state.mine === 'fav') markStale(id, !on);
  } else if (ev.type === 'rating' || ev.type === 'cooked') {
    if (node) fillMine($('.card-mine', node), id);
    if (ev.type === 'cooked') {
      updateMineChips();
      if (state.mine === 'done') markStale(id, !Store.getCooked(id));
    }
  }
  if (openId === id) syncDetailMine();
  else if (cook.open && cook.id === id) syncCookFinal();
});

/* =========================================================
   Historial: Atrás cierra el detalle y el modo cocina
   ========================================================= */
window.addEventListener('popstate', () => {
  if (location.hash === '#lista' || location.hash === '#grid') return;
  const h = parseHash();
  if (h.r && !BY_ID.has(h.r)) {
    toast('Esa receta ya no está');
    h.r = null; h.cook = false;
    try { history.replaceState(null, '', basePath() + location.hash.replace(/([#&])r=[^&]*&?/, '$1').replace(/[#&]$/, '')); } catch (e) {}
  }
  if (!sameState(h.list, state)) {
    Object.assign(state, h.list);
    setQuery(state.q);
    $('#sort').value = state.sort;
    render();
    revealActiveChips();
  }
  if (h.r && BY_ID.has(h.r)) {
    if (openId !== h.r || !detail.open) { randomInfo = null; showDetail(BY_ID.get(h.r)); }
    if (h.cook && !cook.open) startCook(false);
    else if (!h.cook && cook.open) closeCookUI();
  } else {
    if (cook.open) closeCookUI(true);
    if (detail.open) hideDetail();
  }
});
window.addEventListener('pagehide', saveScroll);

/* =========================================================
   Cabecera: línea de fecha y barra fija
   ========================================================= */
function updateDateline() {
  const link = $('#dateline-link');
  const n = DATA.length;
  if (LATEST && LATEST.ts) {
    link.textContent = n + (n === 1 ? ' receta' : ' recetas') + ' · última ' + relTime(LATEST.ts);
    link.setAttribute('href', '#r=' + encodeURIComponent(LATEST.id));
    link.dataset.action = 'open';
    link.dataset.id = LATEST.id;
  } else link.textContent = n + (n === 1 ? ' receta' : ' recetas');
  updateFeatureKicker();
}
if ('IntersectionObserver' in window) {
  new IntersectionObserver(es => es.forEach(e => $('#bar').classList.toggle('is-stuck', !e.isIntersecting)))
    .observe($('#masthead'));
}

/* =========================================================
   Arranque
   ========================================================= */
async function boot() {
  try { history.scrollRestoration = 'manual'; } catch (e) {}
  await Store.init();
  applyPersistNotice();
  if (currentTheme() !== 'auto') applyTheme(currentTheme());
  buildStars(dStars);
  buildStars(cStars);
  DATA.forEach(d => cardNodes.set(d.id, buildCard(d, tplCard)));
  if (LATEST) FEATURE = buildCard(LATEST, tplFeature);
  buildChips();
  updateDateline();
  setInterval(updateDateline, 60000);

  const h = parseHash();
  Object.assign(state, h.list);
  setQuery(state.q);
  $('#sort').value = state.sort;
  render(true);
  revealActiveChips();

  const saved = readJSON(ssGet('recetario:scroll'), null);
  if (saved && saved.hash === listHash() && saved.y > 0) requestAnimationFrame(() => window.scrollTo(0, saved.y));

  if (h.r) {
    if (BY_ID.has(h.r)) {
      // Enlace compartido: se crea antes la entrada de la lista, para que Atrás vuelva a ella y no saque de la web.
      try { history.replaceState(null, '', basePath() + listHash()); } catch (e) {}
      openRecipe(h.r);
      if (h.cook) startCook(true);
    } else {
      try { history.replaceState(null, '', basePath() + listHash()); } catch (e) {}
      toast('Esa receta ya no está');
    }
  } else {
    try { history.replaceState(null, '', basePath() + listHash()); } catch (e) {}
  }
}
boot();
})();
</script>
</body>
</html>
'''


_SURROGATE_RE = re.compile('[\ud800-\udfff]')


def safe_json(obj):
    """JSON compacto que se puede meter dentro de <script> sin cerrarlo.

    Sustituir «<» por \\u003c sigue siendo JSON válido y cubre «</script>» y
    «<!--». U+2028/U+2029 se escapan por si alguien lo pega en JS. Los
    surrogates sueltos (válidos en JSON pero no en UTF-8) se dejan escapados.
    allow_nan=False: NaN/Infinity no son JSON y dejarían la web vacía.
    """
    s = json.dumps(obj, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    s = s.replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    return _SURROGATE_RE.sub(lambda m: '\\u%04x' % ord(m.group()), s)


def _drop_non_finite(value, where, warn):
    """Cambia NaN, Infinity y -Infinity por None (null), avisando de cada uno."""
    if isinstance(value, float) and not math.isfinite(value):
        warn('%s: valor numérico no válido (%s); se usa null' % (where, value))
        return None
    if isinstance(value, list):
        return [_drop_non_finite(v, '%s[%d]' % (where, i), warn) for i, v in enumerate(value)]
    if isinstance(value, dict):
        return {k: _drop_non_finite(v, '%s.%s' % (where, k), warn) for k, v in value.items()}
    return value


def _parse_iso(value):
    """Devuelve un datetime con zona horaria o None."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        dt = datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def build_html(recipes_json_str, warnings=None):
    """Devuelve el HTML completo. Si se pasa una lista en `warnings`, añade ahí los avisos."""
    def warn(msg):
        if warnings is not None:
            warnings.append(msg)
        else:
            _print('AVISO: ' + msg, file=sys.stderr)

    recipes = json.loads(recipes_json_str)
    if not isinstance(recipes, list):
        raise ValueError('recipes.json debe contener una lista de recetas')
    # json.loads acepta NaN e Infinity (y 1e400 da inf), pero JSON.parse no: se cambian por null.
    recipes = [_drop_non_finite(r, '«%s»' % (r.get('title') or 'receta n.º %d' % n) if isinstance(r, dict)
                                else 'receta n.º %d' % n, warn)
               for n, r in enumerate(recipes, 1)]

    dates = [d for d in (_parse_iso(r.get('created_at')) for r in recipes if isinstance(r, dict)) if d]
    latest_iso = max(dates).astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ') if dates else ''
    config = {'tagLabel': TAG_LABEL, 'tagIcon': TAG_ICON, 'tagHue': TAG_HUE,
              'chipOrder': CHIP_ORDER, 'hiddenTags': HIDDEN_TAGS}
    recipes_json = safe_json(recipes)

    html = TEMPLATE
    html = html.replace('__FONTS_CSS__', FONTS_CSS)
    html = html.replace('__CONFIG_JSON__', safe_json(config))
    html = html.replace('__LATEST__', latest_iso)
    html = html.replace('__COUNT__', str(len(recipes)))
    left = set(re.findall(r'__[A-Z_]+__', html))
    if left != {'__RECIPES_JSON__', '__VERSION__'}:
        raise RuntimeError('Marcadores sin sustituir en la plantilla: %s' % ', '.join(sorted(left)))
    # Versión determinista: huella de la plantilla ya rellena y de los datos (sin fecha de generación).
    digest = hashlib.sha256()
    digest.update(html.encode('utf-8'))
    digest.update(recipes_json.encode('utf-8'))
    html = html.replace('__VERSION__', digest.hexdigest()[:8])
    # Las recetas van las últimas: un texto de receta con «__ALGO__» no se toca.
    return html.replace('__RECIPES_JSON__', recipes_json)


def _norm_title(s):
    s = unicodedata.normalize('NFD', str(s or '').lower())
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return ' '.join(s.split())


_JPEG_SOF = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}


def _image_size(path):
    """(ancho, alto) de un JPEG o PNG leyendo solo la cabecera (sin PIL); None si no se sabe."""
    try:
        with open(path, 'rb') as f:
            head = f.read(24)
            if head[:8] == b'\x89PNG\r\n\x1a\n' and head[12:16] == b'IHDR':
                return struct.unpack('>II', head[16:24])
            if head[:2] != b'\xff\xd8':
                return None
            f.seek(2)
            while True:
                b = f.read(1)
                while b and b != b'\xff':
                    b = f.read(1)
                while b == b'\xff':
                    b = f.read(1)
                if not b:
                    return None
                marker = b[0]
                if marker == 0x01 or 0xD0 <= marker <= 0xD8:
                    continue  # marcadores sin longitud
                if marker in (0xD9, 0xDA):
                    return None  # fin de imagen o datos de imagen antes del SOF
                seg = f.read(2)
                if len(seg) < 2:
                    return None
                length = struct.unpack('>H', seg)[0]
                if marker in _JPEG_SOF:
                    sof = f.read(5)
                    if len(sof) < 5:
                        return None
                    height, width = struct.unpack('>HH', sof[1:5])
                    return width, height
                f.seek(length - 2, 1)
    except (OSError, struct.error):
        return None


def _is_int(v, lo=None, hi=None):
    if isinstance(v, bool) or not isinstance(v, int):
        return False
    return (lo is None or v >= lo) and (hi is None or v <= hi)


def check_data(recipes, base_dir):
    """Avisos de calidad de datos. Nunca lanza ni cambia el código de salida."""
    w = []
    if not isinstance(recipes, list):
        return ['recipes.json no contiene una lista']
    base_dir = Path(base_dir)
    titles, ids, unknown_tags = {}, {}, {}
    for n, r in enumerate(recipes, 1):
        if not isinstance(r, dict):
            w.append('la receta n.º %d no es un objeto' % n)
            continue
        title = str(r.get('title') or '').strip()
        label = '«%s»' % (title or 'receta n.º %d sin título' % n)
        rid = str(r.get('id') or '').strip()
        if not rid:
            w.append('%s no tiene id' % label)
        else:
            ids.setdefault(rid, []).append(label)
        titles.setdefault(_norm_title(title), []).append((title, rid))

        img = str(r.get('image') or '').strip()
        if not img:
            w.append('%s no tiene imagen' % label)
        else:
            if not re.match(r'^images/[\w.\-]+$', img, re.ASCII):
                w.append('%s: la ruta de imagen «%s» no tiene la forma images/nombre.jpg; la web la tratará como rota' % (label, img))
            path = base_dir / img
            if not path.is_file():
                w.append('%s: la imagen %s no existe' % (label, img))
            else:
                size = path.stat().st_size
                if size > MAX_IMAGE_KB * 1024:
                    w.append('%s: la imagen %s pesa %d KB (más de %d KB)' % (label, img, round(size / 1024), MAX_IMAGE_KB))
                dims = _image_size(path)
                if dims and dims[0] < MIN_IMAGE_WIDTH:
                    w.append('%s: la imagen %s mide %dx%d px (menos de %d de ancho); se verá borrosa'
                             % (label, img, dims[0], dims[1], MIN_IMAGE_WIDTH))

        tags = r.get('tags')
        if not isinstance(tags, list):
            w.append('%s: «tags» no es una lista' % label)
            tags = []
        for t in tags:
            if t not in TAG_LABEL:
                unknown_tags[t] = unknown_tags.get(t, 0) + 1

        src = str(r.get('source') or '').strip()
        if not src:
            w.append('%s no tiene source' % label)
        elif not re.match(r'^https?://', src, re.IGNORECASE):
            w.append('%s: el source «%s» no empieza por http:// o https://' % (label, src))

        if r.get('difficulty') not in ('easy', 'medium', 'hard'):
            w.append('%s: difficulty «%s» no es easy, medium ni hard' % (label, r.get('difficulty')))
        if not _is_int(r.get('health_score'), 0, 10):
            w.append('%s: health_score «%s» no es un entero de 0 a 10' % (label, r.get('health_score')))
        for key in ('prep_time_min', 'cook_time_min'):
            if not _is_int(r.get(key), 0):
                w.append('%s: %s «%s» no es un entero ≥ 0' % (label, key, r.get(key)))
        if _is_int(r.get('prep_time_min'), 0) and _is_int(r.get('cook_time_min'), 0):
            total = r['prep_time_min'] + r['cook_time_min']
            if 'rapida' in tags and total > RAPIDA_MAX_MIN:
                w.append('%s lleva «rapida» pero tarda %d min (más de %d): quita la etiqueta'
                         % (label, total, RAPIDA_MAX_MIN))
            elif 'rapida' not in tags and total <= RAPIDA_MAX_MIN:
                w.append('%s tarda %d min (%d o menos) y no lleva «rapida»: añádela'
                         % (label, total, RAPIDA_MAX_MIN))
        if _parse_iso(r.get('created_at')) is None:
            w.append('%s: created_at «%s» no es una fecha válida' % (label, r.get('created_at')))

        ingredients = r.get('ingredients')
        if not isinstance(ingredients, list):
            w.append('%s: «ingredients» no es una lista' % label)
            ingredients = []
        for ing in ingredients:
            if not isinstance(ing, dict) or not str(ing.get('name') or '').strip():
                w.append('%s: hay un ingrediente sin nombre' % label)
                continue
            for key in ('quantity', 'unit'):
                val = str(ing.get(key) or '')
                if len(val) > 20 or '+' in val:
                    w.append('%s: %s raro en «%s»: «%s»' % (label, key, ing.get('name'), val))

    for norm, items in titles.items():
        if norm and len(items) > 1:
            short = ', '.join((rid[:4] + '…') if rid else '(sin id)' for _, rid in items)
            w.append('título repetido «%s» (ids %s)' % (items[0][0], short))
    for rid, labels in ids.items():
        if len(labels) > 1:
            w.append('id repetido %s en %s' % (rid, ', '.join(labels)))
    for t, count in sorted(unknown_tags.items(), key=lambda kv: (-kv[1], str(kv[0]))):
        w.append('etiqueta «%s» sin entrada en TAG_LABEL (%d %s); se mostrará como «%s»'
                 % (t, count, 'receta' if count == 1 else 'recetas', str(t)[:1].upper() + str(t)[1:]))
    return w


def _print(text, file=None):
    """print() que no falla en consolas que no admiten algún carácter."""
    file = file or sys.stdout
    try:
        print(text, file=file)
    except UnicodeEncodeError:
        enc = getattr(file, 'encoding', None) or 'ascii'
        print(text.encode(enc, errors='replace').decode(enc, errors='replace'), file=file)


def _write_atomic(path, text):
    """Escribe en un temporal y lo renombra: si algo falla, el fichero anterior queda intacto."""
    path = Path(path)
    tmp = path.with_name(path.name + '.tmp')
    try:
        with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
        os.replace(str(tmp), str(path))
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


def main():
    recipes_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("recipes.json")
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("index.html")

    # utf-8-sig lee igual el UTF-8 normal y también el que lleva BOM.
    with open(recipes_path, encoding="utf-8-sig") as f:
        recipes_json_str = f.read()

    # Si build_html falla, no se ha tocado index.html y el código de salida es ≠ 0.
    warnings = []
    html = build_html(recipes_json_str, warnings)
    _write_atomic(output_path, html)

    recipes = json.loads(recipes_json_str)
    _print(f"✅ Generated {output_path} with {len(recipes)} recipes")

    try:
        warnings += check_data(recipes, recipes_path.parent)
    except Exception as e:  # los avisos nunca rompen la generación
        warnings.append('no se pudieron comprobar los datos (%s)' % e)
    # Por stderr: stdout queda solo con la línea «✅ Generated …», como antes.
    for msg in warnings:
        _print('AVISO: ' + msg, file=sys.stderr)


if __name__ == "__main__":
    main()
