from flask import Flask, jsonify, redirect, request, Response, stream_with_context
from flask_cors import CORS
import requests
import hashlib
import re
import logging
from typing import List, Dict

app = Flask(__name__)
CORS(app)

# ---------- Configurações ----------
USERNAME = "Sidney0011"
PASSWORD = "sid09105245"
BASE_URL = "http://new.pionner.pro:8080/player_api.php"
TMDB_API_KEY = "c0d0e0e40bae98909390cde31c402a9b"

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

# ---------- Fórum simples (em memória) ----------
FORUM_TOPICS: List[Dict] = []

# ---------- Utilitários ----------
def safe_json(resp: requests.Response):
    try:
        return resp.json()
    except Exception:
        logger.exception("Resposta não-JSON recebida")
        return {}

def xtream_api(action: str, extra: str = ""):
    url = f"{BASE_URL}?username={USERNAME}&password={PASSWORD}&action={action}{extra}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return safe_json(resp)
    except requests.exceptions.RequestException as e:
        logger.error("Erro ao chamar XTREAM API: %s", e)
        return [] if action.startswith("get_") else {}

def slugify(text: str) -> str:
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r"[^\w-]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text

def generate_slug(title: str, media_id) -> str:
    return f"{slugify(title)}-{hashlib.md5(str(media_id).encode()).hexdigest()[:6]}"

def is_adult_item(item: dict) -> bool:
    text_candidates = []
    for k in ("name", "title", "description", "plot", "category_name"):
        v = item.get(k) if item else None
        if isinstance(v, str):
            text_candidates.append(v.lower())
    joined = " ".join(text_candidates)
    keywords = ["xxx", "18+", "18 +", "adult", "porn", "pornografia", "sexo", "erótico", "erotico"]
    return any(k in joined for k in keywords)

# ---------- Erro 500 ----------
@app.errorhandler(500)
def internal_error(e):
    logger.exception("Erro interno do servidor: %s", e)
    return jsonify({"erro": "Internal Server Error", "detalhe": str(e)}), 500

# ---------- Rotas de filmes ----------
@app.route("/filmes")
def filmes():
    adult_param = request.args.get("adult")
    data = xtream_api("get_vod_streams")
    dominio = request.host_url.rstrip('/')
    if not isinstance(data, list):
        data = []

    items = []
    for item in data:
        try:
            entry = {
                "id": item.get('stream_id'),
                "titulo": item.get('name'),
                "ano": item.get('release_year'),
                "capa": item.get('cover'),
                "player": f"{dominio}/player/{generate_slug(item.get('name',''), item.get('stream_id'))}.mp4?id={item.get('stream_id')}&type=movie",
                "detalhes": f"{dominio}/detalhes?titulo={item.get('name')}&tipo=filme",
                "raw": item
            }
            items.append(entry)
        except Exception:
            logger.exception("Erro ao processar item de filmes: %s", item)

    if adult_param == "1":
        items = [i for i in items if is_adult_item(i.get("raw", {}))]
    elif adult_param == "0":
        items = [i for i in items if not is_adult_item(i.get("raw", {}))]

    return jsonify(items)

@app.route("/filmes/categorias")
def filmes_categorias():
    cats = xtream_api("get_vod_categories")
    dominio = request.host_url.rstrip('/')
    if not isinstance(cats, list):
        cats = []
    return jsonify([{
        "id": cat.get('category_id'),
        "nome": cat.get('category_name'),
        "url": f"{dominio}/filmes/categoria/{cat.get('category_id')}"
    } for cat in cats])

@app.route("/filmes/categoria/<int:cat_id>")
def filmes_por_categoria(cat_id):
    data = xtream_api("get_vod_streams", f"&category_id={cat_id}")
    dominio = request.host_url.rstrip('/')
    if not isinstance(data, list):
        data = []
    return jsonify([{
        "id": item.get('stream_id'),
        "titulo": item.get('name'),
        "player": f"{dominio}/player/{generate_slug(item.get('name',''), item.get('stream_id'))}.mp4?id={item.get('stream_id')}&type=movie"
    } for item in data])

# ---------- Rotas de séries ----------
@app.route("/series")
def series():
    data = xtream_api("get_series")
    dominio = request.host_url.rstrip('/')
    if not isinstance(data, list):
        data = []
    return jsonify([{
        "id": item.get('series_id'),
        "titulo": item.get('name'),
        "temporadas": f"{dominio}/series/{item.get('series_id')}/temporadas",
        "capa": item.get('cover')
    } for item in data])

@app.route("/series/categorias")
def series_categorias():
    cats = xtream_api("get_series_categories")
    dominio = request.host_url.rstrip('/')
    if not isinstance(cats, list):
        cats = []
    return jsonify([{
        "id": cat.get('category_id'),
        "nome": cat.get('category_name'),
        "url": f"{dominio}/series/categoria/{cat.get('category_id')}"
    } for cat in cats])

@app.route("/series/categoria/<int:cat_id>")
def series_por_categoria(cat_id):
    data = xtream_api("get_series", f"&category_id={cat_id}")
    dominio = request.host_url.rstrip('/')
    if not isinstance(data, list):
        data = []
    return jsonify([{
        "id": item.get('series_id'),
        "titulo": item.get('name'),
        "temporadas": f"{dominio}/series/{item.get('series_id')}/temporadas"
    } for item in data])

@app.route("/series/<int:serie_id>/temporadas")
def serie_temporadas(serie_id):
    data = xtream_api("get_series_info", f"&series_id={serie_id}")
    dominio = request.host_url.rstrip('/')
    episodes_map = data.get('episodes', {}) if isinstance(data, dict) else {}
    temporadas = []
    for num in episodes_map.keys():
        try:
            temporadas.append({
                "numero": int(num),
                "episodios": f"{dominio}/series/{serie_id}/temporadas/{num}/episodios"
            })
        except Exception:
            logger.exception("Erro ao processar temporada %s para série %s", num, serie_id)
    return jsonify(temporadas)

@app.route("/series/<int:serie_id>/temporadas/<int:temp_num>/episodios")
def serie_episodios(serie_id, temp_num):
    data = xtream_api("get_series_info", f"&series_id={serie_id}")
    episodios = []
    if isinstance(data, dict):
        episodios = data.get('episodes', {}).get(str(temp_num), [])
    dominio = request.host_url.rstrip('/')
    return jsonify([{
        "id": ep.get('id'),
        "titulo": ep.get('title'),
        "numero": ep.get('episode_num'),
        "player": f"{dominio}/player/{generate_slug(ep.get('title',''), ep.get('id'))}.mp4?id={ep.get('id')}&type=series"
    } for ep in (episodios or [])])

# ---------- Detalhes via TMDB ----------
@app.route('/detalhes')
def detalhes():
    titulo = request.args.get("titulo")
    tipo = request.args.get("tipo")
    if not titulo or not tipo:
        return jsonify({"erro": "Parâmetros obrigatórios: titulo e tipo"}), 400
    try:
        search_type = "movie" if tipo.lower() == "filme" else "tv"
        search_url = f"https://api.themoviedb.org/3/search/{search_type}"
        search_params = {"api_key": TMDB_API_KEY, "query": titulo, "language": "pt-BR"}
        search_res = requests.get(search_url, params=search_params, timeout=10).json()
        if not search_res.get("results"):
            return jsonify({"erro": "Título não encontrado no TMDb"}), 404
        item = search_res["results"][0]
        tmdb_id = item["id"]
        details_res = requests.get(f"https://api.themoviedb.org/3/{search_type}/{tmdb_id}", 
                                   params={"api_key": TMDB_API_KEY, "language": "pt-BR"}, timeout=10).json()
        credits_res = requests.get(f"https://api.themoviedb.org/3/{search_type}/{tmdb_id}/credits",
                                   params={"api_key": TMDB_API_KEY, "language": "pt-BR"}, timeout=10).json()
        elenco = [ator.get("name") for ator in credits_res.get("cast", [])[:10]]
        diretores = [p.get("name") for p in credits_res.get("crew", []) if p.get("job") == "Director"]
        criadores = [p.get("name") for p in details_res.get("created_by", [])]
        videos_res = requests.get(f"https://api.themoviedb.org/3/{search_type}/{tmdb_id}/videos",
                                  params={"api_key": TMDB_API_KEY}, timeout=10).json()
        trailer_key = next((v["key"] for v in videos_res.get("results", []) 
                            if v.get("type")=="Trailer" and v.get("site")=="YouTube"), None)
        return jsonify({
            "titulo": details_res.get("title") or details_res.get("name"),
            "titulo_original": details_res.get("original_title") or details_res.get("original_name"),
            "descricao": details_res.get("overview"),
            "ano": (details_res.get("release_date") or details_res.get("first_air_date") or "")[:4],
            "generos": [g.get("name") for g in details_res.get("genres", [])],
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
        logger.exception("Erro ao obter detalhes TMDB")
        return jsonify({"erro": "Erro ao obter detalhes", "detalhe": str(e)}), 500

# ---------- Player (redirect para Pionner) ----------
@app.route("/player/<path:slug>.mp4")
def player(slug):
    media_id = request.args.get("id")
    raw_type = (request.args.get("type") or "").lower()
    debug = request.args.get("debug")
    type_map = {"movie":"movie","filme":"movie","series":"series","serie":"series","tv":"series"}
    media_type = type_map.get(raw_type)
    if not media_id or not media_type:
        return jsonify({"error":"Parâmetros inválidos. Use ?id=ID&type=[movie|filme|series|serie|tv]"}), 400
    target = f"http://new.pionner.pro:8080/{media_type}/{USERNAME}/{PASSWORD}/{media_id}.mp4"
    if debug=="1":
        return jsonify({"redirect_to": target})
    return redirect(target, code=302)

# ---------- Página inicial ----------
@app.route("/")
def index():
    dominio = request.host_url.rstrip('/')
    return jsonify({
        "rotas": {
            "filmes":{"todos": f"{dominio}/filmes","categorias": f"{dominio}/filmes/categorias","por_categoria": f"{dominio}/filmes/categoria/<ID>"},
            "series":{"todos": f"{dominio}/series","categorias": f"{dominioage"),
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
        logger.exception("Erro ao obter detalhes TMDB")
        return jsonify({"erro": "Erro ao obter detalhes", "detalhe": str(e)}), 500

# ---------- Player (redirecionamento) ----------
@app.route("/player/<slug>.mp4")
def player(slug):
    media_id = request.args.get("id")
    media_type = request.args.get("type")
    if not media_id or media_type not in ["movie", "series"]:
        return jsonify({"error": "Parâmetros inválidos"}), 400
    # exemplo de redirect (ajuste domínio/URL conforme seu serviço)
    return redirect(f"https://finstv.wtf/{media_type}/{USERNAME}/{PASSWORD}/{media_id}.mp4")

# ---------- Página inicial com rotas ----------
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
            "player": f"{dominio}/player/<SLUG>.mp4?id=ID&type=[movie|series]",
            "forum": {
                "listar": f"{dominio}/forum (GET)",
                "criar": f"{dominio}/forum (POST JSON)"
            },
            "conteudo_adulto": f"{dominio}/conteudo/adulto"
        }
    })

# ---------- Endpoints do fórum ----------
@app.route("/forum", methods=["GET"])
def forum_list():
    # opcional: ?page=1&per_page=10
    page = max(1, int(request.args.get("page", 1)))
    per_page = max(1, min(100, int(request.args.get("per_page", 10))))
    start = (page - 1) * per_page
    end = start + per_page
    return jsonify({
        "total": len(FORUM_TOPICS),
        "page": page,
        "per_page": per_page,
        "items": FORUM_TOPICS[start:end]
    })

@app.route("/forum", methods=["POST"])
def forum_create():
    data = request.get_json(force=True, silent=True)
    if not data or not data.get("titulo") or not data.get("conteudo"):
        return jsonify({"erro": "JSON com 'titulo' e 'conteudo' obrigatórios"}), 400
    topic_id = len(FORUM_TOPICS) + 1
    topic = {
        "id": topic_id,
        "titulo": data.get("titulo"),
        "conteudo": data.get("conteudo"),
        "autor": data.get("autor") or "anon",
        "criado_em": data.get("criado_em") or ""
    }
    FORUM_TOPICS.append(topic)
    return jsonify(topic), 201

# ---------- Conteúdo adulto (lista os itens detectados) ----------
@app.route("/conteudo/adulto")
def conteudo_adulto():
    # retorna filmes + series que o detector marcou
    films = xtream_api("get_vod_streams")
    series = xtream_api("get_series")
    adult_items = []

    for item in (films or []):
        if is_adult_item(item):
            adult_items.append({"tipo": "filme", "id": item.get("stream_id"), "titulo": item.get("name")})

    for item in (series or []):
        if is_adult_item(item):
            adult_items.append({"tipo": "serie", "id": item.get("series_id"), "titulo": item.get("name")})

    return jsonify({"total": len(adult_items), "items": adult_items})

