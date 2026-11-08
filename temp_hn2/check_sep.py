import json

with open('temp_hn2/all_matches.json', 'r', encoding='utf-8') as f:
    items = json.load(f)

sep_items = [it for it in items if it['thread'] == 'sep_2026']

for i, it in enumerate(sep_items):
    print(f"[{i+1}] ID: {it['id']} | Worldwide: {it['is_worldwide']} | Jr/Mid: {it['has_junior_mid']}")
    print(f"    Header: {it['first_line']}")
