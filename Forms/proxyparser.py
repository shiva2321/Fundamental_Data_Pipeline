"""
SEC Proxy Statement Parsers
============================
Parsers for SEC Proxy Statements (Schedule 14A variants)

DEF 14A: Definitive Proxy Statement
DEFA14A: Definitive Additional Proxy Soliciting Materials
PX14A6G: Notice of Exempt Solicitation
PX14A6N: Notice to Exempt Solicitation

Author: SEC Filing Analysis System
Date: December 2025
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from Forms.baseParser import SECFormParser


class DEF14AParser(SECFormParser):
    """Parser for SEC DEF 14A - Definitive Proxy Statement"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """
        Parse DEF 14A document

        Args:
            document_text: Raw SEC document text

        Returns:
            Dictionary containing parsed form data
        """
        result = {
            "form_type": "DEF 14A - Definitive Proxy Statement",
            "filing_info": self._parse_header(document_text),
            "meeting_info": {},
            "proposals": [],
            "directors": [],
            "executive_compensation": {},
            "voting_securities": {}
        }

        # Parse meeting information
        result["meeting_info"] = self._parse_meeting_info(document_text)
        
        # Parse proposals
        result["proposals"] = self._parse_proposals(document_text)
        
        # Parse directors
        result["directors"] = self._parse_directors(document_text)
        
        # Parse compensation information
        result["executive_compensation"] = self._parse_compensation(document_text)
        
        # Parse voting securities
        result["voting_securities"] = self._parse_voting_securities(document_text)

        return result

    def _parse_header(self, document_text: str) -> Dict[str, str]:
        """Parse SEC document header information"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}

        header = header_match.group(1)

        return {
            "accession_number": self._extract_field(header, r'ACCESSION NUMBER:\s*(\S+)'),
            "submission_type": self._extract_field(header, r'CONFORMED SUBMISSION TYPE:\s*(.+)'),
            "public_document_count": self._extract_field(header, r'PUBLIC DOCUMENT COUNT:\s*(\d+)'),
            "filed_as_of_date": self.format_date(
                self._extract_field(header, r'FILED AS OF DATE:\s*(\d+)')
            ),
            "date_as_of_change": self.format_date(
                self._extract_field(header, r'DATE AS OF CHANGE:\s*(\d+)')
            ),
            "company_name": self._extract_field(header, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)')
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        """Extract field using regex pattern"""
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""

    def _parse_meeting_info(self, document_text: str) -> Dict[str, str]:
        """Parse annual meeting information"""
        meeting_info = {}

        # Extract meeting date
        date_patterns = [
            r'(?:Annual|Special)\s+Meeting.*?(?:to be held on|on)\s+([A-Za-z]+\s+\d+,\s*\d{4})',
            r'Meeting Date.*?(\w+\s+\d+,\s*\d{4})',
            r'(?:scheduled for|will be held on)\s+([A-Za-z]+\s+\d+,\s*\d{4})'
        ]

        for pattern in date_patterns:
            match = re.search(pattern, document_text, re.IGNORECASE | re.DOTALL)
            if match:
                meeting_info["meeting_date"] = match.group(1)
                break

        # Extract meeting time
        time_match = re.search(
            r'(?:at|@)\s+(\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?))',
            document_text[:5000],
            re.IGNORECASE
        )
        if time_match:
            meeting_info["meeting_time"] = time_match.group(1)

        # Extract meeting location/format
        location_patterns = [
            r'(?:Meeting Location|Location).*?:\s*(.{0,200}?)(?:\n\n|Record Date)',
            r'will be held\s+(?:at|virtually at)\s+(.{0,200}?)(?:\.|;|\n\n)',
            r'(?:virtually|online)\s+at\s+(https?://\S+)'
        ]

        for pattern in location_patterns:
            match = re.search(pattern, document_text[:5000], re.IGNORECASE | re.DOTALL)
            if match:
                meeting_info["meeting_location"] = re.sub(r'<[^>]+>', '', match.group(1)).strip()
                break

        # Extract record date
        record_match = re.search(
            r'Record Date.*?([A-Za-z]+\s+\d+,\s*\d{4})',
            document_text[:5000],
            re.IGNORECASE | re.DOTALL
        )
        if record_match:
            meeting_info["record_date"] = record_match.group(1)

        return meeting_info

    def _parse_proposals(self, document_text: str) -> List[Dict[str, str]]:
        """Parse meeting proposals"""
        proposals = []

        # Look for numbered proposals
        proposal_patterns = [
            r'(?:Proposal|Item)\s+(\d+)[\.:]\s*(.{0,300}?)(?:Proposal|Item|\n\n|Board Recommendation)',
            r'(\d+)\.\s+([A-Z][^\.]{20,200}?\.)\s*(?:The Board|FOR|AGAINST|\d+\.)'
        ]

        for pattern in proposal_patterns:
            matches = re.finditer(pattern, document_text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                proposal_num = match.group(1)
                proposal_text = re.sub(r'<[^>]+>', '', match.group(2)).strip()
                proposal_text = re.sub(r'\s+', ' ', proposal_text)
                
                if len(proposal_text) > 20:
                    # Try to find board recommendation
                    rec_pattern = rf'Proposal\s+{proposal_num}.*?(?:Board.*?recommends.*?(FOR|AGAINST|ABSTAIN)|recommends\s+a\s+vote\s+(FOR|AGAINST))'
                    rec_match = re.search(rec_pattern, document_text[:50000], re.IGNORECASE | re.DOTALL)
                    
                    recommendation = ""
                    if rec_match:
                        recommendation = (rec_match.group(1) or rec_match.group(2) or "").upper()
                    
                    proposals.append({
                        "proposal_number": proposal_num,
                        "description": proposal_text[:300],
                        "board_recommendation": recommendation
                    })

        return proposals[:20]  # Limit to first 20 proposals

    def _parse_directors(self, document_text: str) -> List[Dict[str, str]]:
        """Parse director nominee information"""
        directors = []

        # Look for director tables or lists
        # This is a simplified extraction - actual tables would need more complex parsing
        director_pattern = r'(?:Director|Nominee).*?([A-Z][a-z]+\s+[A-Z]\.?\s+[A-Z][a-z]+).*?Age\s+(\d{2})'
        
        matches = re.finditer(director_pattern, document_text, re.IGNORECASE)
        for match in matches:
            directors.append({
                "name": match.group(1),
                "age": match.group(2)
            })

        return directors[:30]  # Limit to first 30 directors

    def _parse_compensation(self, document_text: str) -> Dict[str, Any]:
        """Parse executive compensation information"""
        compensation = {
            "summary_compensation_table_present": False,
            "say_on_pay_vote": False
        }

        # Check for Summary Compensation Table
        if re.search(r'Summary Compensation Table', document_text, re.IGNORECASE):
            compensation["summary_compensation_table_present"] = True

        # Check for Say on Pay proposal
        if re.search(r'Say[- ]on[- ]Pay|advisory vote.*?compensation', document_text, re.IGNORECASE):
            compensation["say_on_pay_vote"] = True

        # Try to extract CD&A (Compensation Discussion and Analysis) section reference
        cda_match = re.search(r'Compensation Discussion and Analysis', document_text, re.IGNORECASE)
        if cda_match:
            compensation["compensation_discussion_present"] = True

        return compensation

    def _parse_voting_securities(self, document_text: str) -> Dict[str, str]:
        """Parse voting securities information"""
        voting_info = {}

        # Extract outstanding shares
        shares_pattern = r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s+(?:shares|Shares).*?outstanding'
        match = re.search(shares_pattern, document_text[:10000], re.IGNORECASE)
        if match:
            voting_info["outstanding_shares"] = match.group(1)

        # Extract voting record date
        record_pattern = r'(?:record date|entitled to vote).*?([A-Za-z]+\s+\d+,\s*\d{4})'
        match = re.search(record_pattern, document_text[:10000], re.IGNORECASE)
        if match:
            voting_info["record_date"] = match.group(1)

        return voting_info


class DEFA14AParser(DEF14AParser):
    """Parser for SEC DEFA14A - Definitive Additional Proxy Soliciting Materials"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse DEFA14A document"""
        result = super().parse(document_text)
        result["form_type"] = "DEFA14A - Definitive Additional Proxy Soliciting Materials"
        return result


class PX14A6GParser(SECFormParser):
    """Parser for SEC PX14A6G - Notice of Exempt Solicitation"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """
        Parse PX14A6G document

        Args:
            document_text: Raw SEC document text

        Returns:
            Dictionary containing parsed form data
        """
        result = {
            "form_type": "PX14A6G - Notice of Exempt Solicitation",
            "filing_info": self._parse_header(document_text),
            "soliciting_person": "",
            "subject_company": "",
            "proposals_addressed": []
        }

        # Parse soliciting person
        result["soliciting_person"] = self._extract_field(
            document_text,
            r'Name of Person Relying on Exemption.*?:\s*(.+)'
        )

        # Parse subject company
        result["subject_company"] = self._extract_field(
            document_text,
            r'Name of Issuer.*?:\s*(.+)'
        )

        # Extract proposal numbers addressed
        proposal_matches = re.findall(
            r'Proposal\s+(?:No\.\s*)?(\d+)',
            document_text,
            re.IGNORECASE
        )
        result["proposals_addressed"] = list(set(proposal_matches))[:10]

        return result

    def _parse_header(self, document_text: str) -> Dict[str, str]:
        """Parse SEC document header information"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}

        header = header_match.group(1)

        return {
            "accession_number": self._extract_field(header, r'ACCESSION NUMBER:\s*(\S+)'),
            "submission_type": self._extract_field(header, r'CONFORMED SUBMISSION TYPE:\s*(.+)'),
            "filed_as_of_date": self.format_date(
                self._extract_field(header, r'FILED AS OF DATE:\s*(\d+)')
            )
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        """Extract field using regex pattern"""
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""


class PX14A6NParser(PX14A6GParser):
    """Parser for SEC PX14A6N - Notice to Exempt Solicitation"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse PX14A6N document"""
        result = super().parse(document_text)
        result["form_type"] = "PX14A6N - Notice to Exempt Solicitation"
        return result
