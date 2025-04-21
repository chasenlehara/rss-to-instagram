#!/usr/bin/env python3
import os, json, xml.etree.ElementTree as ET
from urllib.request import urlopen, Request
from urllib.parse import urlencode

# Config from environment
FEED_URL      = os.environ.get('RSS_URL', 'https://me.chasen.dev/feed.xml')
IG_USER_ID    = os.environ['IG_USER_ID']
ACCESS_TOKEN  = os.environ['IG_ACCESS_TOKEN']
STATE_FILE    = 'posted.json'

# Load state
try:
    with open(STATE_FILE) as f:
        posted = set(json.load(f))
except FileNotFoundError:
    posted = set()

# Fetch and parse RSS
req = Request(FEED_URL, headers={'User-Agent': 'github-action'})
data = urlopen(req).read()
root = ET.fromstring(data)
items = root.find('channel').findall('item')

new_posted = set(posted)
for item in items:
    guid = item.find('guid').text.strip()
    if guid in posted:
        continue
    desc = item.find('description').text or ''
    # Find all <img> tags
    parts = desc.split('<img')
    for part in parts[1:]:
        # pick src and alt via simple splits
        src = part.split('src="')[1].split('"')[0]
        alt = part.split('alt="')[1].split('"')[0]
        caption = alt
        # 1) create media container
        params = {
            'image_url': src,
            'caption': caption,
            'access_token': ACCESS_TOKEN
        }
        url = f"https://graph.facebook.com/v17.0/{IG_USER_ID}/media"
        try:
            resp = urlopen(Request(url, data=urlencode(params).encode()))
            result = json.load(resp)
        except Exception as e:
            # debug: print Graph API’s JSON error
            import sys, traceback
            print("Error calling", url, "with params:", params, file=sys.stderr)
            if hasattr(e, 'read'):
                print("Response body:", e.read().decode(), file=sys.stderr)
            traceback.print_exc()
            raise
        creation_id = result['id']

        # 2) publish
        pub_url = f"https://graph.facebook.com/v17.0/{IG_USER_ID}/media_publish"
        pub_params = {'creation_id': creation_id, 'access_token': ACCESS_TOKEN}
        urlopen(Request(pub_url, data=urlencode(pub_params).encode()))

    new_posted.add(guid)

# Save updated state
with open(STATE_FILE, 'w') as f:
    json.dump(list(new_posted), f)
