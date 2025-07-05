from flask import Flask, jsonify, redirect, request
from flask_cors import CORS
import requests
import hashlib
import re
import tmdbsimple as tmdb

USERNAME = "98413537"
PASSWORD = "65704277"
BASE_URL = "https://finstv.wtf/player_api.php"
tmdb.API_KEY = "c0d0e0e40bae98909390cde31c402a9b"

app = Flask(__name__)
CORS(app)

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
    dominio = request.host_url.rstrip('/')
    return jsonify({
        "api": "FLISK API",
        "version": "2.0",
        "endpoints": {
            "filmes": {
                "listar": f"{dominio}/filmes",
                "categorias": f"{dominio}/filmes/categorias",
                "por_categoria": f"{dominio}/filmes/categoria/<ID_CATEGORIA>"
            },
            "series": {
                "listar": f"{dominio}/series",
                "categorias": f"{dominio}/series/categorias",
                "por_categoria": f"{dominio}/series/categoria/<ID_CATEGORIA>",
                "temporadas": f"{dominio}/series/<ID_SERIE>/temporadas",
                "episodios": f"{dominio}/series/<ID_SERIE>/temporadas/<NUM_TEMPORADA>/episodios"
            },
            "detalhes": f"{dominio}/detalhes?titulo=TITULO&tipo=[filme|serie]",
            "player": f"{dominio}/player/<SLUG>.mp4"
        }
    })

@app.route("/filmes")
def listar_filmes():
    filmes = xtream_api("get_vod_streams")
    dominio = request.host_url.rstrip('/')
    
    resultado = []
    for idx, filme in enumerate(filmes, 1):
        slug = generate_player_link(filme['name'], filme['stream_id'], 'movie')
        resultado.append({
            "id": idx,
            "titulo": filme['name'],
            "ano": filme.get('release_year', 'N/A'),
            "classificacao": filme.get('rating', '0.0'),
            "url_detalhes": f"{dominio}/detalhes?titulo={filme['name']}&tipo=filme",
            "url_player": f"{dominio}/player/{slug}.mp4",
            "capa": filme.get('cover', '').replace(' ', '%20') if filme.get('cover') else None
        })
    
    return jsonify({
        "total": len(resultado),
        "resultados": resultado
    })

@app.route("/filmes/categorias")
def categorias_filmes():
    categorias = xtream_api("get_vod_categories")
    dominio = request.host_url.rstrip('/')
    
    return jsonify([{
        "id": cat['category_id'],
        "nome": cat['category_name'],
        "total_filmes": cat.get('total', 0),
        "url_filmes": f"{dominio}/filmes/categoria/{cat['category_id']}"
    } for cat in categorias])

@app.route("/filmes/categoria/<int:cat_id>")
def filmes_por_categoria(cat_id):
    filmes = xtream_api("get_vod_streams", f"&category_id={cat_id}")
    dominio = request.host_url.rstrip('/')
    
    resultado = []
    for idx, filme in enumerate(filmes, 1):
        slug = generate_player_link(filme['name'], filme['stream_id'], 'movie')
        resultado.append({
            "id": idx,
            "titulo": filme['name'],
            "ano": filme.get('release_year', 'N/A'),
            "url_detalhes": f"{dominio}/detalhes?titulo={filme['name']}&tipo=filme",
            "url_player": f"{dominio}/player/{slug}.mp4",
            "capa": filme.get('cover', '').replace(' ', '%20') if filme.get('cover') else None
        })
    
    return jsonify({
        "categoria_id": cat_id,
        "total": len(resultado),
        "resultados": resultado
    })

@app.route("/series")
def listar_series():
    series = xtream_api("get_series")
    dominio = request.host_url.rstrip('/')
    
    resultado = []
    for idx, serie in enumerate(series, 1):
        resultado.append({
            "id": idx,
            "titulo": serie['name'],
            "ano": serie.get('release_year', 'N/A'),
            "url_detalhes": f"{dominio}/detalhes?titulo={serie['name']}&tipo=serie",
            "url_temporadas": f"{dominio}/series/{serie['series_id']}/temporadas",
            "capa": serie.get('cover', '').replace(' ', '%20') if serie.get('cover') else None
        })
    
    return jsonify({
        "total": len(resultado),
        "resultados": resultado
    })

@app.route("/series/categorias")
def categorias_series():
    categorias = xtream_api("get_series_categories")
    dominio = request.host_url.rstrip('/')
    
    return jsonify([{
        "id": cat['category_id'],
        "nome": cat['category_name'],
        "total_series": cat.get('total', 0),
        "url_series": f"{dominio}/series/categoria/{cat['category_id']}"
    } for cat in categorias])

@app.route("/series/categoria/<int:cat_id>")
def series_por_categoria(cat_id):
    series = xtream_api("get_series", f"&category_id={cat_id}")
    dominio = request.host_url.rstrip('/')
    
    resultado = []
    for idx, serie in enumerate(series, 1):
        resultado.append({
            "id": idx,
            "titulo": serie['name'],
            "ano": serie.get('release_year', 'N/A'),
            "url_detalhes": f"{dominio}/detalhes?titulo={serie['name']}&tipo=serie",
            "url_temporadas": f"{dominio}/series/{serie['series_id']}/temporadas",
            "capa": serie.get('cover', '').replace(' ', '%20') if serie.get('cover') else None
        })
    
    return jsonify({
        "categoria_id": cat_id,
        "total": len(resultado),
        "resultados": resultado
    })

@app.route("/series/<int:serie_id>/temporadas")
def temporadas_serie(serie_id):
    info = xtream_api("get_series_info", f"&series_id={serie_id}")
    dominio = request.host_url.rstrip('/')
    
    temporadas = []
    for num_temp, episodios in info.get('episodes', {}).items():
        temporadas.append({
            "numero": int(num_temp),
            "total_episodios": len(episodios),
            "url_episodios": f"{dominio}/series/{serie_id}/temporadas/{num_temp}/episodios"
        })
    
    return jsonify({
        "serie_id": serie_id,
        "serie": info.get('info', {}).get('name'),
        "temporadas": sorted(temporadas, key=lambda x: x['numero'])
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
        "serie": info.get('info', {}).get('name'),
        "total_episodios": len(episodios),
        "episodios": resultado
    })

@app.route("/detalhes")
def detalhes():
    titulo = request.args.get("titulo")
    tipo = request.args.get("tipo", "filme")
    dominio = request.host_url.rstrip('/')
    
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
    media_id = resultado['id']
    
    if media_type == 'movie':
        details = tmdb.Movies(media_id).info()
        credits = tmdb.Movies(media_id).credits()
        videos = tmdb.Movies(media_id).videos()
    else:
        details = tmdb.TV(media_id).info()
        credits = tmdb.TV(media_id).credits()
        videos = tmdb.TV(media_id).videos()

    elenco = [{"nome": a["name"], "personagem": a.get("character", "N/A")} 
              for a in credits.get('cast', [])[:10]]
    
    trailer = next((v for v in videos.get('results', []) 
                   if v['type'] == 'Trailer' and v['site'] == 'YouTube'), None)
    
    player_url = None
    for slug, item in slug_stream_map.items():
        if item['title'].lower() == titulo.lower() and item['type'] == media_type:
            player_url = f"{dominio}/player/{slug}.mp4"
            break

    return jsonify({
        "titulo": resultado.get('title') or resultado.get('name'),
        "titulo_original": resultado.get('original_title') or resultado.get('original_name'),
        "ano": (resultado.get('release_date') or resultado.get('first_air_date', ''))[:4],
        "sinopse": resultado.get('overview', 'Sem sinopse disponível'),
        "poster": f"https://image.tmdb.org/t/p/w500{resultado.get('poster_path')}" if resultado.get('poster_path') else None,
        "backdrop": f"https://image.tmdb.org/t/p/original{resultado.get('backdrop_path')}" if resultado.get('backdrop_path') else None,
        "avaliacao": round(resultado.get('vote_average', 0), 1),
        "total_votos": resultado.get('vote_count', 0),
        "generos": [g['name'] for g in details.get('genres', [])],
        "elenco": elenco,
        "trailer": f"https://www.youtube.com/watch?v={trailer['key']}" if trailer else None,
        "url_player": player_url,
        "url_tmdb": f"https://www.themoviedb.org/{media_type}/{media_id}"
    })

@app.route("/player/<slug>.mp4")
def player(slug):
    media = slug_stream_map.get(slug)
    
    if not media:
        match = re.match(r'(.+)-([a-f0-9]{6})$', slug)
        if match:
            nome_slug = match.group(1).replace('-', ' ')
            for item in slug_stream_map.values():
                if slugify(item['title']) in slug:
                    media = item
                    break
    
    if not media:
        return jsonify({"erro": "Conteúdo não encontrado"}), 404
    
    return redirect(
        f"http://finstv.wtf:80/{media['type']}/{USERNAME}/{PASSWORD}/{media['id']}.mp4"
    )

