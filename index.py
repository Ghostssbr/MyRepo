from flask import Flask, jsonify, redirect, request
from flask_cors import CORS
import requests
import hashlib
import re
import tmdbsimple as tmdb

app = Flask(__name__)
CORS(app)

USERNAME = "269841127"
PASSWORD = "466166574"
BASE_URL = "https://mixmil.cyou/player_api.php"
tmdb.API_KEY = "c0d0e0e40bae98909390cde31c402a9b"


# ---------- Funções utilitárias ---------- #
def xtream_api(action, extra=""):
    """Consulta a API Xtream e retorna JSON."""
    url = f"{BASE_URL}?username={USERNAME}&password={PASSWORD}&action={action}{extra}"
    return requests.get(url, timeout=10).json()


def slugify(text):
    text = text.lower().strip()
    return re.sub(r"[^\w-]+", "-", text)


def generate_slug(title, media_id):
    return f"{slugify(title)}-{hashlib.md5(str(media_id).encode()).hexdigest()[:6]}"


# ---------- Filmes ---------- #
@app.route("/filmes")
def filmes():
    data = xtream_api("get_vod_streams")
    dominio = request.host_url.rstrip("/")
    filmes = [
        {
            "id": item["stream_id"],
            "titulo": item["name"],
            "ano": item.get("release_year"),
            "categoria_id": item.get("category_id"),
            "capa": item.get("cover"),
            "player": f"{dominio}/player/{generate_slug(item['name'], item['stream_id'])}.mp4"
                      f"?id={item['stream_id']}&type=movie",
            "detalhes": f"{dominio}/detalhes?titulo={item['name']}&tipo=filme",
        }
        for item in data
    ]
    return jsonify({"status": "ok", "total": len(filmes), "filmes": filmes})


@app.route("/filmes/categorias")
def filmes_categorias():
    cats = xtream_api("get_vod_categories")
    dominio = request.host_url.rstrip("/")
    categorias = [
        {
            "id": cat["category_id"],
            "nome": cat["category_name"],
            "url": f"{dominio}/filmes/categoria/{cat['category_id']}",
        }
        for cat in cats
    ]
    return jsonify({"status": "ok", "total": len(categorias), "categorias": categorias})


@app.route("/filmes/categoria/<int:cat_id>")
def filmes_por_categoria(cat_id):
    data = xtream_api("get_vod_streams", f"&category_id={cat_id}")
    dominio = request.host_url.rstrip("/")
    filmes = [
        {
            "id": item["stream_id"],
            "titulo": item["name"],
            "player": f"{dominio}/player/{generate_slug(item['name'], item['stream_id'])}.mp4"
                      f"?id={item['stream_id']}&type=movie",
        }
        for item in data
    ]
    return jsonify({"status": "ok", "categoria_id": cat_id, "total": len(filmes), "filmes": filmes})


# ---------- Séries ---------- #
@app.route("/series")
def series():
    data = xtream_api("get_series")
    dominio = request.host_url.rstrip("/")
    series = [
        {
            "id": item["series_id"],
            "titulo": item["name"],
            "capa": item.get("cover"),
            "categoria_id": item.get("category_id"),
            "temporadas_url": f"{dominio}/series/{item['series_id']}/temporadas",
        }
        for item in data
    ]
    return jsonify({"status": "ok", "total": len(series), "series": series})


@app.route("/series/categorias")
def series_categorias():
    cats = xtream_api("get_series_categories")
    dominio = request.host_url.rstrip("/")
    categorias = [
        {
            "id": cat["category_id"],
            "nome": cat["category_name"],
            "url": f"{dominio}/series/categoria/{cat['category_id']}",
        }
        for cat in cats
    ]
    return jsonify({"status": "ok", "total": len(categorias), "categorias": categorias})


@app.route("/series/categoria/<int:cat_id>")
def series_por_categoria(cat_id):
    data = xtream_api("get_series", f"&category_id={cat_id}")
    dominio = request.host_url.rstrip("/")
    series = [
        {
            "id": item["series_id"],
            "titulo": item["name"],
            "temporadas_url": f"{dominio}/series/{item['series_id']}/temporadas",
        }
        for item in data
    ]
    return jsonify({"status": "ok", "categoria_id": cat_id, "total": len(series), "series": series})


@app.route("/series/<int:serie_id>/temporadas")
def serie_temporadas(serie_id):
    data = xtream_api("get_series_info", f"&series_id={serie_id}")
    dominio = request.host_url.rstrip("/")
    temporadas = [
        {
            "numero": int(num),
            "episodios_url": f"{dominio}/series/{serie_id}/temporadas/{num}/episodios",
        }
        for num in data.get("episodes", {}).keys()
    ]
    return jsonify({"status": "ok", "serie_id": serie_id, "total": len(temporadas), "temporadas": temporadas})


@app.route("/series/<int:serie_id>/temporadas/<int:temp_num>/episodios")
def serie_episodios(serie_id, temp_num):
    data = xtream_api("get_series_info", f"&series_id={serie_id}")
    dominio = request.host_url.rstrip("/")
    episodios = [
        {
            "id": ep["id"],
            "titulo": ep["title"],
            "numero": ep["episode_num"],
            "player": f"{dominio}/player/{generate_slug(ep['title'], ep['id'])}.mp4"
                      f"?id={ep['id']}&type=series",
        }
        for ep in data.get("episodes", {}).get(str(temp_num), [])
    ]
    return jsonify({
        "status": "ok",
        "serie_id": serie_id,
        "temporada": temp_num,
        "total": len(episodios),
        "episodios": episodios
    })


# ---------- Canais ao vivo ---------- #
@app.route("/canais")
def canais():
    """Lista canais de TV ao vivo"""
    data = xtream_api("get_live_streams")
    dominio = request.host_url.rstrip("/")
    canais = [
        {
            "id": c["stream_id"],
            "nome": c["name"],
            "categoria_id": c.get("category_id"),
            "logo": c.get("stream_icon"),
            "player": f"{dominio}/player/{generate_slug(c['name'], c['stream_id'])}.mp4"
                      f"?id={c['stream_id']}&type=live",
        }
        for c in data
    ]
    return jsonify({"status": "ok", "total": len(canais), "canais": canais})


# ---------- Detalhes via TMDB ---------- #
@app.route("/detalhes")
def detalhes():
    titulo = request.args.get("titulo")
    tipo = request.args.get("tipo")
    if not titulo or not tipo:
        return jsonify({"erro": "Parâmetros obrigatórios: titulo e tipo"}), 400

    try:
        search_type = "movie" if tipo == "filme" else "tv"
        search_url = f"https://api.themoviedb.org/3/search/{search_type}"
        search_params = {"api_key": tmdb.API_KEY, "query": titulo, "language": "pt-BR"}
        search_res = requests.get(search_url, params=search_params).json()

        if not search_res.get("results"):
            return jsonify({"erro": "Título não encontrado no TMDb"}), 404

        item = search_res["results"][0]
        tmdb_id = item["id"]

        details_url = f"https://api.themoviedb.org/3/{search_type}/{tmdb_id}"
        details_res = requests.get(details_url,
                                   params={"api_key": tmdb.API_KEY, "language": "pt-BR"}).json()

        credits_url = f"https://api.themoviedb.org/3/{search_type}/{tmdb_id}/credits"
        credits_res = requests.get(credits_url,
                                   params={"api_key": tmdb.API_KEY, "language": "pt-BR"}).json()

        elenco = [ator["name"] for ator in credits_res.get("cast", [])[:10]]
        diretores = [p["name"] for p in credits_res.get("crew", []) if p["job"] == "Director"]
        criadores = [p["name"] for p in details_res.get("created_by", [])]

        videos_url = f"https://api.themoviedb.org/3/{search_type}/{tmdb_id}/videos"
        videos_res = requests.get(videos_url, params={"api_key": tmdb.API_KEY}).json()
        trailer_key = next(
            (v["key"] for v in videos_res.get("results", [])
             if v["type"] == "Trailer" and v["site"] == "YouTube"), None)

        return jsonify({
            "status": "ok",
            "titulo": details_res.get("title") or details_res.get("name"),
            "titulo_original": details_res.get("original_title")
                               or details_res.get("original_name"),
            "descricao": details_res.get("overview"),
            "ano": (details_res.get("release_date")
                   or details_res.get("first_air_date") or "")[:4],
            "generos": [g["name"] for g in details_res.get("genres", [])],
            "duracao_min": details_res.get("runtime"),
            "temporadas": details_res.get("number_of_seasons"),
            "episodios": details_res.get("number_of_episodes"),
            "nota_media": details_res.get("vote_average"),
            "votos": details_res.get("vote_count"),
            "idiomas": details_res.get("spoken_languages"),
            "poster": (f"https://image.tmdb.org/t/p/w500{details_res.get('poster_path')}"
                       if details_res.get("poster_path") else None),
            "banner": (f"https://image.tmdb.org/t/p/original{details_res.get('backdrop_path')}"
                       if details_res.get("backdrop_path") else None),
            "elenco_principal": elenco,
            "diretores": diretores,
            "criadores": criadores,
            "trailer_youtube": (f"https://www.youtube.com/watch?v={trailer_key}"
                                if trailer_key else None),
        })

    except Exception as e:
        return jsonify({"erro": "Erro ao obter detalhes", "detalhe": str(e)}), 500


# ---------- Player universal ---------- #
@app.route("/player/<slug>.mp4")
def player(slug):
    media_id = request.args.get("id")
    media_type = request.args.get("type")
    if not media_id or media_type not in ["movie", "series", "live"]:
        return jsonify({"error": "Parâmetros inválidos"}), 400

    return redirect(f"https://mixmil.cyou/{media_type}/{USERNAME}/{PASSWORD}/{media_id}.mp4")


# ---------- Índice de rotas ---------- #
@app.route("/")
def index():
    dominio = request.host_url.rstrip("/")
    return jsonify({
        "status": "ok",
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
            "canais": f"{dominio}/canais",
            "detalhes": f"{dominio}/detalhes?titulo=TITULO&tipo=[filme|serie]",
            "player": f"{dominio}/player/<SLUG>.mp4?id=ID&type=[movie|series|live]"
        }
    })
