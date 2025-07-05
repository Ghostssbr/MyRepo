from flask import Flask, jsonify, redirect, request
import requests
import hashlib
import re
import tmdbsimple as tmdb
from datetime import datetime

USERNAME = "98413537"
PASSWORD = "65704277"
BASE_URL = "https://finstv.wtf/player_api.php"
tmdb.API_KEY = "c0d0e0e40bae98909390cde31c402a9b"

app = Flask(__name__)
slug_stream_map = {}

def xtream_api(action, extra=""):
    url = f"{BASE_URL}?username={USERNAME}&password={PASSWORD}&action={action}{extra}"
    try:
        return requests.get(url, timeout=5).json()
    except:
        return []

def slugify(text):
    text = text.lower()
    text = re.sub(r'\s+', '-', text)
    text = re.sub(r'[^\w-]', '', text)
    return text

def generate_player_link(title, media_id, media_type):
    slug = f"{slugify(title)}-{hashlib.md5(f'{media_id}{media_type}'.encode()).hexdigest()[:6]}"
    slug_stream_map[slug] = {
        "id": media_id,
        "type": media_type,
        "title": title
    }
    return slug

@app.route("/")
def index():
    return jsonify({
        "api": "Xtream API Proxy",
        "version": "2.0"
    })

@app.route("/filmes")
def listar_filmes():
    filmes = xtream_api("get_vod_streams")
    resultado = []
    dominio = request.host_url.rstrip('/')
    for idx, filme in enumerate(filmes, 1):
        slug = generate_player_link(filme['name'], filme['stream_id'], 'movie')
        resultado.append({
            "id": idx,
            "titulo": filme['name'],
            "ano": filme.get('release_year', 'N/A'),
            "classificacao": filme.get('rating', '0.0'),
            "url_detalhes": f"{dominio}/detalhes?titulo={filme['name']}&tipo=filme",
            "url_player": f"{dominio}/player/{slug}.mp4",
            "capa": filme.get('cover')
        })
    return jsonify({
        "total": len(resultado),
        "resultados": resultado
    })

@app.route("/player/<slug>.mp4")
def player(slug):
    if slug not in slug_stream_map:
        return jsonify({"erro": "Conteúdo não encontrado"}), 404

    media = slug_stream_map[slug]
    return redirect(
        f"http://finstv.wtf:80/{media['type']}/{USERNAME}/{PASSWORD}/{media['id']}.mp4"
    )

# Adaptador WSGI para Vercel
from vercel_wsgi import handle_request

def handler(environ, start_response):
    return handle_request(app, environ, start_response)
