import json
import re

with open('temp_hn2/nov_2026.json', 'r', encoding='utf-8') as f:
    comments = json.load(f)

applied_companies = {
    'posthog', 'evaboot', 'distru', 'memorang', 'better stack', 'betterstack',
    'sadservers', 'united risk', 'mixrank', 'serpapi', 'cyberatlas', 'trackerbot',
    'railway', 'enveritas', 'tether', 'inferra', 'cea', 'carmlize', 'openalex',
    'micro1', 'g2i', 'dataspecc', 'we are revolution', 'jawa'
}

for c in comments:
    if str(c.get('parent_id')) != '50338728':
        continue
    raw = c.get('text') or c.get('comment_text', '')
    raw_l = raw.lower()
    
    # Check if applied
    if any(comp in raw_l[:150] for comp in applied_companies):
        continue
        
    is_worldwide = any(term in raw_l for term in [
        'worldwide', 'anywhere', 'global remote', 'remote (world)', 'remote (any', 
        'remote (global)', 'all locations', 'remote worldwide', 'work from anywhere'
    ])
    
    first_line = raw.split('<p>')[0].split('\n')[0]
    first_line = re.sub(r'<[^>]+>', ' ', first_line).strip()
    
    if is_worldwide:
        print(f"ID: {c.get('objectID')} | {first_line[:90]}")
