from flask import Flask, jsonify, redirect, request
from flask_cors import CORS
import requests
import hashlib
import re
import tmdbsimple as tmdb

app = Flask(__name__)
CORS(app)

# Configurações
USERNAME = "98413537"
PASSWORD = "65704277"
BASE_URL = "https://finstv.wtf/player_api.php"
tmdb.API_KEY = "c0d0e0e40bae98909390cde31c402a9b"

slug_stream_map = {}

# Utilitários
def xtream_api(action, extra=""):
    url = f"{BASE_URL}?username={USERNAME}&password={PASSWORD}&action={action}{extra}"
    return requests.get(url, timeout=10).json()

def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w-]+', '-', text)
    return text

def generate_slug(title, media_id):
    return f"{slugify(title)}-{hashlib.md5(str(media_id).encode()).hexdigest()[:6]}"

# Rotas de Filmes
@app.route("/filmes")
def filmes():
    data = xtream_api("get_vod_streams")
    dominio = request.host_url.rstrip('/')
    
    return jsonify([{
        "id": item['stream_id'],
        "titulo": item['name'],
        "ano": item.get('release_year'),
        "capa": item.get('cover'),
        "player": f"{dominio}/player/{generate_slug(item['name'], item['stream_id'])}.mp4",
        "detalhes": f"{dominio}/detalhes?titulo={item['name']}&tipo=filme"
    } for item in data])

@app.route("/filmes/categorias")
def filmes_categorias():
    cats = xtream_api("get_vod_categories")
    dominio = request.host_url.rstrip('/')
    
    return jsonify([{
        "id": cat['category_id'],
        "nome": cat['category_name'],
        "url": f"{dominio}/filmes/categoria/{cat['category_id']}"
    } for cat in cats])

@app.route("/filmes/categoria/<int:cat_id>")
def filmes_por_categoria(cat_id):
    data = xtream_api("get_vod_streams", f"&category_id={cat_id}")
    dominio = request.host_url.rstrip('/')
    
    return jsonify([{
        "id": item['stream_id'],
        "titulo": item['name'],
        "player": f"{dominio}/player/{generate_slug(item['name'], item['stream_id'])}.mp4"
    } for item in data])

# Rotas de Séries
@app.route("/series")
def series():
    data = xtream_api("get_series")
    dominio = request.host_url.rstrip('/')
    
    return jsonify([{
        "id": item['series_id'],
        "titulo": item['name'],
        "temporadas": f"{dominio}/series/{item['series_id']}/temporadas",
        "capa": item.get('cover')
    } for item in data])

@app.route("/series/categorias")
def series_categorias():
    cats = xtream_api("get_series_categories")
    dominio = request.host_url.rstrip('/')
    
    return jsonify([{
        "id": cat['category_id'],
        "nome": cat['category_name'],
        "url": f"{dominio}/series/categoria/{cat['category_id']}"
    } for cat in cats])

@app.route("/series/categoria/<int:cat_id>")
def series_por_categoria(cat_id):
    data = xtream_api("get_series", f"&category_id={cat_id}")
    dominio = request.host_url.rstrip('/')
    
    return jsonify([{
        "id": item['series_id'],
        "titulo": item['name'],
        "temporadas": f"{dominio}/series/{item['series_id']}/temporadas"
    } for item in data])

@app.route("/series/<int:serie_id>/temporadas")
def serie_temporadas(serie_id):
    data = xtream_api("get_series_info", f"&series_id={serie_id}")
    dominio = request.host_url.rstrip('/')
    
    return jsonify([{
        "numero": int(num),
        "episodios": f"{dominio}/series/{serie_id}/temporadas/{num}/episodios"
    } for num in data.get('episodes', {}).keys()])

@app.route("/series/<int:serie_id>/temporadas/<int:temp_num>/episodios")
def serie_episodios(serie_id, temp_num):
    data = xtream_api("get_series_info", f"&series_id={serie_id}")
    episodios = data.get('episodes', {}).get(str(temp_num), [])
    dominio = request.host_url.rstrip('/')
    
    return jsonify([{
        "id": ep['id'],
        "titulo": ep['title'],
        "numero": ep['episode_num'],
        "player": f"{dominio}/player/{generate_slug(ep['title'], ep['id'])}.mp4"
    } for ep in episodios])

# Rotas Complementares
@app.route("/detalhes")
def detalhes():
    titulo = request.args.get("titulo")
    tipo = request.args.get("tipo", "filme")
    
    search = tmdb.Search()
    if tipo == "filme":
        search.movie(query=titulo)
        media_type = "movie"
    else:
        search.tv(query=titulo)
        media_type = "tv"
    
    if not search.results:
        return jsonify({"error": "Não encontrado"}), 404
    
    item = search.results[0]
    return jsonify({
        "titulo": item.get('title') or item.get('name'),
        "sinopse": item.get('overview'),
        "poster": f"https://image.tmdb.org/t/p/w500{item.get('poster_path')}",
        "ano": (item.get('release_date') or item.get('first_air_date', ''))[:4],
        "tmdb_url": f"https://www.themoviedb.org/{media_type}/{item['id']}"
    })

@app.route("/player/<slug>.mp4")
def player(slug):
    media_id = request.args.get("id")
    media_type = request.args.get("type")
    
    if not media_id or not media_type:
        return jsonify({"error": "Parâmetros inválidos"}), 400
    
    return redirect(f"http://finstv.wtf:80/{media_type}/{USERNAME}/{PASSWORD}/{media_id}.mp4")

@app.route("/")
def index():
    dominio = request.host_url.rstrip('/')
    return jsonify({
        "rotas": {
            "filmes": {
                "todos": f"{dominio}/filmes",
                "categorias": f"{dominio}/filmes/categorias",
                "por_categoria": f"{dominio}/filmes/categoria/<ID>"
            },
            "series": {
                "todos": f"{dominio}/series",
                "categorias": f"{dominio}/series/categorias",
                "por_categoria": f"{dominio}/series/categoria/<ID>",
                "temporadas": f"{dominio}/series/<ID>/temporadas",
                "episodios": f"{dominio}/series/<ID>/temporadas/<NUM>/episodios"
            },
            "detalhes": f"{dominio}/detalhes?titulo=TITULO&tipo=[filme|serie]",
            "player": f"{dominio}/player/<SLUG>.mp4"
        }
    })
