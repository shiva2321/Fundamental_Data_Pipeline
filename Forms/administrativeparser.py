"""
SEC Administrative and Procedural Forms Parsers
================================================
Parsers for late filing notifications, withdrawals, and administrative filings

NT 10-K: Notification of inability to file 10-K on time
NT 10-Q: Notification of inability to file 10-Q on time
RW: Request for withdrawal of registration statement
EFFECT: Notice of effectiveness
12b-25: Notification of late filing

Author: SEC Filing Analysis System
Date: December 2025
"""

import re
from typing import Dict, Any
from Forms.baseParser import SECFormParser


class NT10KParser(SECFormParser):
    """Parser for NT 10-K - Notification of Late Filing (Annual Report)"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse NT 10-K document"""
        result = {
            "form_type": "NT 10-K - Notification of Late 10-K Filing",
            "filing_info": self._parse_header(document_text),
            "reason_for_delay": "",
            "anticipated_filing_date": "",
            "unable_to_file_reason": []
        }

        result["reason_for_delay"] = self._parse_reason(document_text)
        result["anticipated_filing_date"] = self._parse_anticipated_date(document_text)

        return result

    def _parse_header(self, document_text: str) -> Dict[str, str]:
        """Parse header"""
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
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""

    def _parse_reason(self, document_text: str) -> str:
        """Parse reason for delay"""
        reason_match = re.search(
            r'(?:Reason|Explanation).*?:(.{0,500}?)(?:\n\n|Anticipated|$)',
            document_text, re.IGNORECASE | re.DOTALL
        )
        if reason_match:
            return re.sub(r'<[^>]+>', '', reason_match.group(1)).strip()[:500]
        return ""

    def _parse_anticipated_date(self, document_text: str) -> str:
        """Parse anticipated filing date"""
        date_match = re.search(
            r'Anticipated.*?[Ff]iling.*?(\w+\s+\d+,\s*\d{4})',
            document_text, re.IGNORECASE
        )
        return date_match.group(1) if date_match else ""


class NT10QParser(SECFormParser):
    """Parser for NT 10-Q - Notification of Late Filing (Quarterly Report)"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse NT 10-Q document"""
        result = {
            "form_type": "NT 10-Q - Notification of Late 10-Q Filing",
            "filing_info": self._parse_header(document_text),
            "reason_for_delay": "",
            "anticipated_filing_date": ""
        }

        result["reason_for_delay"] = self._parse_reason(document_text)
        result["anticipated_filing_date"] = self._parse_anticipated_date(document_text)

        return result

    def _parse_header(self, document_text: str) -> Dict[str, str]:
        """Parse header"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}

        header = header_match.group(1)
        return {
            "accession_number": self._extract_field(header, r'ACCESSION NUMBER:\s*(\S+)'),
            "company_name": self._extract_field(header, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)')
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""

    def _parse_reason(self, document_text: str) -> str:
        """Parse reason for delay"""
        reason_match = re.search(
            r'(?:Reason|Explanation).*?:(.{0,500}?)(?:\n\n|Anticipated|$)',
            document_text, re.IGNORECASE | re.DOTALL
        )
        if reason_match:
            return re.sub(r'<[^>]+>', '', reason_match.group(1)).strip()[:500]
        return ""

    def _parse_anticipated_date(self, document_text: str) -> str:
        """Parse anticipated filing date"""
        date_match = re.search(
            r'Anticipated.*?[Ff]iling.*?(\w+\s+\d+,\s*\d{4})',
            document_text, re.IGNORECASE
        )
        return date_match.group(1) if date_match else ""


class RWParser(SECFormParser):
    """Parser for RW - Request for Withdrawal of Registration Statement"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse RW document"""
        result = {
            "form_type": "RW - Request for Withdrawal",
            "filing_info": self._parse_header(document_text),
            "file_number_to_withdraw": "",
            "reason_for_withdrawal": ""
        }

        result["file_number_to_withdraw"] = self._parse_file_number(document_text)
        result["reason_for_withdrawal"] = self._parse_reason(document_text)

        return result

    def _parse_header(self, document_text: str) -> Dict[str, str]:
        """Parse header"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}

        header = header_match.group(1)
        return {
            "accession_number": self._extract_field(header, r'ACCESSION NUMBER:\s*(\S+)'),
            "company_name": self._extract_field(header, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)')
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""

    def _parse_file_number(self, document_text: str) -> str:
        """Parse file number being withdrawn"""
        file_match = re.search(
            r'File\s+No\.\s*([\d-]+)',
            document_text, re.IGNORECASE
        )
        return file_match.group(1) if file_match else ""

    def _parse_reason(self, document_text: str) -> str:
        """Parse reason for withdrawal"""
        reason_match = re.search(
            r'Reason.*?:(.{0,500}?)(?:\n\n|$)',
            document_text, re.IGNORECASE | re.DOTALL
        )
        if reason_match:
            return re.sub(r'<[^>]+>', '', reason_match.group(1)).strip()[:500]
        return ""


class EFFECTParser(SECFormParser):
    """Parser for EFFECT - Notice of Effectiveness"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse EFFECT document"""
        result = {
            "form_type": "EFFECT - Notice of Effectiveness",
            "filing_info": self._parse_header(document_text),
            "effective_date": "",
            "file_number": ""
        }

        result["effective_date"] = self._parse_effective_date(document_text)
        result["file_number"] = self._parse_file_number(document_text)

        return result

    def _parse_header(self, document_text: str) -> Dict[str, str]:
        """Parse header"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}

        header = header_match.group(1)
        return {
            "accession_number": self._extract_field(header, r'ACCESSION NUMBER:\s*(\S+)'),
            "company_name": self._extract_field(header, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)')
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""

    def _parse_effective_date(self, document_text: str) -> str:
        """Parse effective date"""
        date_match = re.search(
            r'Effective.*?[Dd]ate.*?(\w+\s+\d+,\s*\d{4})',
            document_text, re.IGNORECASE
        )
        return date_match.group(1) if date_match else ""

    def _parse_file_number(self, document_text: str) -> str:
        """Parse file number"""
        file_match = re.search(
            r'File\s+No\.\s*([\d-]+)',
            document_text, re.IGNORECASE
        )
        return file_match.group(1) if file_match else ""


class Form12b25Parser(SECFormParser):
    """Parser for Form 12b-25 - Notification of Late Filing"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse Form 12b-25 document"""
        result = {
            "form_type": "12b-25 - Notification of Late Filing",
            "filing_info": self._parse_header(document_text),
            "form_being_reported": "",
            "reason_for_delay": "",
            "anticipated_filing_date": ""
        }

        result["form_being_reported"] = self._parse_form_type(document_text)
        result["reason_for_delay"] = self._parse_reason(document_text)
        result["anticipated_filing_date"] = self._parse_anticipated_date(document_text)

        return result

    def _parse_header(self, document_text: str) -> Dict[str, str]:
        """Parse header"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}

        header = header_match.group(1)
        return {
            "accession_number": self._extract_field(header, r'ACCESSION NUMBER:\s*(\S+)'),
            "company_name": self._extract_field(header, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)')
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""

    def _parse_form_type(self, document_text: str) -> str:
        """Parse which form is being reported as late"""
        form_patterns = ['10-K', '10-Q', '20-F', '11-K']
        for form in form_patterns:
            if re.search(rf'Form\s+{form}', document_text, re.IGNORECASE):
                return form
        return ""

    def _parse_reason(self, document_text: str) -> str:
        """Parse reason for delay"""
        reason_match = re.search(
            r'Part III.*?(.{0,800}?)(?:Part IV|$)',
            document_text, re.IGNORECASE | re.DOTALL
        )
        if reason_match:
            return re.sub(r'<[^>]+>', '', reason_match.group(1)).strip()[:800]
        return ""

    def _parse_anticipated_date(self, document_text: str) -> str:
        """Parse anticipated filing date"""
        date_match = re.search(
            r'anticipated.*?filing date.*?(\w+\s+\d+,\s*\d{4})',
            document_text, re.IGNORECASE
        )
        return date_match.group(1) if date_match else ""
