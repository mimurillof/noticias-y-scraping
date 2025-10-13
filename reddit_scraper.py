import datetime
from typing import Optional

import praw
import requests
from prawcore import exceptions as praw_exceptions

# --- CONFIGURACIÓN INICIAL (RELLENA TUS DATOS AQUÍ) ---

# 1. Rellena tus credenciales obtenidas en el Paso 1 del tutorial de Reddit
CLIENT_ID = "MxBeG-1_aQJZgKVDALR-2A"
CLIENT_SECRET = "aEOfhYLbapPu9GC-Lf74PSenPF17Gw"
USER_AGENT = "python:PortfolioMonitor:v1.1 (by u/Vithrack)" # Cambia TU_USUARIO

# 2. Define los subreddits que quieres monitorear
TARGET_SUBREDDITS = [
    'investing',
    'wallstreetbets',
    'stocks',
    'options',
    'trading',
    'CryptoCurrency'
]

# --- LÓGICA DEL SCRIPT ---


def _http_headers() -> dict[str, str]:
    """Build headers for direct HTTP fallbacks."""
    return {
        "User-Agent": f"{USER_AGENT} fallback/0.1",
        "Accept": "application/json",
    }

def initialize_reddit():
    """Inicializa y devuelve una instancia de PRAW autenticada."""
    if CLIENT_ID == "TU_CLIENT_ID" or CLIENT_SECRET == "TU_CLIENT_SECRET" or "TU_USUARIO_DE_REDDIT" in USER_AGENT:
        print("ADVERTENCIA: Las credenciales de la API de Reddit no están configuradas en reddit_scraper.py. Se omitirá la búsqueda en Reddit.")
        return None
    try:
        reddit = praw.Reddit(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            user_agent=USER_AGENT,
        )
        reddit.read_only = True
        print("Verificando autenticación con Reddit...")
        reddit.user.me()  # This line verifies that the credentials are correct
        print("Autenticación con Reddit exitosa.")
        return reddit
    except Exception as e:
        print("--- ERROR DE AUTENTICACIÓN DE REDDIT ---")
        print(f"No se pudo autenticar con la API de Reddit. Error: {e}")
        print("Por favor, verifica que los siguientes valores en `reddit_scraper.py` son correctos:")
        print(f"  - CLIENT_ID: '{CLIENT_ID}'")
        print(f"  - CLIENT_SECRET: '{'*' * len(CLIENT_SECRET)}'")
        print(f"  - USER_AGENT: '{USER_AGENT}'")
        print("Asegúrate de que has copiado los valores exactamente como aparecen en https://www.reddit.com/prefs/apps")
        print("-----------------------------------------")
        return None

def _parse_listing_children(children: list[dict], source: str) -> list[dict]:
    """Normalize Reddit listing JSON entries."""
    posts: list[dict] = []
    for child in children:
        data = child.get("data", {})
        created = data.get("created_utc")
        try:
            created_iso = (
                datetime.datetime.fromtimestamp(created, tz=datetime.timezone.utc).isoformat()
                if created is not None
                else None
            )
        except Exception:
            created_iso = None

        posts.append({
            'id': data.get('id'),
            'subreddit': data.get('subreddit'),
            'title': data.get('title'),
            'score': data.get('score'),
            'url': data.get('url'),
            'created_utc': created_iso,
            'source': source,
        })
    return posts


def _parse_iso_timestamp(value: Optional[str]) -> float:
    """Convert ISO timestamp string to sortable unix epoch seconds."""
    if not value:
        return float('-inf')
    try:
        return datetime.datetime.fromisoformat(value).timestamp()
    except ValueError:
        return float('-inf')


def _ranking_key(post: dict) -> tuple:
    """Priority tuple to keep portfolio mentions first and high-signal posts on top."""
    source = post.get('source', '') or ''
    score = post.get('score') or 0
    created_epoch = _parse_iso_timestamp(post.get('created_utc'))
    is_portfolio = 0 if 'portfolio' in source else 1
    return (
        is_portfolio,
        -score,
        -created_epoch,
    )


def _fetch_hot_posts_http(subreddit_name: str, limit: int) -> list[dict]:
    """Fallback using Reddit's public JSON endpoint."""
    print(f"    -> Fallback: consultando /r/{subreddit_name}/hot vía JSON público...")
    try:
        response = requests.get(
            f"https://www.reddit.com/r/{subreddit_name}/hot.json",
            headers=_http_headers(),
            params={"limit": limit},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        children = data.get("data", {}).get("children", [])
        return _parse_listing_children(children, source="hot_fallback")
    except Exception as fallback_error:
        print(f"    Fallback también falló para posts 'hot': {fallback_error}")
        return []


def fetch_hot_posts(subreddit, limit=5):
    """Obtiene las publicaciones 'hot' de un subreddit."""
    posts: list[dict] = []
    print(f"  -> Buscando publicaciones 'hot' en r/{subreddit.display_name}...")
    try:
        for submission in subreddit.hot(limit=limit):
            posts.append({
                'id': submission.id,
                'subreddit': subreddit.display_name,
                'title': submission.title,
                'score': submission.score,
                'url': submission.url,
                'created_utc': datetime.datetime.fromtimestamp(
                    submission.created_utc, tz=datetime.timezone.utc
                ).isoformat(),
                'source': 'hot'
            })
    except praw_exceptions.ResponseException as e:
        print(f"    Error al obtener posts 'hot': {e}. Intentando fallback anónimo...")
        posts = _fetch_hot_posts_http(subreddit.display_name, limit)
    except Exception as e:
        print(f"    Error al obtener posts 'hot': {e}")
        if not posts:
            posts = _fetch_hot_posts_http(subreddit.display_name, limit)
    return posts


def fetch_portfolio_posts(subreddit, assets, limit=15):
    """Busca publicaciones nuevas que mencionen activos del portafolio."""
    posts: list[dict] = []
    query = ' OR '.join(asset for asset in assets)
    print(f"  -> Buscando menciones de activos en r/{subreddit.display_name}...")
    try:
        for submission in subreddit.search(query, sort='new', limit=limit):
            posts.append({
                'id': submission.id,
                'subreddit': subreddit.display_name,
                'title': submission.title,
                'score': submission.score,
                'url': submission.url,
                'created_utc': datetime.datetime.fromtimestamp(
                    submission.created_utc, tz=datetime.timezone.utc
                ).isoformat(),
                'source': 'portfolio_mention'
            })
    except praw_exceptions.ResponseException as e:
        print(f"    Error al buscar menciones: {e}. Intentando fallback anónimo...")
        posts = _fetch_portfolio_posts_http(subreddit.display_name, assets, limit)
    except Exception as e:
        print(f"    Error al buscar menciones: {e}")
        if not posts:
            posts = _fetch_portfolio_posts_http(subreddit.display_name, assets, limit)
    return posts


def _fetch_portfolio_posts_http(subreddit_name: str, assets: list[str], limit: int) -> list[dict]:
    """Fallback search using Reddit JSON endpoint when OAuth requests fail."""
    print(f"    -> Fallback: consultando menciones vía JSON público en r/{subreddit_name}...")
    if not assets:
        return []
    query = ' OR '.join(assets)
    params = {
        'q': query,
        'restrict_sr': 1,
        'sort': 'new',
        'limit': limit,
    }
    try:
        response = requests.get(
            f"https://www.reddit.com/r/{subreddit_name}/search.json",
            headers=_http_headers(),
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        children = data.get('data', {}).get('children', [])
        return _parse_listing_children(children, source='portfolio_mention_fallback')
    except Exception as fallback_error:
        print(f"    Fallback también falló al buscar menciones: {fallback_error}")
        return []

def fetch_reddit_posts(portfolio_assets: list[str]):
    """
    Función principal para obtener publicaciones de Reddit relacionadas con un portafolio.
    """
    reddit = initialize_reddit()
    if not reddit:
        return []

    all_posts = []
    seen_post_ids = set()

    print("Iniciando monitor de Reddit para subreddits financieros...")

    for sub_name in TARGET_SUBREDDITS:
        try:
            subreddit = reddit.subreddit(sub_name)
            print(f"Revisando r/{sub_name}...")
            
            # 1. Obtener menciones a nuestro portafolio
            portfolio_posts = fetch_portfolio_posts(subreddit, portfolio_assets)
            
            # 2. Si no hay menciones, obtener publicaciones 'hot'
            if not portfolio_posts:
                hot_posts = fetch_hot_posts(subreddit)
            else:
                hot_posts = []

            # Combinar y evitar duplicados
            for post in portfolio_posts + hot_posts:
                if post['id'] not in seen_post_ids:
                    all_posts.append(post)
                    seen_post_ids.add(post['id'])

        except Exception as e:
            print(f"No se pudo procesar r/{sub_name}: {e}")

    if all_posts:
        ranked_posts = sorted(all_posts, key=_ranking_key)
        return ranked_posts[:3]

    return all_posts
