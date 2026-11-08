import scan_nov

for r in scan_nov.results:
    if r['geo_blocked'] and not r['is_applied']:
        print(f"{r['id']} | Matched: {r['matched_geo']} | Header: {r['first_line'][:70]}")
