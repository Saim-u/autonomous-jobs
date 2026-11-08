import json

with open('temp_hn2/all_matches.json', 'r', encoding='utf-8') as f:
    items = {it['id']: it for it in json.load(f)}

inspect_ids = [
    49159028, # MixRank
    49523704, # CyberAtlas
    49523422, # Proxybase
    49529763, # Pagelove
    49524920, # OpenAlex
    49165651, # Democrance
    49525497, # Inferra (internship!)
    49522912, # Quill
    49527374, # Jawa.gg
    49227265, # Dave Evans
    49166151, # Senior Python Backend (EMEA/APAC)
    49160915, # Railway
]

with open('temp_hn2/inspect_deep.txt', 'w', encoding='utf-8') as out:
    for cid in inspect_ids:
        if cid in items:
            it = items[cid]
            out.write(f"=== ID: {cid} | Thread: {it['thread']} ===\n")
            out.write(f"Header: {it['first_line']}\n")
            out.write(it['text'] + "\n\n" + "="*70 + "\n\n")

print("Written to temp_hn2/inspect_deep.txt")
