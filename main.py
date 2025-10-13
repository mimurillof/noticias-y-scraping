import json
from datetime import datetime, timezone

from Script_noticias import build_payload as build_news_payload
from scrape_sentiment import get_fear_and_greed_index
from reddit_scraper import fetch_reddit_posts
from tradingview_scraper import collect_tradingview_ideas

# --- Configuration ---
# You can change these values
TICKERS = ["AAPL", "MSFT", "TSLA"]
MAX_NEWS = 3
OUTPUT_FILE = "portfolio_news.json"


def main():
    """Orchestrator to fetch news, sentiment, and Reddit posts and generate the final JSON."""
    print("Fetching market sentiment...")
    sentiment = get_fear_and_greed_index()
    if sentiment:
        print(f"  -> Sentiment found: {sentiment['value']} ({sentiment['description']})")
    else:
        print("  -> Could not fetch sentiment.")

    print("Fetching portfolio news...")
    news_payload = build_news_payload(TICKERS, MAX_NEWS, OUTPUT_FILE)
    print("  -> News processing complete.")

    print("Fetching Reddit posts...")
    reddit_posts = fetch_reddit_posts(TICKERS)
    print(f"  -> Found {len(reddit_posts)} Reddit posts.")

    print("Fetching TradingView ideas...")
    tradingview_ideas = collect_tradingview_ideas(
        max_pages=2,
        cutoff_hours=48,
        max_portfolio_items=3,
    )
    print(f"  -> Collected {len(tradingview_ideas)} TradingView ideas.")

    # Combine into the final structure
    final_payload = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "market_sentiment": sentiment,
        "portfolio_news": news_payload.get("portfolio_news", []),
        "reddit_mentions": reddit_posts,
        "tradingview_ideas": tradingview_ideas,
    }

    # Write the final JSON file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_payload, f, ensure_ascii=False, indent=2)

    print(f"\nSuccessfully generated consolidated file: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()