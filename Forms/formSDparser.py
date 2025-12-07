"""
SEC Form SD Parser
==================
Parser for SEC Form SD - Specialized Disclosure Report

Form SD is used for specialized disclosures including:
- Conflict minerals disclosure (Rule 13p-1)
- Resource extraction issuer disclosure (Rule 13q-1)
- Mine safety disclosure

Author: SEC Filing Analysis System
Date: December 2025
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from Forms.baseParser import SECFormParser


class FormSDParser(SECFormParser):
    """Parser for SEC Form SD - Specialized Disclosure Report"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """
        Parse Form SD document

        Args:
            document_text: Raw SEC document text

        Returns:
            Dictionary containing parsed form data
        """
        result = {
            "form_type": "Form SD - Specialized Disclosure Report",
            "filing_info": self._parse_header(document_text),
            "rule": self._parse_rule(document_text),
            "reporting_period": self._parse_reporting_period(document_text),
            "conflict_minerals_disclosure": {},
            "resource_extraction_disclosure": {},
            "exhibits": []
        }

        # Parse HTML content for specific disclosures
        result["conflict_minerals_disclosure"] = self._parse_conflict_minerals(document_text)
        result["resource_extraction_disclosure"] = self._parse_resource_extraction(document_text)
        result["exhibits"] = self._parse_exhibits(document_text)

        return result

    def _parse_header(self, document_text: str) -> Dict[str, str]:
        """Parse SEC document header information"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}

        header = header_match.group(1)

        return {
            "accession_number": self._extract_field(header, r'ACCESSION NUMBER:\s*(\S+)'),
            "submission_type": self._extract_field(header, r'CONFORMED SUBMISSION TYPE:\s*(\S+)'),
            "public_document_count": self._extract_field(header, r'PUBLIC DOCUMENT COUNT:\s*(\d+)'),
            "filed_as_of_date": self.format_date(
                self._extract_field(header, r'FILED AS OF DATE:\s*(\d+)')
            ),
            "date_as_of_change": self.format_date(
                self._extract_field(header, r'DATE AS OF CHANGE:\s*(\d+)')
            ),
            "company_name": self._extract_field(header, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)'),
            "ein": self._extract_field(header, r'EIN:\s*(\d+)'),
            "state_of_incorporation": self._extract_field(header, r'STATE OF INCORPORATION:\s*(\w+)'),
            "fiscal_year_end": self._extract_field(header, r'FISCAL YEAR END:\s*(\d+)')
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        """Extract field using regex pattern"""
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""

    def _parse_rule(self, document_text: str) -> Dict[str, str]:
        """Parse the rule being reported under"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}

        header = header_match.group(1)
        
        rule_match = re.search(r'<RULE-NAME>(.+)', header)
        item_match = re.search(r'<ITEM-NUMBER>(.+)', header)
        period_match = re.search(r'<ITEM-PERIOD>(.+)', header)

        return {
            "rule_name": rule_match.group(1).strip() if rule_match else "",
            "item_number": item_match.group(1).strip() if item_match else "",
            "item_period": self.format_date(period_match.group(1).strip()) if period_match else ""
        }

    def _parse_reporting_period(self, document_text: str) -> Dict[str, str]:
        """Parse reporting period from HTML content"""
        # Look for Rule 13p-1 period
        period_match = re.search(
            r'Rule 13p-1.*?from\s+(\w+ \d+).*?to\s+(\w+ \d+,\s*\d{4})',
            document_text,
            re.IGNORECASE | re.DOTALL
        )
        
        if period_match:
            return {
                "start_date": period_match.group(1),
                "end_date": period_match.group(2)
            }

        # Look for fiscal year ended
        fiscal_match = re.search(
            r'fiscal year ended\s+(.+?)(?:\.|<)',
            document_text,
            re.IGNORECASE
        )
        
        if fiscal_match:
            return {
                "fiscal_year_ended": fiscal_match.group(1).strip()
            }

        return {}

    def _parse_conflict_minerals(self, document_text: str) -> Dict[str, Any]:
        """Parse conflict minerals disclosure section"""
        # Look for Section 1 - Conflict Minerals Disclosure
        section_match = re.search(
            r'Section 1.*?Conflict Minerals Disclosure(.*?)(?:Section \d+|<div class="BRPFPageBreak|$)',
            document_text,
            re.DOTALL | re.IGNORECASE
        )

        if not section_match:
            return {"applicable": False}

        section_text = section_match.group(1)

        # Check if conflict minerals report is filed
        report_match = re.search(
            r'Conflict Minerals Report.*?(?:is provided as )?Exhibit\s+(\d+\.\d+)|'
            r'publicly available at\s+(.+?)(?:\*|<|\n)',
            section_text,
            re.IGNORECASE | re.DOTALL
        )

        result = {
            "applicable": True,
            "items_disclosed": []
        }

        if report_match:
            result["exhibit_number"] = report_match.group(1) if report_match.group(1) else ""
            result["url"] = report_match.group(2).strip() if report_match.group(2) else ""

        # Extract item numbers mentioned
        item_matches = re.findall(r'Item[s]?\s+([\d.]+(?:\s+(?:and|&)\s+[\d.]+)?)', section_text, re.IGNORECASE)
        if item_matches:
            result["items_disclosed"] = item_matches

        return result

    def _parse_resource_extraction(self, document_text: str) -> Dict[str, Any]:
        """Parse resource extraction issuer disclosure section"""
        # Look for Section 2 - Resource Extraction Issuer Disclosure
        section_match = re.search(
            r'Section 2.*?Resource Extraction(.*?)(?:Section \d+|<div class="BRPFPageBreak|$)',
            document_text,
            re.DOTALL | re.IGNORECASE
        )

        if not section_match:
            return {"applicable": False}

        section_text = section_match.group(1)

        # Check if applicable
        not_applicable = re.search(r'Not applicable', section_text, re.IGNORECASE)
        
        result = {
            "applicable": not not_applicable
        }

        if not not_applicable:
            # Parse any exhibit references
            exhibit_match = re.search(r'Exhibit\s+(\d+\.\d+)', section_text, re.IGNORECASE)
            if exhibit_match:
                result["exhibit_number"] = exhibit_match.group(1)

        return result

    def _parse_exhibits(self, document_text: str) -> List[Dict[str, str]]:
        """Parse exhibits section"""
        exhibits = []
        
        # Look for Section 3 - Exhibits
        section_match = re.search(
            r'Section 3.*?Exhibits(.*?)(?:</body>|</html>|$)',
            document_text,
            re.DOTALL | re.IGNORECASE
        )

        if not section_match:
            return exhibits

        section_text = section_match.group(1)

        # Find exhibit references
        exhibit_matches = re.findall(
            r'Exhibit\s+(\d+\.\d+)\s*[-–]\s*(.+?)(?:\n|<br|$)',
            section_text,
            re.IGNORECASE
        )

        for exhibit_num, description in exhibit_matches:
            exhibits.append({
                "exhibit_number": exhibit_num.strip(),
                "description": re.sub(r'<[^>]+>', '', description).strip()
            })

        return exhibits
