#!/usr/bin/env python3
"""Generate index.html from recipes.json for the recetario site."""

import json
import sys
from datetime import datetime
from pathlib import Path


def build_html(recipes_json_str):
    recipes = json.loads(recipes_json_str)

    DIFF_MAP = { 'easy': 'Fácil', 'medium': 'Media', 'hard': 'Difícil' }
    TAG_EMOJI = {
        'desayuno':'🌅', 'postre':'🍰', 'cena':'🌙', 'merienda':'🍪', 'rapida':'⚡',
        'pasta':'🍝', 'arroz':'🍚', 'carne':'🥩', 'pescado':'🐟', 'pollo':'🍗',
        'ensalada':'🥗', 'verdura':'🥬', 'huevo':'🥚', 'sopa':'🍜', 'horno':'🔥'
    }

    latest_iso = ""
    dates = []
    for r in recipes:
        if r.get('created_at'):
            try:
                dt = datetime.fromisoformat(r['created_at'].replace('Z', '+00:00'))
                dates.append(dt)
            except:
                pass
    if dates:
        latest = max(dates)
        latest_iso = latest.strftime('%Y-%m-%dT%H:%M:%SZ')
    last_str = "Recetario de cocina" if not latest_iso else ""

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<title>🥘 Recetario</title>
<style>
  :root {{
    --bg: #faf8f5;
    --card: #fff;
    --text: #2d2a26;
    --muted: #8c8076;
    --accent: #e85d3a;
    --accent2: #3a8c5e;
    --border: #e8e3dc;
    --shadow: 0 2px 12px rgba(0,0,0,.06);
    --tag-bg: #f3efe9;
    --tag-text: #6b5f55;
    --tag-active-bg: #2d2a26;
    --tag-active-text: #fff;
  }}
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html {{ width: 100%; -webkit-text-size-adjust: 100%; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
    width: 100%;
    min-height: 100vh; min-height: 100dvh;
    -webkit-font-smoothing: antialiased;
    overflow-x: hidden;
  }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 20px 16px 40px; }}

  /* Header */
  header {{ text-align: center; padding: 16px 0 8px; }}
  header h1 {{ font-size: 1.8rem; font-weight: 700; letter-spacing: -.02em; }}
  header .count {{ color: var(--text); font-size: 1rem; font-weight: 600; margin-top: 2px; }}
  header .sub {{ color: var(--muted); font-size: .8rem; margin-top: 0; }}

  /* Search */
  .search-wrap {{ position: relative; max-width: 680px; margin: 16px auto 12px; }}
  .search-wrap input {{
    width: 100%; padding: 14px 16px 14px 44px;
    border: 1.5px solid var(--border); border-radius: 14px;
    font-size: 1rem; background: var(--card); color: var(--text);
    outline: none; transition: border-color .2s, box-shadow .2s;
    -webkit-appearance: none;
  }}
  .search-wrap input:focus {{ border-color: var(--accent); box-shadow: 0 0 0 3px rgba(232,93,58,.12); }}
  .search-wrap input::placeholder {{ color: #b8afa6; }}
  .search-icon {{ position: absolute; left: 14px; top: 50%; transform: translateY(-50%); font-size: 1.2rem; color: var(--muted); pointer-events: none; }}

  /* Tags */
  .tags-wrap {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; margin-bottom: 24px; max-width: 800px; margin-left: auto; margin-right: auto; }}
  .tag-chip {{
    padding: 7px 14px; border-radius: 20px; font-size: .85rem; font-weight: 500;
    background: var(--tag-bg); color: var(--tag-text);
    border: none; cursor: pointer; transition: all .15s;
    -webkit-tap-highlight-color: transparent;
    user-select: none;
    touch-action: manipulation;
  }}
  .tag-chip.active {{ background: var(--tag-active-bg); color: var(--tag-active-text); }}
  .tag-chip:hover:not(.active) {{ background: #e8e2da; }}
  .tag-more {{
    padding: 7px 14px; border-radius: 20px; font-size: .8rem; font-weight: 500;
    background: transparent; color: var(--accent);
    border: 1.5px dashed var(--accent); cursor: pointer; transition: all .15s;
    -webkit-tap-highlight-color: transparent;
    user-select: none; touch-action: manipulation;
  }}
  .tag-more:hover {{ background: rgba(232,93,58,.08); }}

  /* Responsive Grid for Cards */
  .recipes {{
    display: grid;
    grid-template-columns: 1fr;
    gap: 18px;
  }}
  @media (min-width: 640px) {{
    .recipes {{ grid-template-columns: repeat(2, 1fr); }}
  }}
  @media (min-width: 960px) {{
    .recipes {{ grid-template-columns: repeat(3, 1fr); gap: 20px; }}
  }}

  .card {{
    background: var(--card); border-radius: 16px; overflow: hidden;
    box-shadow: var(--shadow); transition: transform .15s, box-shadow .15s;
    cursor: pointer; -webkit-tap-highlight-color: transparent;
    display: flex; flex-direction: column;
    touch-action: manipulation;
  }}
  .card:active {{ transform: scale(.985); }}
  .card-img {{
    width: 100%; height: 200px; object-fit: cover;
    display: block; background: linear-gradient(135deg, #f0ece6, #e8e3dc);
  }}
  .card-img-placeholder {{
    width: 100%; height: 200px; display: flex;
    align-items: center; justify-content: center;
    background: linear-gradient(135deg, #f0ece6, #e8e3dc);
    font-size: 3rem;
  }}
  .card-body {{ padding: 14px 16px 16px; flex: 1; display: flex; flex-direction: column; }}
  .card-title {{ font-size: 1.12rem; font-weight: 600; margin-bottom: 8px; letter-spacing: -.01em; line-height: 1.35; }}
  .card-meta {{ display: flex; flex-wrap: wrap; gap: 6px; align-items: center; font-size: .82rem; color: var(--muted); margin-bottom: 10px; margin-top: auto; }}
  .card-meta span {{ display: inline-flex; align-items: center; gap: 4px; }}
  .meta-dot {{ width: 4px; height: 4px; border-radius: 50%; background: var(--border); margin: 0 2px; }}
  .card-tags {{ display: flex; flex-wrap: wrap; gap: 6px; }}
  .card-tag {{
    padding: 4px 10px; border-radius: 12px; font-size: .75rem;
    background: var(--tag-bg); color: var(--tag-text); font-weight: 500;
  }}
  .health-dot {{
    display: inline-block; width: 10px; height: 10px; border-radius: 50%;
    margin-right: 2px; vertical-align: middle;
  }}

  /* Detail overlay */
  .overlay {{ display: none; }}
  .overlay.open {{
    display: flex; position: fixed; inset: 0; z-index: 100;
    background: rgba(0,0,0,.55); align-items: flex-end; justify-content: center;
    animation: fadeIn .2s;
  }}
  .detail {{
    background: var(--card); border-radius: 24px 24px 0 0;
    width: 100%; max-width: 680px; max-height: 88vh; max-height: 88dvh;
    overflow-y: auto; padding: 0; position: relative;
    -webkit-overflow-scrolling: touch;
    animation: slideUp .3s ease;
    transition: transform .15s ease-out;
  }}
  /* Handle indicator for mobile swipe */
  .drag-handle {{
    width: 40px; height: 5px; border-radius: 3px;
    background: #d4ccc3; margin: 10px auto 4px;
    display: block;
  }}
  @keyframes fadeIn {{ from {{ opacity: 0 }} to {{ opacity: 1 }} }}
  @keyframes slideUp {{ from {{ transform: translateY(20%) }} to {{ transform: translateY(0) }} }}

  .detail-img {{
    width: 100%; height: 230px; object-fit: cover; display: block; background: #f0ece6;
  }}
  .detail-content {{ padding: 18px 20px 30px; }}
  .detail-close {{
    position: absolute; top: 14px; right: 14px;
    width: 36px; height: 36px; border-radius: 50%; border: none;
    background: rgba(0,0,0,.5); color: #fff; font-size: 1.1rem;
    cursor: pointer; display: flex; align-items: center; justify-content: center;
    z-index: 10;
  }}
  .detail h2 {{ font-size: 1.35rem; font-weight: 700; margin-bottom: 8px; line-height: 1.3; }}
  .detail-meta {{ font-size: .85rem; color: var(--muted); margin-bottom: 14px; display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }}
  .detail h3 {{ font-size: 1.05rem; font-weight: 600; margin: 20px 0 10px; display: flex; align-items: center; justify-content: space-between; }}
  .detail-hint {{ font-size: .75rem; color: var(--muted); font-weight: normal; }}

  /* Interactive Ingredients (clickable/strikethrough) */
  .ingredient-list {{ list-style: none; display: flex; flex-direction: column; gap: 7px; }}
  .ingredient-list li {{
    padding: 10px 14px; background: #f9f7f3; border-radius: 12px; font-size: .92rem;
    cursor: pointer; transition: all .15s; user-select: none;
    display: flex; align-items: center; gap: 10px;
    border: 1px solid transparent;
  }}
  .ingredient-list li:active {{ background: #ece6dc; }}
  .ingredient-list li.checked {{
    text-decoration: line-through;
    opacity: 0.55;
    background: #f0ece6;
  }}
  .ingredient-check {{
    width: 18px; height: 18px; border-radius: 4px;
    border: 1.5px solid #a89f95; display: inline-flex;
    align-items: center; justify-content: center; font-size: .75rem;
    flex-shrink: 0; color: transparent;
  }}
  .ingredient-list li.checked .ingredient-check {{
    background: var(--accent2); border-color: var(--accent2); color: #fff;
  }}

  /* Steps list */
  .step-list {{ list-style: none; counter-reset: step; display: flex; flex-direction: column; gap: 12px; }}
  .step-list li {{
    counter-increment: step; display: flex; gap: 12px; font-size: .92rem; line-height: 1.55;
    cursor: pointer; transition: opacity .15s;
  }}
  .step-list li.checked {{ opacity: 0.5; text-decoration: line-through; }}
  .step-list li::before {{
    content: counter(step);
    flex-shrink: 0; width: 26px; height: 26px; border-radius: 50%;
    background: var(--accent); color: #fff;
    display: flex; align-items: center; justify-content: center;
    font-size: .8rem; font-weight: 600;
  }}
  .step-list li.checked::before {{
    background: #8c8076;
  }}

  .detail-tags {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 18px; }}

  /* Action Buttons in Modal (Share + Source) */
  .detail-actions {{ display: flex; gap: 10px; margin-top: 20px; flex-wrap: wrap; }}
  .btn-action {{
    flex: 1; min-width: 140px; display: inline-flex; align-items: center; justify-content: center; gap: 6px;
    padding: 10px 16px; border-radius: 12px; font-size: .88rem; font-weight: 600;
    text-decoration: none; cursor: pointer; border: none; transition: background .15s;
    -webkit-tap-highlight-color: transparent;
  }}
  .btn-share {{ background: var(--tag-bg); color: var(--text); }}
  .btn-share:hover {{ background: #e8e2da; }}
  .btn-source {{ background: rgba(232,93,58,.1); color: var(--accent); }}
  .btn-source:hover {{ background: rgba(232,93,58,.16); }}

  /* No results */
  .no-results {{ text-align: center; padding: 40px 20px; color: var(--muted); display: none; }}
  .no-results.visible {{ display: block; }}
  .no-results .emoji {{ font-size: 3rem; margin-bottom: 12px; }}

  /* Scrollbar */
  .detail::-webkit-scrollbar {{ width: 5px; }}
  .detail::-webkit-scrollbar-thumb {{ background: #d4ccc3; border-radius: 4px; }}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>🥘 Recetario</h1>
    <p class="count" id="recipeCount">{len(recipes)} recetas guardadas</p>
    <p class="sub" id="lastAdded">{last_str}</p>
  </header>

  <div class="search-wrap">
    <span class="search-icon">🔍</span>
    <input type="search" id="searchInput" placeholder="Buscar por plato, ingrediente (ej. aguacate)..." autocomplete="off">
  </div>

  <div class="tags-wrap" id="tagFilters"></div>

  <div class="recipes" id="recipeList"></div>

  <div class="no-results" id="noResults">
    <div class="emoji">👨‍🍳</div>
    <p>No hay recetas que coincidan</p>
  </div>
</div>

<div class="overlay" id="overlay">
  <div class="detail" id="detailPane"></div>
</div>

<script>
const RECIPES = {json.dumps(recipes, ensure_ascii=False, indent=2)};
const LATEST_DATE = {('"' + latest_iso + '"' if latest_iso else 'null')};

const DIFF_MAP = {json.dumps(DIFF_MAP, ensure_ascii=False)};
const TAG_EMOJI = {json.dumps(TAG_EMOJI, ensure_ascii=False)};

function healthColor(score) {{
  if (score >= 8) return '#3a8c5e';
  if (score >= 5) return '#d4a017';
  return '#e85d3a';
}}

function formatTime(min) {{
  if (min < 60) return min + 'min';
  const h = Math.floor(min / 60);
  const m = min % 60;
  return m ? h + 'h ' + m + 'min' : h + 'h';
}}

const MAIN_TAGS = ['carne', 'pescado', 'pasta', 'huevo', 'verdura'];
let showAllTags = false;
let activeTag = null;

function getAllTags() {{
  const counts = {{}};
  RECIPES.forEach(r => r.tags.forEach(t => {{ counts[t] = (counts[t] || 0) + 1; }}));
  return Object.entries(counts).sort((a,b) => b[1] - a[1]);
}}

function renderTags() {{
  const wrap = document.getElementById('tagFilters');
  const allTags = getAllTags();
  const mainTags = allTags.filter(([t]) => MAIN_TAGS.includes(t));
  const extraTags = allTags.filter(([t]) => !MAIN_TAGS.includes(t));
  const visible = showAllTags ? allTags : mainTags;
  let html = visible.map(([tag, count]) =>
    `<button class="tag-chip" data-tag="${{tag}}" onclick="toggleTag('${{tag}}')">${{TAG_EMOJI[tag] || '🏷️'}} ${{tag}} <small>(${{count}})</small></button>`
  ).join('');
  if (!showAllTags && extraTags.length > 0) {{
    html += `<button class="tag-more" onclick="toggleMoreTags()">+ ver más</button>`;
  }} else if (showAllTags) {{
    html += `<button class="tag-more" onclick="toggleMoreTags()">− ver menos</button>`;
  }}
  wrap.innerHTML = html;
}}

function toggleMoreTags() {{
  showAllTags = !showAllTags;
  renderTags();
  activeTag = null;
  document.querySelectorAll('.tag-chip').forEach(b => b.classList.remove('active'));
  filterAndRender();
}}

function toggleTag(tag) {{
  if (activeTag === tag) {{
    activeTag = null;
  }} else {{
    activeTag = tag;
  }}
  document.querySelectorAll('.tag-chip').forEach(b => b.classList.toggle('active', b.dataset.tag === activeTag));
  filterAndRender();
}}

function filterAndRender() {{
  const q = document.getElementById('searchInput').value.trim();
  const query = q.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  const filtered = RECIPES.filter(r => {{
    if (activeTag && !r.tags.includes(activeTag)) return false;
    if (!query) return true;
    
    // Búsqueda profunda en título, etiquetas e ingredientes
    const ingrText = r.ingredients.map(i => i.name).join(' ');
    const haystack = (r.title + ' ' + r.tags.join(' ') + ' ' + ingrText).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    return haystack.includes(query);
  }});

  const list = document.getElementById('recipeList');
  const noRes = document.getElementById('noResults');

  if (filtered.length === 0) {{
    list.innerHTML = '';
    noRes.classList.add('visible');
  }} else {{
    noRes.classList.remove('visible');
    list.innerHTML = filtered.map(r => {{
      const totalTime = r.prep_time_min + r.cook_time_min;
      const hc = healthColor(r.health_score);
      return `
        <div class="card" onclick="openDetail('${{r.id}}')">
          <img class="card-img" src="${{r.image || ''}}" alt="${{r.title}}" loading="lazy" onerror="this.parentNode.insertBefore(Object.assign(document.createElement('div'),{{className:'card-img-placeholder',textContent:'🍽️'}}), this); this.remove();">
          <div class="card-body">
            <div class="card-title">${{r.title}}</div>
            <div class="card-meta">
              <span>⏱️ ${{formatTime(totalTime)}}</span>
              <span class="meta-dot"></span>
              <span>${{DIFF_MAP[r.difficulty] || r.difficulty}}</span>
              <span class="meta-dot"></span>
              <span><span class="health-dot" style="background:${{hc}}"></span> ${{r.health_score}}/10</span>
            </div>
            <div class="card-tags">
              ${{r.tags.map(t => `<span class="card-tag">${{TAG_EMOJI[t] || '🏷️'}} ${{t}}</span>`).join('')}}
            </div>
          </div>
        </div>
      `;
    }}).join('');
  }}
}}

let currentRecipe = null;

function openDetail(id) {{
  const r = RECIPES.find(x => x.id === id);
  if (!r) return;
  currentRecipe = r;

  const totalTime = r.prep_time_min + r.cook_time_min;
  const hc = healthColor(r.health_score);
  const detail = document.getElementById('detailPane');

  detail.innerHTML = `
    <div class="drag-handle"></div>
    ${{r.image ? `<img class="detail-img" src="${{r.image}}" alt="${{r.title}}" onerror="this.parentNode.insertBefore(Object.assign(document.createElement('div'),{{className:'card-img-placeholder',textContent:'🍽️',style:'height:220px'}}), this); this.remove();">` : ''}}
    <button class="detail-close" onclick="closeDetail()" aria-label="Cerrar">✕</button>
    <div class="detail-content">
      <h2>${{r.title}}</h2>
      <div class="detail-meta">
        <span>⏱️ Prep: ${{r.prep_time_min}}m · Cocción: ${{r.cook_time_min}}m · Total: ${{formatTime(totalTime)}}</span>
        <span class="meta-dot"></span>
        <span>${{DIFF_MAP[r.difficulty] || r.difficulty}}</span>
        <span class="meta-dot"></span>
        <span><span class="health-dot" style="background:${{hc}}"></span> Salud ${{r.health_score}}/10</span>
      </div>
      <div class="detail-tags">${{r.tags.map(t => `<span class="card-tag">${{TAG_EMOJI[t] || '🏷️'}} ${{t}}</span>`).join('')}}</div>

      <h3>
        <span>🧂 Ingredientes</span>
        <span class="detail-hint">Toca para tachar</span>
      </h3>
      <ul class="ingredient-list">
        ${{r.ingredients.map(i => `
          <li onclick="this.classList.toggle('checked')">
            <span class="ingredient-check">✓</span>
            <span><strong>${{i.name}}</strong>${{i.quantity ? ' — ' + i.quantity + (i.unit ? ' ' + i.unit : '') : ''}}</span>
          </li>
        `).join('')}}
      </ul>

      <h3>
        <span>📝 Preparación</span>
        <span class="detail-hint">Toca para marcar</span>
      </h3>
      <ol class="step-list">
        ${{r.steps.map(s => `<li onclick="this.classList.toggle('checked')">${{s}}</li>`).join('')}}
      </ol>

      <div class="detail-actions">
        <button class="btn-action btn-share" onclick="shareRecipe()">📤 Compartir</button>
        ${{r.source ? `<a class="btn-action btn-source" href="${{r.source}}" target="_blank" rel="noopener">🔗 Ver original</a>` : ''}}
      </div>
    </div>
  `;
  document.getElementById('overlay').classList.add('open');
  document.body.style.overflow = 'hidden';
  setupSwipeToClose(detail);
}}

function closeDetail() {{
  document.getElementById('overlay').classList.remove('open');
  document.body.style.overflow = '';
  currentRecipe = null;
}}

function shareRecipe() {{
  if (!currentRecipe) return;
  const title = currentRecipe.title;
  const url = currentRecipe.source || window.location.href;
  if (navigator.share) {{
    navigator.share({{
      title: title,
      text: 'Receta de ' + title + ' en mi recetario:',
      url: url
    }}).catch(() => {{}});
  }} else {{
    navigator.clipboard.writeText(title + ' - ' + url);
    alert('¡Enlace copiado al portapapeles!');
  }}
}}

// Gesto de swipe hacia abajo para cerrar en móvil
function setupSwipeToClose(el) {{
  let startY = 0;
  let currentY = 0;
  let isDragging = false;

  el.ontouchstart = (e) => {{
    if (el.scrollTop === 0) {{
      startY = e.touches[0].clientY;
      isDragging = true;
    }}
  }};

  el.ontouchmove = (e) => {{
    if (!isDragging) return;
    currentY = e.touches[0].clientY;
    const diff = currentY - startY;
    if (diff > 0 && el.scrollTop === 0) {{
      el.style.transform = `translateY(${{diff}}px)`;
    }}
  }};

  el.ontouchend = () => {{
    if (!isDragging) return;
    isDragging = false;
    const diff = currentY - startY;
    if (diff > 120 && el.scrollTop === 0) {{
      closeDetail();
    }}
    el.style.transform = '';
    startY = 0;
    currentY = 0;
  }};
}}

document.getElementById('overlay').addEventListener('click', function(e) {{
  if (e.target === this) closeDetail();
}});

document.getElementById('searchInput').addEventListener('input', filterAndRender);

document.addEventListener('keydown', function(e) {{
  if (e.key === 'Escape') closeDetail();
}});

// Dynamic last-added timer
function updateLastAdded() {{
  const el = document.getElementById('lastAdded');
  if (!LATEST_DATE) {{ el.textContent = ''; return; }}
  const now = new Date();
  const latest = new Date(LATEST_DATE);
  const diff = (now - latest) / 1000;
  const days = Math.floor(diff / 86400);
  const hours = Math.floor((diff % 86400) / 3600);
  const minutes = Math.floor((diff % 3600) / 60);
  let text;
  if (days >= 30) {{
    const months = Math.floor(days / 30);
    text = months === 1 ? 'Última añadida hace 1 mes' : 'Última añadida hace ' + months + ' meses';
  }} else if (days >= 7) {{
    const weeks = Math.floor(days / 7);
    text = weeks === 1 ? 'Última añadida hace 1 semana' : 'Última añadida hace ' + weeks + ' semanas';
  }} else if (days >= 2) {{
    text = 'Última añadida hace ' + days + ' días';
  }} else if (days === 1) {{
    text = 'Última añadida hace 1 día';
  }} else if (hours >= 2) {{
    text = 'Última añadida hace ' + hours + ' horas';
  }} else if (hours === 1) {{
    text = 'Última añadida hace 1 hora';
  }} else if (minutes >= 2) {{
    text = 'Última añadida hace ' + minutes + ' minutos';
  }} else {{
    text = 'Última añadida hace unos segundos';
  }}
  el.textContent = text;
}}
updateLastAdded();
setInterval(updateLastAdded, 30000);

// Init
renderTags();
filterAndRender();
</script>
</body>
</html>"""


def main():
    recipes_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("recipes.json")
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("index.html")

    with open(recipes_path) as f:
        recipes_json_str = f.read()

    html = build_html(recipes_json_str)

    with open(output_path, "w") as f:
        f.write(html)

    print(f"✅ Generated {output_path} with {len(json.loads(recipes_json_str))} recipes")


if __name__ == "__main__":
    main()
