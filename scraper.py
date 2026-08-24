import os
import time
import json
import requests

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# Configuration
SEARCH_QUERY = "balance bike"
AREA_CODE = "fayar" # Fayetteville / NWA area code from your URL
MAX_ITEMS = 5

def fetch_craigslist_items(query, area, limit=5):
    # Craigslist's modern direct JSON API endpoint
    api_url = f"https://www.craigslist.org/async/search/items"
    
    params = {
        "area": area,
        "query": query,
        "sort": "date"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    try:
        response = requests.get(api_url, params=params, headers=headers, timeout=10)
        print(f"API Response Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Failed request. Response text: {response.text[:200]}")
            return []
            
        data = response.json()
        
        # Extract items list from the JSON payload
        items_data = data.get("items", [])
        print(f"Total raw items returned from API: {len(items_data)}")
        
        items = []
        for item in items_data[:limit]:
            posting_id = item.get("postingId")
            title = item.get("title", "No Title")
            price = f"${item.get('price', 0)}" if "price" in item else "No Price"
            
            # Construct direct link to the listing
            link = f"https://{area}.craigslist.org/d/item/{posting_id}.html" if posting_id else "https://craigslist.org"
            
            items.append({
                "title": f"{title} - {price}",
                "link": link,
                "published": item.get("postedDate", "Recently")
            })
            
        return items

    except Exception as e:
        print(f"Error fetching from Craigslist API: {e}")
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
