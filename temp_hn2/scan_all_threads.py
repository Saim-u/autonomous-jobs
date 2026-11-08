import json
import re

threads = ['oct_2026', 'sep_2026', 'aug_2026']

all_comments = []
for t in threads:
    with open(f'temp_hn2/{t}.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        for c in data:
            c['thread'] = t
            all_comments.append(c)

print(f"Total comments across 3 months: {len(all_comments)}")

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

candidates = []

for c in all_comments:
    raw = c.get('text', '')
    if not raw:
        continue
    text = clean_html(raw)
    text_l = text.lower()
    first_line = text.split('\n')[0].strip()
    first_l = first_line.lower()
    
    if 'remote' not in text_l:
        continue
        
    # Check geo restrictions
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
    ]
    
    has_geo_block = any(re.search(pat, text_l) for pat in geo_disqualifiers)
    
    # Check if explicitly worldwide / global / anywhere
    worldwide_pat = r'\b(worldwide|world-wide|global|anywhere|any location|work from anywhere|remote \(any\)|remote \(worldwide\)|remote \(global\)|all-remote|fully remote worldwide|remote globally)\b'
    is_worldwide = bool(re.search(worldwide_pat, text_l) or re.search(worldwide_pat, first_l))
    
    # If blocked by geo and NOT explicitly saying worldwide
    if has_geo_block and not is_worldwide:
        continue
        
    # Check role: backend, frontend, fullstack, intern, web dev, software engineer
    role_pat = r'\b(backend|back-end|back end|frontend|front-end|front end|fullstack|full-stack|full stack|web developer|intern|internship|interns)\b'
    has_role = bool(re.search(role_pat, text_l))
    
    # Check if generic software engineer with web/backend/frontend technologies
    has_tech = bool(re.search(r'\b(python|react|typescript|javascript|node\.js|fastapi|django|ruby|rails|postgres|go|golang|rust|html|css)\b', text_l))
    has_swe = bool(re.search(r'\b(software engineer|software developer|product engineer)\b', text_l))
    
    if not (has_role or (has_swe and has_tech)):
        continue
        
    # Check level: Is it strictly senior/staff/principal/lead only?
    # If the only titles are Senior / Staff / Principal / Lead / Director / VP
    # and no mention of junior / mid / intern / all levels
    has_junior_mid = bool(re.search(r'\b(junior|jr|mid-level|mid level|entry-level|entry level|intern|internship|associate|all levels)\b', text_l))
    
    # Check if header explicitly says senior / staff / principal / lead only
    header_is_senior = any(s in first_l for s in ['senior', 'sr.', 'staff', 'principal', 'lead', 'head of', 'director', 'vp'])
    
    if header_is_senior and not has_junior_mid:
        # Check if multiple roles exist and one is not senior
        sub_roles = [line for line in text.split('\n')[:10] if any(w in line.lower() for w in ['engineer', 'developer', 'intern'])]
        non_senior_found = False
        for sr in sub_roles:
            sr_l = sr.lower()
            if not any(s in sr_l for s in ['senior', 'sr.', 'staff', 'principal', 'lead', 'head', 'director', 'manager']):
                non_senior_found = True
                break
        if not non_senior_found:
            continue
            
    candidates.append({
        'id': c['id'],
        'thread': c['thread'],
        'author': c.get('by'),
        'first_line': first_line,
        'is_worldwide': is_worldwide,
        'has_junior_mid': has_junior_mid,
        'text': text
    })

print(f"Total matching candidates found: {len(candidates)}")

with open('temp_hn2/all_matches.json', 'w', encoding='utf-8') as f:
    json.dump(candidates, f, indent=2)

for i, c in enumerate(candidates):
    print(f"[{i+1}] {c['thread']} | ID: {c['id']} | Worldwide: {c['is_worldwide']} | Jr/Mid: {c['has_junior_mid']}")
    print(f"    {c['first_line'][:120]}")
