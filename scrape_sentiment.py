import requests
import json
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional

def get_rating_from_score(score: int) -> str:
    """
    Determines the rating based on the Fear & Greed Index score.
    """
    if score <= 25:
        return "Extreme Fear"
    elif score <= 45:
        return "Fear"
    elif score <= 54:
        return "Neutral"
    elif score <= 74:
        return "Greed"
    else:
        return "Extreme Greed"

def get_fear_and_greed_index() -> Optional[Dict[str, Any]]:
    """
    Scrapes the Fear & Greed Index from feargreedmeter.com by finding the JSON data in a script tag.
    """
    url = "https://feargreedmeter.com/"
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching URL for sentiment: {e}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')

    try:
        script_tag = soup.find("script", id="__NEXT_DATA__")
        if not script_tag:
            return None

        data = json.loads(script_tag.string)
        
        # Navigate through the JSON structure to find the fear and greed data
        score = data["props"]["pageProps"]["data"]["fgi"]["latest"]["now"]
        
        if score is not None:
            rating = get_rating_from_score(score)
            return {"value": int(score), "description": rating.title()}
            
    except (json.JSONDecodeError, AttributeError, ValueError, TypeError, KeyError):
        # This will catch errors if the script tag is not found, is not valid JSON,
        # or if the nested data structure changes.
        return None
        
    return None

if __name__ == '__main__':
    sentiment = get_fear_and_greed_index()
    if sentiment:
        print(f"Fear & Greed Index: {sentiment['value']} ({sentiment['description']})")
    else:
        print("Could not retrieve the Fear & Greed Index.")