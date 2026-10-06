import os
from collections import Counter
from threading import Lock
from flask import request, jsonify, render_template_string
from app_v5 import app, extract_urls, message_signals, host_signals, mentioned_entity, verify_entity_domain, HTML

_original_analyze = app.view_functions.get('analyze')
_metrics = Counter()
_sources = Counter()
_metrics_lock = Lock()


def _bump(key, amount=1):
    with _metrics_lock:
        _metrics[key] += amount


def _safe_fallback(message, lang='es'):
    score, signals, critical = message_signals(message, lang)
    urls = extract_urls(message)
    host = '—'; final = '—'; https = '—'; verified = 'No'
    external = 'No disponible' if lang == 'es' else 'Unavailable'
    if urls:
        raw = urls[0]
        try:
            from urllib.parse import urlparse
            p = urlparse(raw); host = p.hostname or '—'; final = raw
            https = ('Sí' if p.scheme == 'https' else 'No') if lang == 'es' else ('Yes' if p.scheme == 'https' else 'No')
            hs, hsig, hcrit = host_signals(host, lang); score += hs; signals += hsig; critical += hcrit
            entity = mentioned_entity(message)
            if entity and not verify_entity_domain(entity, host):
                score += 28
                signals.append('El enlace no usa el dominio verificado de la entidad mencionada.' if lang == 'es' else 'The link does not use the verified domain of the named organization.')
                critical.append('brand_mismatch')
        except Exception:
            score += 25
            signals.append('No pudimos comprobar técnicamente el enlace, así que lo tratamos como riesgoso.' if lang == 'es' else 'We could not technically verify the link, so it is treated as risky.')
            critical.append('technical_failure')
    score = min(max(score, 0), 99)
    if urls:
        decision = 'red'; level = 'Riesgo alto' if lang == 'es' else 'High risk'; score = max(score, 65)
        action = 'No abras el enlace ni entregues información. Entra tú mismo a la app o página oficial de la empresa para comprobar el mensaje.' if lang == 'es' else 'Do not open the link or share information. Go directly to the organization’s official app or website to verify the message.'
    else:
        decision = 'gray'; level = 'No hay suficiente información' if lang == 'es' else 'Not enough information'
        action = 'No hay un enlace que podamos verificar. Si el mensaje te pide hacer algo, entra por la app o web oficial.' if lang == 'es' else 'There is no link to verify. If the message asks you to act, use the official app or website.'
    return jsonify(score=score, decision=decision, level=level, signals=signals, action=action, count=len(urls), host=host, final=final, https=https, verified=verified, external=external)


def _normalize_success(response):
    try:
        data = response.get_json(silent=True)
        if not isinstance(data, dict) or 'decision' not in data: return response
        decision = data.get('decision'); score = int(data.get('score') or 0); external = data.get('external')
        if decision == 'red' and score < 65: data['score'] = 65
        if external in ('No configurada', 'Not configured', None, ''):
            data['external'] = 'No disponible' if request.json is None or request.json.get('lang') != 'en' else 'Unavailable'
        normalized = jsonify(data); normalized.status_code = response.status_code; return normalized
    except Exception:
        return response


def safe_analyze():
    _bump('analyze_requests')
    try:
        response = _original_analyze()
    except Exception:
        app.logger.exception('Unexpected analyzer failure; using safe fallback')
        payload = request.get_json(silent=True) or {}; message = (payload.get('message') or '').strip(); lang = 'en' if payload.get('lang') == 'en' else 'es'
        _bump('analyze_completed')
        return _safe_fallback(message, lang), 200
    status = response[1] if isinstance(response, tuple) and len(response) > 1 else getattr(response, 'status_code', 200)
    if status >= 500:
        payload = request.get_json(silent=True) or {}; message = (payload.get('message') or '').strip(); lang = 'en' if payload.get('lang') == 'en' else 'es'
        app.logger.warning('Using safe analysis fallback after internal analyzer failure'); _bump('analyze_completed')
        return _safe_fallback(message, lang), 200
    if status < 400: _bump('analyze_completed')
    if isinstance(response, tuple):
        flask_response = response[0]; normalized = _normalize_success(flask_response); return normalized, status
    return _normalize_success(response)


app.view_functions['analyze'] = safe_analyze

# Add a lightweight clear button and first-party aggregate usage counters.
_launch_html = HTML.replace(
    'button.main{width:100%;margin-top:10px;padding:15px 18px;border:0;border-radius:14px;background:var(--acc);font-weight:850;font-size:16px;cursor:pointer}',
    'button.main{width:100%;margin-top:10px;padding:15px 18px;border:0;border-radius:14px;background:var(--acc);font-weight:850;font-size:16px;cursor:pointer}.clearBtn{width:100%;margin-top:8px;padding:12px 16px;border:1px solid var(--line);border-radius:14px;background:transparent;color:#c6d0d9;font-weight:750;font-size:14px;cursor:pointer}.clearBtn:active{transform:translateY(1px)}'
).replace(
    '<button class="main" id="analyzeBtn" onclick="analyze()">Analizar mensaje</button>',
    '<button class="main" id="analyzeBtn" onclick="analyze()">Analizar mensaje</button><button class="clearBtn" id="clearBtn" type="button" onclick="clearMessage()">Limpiar</button>'
).replace(
    "loading:'Analizando…',risk:'RIESGO'",
    "loading:'Analizando…',clear:'Limpiar',risk:'RIESGO'"
).replace(
    "loading:'Checking…',risk:'RISK'",
    "loading:'Checking…',clear:'Clear',risk:'RISK'"
).replace(
    "loading:t.loading,riskLabel:t.risk",
    "loading:t.loading,clearBtn:t.clear,riskLabel:t.risk"
).replace(
    "async function analyze(){",
    "function track(event){try{const q=new URLSearchParams(location.search);const source=q.get('utm_source')||(document.referrer?new URL(document.referrer).hostname:'direct');fetch('/api/event',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({event,source}),keepalive:true}).catch(()=>{})}catch(e){}}function clearMessage(){message.value='';result.style.display='none';error.style.display='none';loading.style.display='none';message.focus();track('clear')}async function analyze(){"
).replace(
    "if('serviceWorker' in navigator)",
    "track('page_view');if('serviceWorker' in navigator)"
)


def home_v6():
    return render_template_string(_launch_html)
app.view_functions['home'] = home_v6


@app.post('/api/event')
def usage_event():
    data = request.get_json(silent=True) or {}; event = str(data.get('event') or '')[:40]; source = str(data.get('source') or 'direct')[:80]
    if event in {'page_view','clear'}:
        _bump(event)
        if event == 'page_view':
            with _metrics_lock: _sources[source or 'direct'] += 1
    return ('', 204)


@app.get('/api/stats')
def usage_stats():
    with _metrics_lock:
        return jsonify(metrics=dict(_metrics), sources=dict(_sources), note='Contadores temporales: se reinician al reiniciar o desplegar el servicio.')


@app.after_request
def launch_headers(response):
    if request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store, max-age=0'; response.headers['Pragma'] = 'no-cache'
    response.headers['X-Content-Type-Options'] = 'nosniff'; response.headers['Referrer-Policy'] = 'no-referrer'
    return response


@app.get('/health')
def health():
    return jsonify(status='ok', version='launch-2026-10-05-metrics-clear')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
