import os
from flask import request, jsonify
from app_v5 import app, extract_urls, message_signals, host_signals, mentioned_entity, verify_entity_domain

_original_analyze = app.view_functions.get('analyze')


def _safe_fallback(message, lang='es'):
    score, signals, critical = message_signals(message, lang)
    urls = extract_urls(message)
    host = '—'
    final = '—'
    https = '—'
    verified = 'No'
    external = 'No disponible' if lang == 'es' else 'Unavailable'

    if urls:
        raw = urls[0]
        try:
            from urllib.parse import urlparse
            p = urlparse(raw)
            host = p.hostname or '—'
            final = raw
            https = ('Sí' if p.scheme == 'https' else 'No') if lang == 'es' else ('Yes' if p.scheme == 'https' else 'No')
            hs, hsig, hcrit = host_signals(host, lang)
            score += hs
            signals += hsig
            critical += hcrit
            entity = mentioned_entity(message)
            if entity and not verify_entity_domain(entity, host):
                score += 28
                signals.append(
                    'El enlace no usa el dominio verificado de la entidad mencionada.'
                    if lang == 'es' else
                    'The link does not use the verified domain of the named organization.'
                )
                critical.append('brand_mismatch')
        except Exception:
            score += 25
            signals.append(
                'No pudimos comprobar técnicamente el enlace, así que lo tratamos como riesgoso.'
                if lang == 'es' else
                'We could not technically verify the link, so it is treated as risky.'
            )
            critical.append('technical_failure')

    score = min(max(score, 0), 99)

    if urls:
        decision = 'red'
        level = 'Riesgo alto' if lang == 'es' else 'High risk'
        score = max(score, 65)
        action = (
            'No abras el enlace ni entregues información. Entra tú mismo a la app o página oficial de la empresa para comprobar el mensaje.'
            if lang == 'es' else
            'Do not open the link or share information. Go directly to the organization’s official app or website to verify the message.'
        )
    else:
        decision = 'gray'
        level = 'No hay suficiente información' if lang == 'es' else 'Not enough information'
        action = (
            'No hay un enlace que podamos verificar. Si el mensaje te pide hacer algo, entra por la app o web oficial.'
            if lang == 'es' else
            'There is no link to verify. If the message asks you to act, use the official app or website.'
        )

    return jsonify(
        score=score,
        decision=decision,
        level=level,
        signals=signals,
        action=action,
        count=len(urls),
        host=host,
        final=final,
        https=https,
        verified=verified,
        external=external,
    )


def _normalize_success(response):
    """Keep launch behavior conservative and internally consistent."""
    try:
        data = response.get_json(silent=True)
        if not isinstance(data, dict) or 'decision' not in data:
            return response

        decision = data.get('decision')
        score = int(data.get('score') or 0)
        external = data.get('external')

        # A red/high-risk decision must never display a low-looking percentage.
        if decision == 'red' and score < 65:
            data['score'] = 65

        # Lack of the optional external reputation service must not look like
        # a broken product or crash the analysis.
        if external in ('No configurada', 'Not configured', None, ''):
            data['external'] = 'No disponible' if request.json is None or request.json.get('lang') != 'en' else 'Unavailable'

        normalized = jsonify(data)
        normalized.status_code = response.status_code
        return normalized
    except Exception:
        return response


def safe_analyze():
    try:
        response = _original_analyze()
    except Exception:
        app.logger.exception('Unexpected analyzer failure; using safe fallback')
        payload = request.get_json(silent=True) or {}
        message = (payload.get('message') or '').strip()
        lang = 'en' if payload.get('lang') == 'en' else 'es'
        return _safe_fallback(message, lang), 200

    status = response[1] if isinstance(response, tuple) and len(response) > 1 else getattr(response, 'status_code', 200)

    if status >= 500:
        payload = request.get_json(silent=True) or {}
        message = (payload.get('message') or '').strip()
        lang = 'en' if payload.get('lang') == 'en' else 'es'
        app.logger.warning('Using safe analysis fallback after internal analyzer failure')
        return _safe_fallback(message, lang), 200

    if isinstance(response, tuple):
        flask_response = response[0]
        normalized = _normalize_success(flask_response)
        return normalized, status

    return _normalize_success(response)


app.view_functions['analyze'] = safe_analyze


@app.after_request
def launch_headers(response):
    # Analysis results should never be cached by browsers, proxies or the PWA.
    if request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store, max-age=0'
        response.headers['Pragma'] = 'no-cache'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response


@app.get('/health')
def health():
    return jsonify(status='ok', version='launch-2026-10-05')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
