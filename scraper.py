import os
import time
import json
import requests
from bs4 import BeautifulSoup

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# 1. ADD YOUR SEARCH ITEMS HERE
SEARCH_QUERIES = [
    "balance bike",
    "TB",
    "computer",
    "laptop"
]

AREA_CODE = "fayar"  # Northwest Arkansas / Fayetteville
MAX_ITEMS_PER_QUERY = 5
SEEN_FILE = "seen_listings.json"


def load_seen_listings():
    """Loads previously alerted listing URLs/IDs from JSON."""
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r") as f:
                return set(json.load(f))
        except Exception as e:
            print(f"Error loading seen listings file: {e}")
    return set()


def save_seen_listings(seen_set):
    """Saves updated seen listing IDs back to JSON."""
    try:
        with open(SEEN_FILE, "w") as f:
            json.dump(list(seen_set), f, indent=2)
        print(f"Saved {len(seen_set)} total items to {SEEN_FILE}")
    except Exception as e:
        print(f"Error saving seen listings file: {e}")


def fetch_craigslist_items(query, area, limit=5):
    formatted_query = query.replace(" ", "+")
    search_url = f"https://www.craigslist.org/search/area/{area}?query={formatted_query}#search=1~gallery~0~0"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    try:
        response = requests.get(search_url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"Failed query '{query}' (Status: {response.status_code})")
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        results = soup.select('ol.cl-static-search-results li.cl-static-search-result')
        if not results:
            results = soup.select('li.cl-search-result')

        items = []
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
                    "query": query,
                    "published": "Recently"
                })
                
        return items
    except Exception as e:
        print(f"Error fetching '{query}': {e}")
        return []


def send_discord_webhook(webhook_url, item):
    payload = {
        "embeds": [
            {
                "title": f"🚨 New Listing: {item['title']}",
                "url": item["link"],
                "color": 3447003,
                "fields": [
                    {"name": "Search Query", "value": item["query"], "inline": True},
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

    seen_items = load_seen_listings()
    print(f"Loaded {len(seen_items)} previously seen listings.")
    
    new_alerts_count = 0

    for query in SEARCH_QUERIES:
        print(f"\n--- Searching for: '{query}' ---")
        results = fetch_craigslist_items(query, AREA_CODE, limit=MAX_ITEMS_PER_QUERY)
        
        for item in results:
            link = item["link"]
            
            # Check if we've already sent this link
            if link in seen_items:
                print(f"Skipping (Already Seen): {item['title']}")
                continue
                
            # Send alert to Discord
            status = send_discord_webhook(DISCORD_WEBHOOK_URL, item)
            if status in (200, 204):
                print(f"Sent: {item['title']}")
                seen_items.add(link)
                new_alerts_count += 1
            else:
                print(f"Failed to send ({status}): {item['title']}")
            
            time.sleep(1)

    # Save updated list back to disk
    save_seen_listings(seen_items)
    print(f"\nDone! Sent {new_alerts_count} new alerts.")
