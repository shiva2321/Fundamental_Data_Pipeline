from pathlib import Path

text = Path('real_demo.log').read_text()
marker = '=== 10-K/10-Q Narrative Extraction ==='
print('marker occurs:', text.count(marker))
if marker in text:
    idx = text.index(marker)
    snippet = text[idx: idx + 2000]
    print(snippet)
else:
    print('marker not found')
