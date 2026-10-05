import os,re,socket,ipaddress,logging
from urllib.parse import urlparse,urljoin
from flask import Flask,request,jsonify,render_template_string,send_from_directory
import requests

app=Flask(__name__)
logging.basicConfig(level=logging.INFO)
UA='EstoEsReal/5.0'
SHORTENERS={'bit.ly','tinyurl.com','t.co','goo.gl','ow.ly','buff.ly','is.gd','cutt.ly','rebrand.ly','rb.gy','shorturl.at'}
SUSPICIOUS_TLDS={'zip','mov','click','top','xyz','work','support','rest','country','gq','tk','ml','cf','ga'}
VERIFIED_ENTITIES={
 'coordinadora':['coordinadora.com'],'bancolombia':['bancolombia.com'],'davivienda':['davivienda.com'],
 'bbva':['bbva.com','bbva.com.co'],'dian':['dian.gov.co'],'servientrega':['servientrega.com'],
 'interrapidisimo':['interrapidisimo.com'],'paypal':['paypal.com'],'apple':['apple.com'],'google':['google.com'],
 'microsoft':['microsoft.com'],'amazon':['amazon.com'],'netflix':['netflix.com']}

HTML='''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="theme-color" content="#0b0e12"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="Esto es real"><link rel="manifest" href="/static/manifest.webmanifest"><link rel="icon" href="/static/icon.svg"><title>¿Esto es real?</title><style>:root{--bg:#0b0e12;--panel:#141a21;--line:#26313d;--txt:#f4f7fa;--muted:#98a5b3;--acc:#7ce3c4;--bad:#ff6b6b;--warn:#ffd166;--good:#69db7c;--gray:#aab4bf}*{box-sizing:border-box}body{margin:0;background:linear-gradient(180deg,#0b0e12,#111820);color:var(--txt);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;min-height:100vh}.wrap{max-width:820px;margin:auto;padding:28px 18px 60px}.top{display:flex;justify-content:space-between;align-items:center;margin-bottom:26px}.brand{color:var(--muted);font-size:12px;letter-spacing:.08em}.langs{display:flex;gap:7px}.langs button{border:1px solid var(--line);border-radius:999px;background:#182029;color:#fff;padding:7px 11px;font-weight:700}.langs button.active{background:var(--acc);color:#08110e}.hero h1{font-size:clamp(42px,8vw,70px);letter-spacing:-2.8px;line-height:.95;margin:0 0 14px}.lead{color:#c6d0d9;font-size:19px;line-height:1.45;margin:0 0 24px}.card{background:rgba(20,26,33,.98);border:1px solid var(--line);border-radius:22px;padding:18px;box-shadow:0 25px 80px #0005}textarea{width:100%;min-height:190px;padding:16px;border-radius:15px;border:1px solid #32404e;background:#0c1117;color:white;font-size:17px;line-height:1.45;outline:none;resize:vertical}button.main{width:100%;margin-top:10px;padding:15px 18px;border:0;border-radius:14px;background:var(--acc);font-weight:850;font-size:16px;cursor:pointer}.small{font-size:12px;color:var(--muted);line-height:1.55;margin-top:10px}.loading,.error,.result{display:none}.loading{margin-top:18px;color:var(--muted)}.error{margin-top:14px;padding:12px;border:1px solid #713b3b;background:#2b1518;border-radius:12px;color:#ffd2d2}.result{margin-top:18px}.scorebox{display:grid;grid-template-columns:130px 1fr;gap:18px;padding:18px;border:1px solid var(--line);border-radius:18px;background:#0d1218}.score{font-size:43px;font-weight:900}.level{font-size:25px;font-weight:850}.bar{height:9px;background:#222c36;border-radius:9px;overflow:hidden;margin-top:12px}.fill{height:100%;width:0}.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px}.box{background:#0d1218;border:1px solid var(--line);border-radius:16px;padding:16px;overflow-wrap:anywhere}.box h3{font-size:13px;margin:0 0 9px;color:#dbe3ea}.signals{margin:0;padding-left:20px;color:#c0cad3;line-height:1.6}.action{color:#e8edf2;line-height:1.55}.technical{margin-top:12px}.technical summary{cursor:pointer;color:var(--muted);font-size:13px}.kv{margin:6px 0;color:#c0cad3}.kv b{color:white}@media(max-width:620px){.grid,.scorebox{grid-template-columns:1fr}}</style></head><body><main class="wrap"><div class="top"><div class="brand">ESTO ES REAL</div><div class="langs"><button id="esBtn" class="active" onclick="setLang('es')">ES</button><button id="enBtn" onclick="setLang('en')">EN</button></div></div><section class="hero"><h1 id="title">¿Esto es real?</h1><p id="lead" class="lead">Pega aquí el mensaje que recibiste.</p></section><section class="card"><textarea id="message" placeholder="Pega aquí el mensaje..."></textarea><button class="main" id="analyzeBtn" onclick="analyze()">Analizar mensaje</button><div id="hint" class="small">Puedes pegar un SMS, WhatsApp, correo o un enlace. Nunca escribas contraseñas ni códigos.</div><div id="loading" class="loading">Analizando…</div><div id="error" class="error"></div><div id="result" class="result"><div class="scorebox"><div><div id="riskLabel" style="font-size:12px;color:var(--muted)">RIESGO</div><div id="score" class="score"></div></div><div><div id="level" class="level"></div><div class="bar"><div id="fill" class="fill"></div></div></div></div><div class="grid"><div class="box"><h3 id="whyTitle">¿POR QUÉ?</h3><ul id="signals" class="signals"></ul></div><div class="box"><h3 id="whatTitle">¿QUÉ HACER?</h3><div id="action" class="action"></div></div></div><details class="technical"><summary id="techSummary">Ver detalles técnicos</summary><div class="box" style="margin-top:10px"><div class="kv"><b>Enlaces:</b> <span id="count"></span></div><div class="kv"><b>Dominio:</b> <span id="host"></span></div><div class="kv"><b>Destino:</b> <span id="final"></span></div><div class="kv"><b>HTTPS:</b> <span id="https"></span></div><div class="kv"><b>Entidad verificada:</b> <span id="verified"></span></div><div class="kv"><b>Reputación externa:</b> <span id="external"></span></div></div></details></div></section></main><script>let lang='es';const tx={es:{title:'¿Esto es real?',lead:'Pega aquí el mensaje que recibiste.',ph:'Pega aquí el mensaje...',btn:'Analizar mensaje',hint:'Puedes pegar un SMS, WhatsApp, correo o un enlace. Nunca escribas contraseñas ni códigos.',loading:'Analizando…',risk:'RIESGO',why:'¿POR QUÉ?',what:'¿QUÉ HACER?',tech:'Ver detalles técnicos'},en:{title:'Is this real?',lead:'Paste the message you received here.',ph:'Paste the message here...',btn:'Check message',hint:'You can paste an SMS, WhatsApp message, email, or link. Never enter passwords or verification codes.',loading:'Checking…',risk:'RISK',why:'WHY?',what:'WHAT TO DO',tech:'View technical details'}};function setLang(l){lang=l;let t=tx[l];for(let [id,v] of Object.entries({title:t.title,lead:t.lead,analyzeBtn:t.btn,hint:t.hint,loading:t.loading,riskLabel:t.risk,whyTitle:t.why,whatTitle:t.what,techSummary:t.tech}))document.getElementById(id).textContent=v;message.placeholder=t.ph;esBtn.classList.toggle('active',l==='es');enBtn.classList.toggle('active',l==='en')}async function analyze(){let m=message.value.trim();error.style.display='none';result.style.display='none';if(!m)return;loading.style.display='block';try{let res=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:m,lang})});let d=await res.json();if(!res.ok)throw new Error(d.error||'No se pudo analizar');score.textContent=d.score+'%';level.textContent=d.level;let c=d.decision==='green'?'var(--good)':d.decision==='red'?'var(--bad)':d.decision==='gray'?'var(--gray)':'var(--warn)';level.style.color=c;fill.style.width=d.score+'%';fill.style.background=c;for(let k of ['count','host','final','https','verified','external','action'])document.getElementById(k).textContent=d[k];signals.innerHTML=(d.signals.length?d.signals:[lang==='es'?'No vimos señales claras.':'We did not find clear warning signs.']).map(x=>'<li>'+x.replace(/[&<>]/g,s=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[s]))+'</li>').join('');result.style.display='block'}catch(x){error.textContent=x.message;error.style.display='block'}finally{loading.style.display='none'}}if('serviceWorker' in navigator)window.addEventListener('load',()=>navigator.serviceWorker.register('/static/sw.js').catch(()=>{}));</script></body></html>'''

def extract_urls(text):
    return list(dict.fromkeys(u.rstrip('.,;:!?)\]\}') for u in re.findall(r'(?i)\bhttps?://[^\s<>"\']+',text or '')))

def mentioned_entity(text):
    t=(text or '').lower()
    for name in VERIFIED_ENTITIES:
        if name in t:return name
    return None

def normalize_url(raw):
    p=urlparse((raw or '').strip())
    if p.scheme not in ('http','https') or not p.hostname:raise ValueError('URL no válida.')
    if p.username or p.password:raise ValueError('No se permiten credenciales dentro del enlace.')
    return raw.strip()

def resolve_public(host):
    try:infos=socket.getaddrinfo(host,None,proto=socket.IPPROTO_TCP)
    except socket.gaierror:raise ValueError('El dominio no existe o no responde.')
    ips=sorted({x[4][0] for x in infos})
    if not ips:raise ValueError('El dominio no resolvió a ninguna dirección.')
    for ip in ips:
        if not ipaddress.ip_address(ip).is_global:raise ValueError('No analizamos direcciones privadas o locales.')
    return ips

def domain_matches(host,official):
    h=(host or '').lower().rstrip('.')
    return h==official or h.endswith('.'+official)

def verify_entity_domain(entity,host):
    return bool(entity and host and any(domain_matches(host,d) for d in VERIFIED_ENTITIES.get(entity,[])))

def message_signals(text,lang='es'):
    t=(text or '').lower();score=0;sig=[];critical=[]
    rules=[(r'no logramos ubicarte|pedido.*pendiente|entrega.*pendiente|paquete.*pendiente',10,'Habla de un pedido o entrega pendiente para que actúes rápido.'),(r'revisa|actualiza|confirma|verifica.{0,20}(informaci[oó]n|datos|cuenta)',12,'Te pide revisar o actualizar información.'),(r'urgente|inmediatamente|hoy|24 horas|suspendid|bloquead',10,'Usa urgencia o presión.'),(r'contrase[nñ]a|clave|pin|otp|c[oó]digo de verificaci[oó]n|cvv|tarjeta',22,'Menciona datos sensibles que no deberías entregar por mensaje.'),(r'transferencia|pago|consignaci[oó]n|nequi|daviplata|bitcoin|usdt',18,'Habla de pagos o transferencias.')]
    en={'Habla de un pedido o entrega pendiente para que actúes rápido.':'It uses a delivery problem to push you to act quickly.','Te pide revisar o actualizar información.':'It asks you to review or update information.','Usa urgencia o presión.':'It uses urgency or pressure.','Menciona datos sensibles que no deberías entregar por mensaje.':'It mentions sensitive information you should not share by message.','Habla de pagos o transferencias.':'It mentions payments or transfers.'}
    for pat,pts,msg in rules:
        if re.search(pat,t,re.I):score+=pts;sig.append(en[msg] if lang=='en' else msg)
    if re.search(r'contrase[nñ]a|otp|cvv|c[oó]digo de verificaci[oó]n',t,re.I):critical.append('sensitive_request')
    if any(w in t for w in ['coordlnadora','informacion  ','  para  ','access:']):score+=7;sig.append('It has unusual spelling or formatting.' if lang=='en' else 'Tiene errores o un formato poco profesional.')
    return min(score,50),sig,critical

def host_signals(host,lang='es'):
    s=[];critical=[];score=0;h=(host or '').lower().rstrip('.')
    try:ipaddress.ip_address(h);s.append('The link uses an IP address instead of a normal domain.' if lang=='en' else 'El enlace usa una dirección IP en vez de un dominio normal.');score+=30;critical.append('ip_direct')
    except ValueError:pass
    if h.startswith('xn--') or '.xn--' in h:s.append('The domain uses encoded characters that can imitate a brand.' if lang=='en' else 'El dominio usa caracteres codificados que pueden imitar una marca.');score+=20
    if h in SHORTENERS:s.append('The shortened link hides its real destination.' if lang=='en' else 'El enlace está acortado y oculta el destino real.');score+=15
    tld=h.rsplit('.',1)[-1] if '.' in h else ''
    if tld in SUSPICIOUS_TLDS:s.append('The domain ending needs extra caution.' if lang=='en' else 'La extensión del dominio requiere más cuidado.');score+=10
    return min(score,45),s,critical

def web_risk_lookup(url):
    key=os.getenv('GOOGLE_WEB_RISK_API_KEY') or os.getenv('WEB_RISK_API_KEY')
    if not key:return None
    try:
        params=[('threatTypes','MALWARE'),('threatTypes','SOCIAL_ENGINEERING'),('threatTypes','UNWANTED_SOFTWARE'),('uri',url),('key',key)]
        r=requests.get('https://webrisk.googleapis.com/v1/uris:search',params=params,timeout=7)
        if r.status_code==200:return r.json().get('threat',{}).get('threatTypes',[])
        app.logger.warning('Web Risk status=%s body=%s',r.status_code,r.text[:250])
    except Exception as e:app.logger.warning('Web Risk lookup failed: %s',e)
    return None

def fetch_chain(start):
    cur=start;chain=[];html='';https_ok=False;s=requests.Session();s.headers.update({'User-Agent':UA,'Accept':'text/html,application/xhtml+xml'})
    for _ in range(6):
        p=urlparse(cur);resolve_public(p.hostname)
        try:r=s.get(cur,timeout=(4,8),allow_redirects=False,stream=True,verify=True)
        except requests.exceptions.SSLError:raise ValueError('El sitio tiene un problema con su certificado HTTPS.')
        except requests.RequestException:raise ValueError('No pudimos conectar con el sitio de forma segura.')
        https_ok=p.scheme=='https'
        if r.is_redirect or r.is_permanent_redirect:
            loc=r.headers.get('Location')
            if not loc:break
            cur=normalize_url(urljoin(cur,loc));chain.append(cur);continue
        if 'text/html' in (r.headers.get('content-type') or '').lower():
            data=b''
            for ch in r.iter_content(16384):
                data+=ch
                if len(data)>300000:break
            html=data.decode(r.encoding or 'utf-8',errors='ignore')
        return cur,chain,https_ok,html
    raise ValueError('El enlace redirige demasiadas veces.')

@app.get('/')
def home():return render_template_string(HTML)

@app.post('/api/analyze')
def analyze():
    try:
        p=request.get_json(silent=True) or {};message=(p.get('message') or '').strip();lang='en' if p.get('lang')=='en' else 'es'
        if not message:return jsonify(error='Paste a message first.' if lang=='en' else 'Pega primero el mensaje que quieres revisar.'),400
        score,sig,critical=message_signals(message,lang);urls=extract_urls(message);entity=mentioned_entity(message)
        host='—';final='—';https='—';verified='No';external='Not configured' if lang=='en' else 'No configurada';positive=False;external_clean=False
        if urls:
            original=normalize_url(urls[0]);host=urlparse(original).hostname
            hs,hsig,hcrit=host_signals(host,lang);score+=hs;sig+=hsig;critical+=hcrit
            try:
                final,chain,https_ok,html=fetch_chain(original)
            except ValueError as e:
                final=original;https_ok=urlparse(original).scheme=='https';html='';score+=20
                sig.append(('We could not safely connect to the destination: ' if lang=='en' else 'No pudimos conectarnos de forma segura al destino: ')+str(e))
                critical.append('connection_failed')
            https=('Yes' if https_ok else 'No') if lang=='en' else ('Sí' if https_ok else 'No')
            final_host=urlparse(final).hostname
            positive=verify_entity_domain(entity,final_host);verified=('Yes' if lang=='en' else 'Sí') if positive else 'No'
            if entity and not positive:
                score+=28;critical.append('brand_mismatch');sig.append('The message names an organization, but the link does not use its verified domain.' if lang=='en' else 'El mensaje menciona una entidad, pero el enlace no usa su dominio verificado.')
            if not https_ok:score+=18;sig.append('The destination does not use HTTPS.' if lang=='en' else 'El destino no usa HTTPS.')
            wr=web_risk_lookup(final)
            if wr is not None:
                external='Google Web Risk: '+(', '.join(wr) if wr else ('no match' if lang=='en' else 'sin coincidencias'));external_clean=not wr
                if wr:score+=45;critical.append('webrisk_hit');sig.append('Google Web Risk lists this destination as unsafe.' if lang=='en' else 'Google Web Risk tiene este destino en una lista de riesgo.')
        score=min(max(score,0),99)
        if critical:
            decision='red';level='High risk' if lang=='en' else 'Riesgo alto';action='Do not open the link or enter information. Contact the organization using an official channel you find yourself.' if lang=='en' else 'No abras el enlace ni entregues información. Contacta a la entidad usando un canal oficial que busques tú mismo.'
        elif urls and positive and https_ok and external_clean:
            decision='green';level='Verified' if lang=='en' else 'Verificado';score=min(score,20);action='You can open it. The destination matches the verified organization and the configured checks found no warning signs.' if lang=='en' else 'Puedes abrirlo. El destino coincide con la entidad verificada y las comprobaciones configuradas no encontraron alertas.'
        elif not urls and score<25:
            decision='gray';level='Not enough information' if lang=='en' else 'No hay suficiente información';action='There is no link to verify. Use the organization’s official app or website if the message asks you to take action.' if lang=='en' else 'No hay un enlace que podamos verificar. Si el mensaje te pide hacer algo, entra por la app o web oficial de la entidad.'
        elif score>=45:
            decision='red';level='High risk' if lang=='en' else 'Riesgo alto';action='Do not continue from this message. Verify the request through an official channel.' if lang=='en' else 'No continúes desde este mensaje. Verifica la solicitud por un canal oficial.'
        else:
            decision='yellow';level='Check first' if lang=='en' else 'Verifica primero';action='Do not use the link yet. Open the official app or website yourself and check whether the request is real.' if lang=='en' else 'No uses el enlace todavía. Entra tú mismo a la app o web oficial y revisa si la solicitud es real.'
        app.logger.info('analysis decision=%s urls=%s',decision,len(urls))
        return jsonify(score=score,decision=decision,level=level,signals=sig,action=action,count=len(urls),host=host,final=final,https=https,verified=verified,external=external)
    except Exception as e:
        app.logger.exception('analysis failed')
        return jsonify(error='Ocurrió un error durante el análisis.'),500

if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)))
