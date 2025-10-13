#!/usr/bin/env python3
"""
Descarga noticias con miniaturas para un portafolio de tickers usando yfinance.
Guarda un JSON con máximo tres notas por activo.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

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
    try:
        # Value can be int, float, or string representations of them
        return int(float(time_val))
    except (ValueError, TypeError):
        return None


def format_news_item(news: Dict[str, Any]) -> Dict[str, Any] | None:
    """Formats a raw news item dictionary."""
    uuid = news.get("uuid") or news.get("id")
    if not uuid:
        return None

    content = news.get("content")
    if not isinstance(content, dict):
        content = {}

    thumbnail_url = None
    thumbnail_payload = news.get("thumbnail") or content.get("thumbnail")
    if thumbnail_payload:
        thumbnail_url = pick_thumbnail_url(thumbnail_payload)

    link = news.get("link") or content.get("link")
    if isinstance(link, dict):
        link = link.get("url")
    if not link:
        link = (
            news.get("url") or content.get("url") or content.get("clickThroughUrl")
        )

    publish_epoch = get_publish_epoch(news)

    return {
        "uuid": uuid,
        "title": news.get("title") or content.get("title"),
        "publisher": (
            news.get("publisher")
            or news.get("source")
            or content.get("publisher")
        ),
        "link": link,
        "published_at": format_publish_time(publish_epoch)
        if publish_epoch
        else None,
        "image_url": thumbnail_url,
        "type": (
            news.get("type") or content.get("contentType") or content.get("type")
        ),
        "_publish_epoch": publish_epoch,  # Internal field for sorting
    }


def get_new_and_recent_news(
    tickers: List[str], seen_uuids: set[str]
) -> List[Dict[str, Any]]:
    """Fetches, filters for new and recent, and formats news."""
    news_by_ticker: Dict[str, List[Dict[str, Any]]] = {}
    for ticker in tickers:
        ticker_obj = yf.Ticker(ticker)
        news_items = ticker_obj.news or []
        if isinstance(news_items, list):
            news_by_ticker[ticker] = news_items

    interleaved_news: List[Dict[str, Any]] = []
    max_depth = max((len(v) for v in news_by_ticker.values()), default=0)
    for i in range(max_depth):
        for ticker in tickers:
            if i < len(news_by_ticker.get(ticker, [])):
                interleaved_news.append(news_by_ticker[ticker][i])

    # Process and filter
    new_and_recent: List[Dict[str, Any]] = []
    thirty_minutes_ago = int(datetime.now(tz=timezone.utc).timestamp()) - (30 * 60)

    processed_in_this_run = set()

    for raw_news in interleaved_news:
        uuid = raw_news.get("uuid") or raw_news.get("id")
        if not uuid or uuid in seen_uuids or uuid in processed_in_this_run:
            continue

        formatted_news = format_news_item(raw_news)
        if not formatted_news:
            continue

        publish_epoch = formatted_news.get("_publish_epoch")
        if publish_epoch and publish_epoch > thirty_minutes_ago:
            new_and_recent.append(formatted_news)
            processed_in_this_run.add(uuid)

    return new_and_recent


def build_payload(
    tickers: List[str], max_items: int, output_file: str
) -> Dict[str, Any]:
    try:
        with open(output_file, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
            previous_news = existing_data.get("portfolio_news", [])
    except (FileNotFoundError, json.JSONDecodeError):
        previous_news = []

    seen_uuids = {news.get("uuid") for news in previous_news}

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