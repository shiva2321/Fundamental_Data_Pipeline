"""
SEC Miscellaneous Form Parsers
================================
Parsers for miscellaneous SEC forms and correspondence

CERT: Certification
CERTNYS: New York Stock Exchange Certification
CORRESP: Correspondence
IRANNOTICE: Iran Notice
NO ACT: Request for No-Action Letter
UPLOAD: General upload document

Author: SEC Filing Analysis System
Date: December 2025
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from Forms.baseParser import SECFormParser


class CERTParser(SECFormParser):
    """Parser for SEC CERT - Certification"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """
        Parse CERT document

        Args:
            document_text: Raw SEC document text

        Returns:
            Dictionary containing parsed form data
        """
        result = {
            "form_type": "CERT - Certification",
            "filing_info": self._parse_header(document_text),
            "certification_type": "",
            "certifying_person": {},
            "certification_text": "",
            "related_filing": ""
        }

        # Parse certification type
        result["certification_type"] = self._parse_certification_type(document_text)
        
        # Parse certifying person
        result["certifying_person"] = self._parse_certifying_person(document_text)
        
        # Parse certification text
        result["certification_text"] = self._parse_certification_text(document_text)
        
        # Parse related filing
        result["related_filing"] = self._parse_related_filing(document_text)

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
            ),
            "company_name": self._extract_field(header, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)')
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        """Extract field using regex pattern"""
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""

    def _parse_certification_type(self, document_text: str) -> str:
        """Parse certification type"""
        cert_types = {
            "Section 302": r'Section 302|Certification.*?Exchange Act',
            "Section 906": r'Section 906|18 U\.S\.C\. Section 1350',
            "Section 1350": r'Section 1350|Sarbanes-Oxley',
            "SOX": r'Sarbanes-Oxley',
            "CEO": r'Chief Executive Officer',
            "CFO": r'Chief Financial Officer'
        }

        for cert_type, pattern in cert_types.items():
            if re.search(pattern, document_text[:2000], re.IGNORECASE):
                return cert_type

        return "Unknown"

    def _parse_certifying_person(self, document_text: str) -> Dict[str, str]:
        """Parse information about the certifying person"""
        person_info = {}

        # Extract name
        name_patterns = [
            r'/s/\s*([A-Za-z\s\.]+)',
            r'By:\s*([A-Za-z\s\.]+)',
            r'Name:\s*([A-Za-z\s\.]+)'
        ]

        for pattern in name_patterns:
            match = re.search(pattern, document_text, re.IGNORECASE)
            if match:
                person_info["name"] = match.group(1).strip()
                break

        # Extract title
        title_patterns = [
            r'Title:\s*(.+?)(?:\n|$)',
            r'(Chief\s+(?:Executive|Financial)\s+Officer)',
            r'((?:President|Vice President|Secretary|Treasurer))'
        ]

        for pattern in title_patterns:
            match = re.search(pattern, document_text, re.IGNORECASE)
            if match:
                person_info["title"] = match.group(1).strip()
                break

        # Extract date
        date_match = re.search(
            r'Date:\s*([A-Za-z]+\s+\d+,\s*\d{4})',
            document_text,
            re.IGNORECASE
        )
        if date_match:
            person_info["date"] = date_match.group(1)

        return person_info

    def _parse_certification_text(self, document_text: str) -> str:
        """Parse the actual certification text"""
        # Look for "I certify" or similar language
        cert_match = re.search(
            r'I(?:,\s*[\w\s]+,)?\s+certify\s+that(.{0,1000}?)(?:Date:|/s/|$)',
            document_text,
            re.IGNORECASE | re.DOTALL
        )

        if cert_match:
            cert_text = re.sub(r'<[^>]+>', '', cert_match.group(1)).strip()
            cert_text = re.sub(r'\s+', ' ', cert_text)
            return cert_text[:1000]

        return ""

    def _parse_related_filing(self, document_text: str) -> str:
        """Parse related filing information"""
        # Look for Form 10-K, 10-Q reference
        form_match = re.search(
            r'Form\s+(10-K|10-Q).*?(?:for the|ended)\s+([A-Za-z]+\s+\d+,\s*\d{4})',
            document_text,
            re.IGNORECASE | re.DOTALL
        )

        if form_match:
            return f"{form_match.group(1)} for period ended {form_match.group(2)}"

        return ""


class CERTNYSParser(CERTParser):
    """Parser for SEC CERTNYS - New York Stock Exchange Certification"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse CERTNYS document"""
        result = super().parse(document_text)
        result["form_type"] = "CERTNYS - NYSE Certification"
        result["exchange"] = "New York Stock Exchange"
        return result


class CORRESPParser(SECFormParser):
    """Parser for SEC CORRESP - Correspondence"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """
        Parse CORRESP document

        Args:
            document_text: Raw SEC document text

        Returns:
            Dictionary containing parsed form data
        """
        result = {
            "form_type": "CORRESP - Correspondence",
            "filing_info": self._parse_header(document_text),
            "correspondence_type": "",
            "from_entity": "",
            "to_entity": "",
            "subject": "",
            "date": "",
            "content_summary": ""
        }

        # Parse correspondence details
        result["from_entity"] = self._parse_from_entity(document_text)
        result["to_entity"] = self._parse_to_entity(document_text)
        result["subject"] = self._parse_subject(document_text)
        result["date"] = self._parse_correspondence_date(document_text)
        result["content_summary"] = self._parse_content_summary(document_text)

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
            ),
            "company_name": self._extract_field(header, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)')
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        """Extract field using regex pattern"""
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""

    def _parse_from_entity(self, document_text: str) -> str:
        """Parse from entity"""
        from_patterns = [
            r'From:\s*(.+?)(?:\n|<)',
            r'(?:^|\n)([A-Z][A-Za-z\s,\.]+)(?:\n|<)'
        ]

        for pattern in from_patterns:
            match = re.search(pattern, document_text[:1000], re.MULTILINE)
            if match:
                return match.group(1).strip()

        return ""

    def _parse_to_entity(self, document_text: str) -> str:
        """Parse to entity"""
        # Usually SEC or specific division
        to_patterns = [
            r'To:\s*(.+?)(?:\n|<)',
            r'(?:Securities and Exchange Commission|SEC)',
            r'(?:Division of Corporation Finance)'
        ]

        for pattern in to_patterns:
            match = re.search(pattern, document_text[:1000], re.IGNORECASE)
            if match:
                return match.group(0).strip() if isinstance(match.group(0), str) else match.group(1).strip()

        return "SEC"

    def _parse_subject(self, document_text: str) -> str:
        """Parse subject line"""
        subject_patterns = [
            r'(?:Subject|Re):\s*(.+?)(?:\n\n|\n[A-Z])',
            r'(?:regarding|concerning)\s+(.+?)(?:\n|\.)'
        ]

        for pattern in subject_patterns:
            match = re.search(pattern, document_text[:2000], re.IGNORECASE | re.DOTALL)
            if match:
                return re.sub(r'<[^>]+>', '', match.group(1)).strip()[:200]

        return ""

    def _parse_correspondence_date(self, document_text: str) -> str:
        """Parse correspondence date"""
        date_match = re.search(
            r'([A-Za-z]+\s+\d+,\s*\d{4})',
            document_text[:1000],
            re.IGNORECASE
        )

        if date_match:
            return date_match.group(1)

        return ""

    def _parse_content_summary(self, document_text: str) -> str:
        """Parse content summary"""
        # Get first few paragraphs
        content_match = re.search(
            r'<TEXT>(.*?)</TEXT>',
            document_text,
            re.DOTALL
        )

        if content_match:
            content = re.sub(r'<[^>]+>', '', content_match.group(1)).strip()
            content = re.sub(r'\s+', ' ', content)
            return content[:500]

        return ""


class IRANNOTICEParser(SECFormParser):
    """Parser for SEC IRANNOTICE - Iran Notice"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse IRANNOTICE document"""
        result = {
            "form_type": "IRANNOTICE - Iran Notice",
            "filing_info": self._parse_header(document_text),
            "notice_type": "Iran Disclosure Notice",
            "content": ""
        }

        # Parse content
        content_match = re.search(
            r'<TEXT>(.*?)</TEXT>',
            document_text,
            re.DOTALL
        )

        if content_match:
            result["content"] = re.sub(r'<[^>]+>', '', content_match.group(1)).strip()[:1000]

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
            ),
            "company_name": self._extract_field(header, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)')
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        """Extract field using regex pattern"""
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""


class NOACTParser(SECFormParser):
    """Parser for SEC NO ACT - Request for No-Action Letter"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse NO ACT document"""
        result = {
            "form_type": "NO ACT - Request for No-Action Letter",
            "filing_info": self._parse_header(document_text),
            "request_summary": "",
            "requester": ""
        }

        # Parse request summary
        content_match = re.search(
            r'<TEXT>(.*?)</TEXT>',
            document_text,
            re.DOTALL
        )

        if content_match:
            result["request_summary"] = re.sub(r'<[^>]+>', '', content_match.group(1)).strip()[:800]

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
            ),
            "company_name": self._extract_field(header, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)')
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        """Extract field using regex pattern"""
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""


class UPLOADParser(SECFormParser):
    """Parser for SEC UPLOAD - General upload document"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse UPLOAD document"""
        result = {
            "form_type": "UPLOAD - General Document Upload",
            "filing_info": self._parse_header(document_text),
            "document_type": "",
            "content_summary": ""
        }

        # Try to determine document type from content
        if re.search(r'exhibit', document_text[:1000], re.IGNORECASE):
            result["document_type"] = "Exhibit"
        elif re.search(r'correspondence', document_text[:1000], re.IGNORECASE):
            result["document_type"] = "Correspondence"
        else:
            result["document_type"] = "General Document"

        # Parse content summary
        content_match = re.search(
            r'<TEXT>(.*?)</TEXT>',
            document_text,
            re.DOTALL
        )

        if content_match:
            result["content_summary"] = re.sub(r'<[^>]+>', '', content_match.group(1)).strip()[:500]

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
            ),
            "company_name": self._extract_field(header, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)')
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        """Extract field using regex pattern"""
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""
