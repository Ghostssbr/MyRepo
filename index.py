from http.server import BaseHTTPRequestHandler
from flask import Flask, jsonify, redirect, request
from flask_cors import CORS
import requests
import hashlib
import re
import logging
import json
from typing import List, Dict
from urllib.parse import urlparse, parse_qs

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

def get_dominio_from_headers(headers):
    host = headers.get('Host', '')
    if host:
        return f"https://{host}"
    return "http://localhost:3000"

# ---------- Handler principal para Vercel ----------
class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.handle_request('GET')
    
    def do_POST(self):
        self.handle_request('POST')
    
    def handle_request(self, method):
        try:
            path = self.path.split('?')[0]
            query_params = parse_qs(urlparse(self.path).query)
            
            # Headers
            headers = dict(self.headers)
            
            # Body para POST
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else b''
            
            # Processar a requisição
            response = self.process_route(path, method, query_params, headers, body)
            
            # Enviar resposta
            self.send_response(response['status'])
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            
            self.wfile.write(json.dumps(response['body']).encode('utf-8'))
            
        except Exception as e:
            logger.exception("Erro no handler")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"erro": "Internal Server Error", "detalhe": str(e)}).encode('utf-8'))
    
    def process_route(self, path, method, query_params, headers, body):
        dominio = get_dominio_from_headers(headers)
        
        # Rota principal
        if path == '/':
            return {
                'status': 200,
                'body': {
                    "rotas": {
                        "filmes": {"todos": f"{dominio}/filmes", "categorias": f"{dominio}/filmes/categorias"},
                        "series": {"todos": f"{dominio}/series", "categorias": f"{dominio}/series/categorias"},
                        "detalhes": f"{dominio}/detalhes?titulo=TITULO&tipo=[filme|serie]",
                        "forum": f"{dominio}/forum"
                    }
                }
            }
        
        # Filmes
        elif path == '/filmes':
            adult_param = query_params.get('adult', [None])[0]
            data = xtream_api("get_vod_streams")
            
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
                    logger.exception("Erro ao processar item de filmes")

            if adult_param == "1":
                items = [i for i in items if is_adult_item(i.get("raw", {}))]
            elif adult_param == "0":
                items = [i for i in items if not is_adult_item(i.get("raw", {}))]

            return {'status': 200, 'body': items}
        
        # Categorias de filmes
        elif path == '/filmes/categorias':
            cats = xtream_api("get_vod_categories")
            if not isinstance(cats, list):
                cats = []
            return {'status': 200, 'body': [{
                "id": cat.get('category_id'),
                "nome": cat.get('category_name'),
                "url": f"{dominio}/filmes/categoria/{cat.get('category_id')}"
            } for cat in cats]}
        
        # Séries
        elif path == '/series':
            data = xtream_api("get_series")
            if not isinstance(data, list):
                data = []
            return {'status': 200, 'body': [{
                "id": item.get('series_id'),
                "titulo": item.get('name'),
                "temporadas": f"{dominio}/series/{item.get('series_id')}/temporadas",
                "capa": item.get('cover')
            } for item in data]}
        
        # Categorias de séries
        elif path == '/series/categorias':
            cats = xtream_api("get_series_categories")
            if not isinstance(cats, list):
                cats = []
            return {'status': 200, 'body': [{
                "id": cat.get('category_id'),
                "nome": cat.get('category_name'),
                "url": f"{dominio}/series/categoria/{cat.get('category_id')}"
            } for cat in cats]}
        
        # Detalhes TMDB
        elif path == '/detalhes':
            titulo = query_params.get('titulo', [None])[0]
            tipo = query_params.get('tipo', [None])[0]
            
            if not titulo or not tipo:
                return {'status': 400, 'body': {"erro": "Parâmetros obrigatórios: titulo e tipo"}}
            
            try:
                search_type = "movie" if tipo.lower() == "filme" else "tv"
                search_url = f"https://api.themoviedb.org/3/search/{search_type}"
                search_params = {"api_key": TMDB_API_KEY, "query": titulo, "language": "pt-BR"}
                search_res = requests.get(search_url, params=search_params, timeout=10).json()
                
                if not search_res.get("results"):
                    return {'status': 404, 'body': {"erro": "Título não encontrado no TMDb"}}
                
                item = search_res["results"][0]
                tmdb_id = item["id"]
                
                details_res = requests.get(f"https://api.themoviedb.org/3/{search_type}/{tmdb_id}", 
                                         params={"api_key": TMDB_API_KEY, "language": "pt-BR"}, timeout=10).json()
                
                credits_res = requests.get(f"https://api.themoviedb.org/3/{search_type}/{tmdb_id}/credits",
                                         params={"api_key": TMDB_API_KEY, "language": "pt-BR"}, timeout=10).json()
                
                elenco = [ator.get("name") for ator in credits_res.get("cast", [])[:10]]
                diretores = [p.get("name") for p in credits_res.get("crew", []) if p.get("job") == "Director"]
                
                return {'status': 200, 'body': {
                    "titulo": details_res.get("title") or details_res.get("name"),
                    "titulo_original": details_res.get("original_title") or details_res.get("original_name"),
                    "descricao": details_res.get("overview"),
                    "ano": (details_res.get("release_date") or details_res.get("first_air_date") or "")[:4],
                    "generos": [g.get("name") for g in details_res.get("genres", [])],
                    "nota": details_res.get("vote_average"),
                    "poster": f"https://image.tmdb.org/t/p/w500{details_res.get('poster_path')}" if details_res.get("poster_path") else None,
                    "elenco": elenco,
                    "diretores": diretores
                }}
                
            except Exception as e:
                logger.exception("Erro ao obter detalhes TMDB")
                return {'status': 500, 'body': {"erro": "Erro ao obter detalhes", "detalhe": str(e)}}
        
        # Fórum - GET
        elif path == '/forum' and method == 'GET':
            page = max(1, int(query_params.get('page', [1])[0]))
            per_page = max(1, min(100, int(query_params.get('per_page', [10])[0])))
            start = (page - 1) * per_page
            end = start + per_page
            
            return {'status': 200, 'body': {
                "total": len(FORUM_TOPICS),
                "page": page,
                "per_page": per_page,
                "items": FORUM_TOPICS[start:end]
            }}
        
        # Fórum - POST
        elif path == '/forum' and method == 'POST':
            try:
                data = json.loads(body.decode('utf-8')) if body else {}
                if not data or not data.get("titulo") or not data.get("conteudo"):
                    return {'status': 400, 'body': {"erro": "JSON com 'titulo' e 'conteudo' obrigatórios"}}
                
                topic_id = len(FORUM_TOPICS) + 1
                topic = {
                    "id": topic_id,
                    "titulo": data.get("titulo"),
                    "conteudo": data.get("conteudo"),
                    "autor": data.get("autor") or "anon",
                    "criado_em": data.get("criado_em") or ""
                }
                FORUM_TOPICS.append(topic)
                
                return {'status': 201, 'body': topic}
                
            except json.JSONDecodeError:
                return {'status': 400, 'body': {"erro": "JSON inválido"}}
        
        # Rota não encontrada
        else:
            return {'status': 404, 'body': {"erro": "Rota não encontrada"}}

# ---------- Para desenvolvimento local ----------
if __name__ == "__main__":
    from http.server import HTTPServer
    server = HTTPServer(('localhost', 3000), handler)
    print("Servidor rodando em http://localhost:3000")
    server.serve_forever()
