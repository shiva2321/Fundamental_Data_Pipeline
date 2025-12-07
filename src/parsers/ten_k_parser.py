"""
10-K / 10-Q Parser
Extracts narrative sections such as Business, Risk Factors, MD&A, and Financial Statements for downstream analysis.
"""
import logging
import re
from typing import Dict, List, Any, Optional

from src.parsers.filing_content_parser import SECFilingContentFetcher

logger = logging.getLogger(__name__)


class TenK10QParser:
    """Parse 10-K and 10-Q filings for narrative insights."""

    SECTION_ORDER = ["1", "1A", "7", "7A", "8"]
    SECTION_TITLES = {
        "1": "Business",
        "1A": "Risk Factors",
        "7": "Management's Discussion and Analysis",
        "7A": "Market Risk",
        "8": "Financial Statements and Supplementary Data"
    }
    KEY_TERMS = ["risk", "litigation", "cyber", "regulatory", "liquidity", "macroeconomic", "revenue", "cash", "debt"]

    def __init__(self, fetcher: Optional[SECFilingContentFetcher] = None):
        self.fetcher = fetcher or SECFilingContentFetcher()

    def parse_reports(self, filings: List[Dict[str, Any]], max_reports_per_form: int = 2) -> Dict[str, Any]:
        """Parse the most recent 10-K and 10-Q filings for narrative sections."""
        annual_filings = [f for f in filings if self._is_annual_form(f.get("form"))]

        if not annual_filings:
            return {
                "total_reports": 0,
                "forms_seen": {},
                "reports": [],
                "risk_summary": {},
                "mdna_summary": {},
                "warnings": ["No 10-K/10-Q filings available"],
            }

        sorted_filings = sorted(annual_filings, key=lambda x: x.get("filingDate", ""), reverse=True)
        counts: Dict[str, int] = {}
        reports: List[Dict[str, Any]] = []
        warnings: List[str] = []

        for filing in sorted_filings:
            form_type = self._normalize_form(filing.get("form"))
            if counts.get(form_type, 0) >= max_reports_per_form:
                continue

            accession = filing.get("accessionNumber")
            cik = filing.get("cik")
            if not accession or not cik:
                warnings.append(f"Skipping {form_type} without accession or CIK: {filing}")
                continue

            content = self.fetcher.fetch_filing_content(cik, accession)
            sections = self._extract_sections(content or "")
            insights = self._extract_insights(sections)

            reports.append({
                "form": form_type,
                "filing_date": filing.get("filingDate"),
                "report_date": filing.get("reportDate"),
                "accession_number": accession,
                "available": bool(content),
                "sections": sections,
                "insights": insights
            })

            counts[form_type] = counts.get(form_type, 0) + 1

        risk_sections = [r for r in reports if r["sections"]["1A"]["summary"]["word_count"]]
        mdna_sections = [r for r in reports if r["sections"]["7"]["summary"]["word_count"]]

        risk_summary = self._aggregate_section_stats(risk_sections, "1A")
        mdna_summary = self._aggregate_section_stats(mdna_sections, "7")

        return {
            "total_reports": len(reports),
            "forms_seen": counts,
            "reports": reports,
            "risk_summary": risk_summary,
            "mdna_summary": mdna_summary,
            "warnings": warnings
        }

    def _aggregate_section_stats(self, sections: List[Dict[str, Any]], key: str) -> Dict[str, Any]:
        if not sections:
            return {"average_word_count": 0, "keyword_mentions": 0}

        total_words = sum(s["sections"][key]["summary"]["word_count"] for s in sections)
        total_mentions = sum(
            s["sections"][key]["summary"]["keyword_counts"].get("risk", 0) for s in sections
        )
        return {
            "average_word_count": round(total_words / len(sections)),
            "keyword_mentions": total_mentions,
            "sections_analyzed": len(sections)
        }

    @classmethod
    def _is_annual_form(cls, form: Optional[str]) -> bool:
        if not form:
            return False
        return form.startswith("10-K") or form.startswith("10-Q")

    @classmethod
    def _normalize_form(cls, form: Optional[str]) -> str:
        if not form:
            return "Unknown"
        if form.startswith("10-K"):
            return "10-K"
        if form.startswith("10-Q"):
            return "10-Q"
        return form

    def _extract_sections(self, content: str) -> Dict[str, Any]:
        normalized = self._normalize_content(content)
        sections: Dict[str, Any] = {}

        for idx, item in enumerate(self.SECTION_ORDER):
            next_items = self.SECTION_ORDER[idx + 1 :]
            section_text = self._extract_section(normalized, item, next_items)

            sections[item] = {
                "title": self.SECTION_TITLES.get(item, f"Item {item}"),
                "text": section_text,
                "summary": self._summarize_section(section_text)
            }

        return sections

    def _extract_section(self, content: str, item: str, next_items: List[str]) -> str:
        if not content:
            return ""

        stop_tokens = [fr"Item\s+{ni}" for ni in next_items]
        stop_pattern = "|".join(stop_tokens) if stop_tokens else r"Item\s+\d+[A-Za-z]?"
        pattern = re.compile(
            fr"Item\s+{re.escape(item)}\.?[\.\s\-]*([^\n].*?)(?={stop_pattern}|$)",
            re.IGNORECASE | re.DOTALL
        )
        match = pattern.search(content)
        return match.group(1).strip() if match else ""

    def _summarize_section(self, text: str) -> Dict[str, Any]:
        clean_text = text.strip()
        if not clean_text:
            return {
                "word_count": 0,
                "keyword_counts": {term: 0 for term in self.KEY_TERMS},
                "snippet": ""
            }

        words = re.findall(r"\w+", clean_text)
        lowers = clean_text.lower()
        keyword_counts = {term: lowers.count(term) for term in self.KEY_TERMS}

        return {
            "word_count": len(words),
            "keyword_counts": keyword_counts,
            "snippet": clean_text[:256]
        }

    def _extract_insights(self, sections: Dict[str, Any]) -> List[str]:
        insights: List[str] = []
        risk_text = sections["1A"]["text"].lower()
        mdna_text = sections["7"]["text"].lower()

        if "cyber" in risk_text:
            insights.append("Cybersecurity risk is called out in Item 1A")
        if "litigation" in risk_text or "lawsuit" in risk_text:
            insights.append("Litigation risk appears in the risk factor narrative")
        if "revenue" in mdna_text:
            insights.append("MD&A emphasizes revenue trends and outlook")
        if "cash" in mdna_text and "flow" in mdna_text:
            insights.append("MD&A discusses cash flow dynamics")

        return insights

    def _normalize_content(self, content: str) -> str:
        return re.sub(r"\r\n", "\n", content)
