import os, re, socket, ipaddress, base64, hashlib
from urllib.parse import urlparse, urljoin
from flask import Flask, request, jsonify, render_template_string
import requests

app = Flask(__name__)

SHORTENERS = {"bit.ly","tinyurl.com","t.co","goo.gl","ow.ly","buff.ly","is.gd","cutt.ly","rebrand.ly","rb.gy","shorturl.at"}
SUSPICIOUS_TLDS = {"zip","mov","click","top","xyz","work","support","rest","country","gq","tk","ml","cf","ga"}
BRANDS = {"bancolombia":"bancolombia.com","davivienda":"davivienda.com","bbva":"bbva.com","paypal":"paypal.com","apple":"apple.com","google":"google.com","microsoft":"microsoft.com","amazon":"amazon.com","netflix":"netflix.com","instagram":"instagram.com","facebook":"facebook.com"}
UA = "EstoEsReal/1.0 (+security URL checker)"

HTML = r'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>¿Esto es real?</title><style>
:root{--bg:#0b0e12;--panel:#141a21;--line:#26313d;--txt:#f4f7fa;--muted:#98a5b3;--acc:#7ce3c4;--bad:#ff6b6b;--warn:#ffd166;--good:#69db7c}*{box-sizing:border-box}body{margin:0;background:linear-gradient(180deg,#0b0e12,#111820);color:var(--txt);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;min-height:100vh}.wrap{max-width:820px;margin:auto;padding:28px 18px 60px}.brand{color:var(--muted);font-size:13px;margin-bottom:28px}h1{font-size:clamp(40px,8vw,68px);letter-spacing:-2.5px;line-height:.95;margin:0 0 14px}.lead{color:#c3cbd4;font-size:18px;line-height:1.5;margin-bottom:24px}.card{background:rgba(20,26,33,.96);border:1px solid var(--line);border-radius:22px;padding:18px;box-shadow:0 25px 80px #0005}.inputrow{display:flex;gap:10px;flex-wrap:wrap}input{flex:1;min-width:220px;padding:15px;border-radius:14px;border:1px solid #32404e;background:#0c1117;color:white;font-size:16px;outline:none}button{padding:14px 18px;border:0;border-radius:14px;background:var(--acc);font-weight:800;cursor:pointer}.small{font-size:12px;color:var(--muted);line-height:1.5;margin-top:10px}.loading{display:none;margin-top:18px;color:var(--muted)}.result{display:none;margin-top:18px}.scorebox{display:grid;grid-template-columns:130px 1fr;gap:18px;padding:18px;border:1px solid var(--line);border-radius:18px;background:#0d1218}.score{font-size:43px;font-weight:900}.level{font-size:24px;font-weight:850}.bar{height:9px;background:#222c36;border-radius:9px;overflow:hidden;margin-top:12px}.fill{height:100%;width:0}.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px}.box{background:#0d1218;border:1px solid var(--line);border-radius:16px;padding:16px;overflow-wrap:anywhere}.box h3{font-size:13px;margin:0 0 9px;color:#dbe3ea}.kv{margin:6px 0;color:#c0cad3}.kv b{color:white}.signals{margin:0;padding-left:20px;color:#c0cad3;line-height:1.55}.action{margin-top:12px;padding:16px;border:1px solid var(--line);border-radius:16px;background:#0d1218;line-height:1.5}.error{display:none;margin-top:14px;padding:12px;border:1px solid #713b3b;background:#2b1518;border-radius:12px;color:#ffd2d2}@media(max-width:620px){.grid{grid-template-columns:1fr}.scorebox{grid-template-columns:1fr}}
</style></head><body><main class="wrap"><div class="brand">URL SECURITY CHECKER · V1</div><h1>¿Esto es real?</h1><p class="lead">Pega un enlace sospechoso. Lo revisamos sin que tengas que abrirlo: dominio, DNS, HTTPS, redirecciones, suplantación y señales de phishing.</p><section class="card"><div class="inputrow"><input id="url" type="url" placeholder="https://ejemplo.com"><button onclick="analyze()">Analizar enlace</button></div><div class="small">No introduzcas contraseñas. La herramienta solo inspecciona el enlace y el HTML público; nunca envía formularios.</div><div id="loading" class="loading">Analizando…</div><div id="error" class="error"></div><div id="result" class="result"><div class="scorebox"><div><div style="font-size:12px;color:var(--muted)">RIESGO</div><div id="score" class="score"></div></div><div><div id="level" class="level"></div><div class="bar"><div id="fill" class="fill"></div></div></div></div><div class="grid"><div class="box"><h3>DATOS TÉCNICOS</h3><div class="kv"><b>Dominio:</b> <span id="host"></span></div><div class="kv"><b>URL final:</b> <span id="final"></span></div><div class="kv"><b>Redirecciones:</b> <span id="redirects"></span></div><div class="kv"><b>HTTPS:</b> <span id="https"></span></div><div class="kv"><b>DNS:</b> <span id="dns"></span></div><div class="kv"><b>VirusTotal:</b> <span id="vt"></span></div></div><div class="box"><h3>SEÑALES DETECTADAS</h3><ul id="signals" class="signals"></ul></div></div><div class="action"><b>Qué hacer:</b> <span id="action"></span></div></div></section></main><script>
async function analyze(){let u=document.getElementById('url').value.trim(),l=document.getElementById('loading'),e=document.getElementById('error'),r=document.getElementById('result');e.style.display='none';r.style.display='none';if(!u)return;l.style.display='block';try{let res=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:u})});let d=await res.json();if(!res.ok)throw new Error(d.error||'No se pudo analizar');document.getElementById('score').textContent=d.score+'%';document.getElementById('level').textContent=d.level;let c=d.score>=65?'var(--bad)':d.score>=35?'var(--warn)':'var(--good)';document.getElementById('level').style.color=c;document.getElementById('fill').style.width=d.score+'%';document.getElementById('fill').style.background=c;for(let k of ['host','final','redirects','https','dns','vt','action'])document.getElementById(k).textContent=d[k];document.getElementById('signals').innerHTML=(d.signals.length?d.signals:['No se detectaron señales fuertes.']).map(x=>'<li>'+x.replace(/[&<>]/g,s=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[s]))+'</li>').join('');r.style.display='block'}catch(x){e.textContent=x.message;e.style.display='block'}finally{l.style.display='none'}}
</script></body></html>'''

def normalize_url(raw):
    raw = (raw or '').strip()
    if not raw: raise ValueError('Escribe un enlace.')
    if not re.match(r'^https?://', raw, re.I): raw = 'https://' + raw
    p = urlparse(raw)
    if p.scheme not in ('http','https') or not p.hostname: raise ValueError('URL no válida.')
    if p.username or p.password: raise ValueError('No se permiten credenciales incrustadas en la URL.')
    return raw

def resolve_public(host):
    try:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise ValueError('El dominio no resuelve en DNS.')
    ips = sorted({x[4][0] for x in infos})
    if not ips: raise ValueError('No se encontraron direcciones IP.')
    for ip in ips:
        obj = ipaddress.ip_address(ip)
        if not obj.is_global:
            raise ValueError('Por seguridad no analizamos direcciones privadas, locales o reservadas.')
    return ips

def host_signals(host):
    s=[]; h=host.lower().rstrip('.')
    if h.startswith('xn--') or '.xn--' in h: s.append('El dominio usa Punycode; puede ocultar caracteres parecidos a los de una marca.')
    if h.count('.') >= 4: s.append('El dominio tiene un número inusual de subdominios.')
    try:
        ipaddress.ip_address(h); s.append('La URL usa una dirección IP en lugar de un dominio.')
    except ValueError: pass
    tld=h.rsplit('.',1)[-1] if '.' in h else ''
    if tld in SUSPICIOUS_TLDS: s.append('La extensión del dominio aparece con frecuencia en campañas de abuso y merece verificación adicional.')
    if h in SHORTENERS: s.append('Es un acortador de enlaces; oculta el destino real.')
    compact=re.sub(r'[^a-z0-9]','',h)
    for brand,official in BRANDS.items():
        if brand in compact and not (h==official or h.endswith('.'+official)):
            s.append(f'El dominio menciona “{brand}” pero no corresponde al dominio oficial esperado.')
    if h.count('-')>=3: s.append('El dominio contiene muchos guiones, un patrón frecuente en imitaciones.')
    return s

def vt_lookup(url):
    key=os.getenv('VIRUSTOTAL_API_KEY')
    if not key: return None
    try:
        ident=base64.urlsafe_b64encode(url.encode()).decode().strip('=')
        rr=requests.get('https://www.virustotal.com/api/v3/urls/'+ident,headers={'x-apikey':key},timeout=6)
        if rr.status_code==200:
            stats=rr.json()['data']['attributes']['last_analysis_stats']
            return {'malicious':stats.get('malicious',0),'suspicious':stats.get('suspicious',0),'harmless':stats.get('harmless',0)}
    except Exception: pass
    return None

def fetch_chain(start):
    cur=start; chain=[]; html=''; https_ok=False; ips=[]
    sess=requests.Session(); sess.headers.update({'User-Agent':UA,'Accept':'text/html,application/xhtml+xml'})
    for i in range(6):
        p=urlparse(cur); ips=resolve_public(p.hostname)
        try:
            resp=sess.get(cur,timeout=(4,8),allow_redirects=False,stream=True,verify=True)
        except requests.exceptions.SSLError:
            raise ValueError('El sitio presenta un error de certificado TLS/HTTPS.')
        except requests.RequestException as ex:
            raise ValueError('No fue posible conectar con el sitio de forma segura.')
        https_ok = p.scheme=='https'
        if resp.is_redirect or resp.is_permanent_redirect:
            loc=resp.headers.get('Location')
            if not loc: break
            nxt=urljoin(cur,loc); chain.append(nxt); cur=normalize_url(nxt); continue
        ctype=(resp.headers.get('content-type') or '').lower()
        if 'text/html' in ctype:
            data=b''
            for chunk in resp.iter_content(16384):
                data += chunk
                if len(data)>350000: break
            html=data.decode(resp.encoding or 'utf-8',errors='ignore')
        return cur,chain,https_ok,ips,html,resp.status_code
    if len(chain)>=6: raise ValueError('Demasiadas redirecciones.')
    return cur,chain,https_ok,ips,html,0

def score_analysis(original, final, chain, https_ok, html):
    score=0; sig=[]; p=urlparse(original); fp=urlparse(final)
    hs=host_signals(p.hostname); sig+=hs; score+=min(45,len(hs)*13)
    if not https_ok: score+=18; sig.append('El destino final no usa HTTPS.')
    if chain: score+=min(15,len(chain)*4)
    if fp.hostname!=p.hostname: sig.append(f'El enlace termina en un dominio distinto: {fp.hostname}.'); score+=10
    low=html.lower()
    credential_terms=['password','contraseña','clave','otp','verification code','código de verificación','cvv','credit card','tarjeta']
    payment_terms=['transferencia','pago','payment','wallet','bitcoin','usdt','nequi','daviplata']
    if html and any(x in low for x in credential_terms): score+=17; sig.append('La página contiene campos o texto relacionado con credenciales/datos sensibles.')
    if html and any(x in low for x in payment_terms): score+=10; sig.append('La página contiene términos relacionados con pagos o transferencias.')
    if '<form' in low and ('password' in low or 'type="password"' in low or "type='password'" in low): score+=15; sig.append('Se detectó un formulario que solicita contraseña.')
    return min(score,97),sig

@app.get('/')
def home(): return render_template_string(HTML)

@app.post('/api/analyze')
def analyze():
    try:
        original=normalize_url((request.get_json(silent=True) or {}).get('url'))
        final,chain,https_ok,ips,html,status=fetch_chain(original)
        score,sig=score_analysis(original,final,chain,https_ok,html)
        vt=vt_lookup(final)
        vt_text='No configurado'
        if vt:
            vt_text=f"{vt['malicious']} maliciosos · {vt['suspicious']} sospechosos"
            if vt['malicious']>0: score=min(99,score+35); sig.append(f"VirusTotal reporta {vt['malicious']} detecciones maliciosas.")
            elif vt['suspicious']>0: score=min(99,score+18); sig.append(f"VirusTotal reporta {vt['suspicious']} detecciones sospechosas.")
        level='Riesgo alto' if score>=65 else 'Riesgo medio' if score>=35 else 'Riesgo bajo'
        action=('No abras el enlace ni entregues datos. Verifica con la entidad por un canal oficial independiente.' if score>=65 else 'Verifica el dominio y la solicitud por otro canal antes de continuar.' if score>=35 else 'No aparecen muchas señales técnicas de fraude, pero riesgo bajo no significa que el sitio sea legítimo. Si pide dinero o credenciales, verifica por un canal oficial.')
        return jsonify(score=score,level=level,signals=sig,host=urlparse(original).hostname,final=final,redirects=str(len(chain)),https='Sí' if https_ok else 'No',dns=', '.join(ips[:3]),vt=vt_text,action=action,status=status)
    except ValueError as e: return jsonify(error=str(e)),400
    except Exception: return jsonify(error='Ocurrió un error inesperado durante el análisis.'),500

if __name__=='__main__':
    app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)))
