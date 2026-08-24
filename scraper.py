import os
import time
import json
import requests
from craigslist import CraigslistForSale

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# Configuration
SEARCH_QUERY = "balance bike"
CRAIGSLIST_SITE = "fayar"  # Northwest Arkansas / Fayetteville
MAX_ITEMS = 5

def fetch_craigslist_items(query, site, limit=5):
    try:
        # Initialize Craigslist search wrapper
        cl = CraigslistForSale(
            site=site,
            category='sss', # All For Sale
            filters={'query': query}
        )
        
        items = []
        # Query results sorted by newest
        for result in cl.get_results(sort_by='newest', limit=limit):
            items.append({
                "title": f"{result.get('name', 'No Title')} - {result.get('price', 'No Price')}",
                "link": result.get('url', ''),
                "published": result.get('datetime', 'Recently')
            })
            
        return items
    except Exception as e:
        print(f"Error fetching Craigslist items: {e}")
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

    print(f"Searching Craigslist ({CRAIGSLIST_SITE}) for: '{SEARCH_QUERY}'...")
    results = fetch_craigslist_items(SEARCH_QUERY, CRAIGSLIST_SITE, limit=MAX_ITEMS)
    
    print(f"Found {len(results)} items.")

    for item in results:
        status = send_discord_webhook(DISCORD_WEBHOOK_URL, item)
        if status in (200, 204):
            print(f"Sent: {item['title']}")
        else:
            print(f"Failed to send ({status}): {item['title']}")
        time.sleep(1)
