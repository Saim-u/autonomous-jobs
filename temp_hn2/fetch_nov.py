import urllib.request
import json
import time

story_id = '50338728'
all_hits = []
page = 0

while True:
    url = f"https://hn.algolia.com/api/v1/search?tags=comment,story_{story_id}&hitsPerPage=100&page={page}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            hits = data.get('hits', [])
            all_hits.extend(hits)
            nb_pages = data.get('nbPages', 0)
            nb_hits = data.get('nbHits', 0)
            print(f"Page {page}: got {len(hits)} hits, total so far {len(all_hits)} / {nb_hits}")
            if page >= nb_pages - 1 or len(hits) == 0:
                break
            page += 1
            time.sleep(0.5)
    except Exception as e:
        print(f"Error fetching page {page}: {e}")
        break

with open('temp_hn2/nov_2026.json', 'w', encoding='utf-8') as f:
    json.dump(all_hits, f, indent=2)

print(f"Saved {len(all_hits)} comments to temp_hn2/nov_2026.json")
