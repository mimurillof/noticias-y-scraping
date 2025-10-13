"""Scraper de ideas de TradingView enfocado en el portafolio de `main.py`."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional, Sequence
from urllib.parse import urlencode, urlparse

import requests
from bs4 import BeautifulSoup

# --- Configuración estática ---


@dataclass(frozen=True)
class TradingViewSymbol:
    ticker: str
    tv_symbol: str
    category: str
    params: Dict[str, str]


PORTFOLIO_SYMBOLS: Sequence[TradingViewSymbol] = (
    TradingViewSymbol("AAPL", "NASDAQ-AAPL", "stock", {"sort": "recent"}),
    TradingViewSymbol("MSFT", "NASDAQ-MSFT", "stock", {"sort": "recent"}),
    TradingViewSymbol("TSLA", "NASDAQ-TSLA", "stock", {"sort": "recent"}),
)

MARKET_REFERENCES: Sequence[TradingViewSymbol] = (
    TradingViewSymbol("SPX", "SPX", "market", {"sort": "recent"}),
    TradingViewSymbol("NDX", "NASDAQ100", "market", {"sort": "recent"}),
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7",
}

CARD_SELECTORS: Sequence[str] = (
    "div.tv-feed__item",
    "div.js-feed__item",
    "article.tv-feed__item",
    "article.tv-idea-card",
    "article[class*='idea-card']",
    "article[class*='card-exterior']",
)


# --- Utilidades internas ---


def _build_url(symbol: TradingViewSymbol, page: int) -> str:
    base = f"https://es.tradingview.com/symbols/{symbol.tv_symbol}/ideas/"
    if page > 1:
        base += f"page-{page}/"
    query = urlencode(symbol.params)
    return f"{base}?{query}" if query else base


def _to_datetime(timestamp: Optional[int] | Optional[str]) -> Optional[datetime]:
    if timestamp is None:
        return None
    try:
        if isinstance(timestamp, str):
            if timestamp.isdigit():
                timestamp = int(timestamp)
            else:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        if isinstance(timestamp, (int, float)):
            return datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
    except ValueError:
        return None
    return None


def _select_text(node, selectors: Sequence[str]) -> Optional[str]:
    for selector in selectors:
        element = node.select_one(selector)
        if element:
            text = element.get_text(strip=True)
            if text:
                return text
    return None


def _select_attr(node, selectors: Sequence[str], attr: str) -> Optional[str]:
    for selector in selectors:
        element = node.select_one(selector)
        if element:
            value = element.get(attr)
            if isinstance(value, str) and value:
                return value
    return None


def _resolve_image(node) -> Optional[str]:
    for selector in (
        "img.tv-widget-idea__image",
        "img[data-src]",
        "picture img",
        "a[data-qa-id='ui-lib-card-link-image'] img",
    ):
        element = node.select_one(selector)
        if not element:
            continue
        for attribute in ("data-src", "data-full-src", "src"):
            value = element.get(attribute)
            if isinstance(value, str) and value.startswith("http"):
                return value
    return None


def _extract_rating(node) -> Optional[str]:
    rating = _select_text(
        node,
        (
            "span.tv-widget-idea__label",
            "span.tv-idea-labeled-list__label",
            "span[class*='rating']",
            "span[class*='strategy']",
            "span[data-qa-id='idea-strategy-label']",
        ),
    )
    return rating


def _parse_card(card, symbol: TradingViewSymbol, source_url: str) -> Optional[Dict[str, Optional[str]]]:
    title_node = None
    for selector in (
        "a.tv-widget-idea__title",
        "a.js-widget-idea__title",
        "a[data-qa-id='ui-lib-card-link-title']",
        "a.title-tkslJwxl",
    ):
        title_node = card.select_one(selector)
        if title_node:
            break
    if not title_node:
        return None

    link_href = title_node.get("href")

    def _idea_id_from_url(url: Optional[str]) -> Optional[str]:
        if not url:
            return None
        parsed = urlparse(url)
        path = parsed.path if parsed.scheme else url
        if not isinstance(path, str):
            return None
        clean = path.strip("/")
        if not clean:
            return None
        return clean.split("/")[-1]

    idea_id = card.get("data-id") or _idea_id_from_url(link_href) or card.get("id")
    if not idea_id:
        return None

    idea_url = f"https://es.tradingview.com{link_href}" if link_href and link_href.startswith("/") else link_href
    if not idea_url:
        return None

    timestamp_candidate = card.get("data-timestamp") or _select_attr(
        card,
        (
            "span[data-timestamp]",
            "time[data-timestamp]",
            "*[data-timestamp]",
        ),
        "data-timestamp",
    )
    published_at = _to_datetime(timestamp_candidate)
    if not published_at:
        # fallback to `datetime` attribute if available
        published_at = _to_datetime(
            _select_attr(card, ("time[datetime]",), "datetime")
        )

    author = _select_text(
        card,
        (
            "a.tv-card-user-info__name",
            "a.tv-user-link__name",
            "span.tv-user-link__name",
            "a.tv-card-user__name",
            "address a.card-author-link-BhFUdJAZ",
            "address a[data-username]",
            "address a",
        ),
    )

    rating = _extract_rating(card)
    image_url = _resolve_image(card)

    return {
        "id": idea_id.strip(),
        "ticker": symbol.ticker,
        "category": symbol.category,
        "title": title_node.get_text(strip=True),
        "author": author,
        "rating": rating,
        "published_at": published_at.isoformat() if published_at else None,
        "idea_url": idea_url,
        "image_url": image_url,
        "source_url": source_url,
    }


def _filter_recent(ideas: Iterable[Dict[str, Optional[str]]], cutoff_hours: int) -> List[Dict[str, Optional[str]]]:
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=cutoff_hours)
    recent: List[Dict[str, Optional[str]]] = []
    for idea in ideas:
        published_at = idea.get("published_at")
        if not published_at:
            continue
        try:
            dt = datetime.fromisoformat(published_at)
        except ValueError:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt >= cutoff:
            recent.append(idea)
    return recent


def _dedupe(ideas: Iterable[Dict[str, Optional[str]]]) -> List[Dict[str, Optional[str]]]:
    seen: set[str] = set()
    unique: List[Dict[str, Optional[str]]] = []
    for idea in ideas:
        identifier = idea.get("id")
        if not identifier or identifier in seen:
            continue
        seen.add(identifier)
        unique.append(idea)
    return unique


def _scrape_symbol(
    session: requests.Session,
    symbol: TradingViewSymbol,
    max_pages: int,
    cutoff_hours: int,
) -> List[Dict[str, Optional[str]]]:
    ideas: List[Dict[str, Optional[str]]] = []
    for page in range(1, max_pages + 1):
        url = _build_url(symbol, page)
        try:
            response = session.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
        except requests.RequestException as exc:
            print(f"    x Error al descargar {url}: {exc}")
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        cards = []
        for selector in CARD_SELECTORS:
            cards = soup.select(selector)
            if cards:
                break
        if not cards:
            continue

        page_ideas: List[Dict[str, Optional[str]]] = []
        for card in cards:
            parsed = _parse_card(card, symbol, url)
            if parsed:
                page_ideas.append(parsed)

        recent = _filter_recent(page_ideas, cutoff_hours)
        ideas.extend(recent)
        if ideas:
            break
    return _dedupe(ideas)


def _scrape_market_fallback(
    session: requests.Session,
    existing_ids: set[str],
    max_pages: int,
    cutoff_hours: int,
    limit: int,
) -> List[Dict[str, Optional[str]]]:
    collected: List[Dict[str, Optional[str]]] = []
    for symbol in MARKET_REFERENCES:
        if len(collected) >= limit:
            break
        ideas = _scrape_symbol(session, symbol, max_pages, cutoff_hours)
        for idea in ideas:
            if idea["id"] in existing_ids:
                continue
            collected.append(idea)
            if len(collected) >= limit:
                break
    return collected[:limit]


def collect_tradingview_ideas(
    max_pages: int = 2,
    cutoff_hours: int = 48,
    max_portfolio_items: int = 3,
) -> List[Dict[str, Optional[str]]]:
    session = requests.Session()
    try:
        collected: List[Dict[str, Optional[str]]] = []
        for symbol in PORTFOLIO_SYMBOLS:
            if len(collected) >= max_portfolio_items:
                break
            ideas = _scrape_symbol(session, symbol, max_pages, cutoff_hours)
            if ideas:
                collected.extend(ideas)

        collected = _dedupe(collected)
        if len(collected) >= max_portfolio_items:
            return collected[:max_portfolio_items]

        remaining = max_portfolio_items - len(collected)
        fallback = _scrape_market_fallback(
            session,
            existing_ids={str(idea["id"]) for idea in collected if idea.get("id")},
            max_pages=max_pages,
            cutoff_hours=cutoff_hours,
            limit=remaining,
        )
        return (collected + fallback)[:max_portfolio_items]
    finally:
        session.close()


__all__ = ["collect_tradingview_ideas"]
