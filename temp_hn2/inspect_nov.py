import json

with open('temp_hn2/nov_candidates.json', 'r', encoding='utf-8') as f:
    candidates = json.load(f)

check_ids = {'50357754', '50356058', '50353951', '50350077', '50349615', '50344773', '50343048', '50342723', '50341745', '50340434', '50339750', '50339735', '50338732'}

with open('temp_hn2/inspect_output.txt', 'w', encoding='utf-8') as out:
    for c in candidates:
        if c['id'] in check_ids:
            out.write("="*60 + "\n")
            out.write(f"ID: {c['id']}\n")
            out.write(f"Header: {c['first_line']}\n")
            out.write("="*60 + "\n")
            out.write(c['text'] + "\n\n")

