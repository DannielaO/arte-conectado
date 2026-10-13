"""Retired legacy app: redirect visitors to TRAMA without serving prior features."""
from flask import Flask, redirect

app = Flask(__name__)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def trama_redirect(path):
    return redirect('https://trama-territorial.onrender.com/', code=302)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
