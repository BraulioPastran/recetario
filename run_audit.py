import json, base64, urllib.request, urllib.error, os, time

with open('/home/miguel/.openclaw/openclaw.json') as f:
    cfg = json.load(f)

key = cfg['models']['providers']['google']['apiKey']

# We will use gemini-2.5-flash which is standard and cheap, with proper delay and retries
model = "gemini-2.5-flash"
url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

recipes_path = '/home/miguel/.openclaw/workspace/proyectos/recetario/recipes.json'
with open(recipes_path) as f:
    recipes = json.load(f)

results = []
bad = []

prompt = """Eres un editor de fotografía gastronómica estricto. Evalúa si esta imagen muestra un plato TERMINADO, emplatado de forma apetecible y listo para servir.
RECHAZA (is_good: false) si:
- Aparece una persona, cara, o manos manipulando comida/ingredientes.
- Solo se ven ingredientes crudos o en proceso de preparación.
- La comida está en una sartén/olla en proceso de cocción sin ser el plato final emplatado.
- Es borrosa, oscura, de muy baja resolución o fotograma sucio.
- Hay texto gigante, marcas de agua invasivas o stickers de vídeo tapando la comida.
Responde estrictamente en JSON:
{"is_good": true, "reason": "ok"} o {"is_good": false, "reason": "<motivo breve en español>"}"""

out_file = '/home/miguel/.openclaw/workspace/proyectos/recetario/audit_results_latest.json'

for idx, r in enumerate(recipes):
    title = r.get('title', 'Sin título')
    img_rel = r.get('image', '')
    img_path = os.path.join('/home/miguel/.openclaw/workspace/proyectos/recetario', img_rel)
    
    if not os.path.exists(img_path):
        bad.append({'title': title, 'image': img_rel, 'reason': 'El archivo de imagen no existe', 'source': r.get('source', '')})
        print(f"[{idx+1}/{len(recipes)}] ❌ {title} -> No existe", flush=True)
        continue

    with open(img_path, 'rb') as f:
        img_bytes = f.read()
    b64 = base64.b64encode(img_bytes).decode('utf-8')
    
    payload = {
        "contents": [{
            "parts": [
                {"text": f"Receta: {title}\n\n" + prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": b64}}
            ]
        }],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.1
        }
    }
    
    success = False
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                raw_text = data['candidates'][0]['content']['parts'][0]['text']
                parsed = json.loads(raw_text)
                
                is_good = parsed.get('is_good', False)
                reason = parsed.get('reason', 'Sin motivo')
                
                if not is_good:
                    bad.append({'title': title, 'image': img_rel, 'reason': reason, 'source': r.get('source', '')})
                    print(f"[{idx+1}/{len(recipes)}] ❌ {title} -> {reason}", flush=True)
                else:
                    print(f"[{idx+1}/{len(recipes)}] ✅ {title}", flush=True)
                success = True
                time.sleep(1.5)
                break
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait_sec = (attempt + 1) * 4
                print(f"⚠️ 429 Rate limit en {title}, esperando {wait_sec}s...", flush=True)
                time.sleep(wait_sec)
            else:
                print(f"⚠️ HTTP Error {e.code} en {title}: {e}", flush=True)
                time.sleep(2)
        except Exception as e:
            print(f"⚠️ Error en {title}: {e}", flush=True)
            time.sleep(2)
            
    if not success:
        bad.append({'title': title, 'image': img_rel, 'reason': 'Error de conexión / timeout API tras reintentos', 'source': r.get('source', '')})

    # Guardar progreso incremental
    with open(out_file, 'w') as f:
        json.dump({'total': len(recipes), 'processed': idx+1, 'bad_count': len(bad), 'bad_images': bad}, f, indent=2, ensure_ascii=False)

print(f"\n--- AUDITORÍA TERMINADA ---", flush=True)
print(f"Total: {len(recipes)} | Malas: {len(bad)}", flush=True)
