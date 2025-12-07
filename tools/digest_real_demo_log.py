from pathlib import Path
import json
import itertools

LOG_PATH = Path('real_demo.log')
OUT_PATH = Path('real_demo_summary.txt')

text = LOG_PATH.read_text()
marker = '=== 10-K/10-Q Narrative Extraction ==='
pos = 0
blocks = []

while True:
    idx = text.find(marker, pos)
    if idx == -1:
        break
    idx += len(marker)
    brace_start = text.find('{', idx)
    if brace_start == -1:
        break
    depth = 0
    block_chars = []
    for c in text[brace_start:]:
        block_chars.append(c)
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                break
    block = ''.join(block_chars)
    blocks.append(block)
    pos = brace_start + len(block)

records = []
for block in blocks:
    try:
        records.append(json.loads(block))
    except json.JSONDecodeError:
        continue

lines = []
if not records:
    lines.append('no extractions found')
else:
    for i, rec in enumerate(records, 1):
        lines.append(f'extraction #{i}: forms={rec.get('forms_seen')} reports={len(rec.get('reports', []))}')
        for rpt in rec.get('reports', []):
            sections = sorted(rpt.get('sections', {}).keys())
            insights = rpt.get('insights', [])
            lines.append(f"  {rpt.get('form')} {rpt.get('accession_number')} sections={sections} insights={insights[:3]}")
        lines.append(f"  risk_summary={rec.get('risk_summary')}")
        lines.append(f"  mdna_summary={rec.get('mdna_summary')}")
        lines.append(f"  warnings={rec.get('warnings')}")
        lines.append('---')

OUT_PATH.write_text('\n'.join(lines))
