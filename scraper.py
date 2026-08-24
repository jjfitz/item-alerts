import os
import time
import json
import requests
from bs4 import BeautifulSoup

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# 1. CONFIGURE YOUR SEARCH TARGETS & MAX PRICES HERE
# Set max_price to None if you don't want a price limit on that specific item.
SEARCH_TARGETS = [
    {"query": "balance bike", "max_price": 20},
    {"query": "TB", "max_price": 500},
    {"query": "computer", "max_price": 200},
    {"query": "laptop", "max_price": 200},
]


# Set to True to fetch EVERYTHING posted to the general Free Stuff category
INCLUDE_ALL_FREE_STUFF = True
MAX_FREE_ITEMS = 10  # Max free items to check per run

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


def parse_price(price_str):
    """Parses '$45' or 'free' into an integer price value."""
    if not price_str:
        return None
    cleaned = price_str.lower().replace("$", "").replace(",", "").strip()
    if cleaned in ("free", "0"):
        return 0
    try:
        return int(float(cleaned))
    except ValueError:
        return None


def fetch_craigslist_items(query=None, area="fayar", max_price=None, category=None, limit=5):
    """Fetches items either by search query or by category (e.g., category='zip' for Free)."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    # Build URL based on whether we're searching keywords or grabbing category listings
    if category:
        search_url = f"https://www.craigslist.org/search/area/{area}?cat={category}#search=1~gallery~0~0"
    else:
        formatted_query = query.replace(" ", "+") if query else ""
        search_url = f"https://www.craigslist.org/search/area/{area}?query={formatted_query}"
        if max_price is not None:
            search_url += f"&max_price={max_price}"
        search_url += "#search=1~gallery~0~0"
    
    try:
        response = requests.get(search_url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"Failed fetch (Status: {response.status_code})")
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
            
            raw_title = title_div.text.strip() if title_div else (a_tag.text.strip() if a_tag else "Listing")
            price_text = price_div.text.strip() if price_div else ""
            numeric_price = parse_price(price_text)
            
            # Python-side price filter for keyword searches
            if category is None and max_price is not None and numeric_price is not None and numeric_price > max_price:
                continue

            display_price = f" ({price_text})" if price_text else " (FREE)"
            link = a_tag.get('href', '') if a_tag else ""
            
            if link:
                items.append({
                    "title": f"{raw_title}{display_price}",
                    "link": link,
                    "query": query if query else "Free Stuff Category",
                    "price_val": numeric_price,
                    "is_free": category == "zip" or numeric_price == 0,
                    "published": "Recently"
                })
                
        return items
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []


def send_discord_webhook(webhook_url, item):
    # Gold border for free items, Blue for normal matches
    embed_color = 15844367 if item["is_free"] else 3447003
    header_tag = "🎁 FREE LISTING" if item["is_free"] else "🚨 New Listing"
    
    payload = {
        "embeds": [
            {
                "title": f"{header_tag}: {item['title']}",
                "url": item["link"],
                "color": embed_color,
                "fields": [
                    {"name": "Source / Query", "value": item["query"], "inline": True},
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

    # 1. RUN TARGETED KEYWORD SEARCHES
    for target in SEARCH_TARGETS:
        query = target["query"]
        max_price = target.get("max_price")
        
        price_str = f"under ${max_price}" if max_price is not None else "no price limit"
        print(f"\n--- Searching for: '{query}' ({price_str}) ---")
        
        results = fetch_craigslist_items(query=query, area=AREA_CODE, max_price=max_price, limit=MAX_ITEMS_PER_QUERY)
        
        for item in results:
            link = item["link"]
            if link in seen_items:
                print(f"Skipping (Already Seen): {item['title']}")
                continue
                
            status = send_discord_webhook(DISCORD_WEBHOOK_URL, item)
            if status in (200, 204):
                print(f"Sent: {item['title']}")
                seen_items.add(link)
                new_alerts_count += 1
            else:
                print(f"Failed to send ({status}): {item['title']}")
            
            time.sleep(1)

    # 2. RUN GENERAL FREE STUFF CATEGORY SCAN (NO KEYWORDS)
    if INCLUDE_ALL_FREE_STUFF:
        print(f"\n--- Checking general FREE STUFF section (cat=zip) ---")
        free_results = fetch_craigslist_items(area=AREA_CODE, category="zip", limit=MAX_FREE_ITEMS)
        
        for item in free_results:
            link = item["link"]
            if link in seen_items:
                continue
                
            status = send_discord_webhook(DISCORD_WEBHOOK_URL, item)
            if status in (200, 204):
                print(f"Sent Free Alert: {item['title']}")
                seen_items.add(link)
                new_alerts_count += 1
            
            time.sleep(1)

    # Save state back to JSON file
    save_seen_listings(seen_items)
    print(f"\nDone! Sent {new_alerts_count} new alerts.")
