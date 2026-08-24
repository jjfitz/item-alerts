import feedparser
import requests
import json
import time
import os

# Grab the Discord Webhook from repository environment secrets
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

SEARCH_QUERY = "balance bike"
CRAIGSLIST_REGION = "fayetteville"
CATEGORY = "sss"
MAX_ITEMS = 5 

def fetch_craigslist_items(query, region, category="sss", limit=5):
    formatted_query = query.replace(" ", "+")
    rss_url = f"https://{region}.craigslist.org/search/{category}?query={formatted_query}&format=rss"
    
    feed = feedparser.parse(rss_url)
    items = []
    
    for entry in feed.entries[:limit]:
        item = {
            "title": entry.get("title", "No Title"),
            "link": entry.get("link", ""),
            "published": entry.get("published", "Recently")
        }
        items.append(item)
        
    return items

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

    for item in results:
        status = send_discord_webhook(DISCORD_WEBHOOK_URL, item)
        if status in (200, 204):
            print(f"Sent: {item['title']}")
        time.sleep(1)
