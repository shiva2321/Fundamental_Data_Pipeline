"""Summarize each 10-K/10-Q extraction reported in `real_demo.log`."""
import json
from pathlib import Path
from typing import List

LOG_PATH = Path(__file__).resolve().parent.parent / "real_demo.log"


def extract_json_blocks(text: str) -> List[str]:
    marker = "=== 10-K/10-Q Narrative Extraction ==="
    blocks = []

    for chunk in text.split(marker)[1:]:
        start = chunk.find('{')
        if start == -1:
            continue

        depth = 0
        block = []
        for char in chunk[start:]:
            block.append(char)
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    break
        blocks.append(''.join(block))

    return blocks


def parse_blocks(blocks: List[str]) -> List[dict]:
    parsed = []
    for idx, block in enumerate(blocks, start=1):
        try:
            parsed.append(json.loads(block))
        except json.JSONDecodeError as exc:
            print(f"block {idx} JSON decode error: {exc}")
    return parsed


def summarize(parsed: List[dict]) -> None:
    if not parsed:
        print("No extractions found")
        return

    for idx, payload in enumerate(parsed, start=1):
        forms = payload.get("forms_seen", {})
        reports = payload.get("reports", [])
        print(f"Extraction #{idx}: {len(reports)} reports, forms seen: {forms}")

        for report in reports:
            form = report.get("form")
            acc = report.get("accession_number")
            insights = report.get("insights", [])
            section_keys = list(report.get("sections", {}).keys())
            print(f"  • {form} {acc} sections: {section_keys} insights: {insights[:3]}")
        risk_summary = payload.get("risk_summary")
        mdna_summary = payload.get("mdna_summary")
        print(f"  Risk summary: {risk_summary}")
        print(f"  MD&A summary: {mdna_summary}")
        warnings = payload.get("warnings")
        print(f"  Warnings: {warnings}")
        print("---")


def main() -> None:
    if not LOG_PATH.exists():
        raise SystemExit(f"Log not found: {LOG_PATH}")

    text = LOG_PATH.read_text()
    blocks = extract_json_blocks(text)
    parsed = parse_blocks(blocks)
    summarize(parsed)


if __name__ == "__main__":
    main()

