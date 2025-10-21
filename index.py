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
STREAM_BASE = BASE_URL.rsplit("/", 1)[0]
tmdb.API_KEY = "c0d0e0e40bae98909390cde31c402a9b"

def xtream_api(action, extra=""):
    try:
        url = f"{BASE_URL}?username={USERNAME}&password={PASSWORD}&action={action}{extra}"
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        return res.json()
    except Exception:
        return []

def slugify(text):
    text = (text or "").lower().strip()
    return re.sub(r"[^\w-]+", "-", text)

def generate_slug(title, media_id):
    return f"{slugify(title)}-{hashlib.md5(str(media_id).encode()).hexdigest()[:6]}"

def find_item(media_type, media_id):
    mid = str(media_id)
    if media_type == "live":
        data = xtream_api("get_live_streams") or []
        for s in data:
            if str(s.get("stream_id")) == mid or str(s.get("id") or "") == mid:
                return s
        return None
    if media_type in ("movie", "vod"):
        data = xtream_api("get_vod_streams") or []
        for v in data:
            if str(v.get("stream_id")) == mid or str(v.get("id") or "") == mid:
                return v
        return None
    if media_type == "series":
        series_list = xtream_api("get_series") or []
        for s in series_list:
            sid = s.get("series_id")
            if not sid:
                continue
            info = xtream_api("get_series_info", f"&series_id={sid}") or {}
            episodes_dict = info.get("episodes", {}) or {}
            for season_eps in episodes_dict.values():
                for ep in season_eps:
                    if str(ep.get("id")) == mid or str(ep.get("episode_num") or "") == mid:
                        ep["_series"] = {"series_id": sid, "series_name": s.get("name")}
                        return ep
        return None
    return None

@app.route("/filmes")
def filmes():
    data = xtream_api("get_vod_streams") or []
    dominio = request.host_url.rstrip("/")
    filmes = []
    for item in data:
        sid = item.get("stream_id")
        filmes.append({
            "id": sid,
            "titulo": item.get("name"),
            "ano": item.get("release_year"),
            "categoria_id": item.get("category_id"),
            "capa": item.get("stream_icon") or item.get("cover") or "https://fliskbr.vercel.app/img/sem-capa.jpg",
            "player": f"{dominio}/player/{generate_slug(item.get('name'), sid)}.mp4?id={sid}&type=movie",
            "detalhes": f"{dominio}/detalhes?titulo={item.get('name')}&tipo=filme",
            "container_extension": item.get("container_extension"),
            "direct_source": item.get("direct_source")
        })
    return jsonify({"status": "ok", "total": len(filmes), "filmes": filmes})

@app.route("/filmes/categorias")
def filmes_categorias():
    cats = xtream_api("get_vod_categories") or []
    dominio = request.host_url.rstrip("/")
    categorias = [{"id": c.get("category_id"), "nome": c.get("category_name"),
                   "url": f"{dominio}/filmes/categoria/{c.get('category_id')}"} for c in cats]
    return jsonify({"status": "ok", "total": len(categorias), "categorias": categorias})

@app.route("/filmes/categoria/<int:cat_id>")
def filmes_por_categoria(cat_id):
    data = xtream_api("get_vod_streams", f"&category_id={cat_id}") or []
    dominio = request.host_url.rstrip("/")
    filmes = [{"id": i.get("stream_id"),
               "titulo": i.get("name"),
               "capa": i.get("stream_icon") or i.get("cover") or "https://fliskbr.vercel.app/img/sem-capa.jpg",
               "player": f"{dominio}/player/{generate_slug(i.get('name'), i.get('stream_id'))}.mp4?id={i.get('stream_id')}&type=movie"}
              for i in data]
    return jsonify({"status": "ok", "categoria_id": cat_id, "total": len(filmes), "filmes": filmes})

@app.route("/series")
def series():
    data = xtream_api("get_series") or []
    dominio = request.host_url.rstrip("/")
    srs = [{"id": s.get("series_id"), "titulo": s.get("name"),
            "capa": s.get("stream_icon") or s.get("cover") or "https://fliskbr.vercel.app/img/sem-capa.jpg",
            "categoria_id": s.get("category_id"), "temporadas_url": f"{dominio}/series/{s.get('series_id')}/temporadas"}
           for s in data]
    return jsonify({"status": "ok", "total": len(srs), "series": srs})

@app.route("/series/categorias")
def series_categorias():
    cats = xtream_api("get_series_categories") or []
    dominio = request.host_url.rstrip("/")
    categorias = [{"id": c.get("category_id"), "nome": c.get("category_name"),
                   "url": f"{dominio}/series/categoria/{c.get('category_id')}"} for c in cats]
    return jsonify({"status": "ok", "total": len(categorias), "categorias": categorias})

@app.route("/series/categoria/<int:cat_id>")
def series_por_categoria(cat_id):
    data = xtream_api("get_series", f"&category_id={cat_id}") or []
    dominio = request.host_url.rstrip("/")
    srs = [{"id": s.get("series_id"), "titulo": s.get("name"),
            "capa": s.get("stream_icon") or s.get("cover") or "https://fliskbr.vercel.app/img/sem-capa.jpg",
            "temporadas_url": f"{dominio}/series/{s.get('series_id')}/temporadas"}
           for s in data]
    return jsonify({"status": "ok", "categoria_id": cat_id, "total": len(srs), "series": srs})

@app.route("/series/<int:serie_id>/temporadas")
def serie_temporadas(serie_id):
    data = xtream_api("get_series_info", f"&series_id={serie_id}") or {}
    dominio = request.host_url.rstrip("/")
    temporadas = [{"numero": int(num),
                   "episodios_url": f"{dominio}/series/{serie_id}/temporadas/{num}/episodios"}
                  for num in data.get("episodes", {}).keys()]
    return jsonify({"status": "ok", "serie_id": serie_id, "total": len(temporadas), "temporadas": temporadas})

@app.route("/series/<int:serie_id>/temporadas/<int:temp_num>/episodios")
def serie_episodios(serie_id, temp_num):
    data = xtream_api("get_series_info", f"&series_id={serie_id}") or {}
    episodios = data.get("episodes", {}).get(str(temp_num), []) or []
    dominio = request.host_url.rstrip("/")
    eps = [{"id": ep.get("id"), "titulo": ep.get("title"), "numero": ep.get("episode_num"),
           "capa": ep.get("stream_icon") or "https://fliskbr.vercel.app/img/sem-capa.jpg",
           "player": f"{dominio}/player/{generate_slug(ep.get('title'), ep.get('id'))}.mp4?id={ep.get('id')}&type=series",
           "container_extension": ep.get("container_extension"), "direct_source": ep.get("direct_source")}
          for ep in episodios]
    return jsonify({"status": "ok", "serie_id": serie_id, "temporada": temp_num, "total": len(eps), "episodios": eps})

@app.route("/canais")
def canais():
    data = xtream_api("get_live_streams") or []
    dominio = request.host_url.rstrip("/")
    canais = []
    for c in data:
        sid = c.get("stream_id")
        ext = c.get("container_extension") or None
        direct = c.get("direct_source")
        stream_url = None
        if direct:
            stream_url = direct
        elif ext:
            stream_url = f"{STREAM_BASE}/live/{USERNAME}/{PASSWORD}/{sid}.{ext}"
        canais.append({
            "id": sid,
            "nome": c.get("name"),
            "categoria_id": c.get("category_id"),
            "logo": c.get("stream_icon") or "https://fliskbr.vercel.app/img/sem-capa.jpg",
            "player": f"{dominio}/player/{generate_slug(c.get('name'), sid)}.mp4?id={sid}&type=live",
            "stream_url": stream_url,
            "container_extension": ext,
            "direct_source": direct
        })
    return jsonify({"status": "ok", "total": len(canais), "canais": canais})

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
            "status": "ok",
            "titulo": details_res.get("title") or details_res.get("name"),
            "titulo_original": details_res.get("original_title") or details_res.get("original_name"),
            "descricao": details_res.get("overview"),
            "ano": (details_res.get("release_date") or details_res.get("first_air_date") or "")[:4],
            "generos": [g["name"] for g in details_res.get("genres", [])],
            "duracao_min": details_res.get("runtime"),
            "temporadas": details_res.get("number_of_seasons"),
            "episodios": details_res.get("number_of_episodes"),
            "nota_media": details_res.get("vote_average"),
            "votos": details_res.get("vote_count"),
            "idiomas": details_res.get("spoken_languages"),
            "poster": (f"https://image.tmdb.org/t/p/w500{details_res.get('poster_path')}" if details_res.get("poster_path") else None),
            "banner": (f"https://image.tmdb.org/t/p/original{details_res.get('backdrop_path')}" if details_res.get("backdrop_path") else None),
            "elenco_principal": elenco,
            "diretores": diretores,
            "criadores": criadores,
            "trailer_youtube": (f"https://www.youtube.com/watch?v={trailer_key}" if trailer_key else None),
        })
    except Exception as e:
        return jsonify({"erro": "Erro ao obter detalhes", "detalhe": str(e)}), 500

@app.route("/player/<slug>.mp4")
def player(slug):
    media_id = request.args.get("id")
    media_type = request.args.get("type")
    if not media_id or media_type not in ["movie", "series", "live"]:
        return jsonify({"error": "Parâmetros inválidos"}), 400
    item = find_item(media_type, media_id)
    if not item:
        return jsonify({"error": "Mídia não encontrada"}, 404), 404
    direct = item.get("direct_source")
    if direct:
        return redirect(direct)
    ext = item.get("container_extension") or item.get("container") or "ts"
    stream_url = f"{STREAM_BASE}/{media_type}/{USERNAME}/{PASSWORD}/{media_id}.{ext}"
    return redirect(stream_url)

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
