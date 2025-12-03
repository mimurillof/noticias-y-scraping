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


def get_medium_analysis(tags: List[str], limit: int = 3) -> List[Dict]:
    """Obtiene tesis de Medium con imágenes y formato rico, filtrando contenido de baja calidad."""
    analyses = []
    seen_links = set()
    checked_count = 0
    max_to_check = limit * 10  # Revisar hasta 10x más artículos para encontrar los de calidad

    for tag in tags:
        if len(analyses) >= limit:
            break
            
        url = f"https://medium.com/feed/tag/{tag}"
        feed = feedparser.parse(url)

        for entry in feed.entries:
            if len(analyses) >= limit or checked_count >= max_to_check:
                break
            
            checked_count += 1
            
            if entry.link in seen_links:
                continue

            # Medium pone el contenido completo en 'content' o un resumen en 'summary'
            content_html = entry.content[0].value if 'content' in entry else entry.get('summary', '')
            
            # Limpiar Texto para filtrado y subtítulo
            clean_summary = clean_text(entry.get('summary', ''))
            
            # >>> FILTRO DE CALIDAD <<<
            if not is_quality_article(entry, clean_summary):
                continue
            
            # 1. Extraer Imagen
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
                "type": "ANALYSIS"
            })
            seen_links.add(entry.link)
    
    if checked_count > 0:
        print(f"    → Medium: {len(analyses)} artículos de calidad de {checked_count} revisados")
    
    return analyses

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
    
    # 1. Seeking Alpha (Específico)
    print(f"  --> Buscando análisis ricos para: {portfolio_tickers}")
    for ticker in portfolio_tickers:
        # Limpieza básica de ticker (SA usa '-' para crypto, e.g. BTC-USD)
        clean_ticker = ticker.replace("USD", "-USD") if "USD" in ticker and "-" not in ticker else ticker
        sa_news = get_seeking_alpha_analysis(clean_ticker)
        insights.extend(sa_news)

    # 2. Medium (Tesis Generales)
    medium_tags = []
    for t in portfolio_tickers:
        if "BTC" in t: medium_tags.append("bitcoin")
        if "ETH" in t: medium_tags.append("ethereum")
        if "AI" in t or "NVDA" in t: medium_tags.append("artificial-intelligence")
        if "SOL" in t: medium_tags.append("solana")
    
    medium_tags = list(set(medium_tags))
    if medium_tags:
        print(f"  --> Buscando tesis en Medium para tags: {medium_tags}")
        # Traemos un poco más de Medium para rellenar si SA falla
        medium_news = get_medium_analysis(medium_tags, limit=4)
        insights.extend(medium_news)

    return insights


def _convert_to_tradingview_format(insight: Dict) -> Dict:
    """
    Convierte un insight de Medium/SeekingAlpha al formato de TradingView.
    Esto permite un bypass sin modificar la estructura JSON existente.
    """
    # Extraer ticker del título o usar 'GENERAL'
    ticker = "GENERAL"
    title_lower = insight.get("title", "").lower()
    for t in ["btc", "eth", "nvda", "aapl", "msft", "tsla", "sol"]:
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