import os
import time
import json
import requests
from bs4 import BeautifulSoup

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# Configuration
SEARCH_QUERY = "balance bike"
AREA_CODE = "fayar"  # Northwest Arkansas / Fayetteville
MAX_ITEMS = 5

def fetch_craigslist_items(query, area, limit=5):
    formatted_query = query.replace(" ", "+")
    
    # Direct search endpoint matching Craigslist's current URL structure
    search_url = f"https://www.craigslist.org/search/area/{area}?query={formatted_query}#search=1~gallery~0~0"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    try:
        response = requests.get(search_url, headers=headers, timeout=10)
        print(f"Craigslist Search Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Failed to fetch page. Response snippet: {response.text[:200]}")
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        items = []
        
        # Craigslist injects static fallback list items inside 'ol.cl-static-search-results li'
        results = soup.select('ol.cl-static-search-results li.cl-static-search-result')
        
        # Fallback to standard anchor links if layout varies
        if not results:
            results = soup.select('li.cl-search-result')

        print(f"Total HTML listing blocks found: {len(results)}")
        
        for li in results[:limit]:
            a_tag = li.find('a')
            title_div = li.find('div', class_='title')
            price_div = li.find('div', class_='price')
            
            title = title_div.text.strip() if title_div else (a_tag.text.strip() if a_tag else "Listing")
            price = f" ({price_div.text.strip()})" if price_div else ""
            link = a_tag.get('href', '') if a_tag else ""
            
            if link:
                items.append({
                    "title": f"{title}{price}",
                    "link": link,
                    "published": "Recently"
                })
                
        return items

    except Exception as e:
        print(f"Error fetching Craigslist HTML: {e}")
        return []

def send_discord_webhook(webhook_url, item):
    payload = {
        "embeds": [
            {
                "title": f"🚨 New Listing: {item['title']}",
                "url": item["link"],
                "color": 3447003,
                "fields": [
                    {"name": "Published", "value": str(item["published"]), "inline": True}
                ],
                "footer": {"text": "GitHub Action Alert Bot"}
            }
        ]
    }
    
    response = requests.post(
        webhook_url, 
        data=json.dumps(payload), 
        headers={"Content-Type": "application/json"}
    )
    return response.status_code

if __name__ == "__main__":
    if not DISCORD_WEBHOOK_URL:
        print("Error: DISCORD_WEBHOOK_URL environment variable not found.")
        exit(1)

    print(f"Searching Craigslist area '{AREA_CODE}' for: '{SEARCH_QUERY}'...")
    results = fetch_craigslist_items(SEARCH_QUERY, AREA_CODE, limit=MAX_ITEMS)
    
    print(f"Found {len(results)} items.")

    for item in results:
        status = send_discord_webhook(DISCORD_WEBHOOK_URL, item)
        if status in (200, 204):
            print(f"Sent: {item['title']}")
        else:
            print(f"Failed to send ({status}): {item['title']}")
        time.sleep(1)
