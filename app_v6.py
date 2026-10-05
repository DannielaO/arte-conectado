from urllib.parse import urlparse
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
                signals.append('El enlace no usa el dominio verificado de la entidad mencionada.' if lang == 'es' else 'The link does not use the verified domain of the named organization.')
                critical.append('brand_mismatch')
        except Exception:
            score += 25
            signals.append('No pudimos comprobar técnicamente el enlace, así que lo tratamos como riesgoso.' if lang == 'es' else 'We could not technically verify the link, so it is treated as risky.')
            critical.append('technical_failure')

    score = min(max(score, 0), 99)
    if urls:
        decision = 'red'
        level = 'Riesgo alto' if lang == 'es' else 'High risk'
        action = ('No abras el enlace ni entregues información. Entra tú mismo a la app o página oficial de la empresa para comprobar el mensaje.' if lang == 'es' else 'Do not open the link or share information. Go directly to the organization’s official app or website to verify the message.')
        score = max(score, 65)
    else:
        decision = 'gray'
        level = 'No hay suficiente información' if lang == 'es' else 'Not enough information'
        action = ('No hay un enlace que podamos verificar. Si el mensaje te pide hacer algo, entra por la app o web oficial.' if lang == 'es' else 'There is no link to verify. If the message asks you to act, use the official app or website.')

    return jsonify(score=score, decision=decision, level=level, signals=signals, action=action,
                   count=len(urls), host=host, final=final, https=https, verified=verified, external=external)

def safe_analyze():
    response = _original_analyze()
    # Flask views may return either a Response or (Response, status).
    status = response[1] if isinstance(response, tuple) and len(response) > 1 else getattr(response, 'status_code', 200)
    if status >= 500:
        payload = request.get_json(silent=True) or {}
        message = (payload.get('message') or '').strip()
        lang = 'en' if payload.get('lang') == 'en' else 'es'
        app.logger.warning('Using safe analysis fallback after internal analyzer failure')
        return _safe_fallback(message, lang), 200
    return response

app.view_functions['analyze'] = safe_analyze

if __name__ == '__main__':
    import os
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
