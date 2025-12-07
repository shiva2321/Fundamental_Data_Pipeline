"""Fetch real 10-K/10-Q filings and run the narrative parser."""
import json
import logging
from typing import Dict, List

from src.clients.sec_edgar_api_client import SECEdgarClient
from src.parsers.ten_k_parser import TenK10QParser

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def select_form_filings(filings: List[Dict], targets: List[str]) -> List[Dict]:
    """Pick the most recent filing for each target form."""
    selected = {}
    sorted_filings = sorted(filings, key=lambda f: f.get("filingDate", ""), reverse=True)

    for filing in sorted_filings:
        form = filing.get("form", "")
        for target in targets:
            if form.startswith(target) and target not in selected:
                selected[target] = filing
                break
        if len(selected) == len(targets):
            break

    return list(selected.values())


def main() -> None:
    cik = "0000320193"  # Apple Inc.
    print("<run> Starting real 10-K/10-Q narrative extraction demo")
    print(f"Fetching filings for {cik}...")
    client = SECEdgarClient()
    logger.info(f"Fetching filings for CIK {cik}")

    filings = client.get_company_filings(cik, limit=120)
    print(f"...filings retrieved: {len(filings)}")

    forms_to_parse = ["10-K", "10-Q"]
    chosen = select_form_filings(filings, forms_to_parse)

    if not chosen:
        logger.error("No 10-K/10-Q filings detected")
        return

    parser = TenK10QParser()
    parsed = parser.parse_reports(chosen, max_reports_per_form=1)

    print("=== 10-K/10-Q Narrative Extraction ===")
    print(json.dumps(parsed, indent=2, ensure_ascii=False))


def run_demo() -> None:
    main()


if __name__ == "__main__":
    run_demo()
