import json
import os
from datetime import datetime, timezone
from pathlib import Path

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

from supabase import create_client

from Script_noticias import build_payload as build_news_payload
from scrape_sentiment import get_fear_and_greed_index
from tradingview_scraper import collect_tradingview_ideas

# --- Configuration ---
# You can change these values or override them via environment variables
TICKERS = ["AAPL", "MSFT", "TSLA"]
MAX_NEWS = 3


def build_storage_path(base_prefix: str, file_name: str) -> str:
    """Return the storage path honoring optional prefix configuration."""
    if base_prefix:
        return f"{base_prefix.rstrip('/')}/{file_name.lstrip('/')}"
    return file_name


def main():
    """Orchestrator to fetch news, sentiment, and Reddit posts and generate the final JSON."""
    ensure_env_loaded()

    supabase_bucket = os.environ.get("SUPABASE_BUCKET_NAME", "news")
    supabase_base_prefix = os.environ.get("SUPABASE_BASE_PREFIX", "")
    supabase_file_name = os.environ.get("SUPABASE_FILE_NAME", "portfolio_news.json")

    print("Fetching market sentiment...")
    sentiment = get_fear_and_greed_index()
    if sentiment:
        print(f"  -> Sentiment found: {sentiment['value']} ({sentiment['description']})")
    else:
        print("  -> Could not fetch sentiment.")

    print("Fetching portfolio news...")
    supabase_file_path = build_storage_path(supabase_base_prefix, supabase_file_name)
    news_payload = build_news_payload(TICKERS, MAX_NEWS, supabase_file_path)
    print("  -> News processing complete.")

    print("Fetching TradingView ideas...")
    tradingview_ideas = collect_tradingview_ideas(
        max_pages=2,
        cutoff_hours=48,
        max_portfolio_items=5,
    )
    print(f"  -> Collected {len(tradingview_ideas)} TradingView ideas.")

    # Combine into the final structure
    final_payload = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "market_sentiment": sentiment,
        "portfolio_news": news_payload.get("portfolio_news", []),
        "tradingview_ideas": tradingview_ideas,
    }

    # Upload to Supabase Storage
    print("\nUploading to Supabase Storage...")
    try:
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError("Supabase URL or key not found in environment variables.")

        supabase = create_client(supabase_url, supabase_key)
        
        content_bytes = json.dumps(final_payload, ensure_ascii=False, indent=2).encode("utf-8")

        # To overwrite, we first remove the old file.
        try:
            supabase.storage.from_(supabase_bucket).remove([supabase_file_path])
        except Exception:
            # Ignore if file doesn't exist
            pass

        res = supabase.storage.from_(supabase_bucket).upload(
            path=supabase_file_path,
            file=content_bytes,
            file_options={"content-type": "application/json;charset=utf-8"}
        )
        
        print(f"  -> Successfully uploaded to Supabase: {supabase_bucket}/{supabase_file_path}")

    except Exception as e:
        print(f"  -> An error occurred during Supabase upload: {e}")

    print(f"\nProcess complete.")


if __name__ == "__main__":
    main()