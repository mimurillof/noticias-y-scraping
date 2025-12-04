import feedparser
import requests
import re
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from datetime import datetime, timezone

# --- CONFIGURACIÓN ---
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def extract_image_url(html_content: str) -> Optional[str]:
    """Intenta extraer la primera imagen de un contenido HTML (RSS)."""
    if not html_content:
        return None
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        img = soup.find("img")
        if img and img.get("src"):
            return img.get("src")
        # Fallback para Medium: a veces usan figure > img
        return None
    except Exception:
        return None

def clean_text(html_content: str) -> str:
    """Limpia el HTML para dejar solo texto plano para resumen/subtítulo."""
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, "html.parser")
    text = soup.get_text(separator=" ")
    return re.sub(r'\s+', ' ', text).strip()


# --- FILTROS DE CALIDAD PARA MEDIUM ---
SPAM_KEYWORDS = [
    # Promociones y estafas
    "airdrop", "giveaway", "free money", "moon", "lambo", "100x", "1000x",
    "shitcoin", "memecoin", "presale", "ido", "ico launch", "pump",
    "get rich", "millionaire", "treasure", "delta kim", "legends of crypto",
    "join now", "sign up", "referral", "affiliate", "whitelist",
    "scam exposed", "scam alert", "is it a scam", "ponzi",
    # Contenido personal/diario no relevante
    "day 1 of", "day 2 of", "day 3 of", "day 4 of", "day 5 of",
    "it's day", "organically growing", "my journey", "my portfolio",
    # Memecoins específicos
    "blackswan", "pepe", "doge", "shib", "floki", "bonk", "wif",
    # Promociones de proyectos
    "join our", "don't miss", "last chance", "limited time",
]

LOW_QUALITY_PATTERNS = [
    r'^\d{4}/\d{1,2}/\d{1,2}$',  # Títulos como "2025/12/3"
    r'^[A-Z]{2,5}\s*\d+',         # Títulos como "XRP 32 ETH 23"
    r'^[a-z]{2,5}\s+\d+',         # Variante minúscula
    r'^[\d\s/\-\.]+$',            # Solo números y separadores
    r'^day\s+\d+',                # "Day 1", "Day 53", etc.
    r'^\$[A-Z]+',                 # Títulos que empiezan con ticker "$BTC"
]

# Palabras que indican contenido analítico de calidad
QUALITY_INDICATORS = [
    "analysis", "outlook", "forecast", "research", "report",
    "review", "insight", "perspective", "deep dive", "technical",
    "fundamental", "valuation", "earnings", "revenue", "growth",
    "strategy", "market", "investment", "portfolio", "risk",
    "opportunities", "trends", "sector", "industry", "quarterly"
]

def is_quality_article(entry: dict, clean_summary: str) -> bool:
    """
    Filtra artículos de baja calidad de Medium.
    Returns True si el artículo pasa los filtros de calidad.
    """
    title = entry.get('title', '').strip()
    
    # 1. Título demasiado corto (menos de 20 caracteres)
    if len(title) < 20:
        return False
    
    # 2. Título es solo una fecha o números
    for pattern in LOW_QUALITY_PATTERNS:
        if re.match(pattern, title, re.IGNORECASE):
            return False
    
    # 3. Contenido spam (palabras clave en título o resumen)
    text_to_check = (title + " " + clean_summary).lower()
    for keyword in SPAM_KEYWORDS:
        if keyword in text_to_check:
            return False
    
    # 4. Resumen vacío o genérico "Continue reading on Medium"
    if not clean_summary or len(clean_summary) < 50:
        return False
    if clean_summary.strip() == "Continue reading on Medium »":
        return False
    
    # 5. Resumen que es SOLO "Continue reading on Medium" (puede tener prefijo)
    summary_lower = clean_summary.lower().strip()
    if summary_lower.endswith("continue reading on medium »") and len(summary_lower) < 80:
        return False
    
    # 6. Resumen que es solo lista de tickers (xrp 32 eth 23 sol 13...)
    ticker_pattern = r'^([a-z]{2,5}\s+\d+\s*)+$'
    if re.match(ticker_pattern, clean_summary.lower().replace('…', '').strip()):
        return False
    
    # 7. Título en idiomas no latinos (caracteres japoneses, chinos, etc.)
    non_latin_count = len(re.findall(r'[^\x00-\x7F]', title))
    if non_latin_count > len(title) * 0.3:  # Más del 30% no-ASCII
        return False
    
    # 8. BONUS: Preferir artículos con indicadores de calidad
    has_quality_indicator = any(ind in text_to_check for ind in QUALITY_INDICATORS)
    
    # Si no tiene indicadores de calidad Y el resumen es muy corto, rechazar
    if not has_quality_indicator and len(clean_summary) < 100:
        return False
    
    return True


def get_medium_analysis_by_ticker(ticker: str, limit: int = 2) -> List[Dict]:
    """
    Busca análisis en Medium directamente por ticker.
    Usa múltiples estrategias de búsqueda para maximizar resultados.
    """
    analyses = []
    seen_links = set()
    
    # Limpiar ticker para búsqueda
    clean_ticker = ticker.upper().replace("-USD", "").replace("^", "").replace("-", "")
    
    # Generar tags de búsqueda basados en el ticker
    search_tags = _get_search_tags_for_ticker(clean_ticker)
    
    checked_count = 0
    max_to_check = limit * 8
    
    for tag in search_tags:
        if len(analyses) >= limit:
            break
            
        url = f"https://medium.com/feed/tag/{tag}"
        try:
            feed = feedparser.parse(url)
        except Exception:
            continue

        for entry in feed.entries:
            if len(analyses) >= limit or checked_count >= max_to_check:
                break
            
            checked_count += 1
            
            if entry.link in seen_links:
                continue

            content_html = entry.content[0].value if 'content' in entry else entry.get('summary', '')
            clean_summary = clean_text(entry.get('summary', ''))
            
            # Filtro de calidad
            if not is_quality_article(entry, clean_summary):
                continue
            
            image_url = extract_image_url(content_html)
            
            analyses.append({
                "uuid": entry.id if 'id' in entry else entry.link,
                "source": "Medium Expert",
                "author": entry.author if 'author' in entry else "Unknown",
                "title": entry.title,
                "subtitle": clean_summary[:150] + "..." if len(clean_summary) > 150 else clean_summary,
                "summary": clean_summary[:500] + "...",
                "url": entry.link,
                "image": image_url,
                "likes": None,
                "published_at": entry.published if 'published' in entry else str(datetime.now(timezone.utc)),
                "type": "ANALYSIS",
                "related_ticker": ticker  # Guardar referencia al ticker
            })
            seen_links.add(entry.link)
    
    return analyses


def _get_search_tags_for_ticker(ticker: str) -> List[str]:
    """
    Genera tags de búsqueda dinámicamente basados en el tipo de ticker.
    No requiere mapeo manual - detecta automáticamente la categoría.
    """
    tags = []
    ticker_upper = ticker.upper()
    
    # 1. Detectar CRYPTO
    crypto_tickers = ["BTC", "ETH", "SOL", "XRP", "ADA", "DOT", "AVAX", "MATIC", "LINK", "UNI", "PAXG"]
    if ticker_upper in crypto_tickers or "USD" in ticker_upper:
        if "BTC" in ticker_upper:
            tags.extend(["bitcoin", "cryptocurrency"])
        elif "ETH" in ticker_upper:
            tags.extend(["ethereum", "cryptocurrency", "defi"])
        elif "SOL" in ticker_upper:
            tags.extend(["solana", "cryptocurrency"])
        elif "PAXG" in ticker_upper:
            tags.extend(["gold", "cryptocurrency"])
        else:
            tags.extend(["cryptocurrency", "crypto"])
        return tags[:3]
    
    # 2. Detectar ÍNDICES
    if ticker_upper in ["SPX", "SPY", "QQQ", "DIA", "IWM", "VTI", "VOO"]:
        tags.extend(["stock-market", "investing", "index-funds"])
        return tags[:3]
    
    # 3. Para ACCIONES - usar tags genéricos por sector (más escalable)
    # Medium no tiene tags por ticker individual, así que usamos categorías amplias
    tags.extend([
        "stock-market",      # Tag general de mercado
        "investing",         # Tag de inversión
        "stock-analysis"     # Tag de análisis
    ])
    
    return tags[:3]


def get_seeking_alpha_analysis(ticker: str, limit: int = 2) -> List[Dict]:
    """Obtiene análisis de Seeking Alpha con formato rico."""
    url = f"https://seekingalpha.com/api/sa/combined/{ticker}.xml"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=5)
        if response.status_code != 200:
            return []
            
        feed = feedparser.parse(response.content)
        analyses = []
        
        for entry in feed.entries[:limit]:
            # Filtrar solo artículos (análisis), no noticias breves
            if "article" not in entry.link and "news" in entry.link:
                continue

            # Seeking Alpha RSS a veces es escueto con las imágenes
            # Intentamos sacar algo si está en el CDATA, si no, null.
            content_html = entry.get('summary', '') or entry.get('content', '')
            image_url = extract_image_url(content_html)

            # SA suele poner el logo de stock como imagen en sus metadatos internos, 
            # pero por RSS es difícil. Si es null, tu frontend puede poner un placeholder.

            analyses.append({
                "uuid": entry.id if 'id' in entry else entry.link,
                "source": "Seeking Alpha",
                "author": entry.author if 'author' in entry else "Analyst",
                "title": entry.title,
                "subtitle": f"Analysis regarding {ticker} performance and outlook.",
                "summary": clean_text(entry.get('summary', ''))[:500],
                "url": entry.link,
                "image": image_url, 
                "likes": None,
                "published_at": entry.published,
                "type": "ANALYSIS"
            })
            
        return analyses

    except Exception as e:
        print(f"Error fetching Seeking Alpha for {ticker}: {e}")
        return []

def get_expert_insights(portfolio_tickers: List[str]) -> List[Dict]:
    """Orquestador que combina todo."""
    insights = []
    seen_urls = set()  # Para deduplicación global
    
    # 1. Seeking Alpha (Específico por ticker)
    print(f"  --> Buscando análisis para: {portfolio_tickers}")
    for ticker in portfolio_tickers:
        # Limpieza básica de ticker
        clean_ticker = ticker.replace("USD", "-USD") if "USD" in ticker and "-" not in ticker else ticker
        clean_ticker = clean_ticker.replace("^", "")
        
        # Seeking Alpha por ticker
        sa_news = get_seeking_alpha_analysis(clean_ticker, limit=2)
        for article in sa_news:
            url = article.get('url', article.get('uuid', ''))
            if url not in seen_urls:
                insights.append(article)
                seen_urls.add(url)

    # 2. Medium (Por ticker - mismo patrón escalable que SA)
    print(f"  --> Buscando análisis en Medium para: {portfolio_tickers}")
    medium_articles = []
    for ticker in portfolio_tickers:
        ticker_articles = get_medium_analysis_by_ticker(ticker, limit=2)
        for article in ticker_articles:
            url = article.get('url', article.get('uuid', ''))
            if url not in seen_urls:
                medium_articles.append(article)
                seen_urls.add(url)
    
    # Limitar Medium a 4 artículos únicos máximo
    insights.extend(medium_articles[:4])
    
    if medium_articles:
        print(f"    → Medium: {len(medium_articles[:4])} artículos únicos encontrados")

    return insights


def _convert_to_tradingview_format(insight: Dict) -> Dict:
    """
    Convierte un insight de Medium/SeekingAlpha al formato de TradingView.
    Esto permite un bypass sin modificar la estructura JSON existente.
    """
    # Usar el ticker relacionado si existe, sino extraer del título
    ticker = insight.get("related_ticker", "GENERAL")
    if ticker == "GENERAL":
        title_lower = insight.get("title", "").lower()
        for t in ["btc", "eth", "nvda", "aapl", "msft", "tsla", "sol", "jnj", "ko", "pg", "cvx"]:
            if t in title_lower:
                ticker = t.upper()
                break
    
    return {
        # Campos originales de TradingView
        "id": insight.get("uuid", insight.get("url", "")),
        "ticker": ticker,
        "category": "analysis",  # Era 'stock' o 'market' en TV
        "title": insight.get("title", ""),
        "author": insight.get("author", "Unknown"),
        "rating": insight.get("likes"),  # Puede ser None
        "published_at": insight.get("published_at"),
        "idea_url": insight.get("url", ""),
        "image_url": insight.get("image"),
        "source_url": insight.get("url", ""),
        # Campos adicionales que el nuevo scraper provee
        "source": insight.get("source", "Expert Analysis"),
        "subtitle": insight.get("subtitle", ""),
        "summary": insight.get("summary", ""),
        "type": insight.get("type", "ANALYSIS"),
    }


def collect_expert_analysis(
    portfolio_tickers: List[str],
    max_items: int = 5,
    **kwargs  # Para compatibilidad con parámetros de TradingView que ya no usamos
) -> List[Dict]:
    """
    Función wrapper que reemplaza collect_tradingview_ideas.
    Obtiene análisis de expertos y los convierte al formato TradingView.
    
    Args:
        portfolio_tickers: Lista de símbolos del portfolio
        max_items: Número máximo de items a retornar
        **kwargs: Parámetros ignorados (para compatibilidad)
    
    Returns:
        Lista de análisis en formato compatible con tradingview_ideas
    """
    # Si no hay tickers, usar tags genéricos
    if not portfolio_tickers:
        portfolio_tickers = ["BTC", "ETH", "NVDA"]
    
    # Obtener insights
    raw_insights = get_expert_insights(portfolio_tickers)
    
    # Convertir al formato TradingView para bypass
    converted = [_convert_to_tradingview_format(i) for i in raw_insights]
    
    # Limitar cantidad
    return converted[:max_items]