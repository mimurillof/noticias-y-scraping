#!/usr/bin/env python3
"""
Descarga noticias con miniaturas para un portafolio de tickers usando yfinance.
Guarda un JSON con máximo tres notas por activo.
"""

from __future__ import annotations

import argparse
import json
import sys
import os
from pathlib import Path
from supabase import create_client
from datetime import datetime, timezone
from typing import Any, Dict, List

# Importar normalización de símbolos
try:
    from symbol_normalizer import normalize_symbol
    NORMALIZER_AVAILABLE = True
except ImportError:
    NORMALIZER_AVAILABLE = False
    def normalize_symbol(symbol: str, verbose: bool = False) -> str:
        """Fallback si no está disponible el normalizador."""
        return symbol.upper().strip()

_ENV_LOADED = False


def ensure_env_loaded() -> None:
    """Load environment variables from a .env file once if python-dotenv exists."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    try:
        from dotenv import load_dotenv  # type: ignore
    except ImportError:
        _load_env_file()
        _ENV_LOADED = True
        return

    load_dotenv()
    _ENV_LOADED = True


def _load_env_file() -> None:
    """Fallback loader that parses a .env file manually."""
    candidate_paths = [
        Path(__file__).resolve().parent / ".env",
        Path.cwd() / ".env",
    ]

    for env_path in candidate_paths:
        if not env_path.exists():
            continue
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
        break

import yfinance as yf


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Obtiene noticias con imágenes para un portafolio de activos."
    )
    parser.add_argument(
        "--tickers",
        nargs="+",
        default=["AAPL", "MSFT", "TSLA"],
        help=(
            "Símbolos del portafolio (por ejemplo: AAPL MSFT TSLA). "
            "Default: AAPL MSFT TSLA"
        ),
    )
    parser.add_argument(
        "--max-news",
        type=int,
        default=3,
        help="Número máximo de noticias por activo (default: 3).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="portfolio_news.json",
        help="Ruta del archivo JSON de salida (default: portfolio_news.json).",
    )
    return parser.parse_args()


def pick_thumbnail_url(thumbnail_payload: Dict[str, Any]) -> str | None:
    if not isinstance(thumbnail_payload, dict):
        return None

    direct_url = thumbnail_payload.get("url")
    if direct_url:
        return direct_url

    resolutions = thumbnail_payload.get("resolutions") or []
    if not resolutions:
        return None

    richest = max(
        (item for item in resolutions if isinstance(item, dict)),
        key=lambda item: item.get("width", 0),
        default=None,
    )
    if not richest:
        return None
    return richest.get("url")


def format_publish_time(epoch_seconds: Any) -> str | None:
    if not epoch_seconds:
        return None
    try:
        # yfinance may return timestamps as strings, so we convert to int
        return datetime.fromtimestamp(int(epoch_seconds), tz=timezone.utc).isoformat()
    except (ValueError, TypeError):
        return None


def coalesce(*values: Any) -> Any:
    """Return the first truthy value in the provided sequence."""
    for value in values:
        if value:
            return value
    return None


def normalize_text(value: Any) -> str | None:
    """Convert heterogeneous values into trimmed strings when possible."""
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    try:
        text = str(value).strip()
    except Exception:
        return None
    return text or None


def coalesce_text(*values: Any) -> str | None:
    """Return the first non-empty textual representation from the candidates."""
    for value in values:
        text = normalize_text(value)
        if text:
            return text
    return None


def get_publish_epoch(news_item: Dict[str, Any]) -> int | None:
    """Extracts the publication time as an epoch integer."""
    content = news_item.get("content")
    if not isinstance(content, dict):
        content = {}

    time_val = (
        news_item.get("providerPublishTime")
        or content.get("providerPublishTime")
        or news_item.get("published_at")
        or content.get("published_at")
        or news_item.get("pubDate")
        or content.get("pubDate")
    )

    if not time_val:
        return None
    if isinstance(time_val, dict):
        time_val = time_val.get("raw") or time_val.get("value")

    if isinstance(time_val, (int, float)):
        return int(time_val)

    if isinstance(time_val, str):
        stripped = time_val.strip()
        if not stripped:
            return None
        try:
            # Handles numeric strings
            return int(float(stripped))
        except ValueError:
            try:
                # Handles ISO8601 strings such as "2025-10-13T21:06:42Z"
                dt_obj = datetime.fromisoformat(stripped.replace("Z", "+00:00"))
                return int(dt_obj.timestamp())
            except ValueError:
                return None
    return None


def format_news_item(news: Dict[str, Any]) -> Dict[str, Any] | None:
    """Formats a raw news item dictionary."""
    # yfinance ahora retorna: {id: ..., content: {...}}
    uuid = news.get("uuid") or news.get("id")
    if not uuid:
        return None

    content = news.get("content")
    if not isinstance(content, dict):
        content = {}

    # Thumbnail: Intentar content.thumbnail primero
    thumbnail_url = None
    thumbnail_payload = content.get("thumbnail") or news.get("thumbnail")
    if thumbnail_payload:
        thumbnail_url = pick_thumbnail_url(thumbnail_payload)
    thumbnail_url = normalize_text(thumbnail_url)

    # Link: Intentar content.clickThroughUrl (nueva estructura)
    link_value = None
    click_through = content.get("clickThroughUrl")
    if isinstance(click_through, dict):
        link_value = click_through.get("url")
    
    if not link_value:
        link_value = coalesce(
            content.get("canonicalUrl", {}).get("url") if isinstance(content.get("canonicalUrl"), dict) else None,
            news.get("link"),
            content.get("link"),
            news.get("url"),
            content.get("url"),
        )
        if isinstance(link_value, dict):
            link_value = link_value.get("url")
    
    link_value = normalize_text(link_value)

    # Publish time: Intentar content.pubDate (nueva estructura)
    publish_epoch = None
    pub_date = content.get("pubDate")
    if pub_date:
        try:
            if isinstance(pub_date, str):
                dt_obj = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                publish_epoch = int(dt_obj.timestamp())
        except:
            pass
    
    if not publish_epoch:
        publish_epoch = get_publish_epoch(news)

    # Title: Priorizar content.title (nueva estructura)
    title = coalesce_text(content.get("title"), news.get("title"))
    
    # Subtitle/Description: Priorizar content.description
    subtitle = coalesce_text(
        content.get("subtitle"),
        news.get("subtitle"),
        content.get("description"),
        news.get("description"),
    )
    
    # Summary: Priorizar content.summary
    summary = coalesce_text(
        content.get("summary"),
        news.get("summary"),
        content.get("body"),
        content.get("text"),
        news.get("body"),
    )
    if summary and subtitle and summary.strip() == subtitle.strip():
        summary = None
    if not subtitle and summary:
        subtitle = summary

    # Source/Publisher: Priorizar content.provider.displayName (nueva estructura)
    source = None
    provider = content.get("provider")
    if isinstance(provider, dict):
        source = provider.get("displayName")
    
    if not source:
        source = coalesce_text(
            news.get("publisher"),
            news.get("source"),
            content.get("publisher"),
            content.get("source"),
        )

    return {
        "uuid": uuid,
        "title": title,
        "subtitle": subtitle,
        "summary": summary,
        "source": source,
        "url": link_value,
        "published_at": format_publish_time(publish_epoch)
        if publish_epoch
        else None,
        "image": thumbnail_url,
        "type": (
            content.get("contentType") or news.get("type") or content.get("type")
        ),
        "_publish_epoch": publish_epoch,  # Internal field for sorting
    }


def normalize_existing_news_item(news: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure legacy news entries expose the new schema fields."""
    normalized = dict(news)

    link_value = normalized.get("link")
    if isinstance(link_value, dict):
        normalized["url"] = coalesce_text(normalized.get("url"), link_value.get("url"))
    elif isinstance(link_value, str):
        normalized.setdefault("url", normalize_text(link_value))

    if "image" not in normalized and normalized.get("image_url"):
        normalized["image"] = normalized.get("image_url")

    if "source" not in normalized and normalized.get("publisher"):
        normalized["source"] = normalize_text(normalized.get("publisher"))

    for required_key in ("title", "subtitle", "summary", "source", "image"):
        normalized[required_key] = normalize_text(normalized.get(required_key))

    normalized["url"] = normalize_text(normalized.get("url"))
    normalized.pop("image_url", None)
    return normalized


def get_new_and_recent_news(
    tickers: List[str], seen_uuids: set[str]
) -> List[Dict[str, Any]]:
    """Fetches, filters for new and recent, and formats news."""
    # Normalizar los tickers antes de consultar
    normalized_tickers = []
    for ticker in tickers:
        normalized = normalize_symbol(ticker, verbose=False)
        normalized_tickers.append(normalized)
        if NORMALIZER_AVAILABLE and normalized != ticker.upper():
            print(f"  🔧 Normalizado: {ticker} → {normalized}")
    
    news_by_ticker: Dict[str, List[Dict[str, Any]]] = {}
    for ticker in normalized_tickers:
        ticker_obj = yf.Ticker(ticker)
        news_items = ticker_obj.news or []
        if isinstance(news_items, list):
            news_by_ticker[ticker] = news_items
            print(f"     → {ticker}: {len(news_items)} noticias obtenidas de yfinance")

    interleaved_news: List[Dict[str, Any]] = []
    max_depth = max((len(v) for v in news_by_ticker.values()), default=0)
    for i in range(max_depth):
        # BUGFIX: Usar normalized_tickers en lugar de tickers
        for ticker in normalized_tickers:
            if i < len(news_by_ticker.get(ticker, [])):
                interleaved_news.append(news_by_ticker[ticker][i])

    print(f"     → Total noticias intercaladas: {len(interleaved_news)}")
    print(f"     → UUIDs ya vistos: {len(seen_uuids)}")

    # Process and filter
    new_and_recent: List[Dict[str, Any]] = []
    # Cambio: Usar 24 horas en lugar de 30 minutos para capturar más noticias
    twenty_four_hours_ago = int(datetime.now(tz=timezone.utc).timestamp()) - (24 * 60 * 60)

    processed_in_this_run = set()
    skipped_seen = 0
    skipped_no_format = 0
    skipped_old = 0

    for raw_news in interleaved_news:
        uuid = raw_news.get("uuid") or raw_news.get("id")
        if not uuid:
            continue
        
        if uuid in seen_uuids or uuid in processed_in_this_run:
            skipped_seen += 1
            continue

        formatted_news = format_news_item(raw_news)
        if not formatted_news:
            skipped_no_format += 1
            continue

        publish_epoch = formatted_news.get("_publish_epoch")
        # Si no hay timestamp, incluir la noticia de todos modos
        if not publish_epoch or publish_epoch > twenty_four_hours_ago:
            new_and_recent.append(formatted_news)
            processed_in_this_run.add(uuid)
        else:
            skipped_old += 1

    print(f"     → Noticias filtradas:")
    print(f"        • Ya vistas: {skipped_seen}")
    print(f"        • Sin formatear: {skipped_no_format}")
    print(f"        • Muy antiguas (>24h): {skipped_old}")
    print(f"        • Nuevas y válidas: {len(new_and_recent)}")

    return new_and_recent


def build_payload(
    tickers: List[str], max_items: int, remote_path: str
) -> Dict[str, Any]:
    ensure_env_loaded()

    previous_news: List[Dict[str, Any]] = []
    bucket_name = os.environ.get("SUPABASE_BUCKET_NAME", "news")

    # Try fetching from Supabase
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")

    if supabase_url and supabase_key:
        print("Downloading existing news from Supabase...")
        try:
            supabase = create_client(supabase_url, supabase_key)
            content_bytes = supabase.storage.from_(bucket_name).download(remote_path)
            existing_data = json.loads(content_bytes)
            raw_previous_news = existing_data.get("portfolio_news", [])
            previous_news = [
                normalize_existing_news_item(item)
                for item in raw_previous_news
                if isinstance(item, dict)
            ]
            print("  -> Found previous news in Supabase.")
        except Exception:
            print(f"  -> Could not get previous news from Supabase (file may not exist yet). Starting fresh.")
            previous_news = []
    else:
        print("  -> Supabase environment variables not set. Starting fresh.")

    seen_uuids: set[str] = {
        str(news["uuid"])
        for news in previous_news
        if isinstance(news.get("uuid"), str)
    }

    # Add epoch time to previous news for sorting
    for news in previous_news:
        if news.get("published_at"):
            try:
                dt_obj = datetime.fromisoformat(
                    str(news["published_at"]).replace("Z", "+00:00")
                )
                news["_publish_epoch"] = int(dt_obj.timestamp())
            except (ValueError, TypeError):
                news["_publish_epoch"] = 0
        else:
            news["_publish_epoch"] = 0

    new_items = get_new_and_recent_news(tickers, seen_uuids)

    combined_news = new_items + previous_news

    # De-duplicate based on UUID, keeping the one from new_items if conflict
    final_news_map = {news["uuid"]: news for news in combined_news}

    sorted_news = sorted(
        final_news_map.values(),
        key=lambda x: x.get("_publish_epoch", 0),
        reverse=True,
    )

    top_news = sorted_news[:max_items]

    # Clean up internal epoch field before saving
    for news in top_news:
        news.pop("_publish_epoch", None)
        news.pop("link", None)
        news.pop("publisher", None)

    return {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "portfolio_news": top_news,
    }


def main() -> int:
    args = parse_args()
    payload = build_payload(args.tickers, args.max_news, args.output)

    with open(args.output, "w", encoding="utf-8") as json_file:
        json.dump(payload, json_file, ensure_ascii=False, indent=2)

    print(f"Archivo generado: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())