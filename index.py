from flask import Flask, jsonify, redirect, request
from flask_cors import CORS
import requests
import hashlib
import re
import tmdbsimple as tmdb

app = Flask(__name__)
CORS(app)

# Xtream-like URL
XTREAM_URL = "https://mixmil.cyou/get.php?username=269841127&password=466166574&type=m3u"

tmdb.API_KEY = "c0d0e0e40bae98909390cde31c402a9b"

def xtream_api():
    """
    Como a URL M3U não retorna JSON, vamos apenas devolver a URL como player direto
    """
    return XTREAM_URL

def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w-]+', '-', text)
    return text

def generate_slug(title, media_id):
    return f"{slugify(title)}-{hashlib.md5(str(media_id).encode()).hexdigest()[:6]}"

# --- ROTAS FILMES ---
@app.route("/filmes")
def filmes():
    dominio = request.host_url.rstrip('/')
    # Exemplo genérico já que a URL M3U não possui JSON com títulos
    return jsonify([{
        "id": 1,
        "titulo": "Filme Exemplo",
        "ano": "2024",
        "capa": None,
        "player": f"{dominio}/player/filme-exemplo.mp4?id=1&type=movie",
        "detalhes": f"{dominio}/detalhes?titulo=Filme+Exemplo&tipo=filme"
    }])

@app.route("/filmes/categorias")
def filmes_categorias():
    dominio = request.host_url.rstrip('/')
    return jsonify([{
        "id": 1,
        "nome": "Categoria Exemplo",
        "url": f"{dominio}/filmes/categoria/1"
    }])

@app.route("/filmes/categoria/<int:cat_id>")
def filmes_por_categoria(cat_id):
    dominio = request.host_url.rstrip('/')
    return jsonify([{
        "id": 1,
        "titulo": "Filme Exemplo",
        "player": f"{dominio}/player/filme-exemplo.mp4?id=1&type=movie"
    }])

# --- ROTAS SÉRIES ---
@app.route("/series")
def series():
    dominio = request.host_url.rstrip('/')
    return jsonify([{
        "id": 1,
        "titulo": "Série Exemplo",
        "temporadas": f"{dominio}/series/1/temporadas",
        "capa": None
    }])

@app.route("/series/categorias")
def series_categorias():
    dominio = request.host_url.rstrip('/')
    return jsonify([{
        "id": 1,
        "nome": "Categoria Série",
        "url": f"{dominio}/series/categoria/1"
    }])

@app.route("/series/categoria/<int:cat_id>")
def series_por_categoria(cat_id):
    dominio = request.host_url.rstrip('/')
    return jsonify([{
        "id": 1,
        "titulo": "Série Exemplo",
        "temporadas": f"{dominio}/series/1/temporadas"
    }])

@app.route("/series/<int:serie_id>/temporadas")
def serie_temporadas(serie_id):
    dominio = request.host_url.rstrip('/')
    return jsonify([{
        "numero": 1,
        "episodios": f"{dominio}/series/{serie_id}/temporadas/1/episodios"
    }])

@app.route("/series/<int:serie_id>/temporadas/<int:temp_num>/episodios")
def serie_episodios(serie_id, temp_num):
    dominio = request.host_url.rstrip('/')
    return jsonify([{
        "id": 1,
        "titulo": "Episódio Exemplo",
        "numero": 1,
        "player": f"{dominio}/player/episodio-exemplo.mp4?id=1&type=series"
    }])

# --- DETALHES via TMDb ---
@app.route('/detalhes')
def detalhes():
    titulo = request.args.get("titulo")
    tipo = request.args.get("tipo")
    if not titulo or not tipo:
        return jsonify({"erro": "Parâmetros obrigatórios: titulo e tipo"}), 400
    try:
        search_type = "movie" if tipo == "filme" else "tv"
        search_url = f"https://api.themoviedb.org/3/search/{search_type}"
        search_params = {"api_key":tmdb.API_KEY,"query": titulo,"language": "pt-BR"}
        search_res = requests.get(search_url, params=search_params).json()
        if not search_res.get("results"):
            return jsonify({"erro": "Título não encontrado no TMDb"}), 404
        item = search_res["results"][0]
        tmdb_id = item["id"]
        details_url = f"https://api.themoviedb.org/3/{search_type}/{tmdb_id}"
        details_res = requests.get(details_url, params={"api_key": tmdb.API_KEY, "language": "pt-BR"}).json()
        credits_url = f"https://api.themoviedb.org/3/{search_type}/{tmdb_id}/credits"
        credits_res = requests.get(credits_url, params={"api_key": tmdb.API_KEY, "language": "pt-BR"}).json()
        elenco = [ator["name"] for ator in credits_res.get("cast", [])[:10]]
        diretores = [p["name"] for p in credits_res.get("crew", []) if p["job"] == "Director"]
        criadores = [p["name"] for p in details_res.get("created_by", [])]
        videos_url = f"https://api.themoviedb.org/3/{search_type}/{tmdb_id}/videos"
        videos_res = requests.get(videos_url, params={"api_key": tmdb.API_KEY}).json()
        trailer_key = next((v["key"] for v in videos_res.get("results", []) if v["type"] == "Trailer" and v["site"] == "YouTube"), None)
        return jsonify({
            "titulo": details_res.get("title") or details_res.get("name"),
            "titulo_original": details_res.get("original_title") or details_res.get("original_name"),
            "descricao": details_res.get("overview"),
            "ano": (details_res.get("release_date") or details_res.get("first_air_date") or "")[:4],
            "generos": [g["name"] for g in details_res.get("genres", [])],
            "duracao": details_res.get("runtime"),
            "temporadas": details_res.get("number_of_seasons"),
            "episodios": details_res.get("number_of_episodes"),
            "nota": details_res.get("vote_average"),
            "votos": details_res.get("vote_count"),
            "idiomas": details_res.get("spoken_languages"),
            "poster": f"https://image.tmdb.org/t/p/w500{details_res.get('poster_path')}" if details_res.get("poster_path") else None,
            "banner": f"https://image.tmdb.org/t/p/original{details_res.get('backdrop_path')}" if details_res.get("backdrop_path") else None,
            "elenco": elenco,
            "diretores": diretores,
            "criadores": criadores,
            "trailer_youtube": f"https://www.youtube.com/watch?v={trailer_key}" if trailer_key else None
        })
    except Exception as e:
        return jsonify({"erro": "Erro ao obter detalhes", "detalhe": str(e)}), 500

# --- PLAYER ---
@app.route("/player/<slug>.mp4")
def player(slug):
    media_id = request.args.get("id")
    media_type = request.args.get("type")
    if not media_id or media_type not in ["movie", "series"]:
        return jsonify({"error": "Parâmetros inválidos"}), 400
    return redirect(XTREAM_URL)

# --- INDEX ---
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
            "player": f"{dominio}/player/<SLUG>.mp4?id=ID&type=[movie|series]"
        }
    })

# --- RODA NA PORTA 5000 ---
app.run(host="0.0.0.0", port=5000)
