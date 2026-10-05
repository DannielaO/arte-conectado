import os, re, socket, ipaddress, base64
from urllib.parse import urlparse, urljoin
from flask import Flask, request, jsonify, render_template_string
import requests

app = Flask(__name__)

UA = "EstoEsReal/3.0"
SHORTENERS = {"bit.ly","tinyurl.com","t.co","goo.gl","ow.ly","buff.ly","is.gd","cutt.ly","rebrand.ly","rb.gy","shorturl.at"}
SUSPICIOUS_TLDS = {"zip","mov","click","top","xyz","work","support","rest","country","gq","tk","ml","cf","ga"}

# Base curada inicial. Verde solo puede ocurrir si la entidad y el dominio coinciden aquí.
VERIFIED_ENTITIES = {
    "coordinadora": ["coordinadora.com"],
    "bancolombia": ["bancolombia.com"],
    "davivienda": ["davivienda.com"],
    "bbva": ["bbva.com", "bbva.com.co"],
    "dian": ["dian.gov.co"],
    "servientrega": ["servientrega.com"],
    "interrapidisimo": ["interrapidisimo.com"],
    "paypal": ["paypal.com"],
    "apple": ["apple.com"],
    "google": ["google.com"],
    "microsoft": ["microsoft.com"],
    "amazon": ["amazon.com"],
    "netflix": ["netflix.com"]
}

HTML = r'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>¿Esto es real?</title><style>
:root{--bg:#0b0e12;--panel:#141a21;--line:#26313d;--txt:#f4f7fa;--muted:#98a5b3;--acc:#7ce3c4;--bad:#ff6b6b;--warn:#ffd166;--good:#69db7c;--gray:#aab4bf}*{box-sizing:border-box}body{margin:0;background:linear-gradient(180deg,#0b0e12,#111820);color:var(--txt);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;min-height:100vh}.wrap{max-width:820px;margin:auto;padding:28px 18px 60px}.brand{color:var(--muted);font-size:13px;margin-bottom:28px}h1{font-size:clamp(40px,8vw,68px);letter-spacing:-2.5px;line-height:.95;margin:0 0 14px}.lead{color:#c3cbd4;font-size:18px;line-height:1.5;margin-bottom:24px}.card{background:rgba(20,26,33,.96);border:1px solid var(--line);border-radius:22px;padding:18px;box-shadow:0 25px 80px #0005}.langs{display:flex;justify-content:flex-end;gap:8px;margin-bottom:10px}.langs button{width:auto;margin:0;padding:7px 11px;background:#202a35;color:white;font-weight:700}.langs button.active{background:var(--acc);color:#09110f}textarea{width:100%;min-height:190px;padding:15px;border-radius:14px;border:1px solid #32404e;background:#0c1117;color:white;font-size:16px;outline:none;resize:vertical}button.main{width:100%;margin-top:10px;padding:14px 18px;border:0;border-radius:14px;background:var(--acc);font-weight:800;cursor:pointer}.small{font-size:12px;color:var(--muted);line-height:1.5;margin-top:10px}.loading{display:none;margin-top:18px;color:var(--muted)}.result{display:none;margin-top:18px}.scorebox{display:grid;grid-template-columns:130px 1fr;gap:18px;padding:18px;border:1px solid var(--line);border-radius:18px;background:#0d1218}.score{font-size:43px;font-weight:900}.level{font-size:24px;font-weight:850}.bar{height:9px;background:#222c36;border-radius:9px;overflow:hidden;margin-top:12px}.fill{height:100%;width:0}.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px}.box{background:#0d1218;border:1px solid var(--line);border-radius:16px;padding:16px;overflow-wrap:anywhere}.box h3{font-size:13px;margin:0 0 9px;color:#dbe3ea}.kv{margin:6px 0;color:#c0cad3}.kv b{color:white}.signals{margin:0;padding-left:20px;color:#c0cad3;line-height:1.55}.action{margin-top:12px;padding:16px;border:1px solid var(--line);border-radius:16px;background:#0d1218;line-height:1.5}.error{display:none;margin-top:14px;padding:12px;border:1px solid #713b3b;background:#2b1518;border-radius:12px;color:#ffd2d2}.technical{margin-top:12px}.technical summary{cursor:pointer;color:var(--muted)}@media(max-width:620px){.grid{grid-template-columns:1fr}.scorebox{grid-template-columns:1fr}}
</style></head><body><main class="wrap"><div class="brand">ESTO ES REAL · V3</div><h1 id="title">¿Esto es real?</h1><p id="lead" class="lead">Pega aquí el mensaje que recibiste.</p><section class="card"><div class="langs"><button id="esBtn" class="active" onclick="setLang('es')">ES</button><button id="enBtn" onclick="setLang('en')">EN</button></div><textarea id="message" placeholder="Pega aquí el mensaje..."></textarea><button class="main" id="analyzeBtn" onclick="analyze()">Analizar mensaje</button><div id="hint" class="small">Puedes pegar un SMS, WhatsApp, correo o un enlace. Nunca escribas contraseñas ni códigos.</div><div id="loading" class="loading">Analizando…</div><div id="error" class="error"></div><div id="result" class="result"><div class="scorebox"><div><div id="riskLabel" style="font-size:12px;color:var(--muted)">RIESGO</div><div id="score" class="score"></div></div><div><div id="level" class="level"></div><div class="bar"><div id="fill" class="fill"></div></div></div></div><div class="grid"><div class="box"><h3 id="whyTitle">¿POR QUÉ?</h3><ul id="signals" class="signals"></ul></div><div class="box"><h3 id="whatTitle">¿QUÉ HACER?</h3><div id="action" class="kv"></div></div></div><details class="technical"><summary id="techSummary">Ver detalles técnicos</summary><div class="box" style="margin-top:10px"><div class="kv"><b>Enlaces:</b> <span id="count"></span></div><div class="kv"><b>Dominio:</b> <span id="host"></span></div><div class="kv"><b>Destino final:</b> <span id="final"></span></div><div class="kv"><b>HTTPS:</b> <span id="https"></span></div><div class="kv"><b>Entidad verificada:</b> <span id="verified"></span></div><div class="kv"><b>Fuente externa:</b> <span id="external"></span></div></div></details></div></section></main><script>
let lang='es';const tx={es:{title:'¿Esto es real?',lead:'Pega aquí el mensaje que recibiste.',ph:'Pega aquí el mensaje...',btn:'Analizar mensaje',hint:'Puedes pegar un SMS, WhatsApp, correo o un enlace. Nunca escribas contraseñas ni códigos.',loading:'Analizando…',risk:'RIESGO',why:'¿POR QUÉ?',what:'¿QUÉ HACER?',tech:'Ver detalles técnicos'},en:{title:'Is this real?',lead:'Paste the message you received here.',ph:'Paste the message here...',btn:'Check message',hint:'You can paste an SMS, WhatsApp message, email, or link. Never enter passwords or verification codes.',loading:'Checking…',risk:'RISK',why:'WHY?',what:'WHAT TO DO',tech:'View technical details'}};
function setLang(l){lang=l;let t=tx[l];for(let [id,v] of Object.entries({title:t.title,lead:t.lead,analyzeBtn:t.btn,hint:t.hint,loading:t.loading,riskLabel:t.risk,whyTitle:t.why,whatTitle:t.what,techSummary:t.tech}))document.getElementById(id).textContent=v;document.getElementById('message').placeholder=t.ph;document.getElementById('esBtn').classList.toggle('active',l==='es');document.getElementById('enBtn').classList.toggle('active',l==='en')}
async function analyze(){let m=document.getElementById('message').value.trim(),l=document.getElementById('loading'),e=document.getElementById('error'),r=document.getElementById('result');e.style.display='none';r.style.display='none';if(!m)return;l.style.display='block';try{let res=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:m,lang})});let d=await res.json();if(!res.ok)throw new Error(d.error||'No se pudo analizar');document.getElementById('score').textContent=d.score+'%';document.getElementById('level').textContent=d.level;let c=d.decision==='green'?'var(--good)':d.decision==='red'?'var(--bad)':d.decision==='gray'?'var(--gray)':'var(--warn)';document.getElementById('level').style.color=c;document.getElementById('fill').style.width=d.score+'%';document.getElementById('fill').style.background=c;for(let k of ['count','host','final','https','verified','external','action'])document.getElementById(k).textContent=d[k];document.getElementById('signals').innerHTML=(d.signals.length?d.signals:[lang==='es'?'No vimos señales claras.':'We did not find clear warning signs.']).map(x=>'<li>'+x.replace(/[&<>]/g,s=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[s]))+'</li>').join('');r.style.display='block'}catch(x){e.textContent=x.message;e.style.display='block'}finally{l.style.display='none'}}
</script></body></html>'''

def extract_urls(text):
    found = re.findall(r'(?i)\bhttps?://[^\s<>"\']+', text or '')
    return list(dict.fromkeys(u.rstrip('.,;:!?)\]\}') for u in found))

def mentioned_entity(text):
    t=(text or '').lower()
    for name in VERIFIED_ENTITIES:
        if name in t: return name
    return None

def normalize_url(raw):
    p=urlparse((raw or '').strip())
    if p.scheme not in ('http','https') or not p.hostname: raise ValueError('URL no válida.')
    if p.username or p.password: raise ValueError('No se permiten credenciales dentro del enlace.')
    return raw.strip()

def resolve_public(host):
    infos=socket.getaddrinfo(host,None,proto=socket.IPPROTO_TCP)
    ips=sorted({x[4][0] for x in infos})
    for ip in ips:
        if not ipaddress.ip_address(ip).is_global: raise ValueError('No analizamos direcciones privadas o locales.')
    return ips

def domain_matches(host, official):
    h=host.lower().rstrip('.')
    return h==official or h.endswith('.'+official)

def verify_entity_domain(entity, host):
    if not entity or not host: return False
    return any(domain_matches(host,d) for d in VERIFIED_ENTITIES.get(entity,[]))

def message_signals(text):
    t=(text or '').lower(); score=0; sig=[]; critical=[]
    rules=[
      (r'no logramos ubicarte|pedido.*pendiente|entrega.*pendiente|paquete.*pendiente',10,'El mensaje usa un problema de entrega o pedido pendiente para apurarte.'),
      (r'revisa|actualiza|confirma|verifica.{0,20}(informaci[oó]n|datos|cuenta)',12,'Te pide revisar o actualizar información.'),
      (r'urgente|inmediatamente|hoy|24 horas|suspendid|bloquead',10,'Usa urgencia o presión para que actúes rápido.'),
      (r'contrase[nñ]a|clave|pin|otp|c[oó]digo de verificaci[oó]n|cvv|tarjeta',22,'Pide o menciona datos que nunca deberías entregar por un mensaje.'),
      (r'transferencia|pago|consignaci[oó]n|nequi|daviplata|bitcoin|usdt',18,'Habla de pagos o transferencias.'),
    ]
    for pat,pts,msg in rules:
        if re.search(pat,t,re.I): score+=pts; sig.append(msg)
    if re.search(r'contrase[nñ]a|otp|cvv|c[oó]digo de verificaci[oó]n',t,re.I): critical.append('Solicita datos altamente sensibles.')
    typo_like=sum(1 for w in ['coordlnadora','informacion  ','  para  ','access:'] if w in t)
    if typo_like: score+=7; sig.append('Tiene errores o un formato poco profesional.')
    return min(score,50),sig,critical

def host_signals(host):
    s=[]; critical=[]; score=0; h=host.lower().rstrip('.')
    try:
        ipaddress.ip_address(h); s.append('El enlace usa una dirección IP en vez de un dominio normal.'); score+=30; critical.append('Dirección IP directa.')
    except ValueError: pass
    if h.startswith('xn--') or '.xn--' in h: s.append('El dominio usa caracteres codificados que pueden imitar otra marca.'); score+=20
    if h in SHORTENERS: s.append('El enlace está acortado y oculta el destino real.'); score+=15
    tld=h.rsplit('.',1)[-1] if '.' in h else ''
    if tld in SUSPICIOUS_TLDS: s.append('La extensión del dominio requiere más cuidado.'); score+=10
    if h.count('.')>=4: s.append('El dominio tiene demasiados niveles.'); score+=8
    if h.count('-')>=3: s.append('El dominio usa muchos guiones.'); score+=8
    return min(score,45),s,critical

def vt_lookup(url):
    key=os.getenv('VIRUSTOTAL_API_KEY')
    if not key: return None
    try:
        ident=base64.urlsafe_b64encode(url.encode()).decode().strip('=')
        rr=requests.get('https://www.virustotal.com/api/v3/urls/'+ident,headers={'x-apikey':key},timeout=6)
        if rr.status_code==200:
            st=rr.json()['data']['attributes']['last_analysis_stats']
            return {'malicious':st.get('malicious',0),'suspicious':st.get('suspicious',0)}
    except Exception: pass
    return None

def fetch_chain(start):
    cur=start; chain=[]; html=''; https_ok=False
    sess=requests.Session(); sess.headers.update({'User-Agent':UA,'Accept':'text/html,application/xhtml+xml'})
    for _ in range(6):
        p=urlparse(cur); resolve_public(p.hostname)
        try: resp=sess.get(cur,timeout=(4,8),allow_redirects=False,stream=True,verify=True)
        except requests.exceptions.SSLError: raise ValueError('El sitio tiene un problema con su certificado HTTPS.')
        except requests.RequestException: raise ValueError('No pudimos conectar con el sitio de forma segura.')
        https_ok=p.scheme=='https'
        if resp.is_redirect or resp.is_permanent_redirect:
            loc=resp.headers.get('Location')
            if not loc: break
            nxt=normalize_url(urljoin(cur,loc)); chain.append(nxt); cur=nxt; continue
        if 'text/html' in (resp.headers.get('content-type') or '').lower():
            data=b''
            for chunk in resp.iter_content(16384):
                data+=chunk
                if len(data)>300000: break
            html=data.decode(resp.encoding or 'utf-8',errors='ignore')
        return cur,chain,https_ok,html
    raise ValueError('El enlace redirige demasiadas veces.')

def external_reputation(url):
    vt=vt_lookup(url)
    if not vt: return {'status':'unknown','text':'No disponible','critical':False,'score':0}
    if vt['malicious']>0: return {'status':'bad','text':f"{vt['malicious']} detecciones maliciosas",'critical':True,'score':40}
    if vt['suspicious']>0: return {'status':'warn','text':f"{vt['suspicious']} detecciones sospechosas",'critical':False,'score':20}
    return {'status':'clean','text':'Sin detecciones en la fuente externa','critical':False,'score':0}

def decide(message):
    urls=extract_urls(message)
    entity=mentioned_entity(message)
    score,msg_sig,critical=message_signals(message)
    signals=list(msg_sig)
    host='No encontrado'; final='No aplica'; https='No aplica'; verified=False; ext_text='No disponible'; chain=[]

    if not urls:
        # Sin enlace no existe base suficiente para dar verde.
        decision='gray' if score<35 else 'red' if critical else 'yellow'
        level='No pudimos verificar' if decision=='gray' else 'Riesgo alto' if decision=='red' else 'Revisa antes de actuar'
        action='No abras nada ni entregues datos. Si el mensaje dice venir de una empresa, entra tú mismo a su app o página oficial.'
        return decision,min(max(score,20),95),level,signals,action,len(urls),host,final,https,verified,ext_text

    original=normalize_url(urls[0]); p=urlparse(original); host=p.hostname
    hscore,hsig,hcritical=host_signals(host); score+=hscore; signals+=hsig; critical+=hcritical

    if entity:
        verified=verify_entity_domain(entity,host)
        if verified:
            signals.append('El dominio coincide con la entidad mencionada.')
        else:
            signals.append('La empresa mencionada no coincide con el dominio del enlace.')
            score+=30; critical.append('Suplantación de identidad probable.')

    if p.scheme!='https':
        signals.append('El enlace no usa HTTPS.'); score+=15

    try:
        final,chain,https_ok,html=fetch_chain(original)
        https='Sí' if https_ok else 'No'
        if urlparse(final).hostname!=host:
            signals.append('El enlace termina en un dominio diferente al que ves al principio.'); score+=10
        if not https_ok: score+=10
        low=html.lower()
        if '<form' in low and ('password' in low or 'type="password"' in low or "type='password'" in low):
            signals.append('La página pide contraseña.'); score+=20
    except ValueError as e:
        signals.append(str(e)); score+=15

    rep=external_reputation(final if final!='No aplica' else original); ext_text=rep['text']; score+=rep['score']
    if rep['critical']: critical.append('Fuente externa confirmó riesgo.')

    # Verde exige verificación positiva, HTTPS y ausencia total de señales críticas.
    if verified and p.scheme=='https' and https=='Sí' and not critical and rep['status'] in ('clean','unknown') and score<25:
        decision='green'; level='Puedes entrar'; score=max(score,5)
        action='El enlace coincide con la entidad verificada y no encontramos señales de riesgo. Puedes abrirlo, pero nunca entregues contraseñas o códigos fuera del flujo normal de la entidad.'
    elif critical or score>=65:
        decision='red'; level='Riesgo alto'; score=max(score,70)
        action='No abras el enlace y no entregues datos. Entra tú mismo a la app o página oficial de la empresa para comprobar el mensaje.'
    else:
        decision='yellow'; level='Verifica antes de entrar'; score=max(score,30)
        action='Todavía no tenemos evidencia suficiente para darte luz verde. Busca la empresa por tu cuenta y entra desde su canal oficial.'

    return decision,min(score,99),level,signals,action,len(urls),host,final,https,verified,ext_text

@app.get('/')
def home(): return render_template_string(HTML)

@app.post('/api/analyze')
def analyze():
    try:
        payload=request.get_json(silent=True) or {}
        message=(payload.get('message') or '').strip()
        if not message: raise ValueError('Pega el mensaje que quieres revisar.')
        decision,score,level,signals,action,count,host,final,https,verified,external=decide(message)
        return jsonify(decision=decision,score=score,level=level,signals=signals,action=action,count=str(count),host=host,final=final,https=https,verified='Sí' if verified else 'No',external=external)
    except ValueError as e:
        return jsonify(error=str(e)),400
    except Exception:
        return jsonify(error='Ocurrió un error durante el análisis.'),500

if __name__=='__main__':
    app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)))
