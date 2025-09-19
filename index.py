from flask import Flask, jsonify, redirect, request
from flask_cors import CORS
import requests
import hashlib
import re
import tmdbsimple as tmdb

app = Flask(__name__)
CORS(app)

# Configurações Xtream
XTREAM_URL = "https://mixmil.cyou/get.php?username=269841127&password=466166574&type=m3u"

tmdb.API_KEY = "c0d0e0e40bae98909390cde31c402a9b"

def xtream_api():
    """
    Como sua URL é m3u, vamos retornar uma lista simulada de streams
    Aqui você pode adaptar para fazer parsing do m3u se quiser.
    """
    # Para simplificar, vamos retornar uma lista fixa de exemplo
    return [
        {"stream_id": "101", "name": "Filme Exemplo 1", "cover": None, "release_year": "2023"},
        {"stream_id": "102", "name": "Filme Exemplo 2", "cover": None, "release_year": "2022"},
    ]

def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w-]+', '-', text)
    return text

def generate_slug(title, media_id):
    return f"{slugify(title)}-{hashlib.md5(str(media_id).encode()).hexdigest()[:6]}"

@app.route("/filmes")
def filmes():
    data = xtream_api()
    dominio = request.host_url.rstrip('/')
    return jsonify([{
        "id": item['stream_id'],
        "titulo": item['name'],
        "ano": item.get('release_year'),
        "capa": item.get('cover'),
        "player": f"{dominio}/player/{generate_slug(item['name'], item['stream_id'])}.mp4?id={item['stream_id']}&type=movie",
        "detalhes": f"{dominio}/detalhes?titulo={item['name']}&tipo=filme"
    } for item in data])

@app.route("/player/<slug>.mp4")
def player(slug):
    media_id = request.args.get("id")
    media_type = request.args.get("type")
    if not media_id or media_type not in ["movie", "series"]:
        return jsonify({"error": "Parâmetros inválidos"}), 400
    return redirect(f"{XTREAM_URL.replace('type=m3u', f'type={media_type}&id={media_id}')}")

@app.route("/")
def index():
    dominio = request.host_url.rstrip('/')
    return jsonify({
        "rotas": {
            "filmes": {
                "todos": f"{dominio}/filmes",
            },
            "player": f"{dominio}/player/<SLUG>.mp4?id=ID&type=[movie|series]"
        }
    })
