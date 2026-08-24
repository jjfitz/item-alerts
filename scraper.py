import feedparser
import requests
import json
import time
import os

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

SEARCH_QUERY = "a"
CRAIGSLIST_REGION = "fayar" 
CATEGORY = "sss"
MAX_ITEMS = 5 

def fetch_craigslist_items(query, region, category="sss", limit=5):
    formatted_query = query.replace(" ", "+")
    # Using the primary search URL endpoint which automatically renders RSS when format=rss is passed
    rss_url = f"https://{region}.craigslist.org/search/{category}?format=rss&query={formatted_query}"
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "max-age=0",
    })
    
    try:
        response = session.get(rss_url, timeout=10)
        print(f"Craigslist HTTP Status Code: {response.status_code}")
        
        # Parse response content
        feed = feedparser.parse(response.content)
        items = []
        
        for entry in feed.entries[:limit]:
            item = {
                "title": entry.get("title", "No Title"),
                "link": entry.get("link", ""),
                "published": entry.get("published", "Recently")
            }
            items.append(item)
            
        return items
    except Exception as e:
        print(f"Error fetching RSS: {e}")
        return []

def send_discord_webhook(webhook_url, item):
    payload = {
        "embeds": [
            {
                "title": f"🚨 New Listing: {item['title']}",
                "url": item["link"],
                "color": 3447003,
                "fields": [
                    {"name": "Published", "value": item["published"], "inline": True}
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

    print(f"Searching Craigslist ({CRAIGSLIST_REGION}) for: '{SEARCH_QUERY}'...")
    results = fetch_craigslist_items(SEARCH_QUERY, CRAIGSLIST_REGION, CATEGORY, limit=MAX_ITEMS)
    
    print(f"Found {len(results)} items.")

    for item in results:
        status = send_discord_webhook(DISCORD_WEBHOOK_URL, item)
        if status in (200, 204):
            print(f"Sent: {item['title']}")
        else:
            print(f"Failed to send ({status}): {item['title']}")
        time.sleep(1)
