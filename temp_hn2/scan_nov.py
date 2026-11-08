import json
import re

with open('temp_hn2/nov_2026.json', 'r', encoding='utf-8') as f:
    comments = json.load(f)

# Already applied companies (lowercase for checking)
applied_companies = {
    'posthog', 'evaboot', 'distru', 'memorang', 'better stack', 'betterstack',
    'sadservers', 'united risk', 'mixrank', 'serpapi', 'cyberatlas', 'trackerbot',
    'railway', 'enveritas', 'tether', 'inferra', 'cea', 'carmlize', 'openalex',
    'micro1', 'g2i', 'dataspecc', 'we are revolution', 'jawa'
}

def clean_html(text):
    text = re.sub(r'<p>', '\n\n', text)
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<a\s+href="([^"]+)"[^>]*>.*?</a>', r' \1 ', text)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&#x27;', "'", text)
    text = re.sub(r'&quot;', '"', text)
    return text.strip()

geo_disqualifiers = [
    r'\bus only\b', r'\busa only\b', r'\bu\.s\. only\b', r'\bunited states only\b',
    r'remote\s*\(\s*(us|usa|u\.s\.|united states)\s*\)',
    r'remote\s*-\s*(us|usa|u\.s\.)\b',
    r'remote\s*\(u\.s\.', r'remote\s*\(us\b', r'remote us\b',
    r'us\s*\/can\b', r'us\s*and\s*canada', r'us\s*or\s*canada',
    r'north america', r'remote \(north america',
    r'u\.s\.\s*citizenship', r'us\s*citizens?\s*only',
    r'must be (located|based|residing|living) in the (us|u\.s\.|united states)',
    r'must reside in the us', r'w-?2 only', r'us work auth',
    r'remote\s*\(\s*eu\s*\)', r'remote\s*\(\s*europe\s*\)', r'remote\s*\(\s*uk\s*\)',
    r'eu only\b', r'europe only\b', r'uk only\b',
    r'remote\s*\(latam', r'latin america only',
    r'canada\s*only\b', r'remote\s*\(canada\)',
    r'remote\s*india\b', r'bangalore,\s*india',
    r'remote\s*\(\s*germany', r'germany only',
    r'remote\s*\(\s*france', r'france only',
    r'timezone.*utc[-+]([4-8])\b' # purely US timezones with strict overlap requirement if specified
]

results = []

for c in comments:
    raw = c.get('comment_text') or c.get('text', '')
    if not raw:
        continue
    
    # Must be top-level post (parent_id == 50338728)
    if str(c.get('parent_id')) != '50338728':
        continue
        
    text = clean_html(raw)
    first_line = text.split('\n')[0].strip()
    text_l = text.lower()
    first_l = first_line.lower()
    
    # Check if applied
    is_applied = False
    for comp in applied_companies:
        if comp in first_l:
            is_applied = True
            break
            
    if 'remote' not in text_l:
        continue
        
    # Check geo blocks
    geo_blocked = False
    matched_geo = None
    for pat in geo_disqualifiers:
        m = re.search(pat, text_l)
        if m:
            geo_blocked = True
            matched_geo = m.group(0)
            break
            
    # Check role
    tech_keywords = ['engineer', 'developer', 'fullstack', 'full-stack', 'backend', 'frontend', 'software', 'python', 'react', 'typescript', 'web']
    has_tech = any(kw in text_l for kw in tech_keywords)
    
    # Check seniority - is it ONLY senior?
    senior_only = False
    # If the first line says Senior/Staff/Lead/Principal and has no mid/junior/etc.
    if re.search(r'\b(senior|staff|lead|principal|director|head of|vp)\b', first_l):
        # check if it also mentions junior or mid or generalist or intern
        if not re.search(r'\b(junior|mid|intern|associate|entry|generalist)\b', text_l):
            senior_only = True
            
    results.append({
        'id': c.get('objectID'),
        'first_line': first_line,
        'is_applied': is_applied,
        'geo_blocked': geo_blocked,
        'matched_geo': matched_geo,
        'senior_only': senior_only,
        'has_tech': has_tech,
        'text': text
    })

print(f"Total top-level postings with 'remote': {len(results)}")
qualifying = [r for r in results if not r['is_applied'] and not r['geo_blocked'] and not r['senior_only'] and r['has_tech']]
print(f"Potential qualifying postings: {len(qualifying)}")

with open('temp_hn2/nov_candidates.json', 'w', encoding='utf-8') as f:
    json.dump(qualifying, f, indent=2)

for q in qualifying:
    print(f"\nID: {q['id']} - https://news.ycombinator.com/item?id={q['id']}")
    print(f"Header: {q['first_line']}")
