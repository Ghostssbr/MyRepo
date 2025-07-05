from flask import Flask, jsonify, redirect, request
from flask_cors import CORS
import requests
import hashlib
import re
import tmdbsimple as tmdb

# CONFIG
USERNAME = "98413537"
PASSWORD = "65704277"
BASE_URL = "https://finstv.wtf/player_api.php"
tmdb.API_KEY = "c0d0e0e40bae98909390cde31c402a9b"

app = Flask(__name__)
CORS(app)  # Permitir requisições de todos os domínios

slug_stream_map = {}

# UTILS
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

# ROTAS

@app.route("/")
def index():
    return jsonify({
        "api": "FLISK API",
        "version": "2.0",
        "author": "GHOST",
        "endpoints": {
            "filmes": "/filmes",
            "series_episodios": "/series/<serie_id>/temporadas/<temporada_num>/episodios",
            "detalhes": "/detalhes?titulo=TITULO&tipo=[filme|serie]",
            "player": "/player/<slug>.mp4"
        },
        "note": "✨ API desenvolvida por GHOST ✨"
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
    media = slug_stream_map.get(slug)

    if not media:
        match = re.match(r'(.+)-([a-f0-9]{6})$', slug)
        if match:
            nome_slug = match.group(1).replace('-', ' ')
            filmes = xtream_api("get_vod_streams")
            for filme in filmes:
                if slugify(filme['name']) in slug:
                    media = {
                        "id": filme['stream_id'],
                        "type": "movie"
                    }
                    break

    if not media:
        media_id = request.args.get("id")
        media_type = request.args.get("tipo")
        if not media_id or not media_type:
            return jsonify({"erro": "Slug inválido e parâmetros ausentes"}), 404
        media = {
            "id": media_id,
            "type": media_type
        }

    return redirect(
        f"http://finstv.wtf:80/{media['type']}/{USERNAME}/{PASSWORD}/{media['id']}.mp4"
    )

@app.route("/detalhes")
def detalhes():
    titulo = request.args.get("titulo")
    tipo = request.args.get("tipo", "filme")
    if not titulo:
        return jsonify({"erro": "Parâmetro 'titulo' é obrigatório"}), 400

    search = tmdb.Search()
    media_type = 'movie' if tipo == 'filme' else 'tv'
    
    if media_type == 'movie':
        search.movie(query=titulo)
    else:
        search.tv(query=titulo)

    if not search.results:
        return jsonify({"erro": "Conteúdo não encontrado"}), 404

    resultado = search.results[0]
    id_tmdb = resultado['id']

    # Informações principais
    details = tmdb.Movies(id_tmdb).info() if media_type == 'movie' else tmdb.TV(id_tmdb).info()
    credits = tmdb.Movies(id_tmdb).credits() if media_type == 'movie' else tmdb.TV(id_tmdb).credits()
    videos = tmdb.Movies(id_tmdb).videos() if media_type == 'movie' else tmdb.TV(id_tmdb).videos()

    elenco = [ator['name'] for ator in credits.get('cast', [])[:10]]
    producao = [prod['name'] for prod in details.get('production_companies', [])]
    trailers = [
        f"https://www.youtube.com/watch?v={v['key']}"
        for v in videos.get('results', [])
        if v['type'] == 'Trailer' and v['site'] == 'YouTube'
    ]

    player_url = None
    dominio = request.host_url.rstrip('/')
    for slug, item in slug_stream_map.items():
        if item['title'].lower() == titulo.lower() and item['type'] == media_type:
            player_url = f"{dominio}/player/{slug}.mp4"
            break

    return jsonify({
        "titulo": resultado.get('title') or resultado.get('name'),
        "ano": (resultado.get('release_date') or resultado.get('first_air_date', ''))[:4],
        "sinopse": resultado.get('overview', 'Sem sinopse disponível'),
        "poster": f"https://image.tmdb.org/t/p/w500{resultado.get('poster_path')}" if resultado.get('poster_path') else None,
        "avaliacao": resultado.get('vote_average', 0),
        "elenco": elenco,
        "producao": producao,
        "trailers": trailers,
        "url_player": player_url,
        "url_tmdb": f"https://www.themoviedb.org/{media_type}/{id_tmdb}"
    })

@app.route("/series/<int:serie_id>/temporadas/<int:temporada_num>/episodios")
def episodios_temporada(serie_id, temporada_num):
    info = xtream_api("get_series_info", f"&series_id={serie_id}")
    episodios = info.get('episodes', {}).get(str(temporada_num), [])

    dominio = request.host_url.rstrip('/')
    resultado = []
    for idx, ep in enumerate(episodios, 1):
        slug = generate_player_link(ep['name'], ep['id'], 'episode')
        resultado.append({
            "id": idx,
            "titulo": ep['name'],
            "numero_episodio": ep.get('episode_number', idx),
            "url_player": f"{dominio}/player/{slug}.mp4"
        })

    return jsonify({
        "serie_id": serie_id,
        "temporada": temporada_num,
        "total_episodios": len(episodios),
        "episodios": resultado
    })

@app.route("/player_direct")
def player_direct():
    media_id = request.args.get("id")
    media_type = request.args.get("tipo")
    if not media_id or not media_type:
        return jsonify({"erro": "Parâmetros 'id' e 'tipo' são obrigatórios"}), 400

    return redirect(
        f"http://finstv.wtf:80/{media_type}/{USERNAME}/{PASSWORD}/{media_id}.mp4"
    )

