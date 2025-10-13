import requests
import json
from datetime import datetime, timezone

url = "https://www.tradingview.com/ideas/stream/"
params = {"symbol": "NASDAQ:AAPL", "sort": "recent"}
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://www.tradingview.com/symbols/NASDAQ-AAPL/ideas/",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/plain, */*",
}
response = requests.get(url, params=params, headers=headers, timeout=15)
print("status", response.status_code)
data = response.json()

print(data.keys())
print(data["data"].keys())
ideas_container = data["data"]["ideas"]
print(ideas_container.keys())
print("params", ideas_container["params"])
print("context", data.get("context"))
ideas_data = ideas_container["data"]
print("ideas_data keys", ideas_data.keys())
print("next", ideas_data.get("next"))
ideas = ideas_data["items"]
print(len(ideas))
first = ideas[0]
print(first.keys())
print(first.get("title"))
print(first.get("name"))
print(first.get("user"))
print(first.get("symbol"))
print(first.get("reputation"))
print(first.get("actions"))

for key in ["label", "rating", "direction", "likes_count"]:
    print(key, first.get(key))

ts = first.get("date_timestamp")
print("ts", ts, datetime.fromtimestamp(ts, tz=timezone.utc) if ts else None)
