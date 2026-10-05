# ¿Esto es real?

Microapp para analizar enlaces sospechosos antes de abrirlos.

## Qué revisa
- URL y dominio
- DNS y bloqueo de IPs privadas/locales (protección SSRF)
- HTTPS/TLS
- cadena de redirecciones
- Punycode, acortadores, subdominios y patrones de suplantación
- señales de formularios de credenciales/pagos en el HTML público
- VirusTotal opcional mediante `VIRUSTOTAL_API_KEY`

## Ejecutar
```bash
pip install -r requirements.txt
python app.py
```

## Despliegue en Render
El archivo `render.yaml` deja preparado un Web Service. El plan gratuito puede suspenderse cuando no hay tráfico.
